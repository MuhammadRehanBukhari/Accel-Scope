#include "Vaccelscope_seq.h"
#include "verilated.h"

#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

static void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

static void tick(Vaccelscope_seq& dut) {
    dut.clk = 0;
    dut.eval();
    dut.clk = 1;
    dut.eval();
    dut.clk = 0;
    dut.eval();
}

static void clear_inputs(Vaccelscope_seq& dut) {
    for (int word = 0; word < 4; ++word) {
        dut.weights[word] = 0;
    }
    dut.x_vec = 0;
}

static void load_inputs(
    Vaccelscope_seq& dut,
    const std::array<int, 16>& weights,
    const std::array<int, 4>& vector
) {
    clear_inputs(dut);

    for (int index = 0; index < 16; ++index) {
        const uint32_t byte = static_cast<uint8_t>(weights[index]);
        dut.weights[index / 4] |= byte << (8 * (index % 4));
    }

    for (int index = 0; index < 4; ++index) {
        const uint32_t byte = static_cast<uint8_t>(vector[index]);
        dut.x_vec |= byte << (8 * index);
    }
}

static int32_t read_output(const Vaccelscope_seq& dut, int row) {
    const unsigned offset = static_cast<unsigned>(18 * row);
    const unsigned word = offset / 32;
    const unsigned shift = offset % 32;

    const uint64_t pair = static_cast<uint64_t>(dut.y[word])
        | (static_cast<uint64_t>(dut.y[word + 1]) << 32);

    const uint32_t raw =
        static_cast<uint32_t>((pair >> shift) & 0x3ffffu);

    int32_t value = static_cast<int32_t>(raw);

    if (raw & 0x20000u) {
        value -= 0x40000;
    }

    return value;
}

static void check_outputs(
    const Vaccelscope_seq& dut,
    const std::array<int, 4>& expected,
    const std::string& name
) {
    for (int row = 0; row < 4; ++row) {
        const int32_t actual = read_output(dut, row);

        require(
            actual == expected[row],
            name + ": output " + std::to_string(row)
            + " expected " + std::to_string(expected[row])
            + ", received " + std::to_string(actual)
        );
    }
}

static void run_case(
    Vaccelscope_seq& dut,
    const std::array<int, 16>& weights,
    const std::array<int, 4>& vector,
    const std::array<int, 4>& expected,
    const std::string& name
) {
    require(!dut.busy && !dut.done, name + ": circuit was not idle");

    load_inputs(dut, weights, vector);
    dut.start = 1;
    tick(dut);

    require(dut.busy && !dut.done, name + ": start was not accepted");

    // Changing external inputs must not affect captured inputs.
    clear_inputs(dut);

    for (int cycle = 1; cycle <= 16; ++cycle) {
        // Start requests during processing must be ignored.
        dut.start = (cycle == 4) ? 1 : 0;
        tick(dut);

        if (cycle < 16) {
            require(
                dut.busy && !dut.done,
                name + ": completion occurred too early"
            );
        } else {
            require(
                !dut.busy && dut.done,
                name + ": completion did not occur after 16 compute cycles"
            );
        }
    }

    check_outputs(dut, expected, name);

    dut.start = 0;
    tick(dut);

    require(!dut.busy && !dut.done, name + ": done did not clear");
    check_outputs(dut, expected, name + " retained");
}

int main(int argc, char** argv) {
    try {
        require(argc == 2, "Usage: Vaccelscope_seq <vectors.txt>");
        Verilated::commandArgs(argc, argv);

        std::ifstream input(argv[1]);
        require(input.is_open(), "Could not open the vector file");

        Vaccelscope_seq dut;
        dut.clk = 0;
        dut.start = 0;
        clear_inputs(dut);

        dut.rst = 1;
        tick(dut);
        dut.rst = 0;
        tick(dut);

        require(!dut.busy && !dut.done, "Initial reset failed");
        require(
            dut.y[0] == 0 && dut.y[1] == 0 && dut.y[2] == 0,
            "Initial reset did not clear outputs"
        );

        int case_count = 0;
        std::string name;

        while (input >> name) {
            std::array<int, 16> weights{};
            std::array<int, 4> vector{};
            std::array<int, 4> expected{};

            for (int& value : weights) {
                require(
                    static_cast<bool>(input >> value),
                    name + ": invalid weights"
                );
            }

            for (int& value : vector) {
                require(
                    static_cast<bool>(input >> value),
                    name + ": invalid vector"
                );
            }

            for (int& value : expected) {
                require(
                    static_cast<bool>(input >> value),
                    name + ": invalid expected output"
                );
            }

            run_case(dut, weights, vector, expected, name);
            ++case_count;
        }

        require(case_count > 0, "The vector file was empty");

        const std::array<int, 16> identity{
            1, 0, 0, 0, 0, 1, 0, 0,
            0, 0, 1, 0, 0, 0, 0, 1
        };
        const std::array<int, 4> recovery{-128, -1, 0, 127};

        // Reset must abort processing and clear a nonzero partial result.
        load_inputs(dut, identity, recovery);
        dut.start = 1;
        tick(dut);
        dut.start = 0;

        for (int cycle = 0; cycle < 5; ++cycle) {
            tick(dut);
        }

        require(
            dut.busy && !dut.done,
            "Reset test did not enter processing"
        );
        require(
            read_output(dut, 0) == -128,
            "Reset test lacked a nonzero partial output"
        );

        dut.rst = 1;
        tick(dut);

        require(
            !dut.busy && !dut.done,
            "Reset did not abort processing"
        );
        require(
            dut.y[0] == 0 && dut.y[1] == 0 && dut.y[2] == 0,
            "Reset did not clear partial outputs"
        );

        dut.rst = 0;
        tick(dut);

        // A fresh calculation must work after an interrupted one.
        run_case(dut, identity, recovery, recovery, "reset_recovery");

        dut.final();

        std::cout
            << "PASS: " << case_count << " Python-reference cases\n"
            << "PASS: input capture and ignored start while busy\n"
            << "PASS: done pulse and output retention\n"
            << "PASS: reset during processing and recovery\n"
            << "Measured compute cycles per case: 16\n";

        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << "\n";
        return 1;
    }
}
