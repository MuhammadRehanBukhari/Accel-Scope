# AccelScope

**Compare AI compute hardware designs, set resource limits, and verify custom inputs against a Python reference.**

Choosing more parallel hardware trades logic resources for fewer processing cycles. AccelScope makes that tradeoff visible with two working Verilog designs, repeatable simulation checks, generic synthesis measurements, and a local interactive interface. No physical FPGA is needed to run the prototype.

The current workload is a **4×4 matrix multiplied by a four-element vector**, using signed 8-bit weights and inputs with exact signed 18-bit outputs. This operation is a small building block used in AI computation. The prototype implements this kernel; it does not run an entire neural network.

## What you can do

- Compare a sequential implementation with a parallel implementation.
- Set a maximum processing-cycle count and an optional generic-cell budget.
- Select the design with the fewest generic cells among verified designs meeting every limit.
- See why each rejected design fails a constraint.
- Enter your own matrix and vector and run both compiled RTL simulations.
- Download the architecture decision and inspect the saved benchmark evidence.

## Verified local results

| Architecture | Compute cycles | High-level multipliers | Generic cells | Mapped register bits |
|---|---:|---:|---:|---:|
| Sequential | 16 | 1 | 1,123 | 256 |
| Parallel | 4 | 4 | 3,133 | 308 |

Both designs passed **1,006 Python-reference cases** in the local benchmark. The native testbenches also exercise input capture, ignored starts while busy, the completion pulse, output retention, and reset recovery. The Python reference and selector suite passed **27 tests**. A live test from the interface matched all four outputs for the example below.

These measurements were obtained with Verilator 5.020 and Yosys 0.33 on Ubuntu under WSL. The generated report records the tool versions, source fingerprints, reference-vector fingerprint, verification results, and synthesis flow. Generic cell counts can change with tool versions and synthesis settings.

**The parallel design uses one quarter of the compute cycles. This does not establish a fourfold improvement in elapsed time.** Clock frequency, physical chip area, power, FPGA resource utilization, and end-to-end throughput have not been measured. Generic cells are synthesis primitives, not a physical area measurement or a device-specific LUT count.

## Quick start: Ubuntu or Ubuntu in WSL

Use the Linux terminal for the Python environment and hardware tools.

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip verilator yosys g++ make
```

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/rebuild.py
python -m streamlit run app/main.py --server.address 127.0.0.1
```

Open **http://localhost:8501** in your browser. Keep the terminal running and use **Ctrl+C** to stop the server. On Windows, perform these commands inside Ubuntu WSL, then open the interface in the Windows browser.

`requirements.txt` pins the interface dependency. `requirements.lock.txt`, when present, records the resolved Python packages from the development environment. You can use `python -m pip install -r requirements.lock.txt` instead when reproducing that environment. Native tool versions are recorded separately in the benchmark report.

The rebuild command runs the Python tests, generates reference vectors, lints and compiles both designs, verifies the simulations, runs synthesis, and refreshes the report. Compiler logs are written to `build/logs/`. A failed stage stops the command.

## Try the demo

1. With a **16-cycle** limit and no cell budget, Sequential is recommended for the recorded measurements.
2. Change the limit to **8 cycles**: Parallel is recommended.
3. Add a **2,000-cell** budget: neither supported design satisfies both limits.
4. Open **Test your inputs** and run both hardware simulations using the example values.

```text
W = [[1, 2, 3, 4],
     [-1, -2, -3, -4],
     [1, 1, 1, 1],
     [2, 0, -2, 0]]
x = [1, 2, 3, 4]
y = [30, -30, 10, -4]
```

The interface validates integer inputs in the range **−128 to 127**. If the circuit source, testbench, or compiled executable differs from the saved report, the live test asks you to rebuild the evidence. A fresh clone needs a rebuild before native simulations are available; generated binaries are excluded from Git.

## Project structure

| Path | Purpose |
|---|---|
| `src/accelscope/reference.py` | Exact Python matrix-vector calculation and input validation |
| `src/accelscope/selector.py` | Report validation and constraint-based architecture selection |
| `rtl/accelscope_seq.v` | Sequential circuit with one data multiplier |
| `rtl/accelscope_parallel.v` | Circuit with four concurrent row multipliers |
| `sim/` | C++ Verilator testbenches |
| `tests/` | Python reference and selector tests |
| `scripts/rebuild.py` | Complete rebuild and verification command |
| `scripts/compare_architectures.py` | Native verification and Yosys resource comparison |
| `scripts/select_architecture.py` | Command-line architecture selection |
| `app/main.py` | Streamlit interface and custom-input simulation runner |
| `reports/` | Saved comparison and verification logs |
| `docs/` | Architecture, measurement, reproduction, and attribution notes |

## Command-line selection

```bash
python scripts/select_architecture.py --max-cycles 8
python scripts/select_architecture.py --max-cycles 8 --max-cells 2000
```

The first selects Parallel for the recorded benchmark. The second returns a no-feasible-design decision with reasons for both exclusions.

## Further reading

- [Architecture and measurement definitions](docs/architecture.md)
- [Reproduction and troubleshooting](docs/reproduce.md)
- [Third-party tools and AI assistance](docs/third-party.md)

## Current scope and next steps

The prototype compares two fixed architectures for one exact integer kernel. Device-specific FPGA mapping, timing analysis, power estimates, memory traffic, larger matrix sizes, and additional architectures are possible next steps. Each would need separate implementation and validation before being presented as measured capability.
