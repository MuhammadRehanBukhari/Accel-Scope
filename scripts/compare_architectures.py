"""Verify both accelerators and compare resources under one Yosys flow."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
BUILD = ROOT / "build/resources"

DESIGNS = {
    "sequential": ("accelscope_seq", "seq", "test_seq.cpp"),
    "parallel": ("accelscope_parallel", "parallel", "test_parallel.cpp"),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, log=None):
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr

    if log is not None:
        log.write_text(output, encoding="utf-8")

    if result.returncode:
        raise RuntimeError(
            f"Command failed: {command[0]}\n{output[-4000:]}"
        )

    return output.strip()


def cell_counts(path, top):
    design = json.loads(path.read_text())
    cells = design["modules"][top]["cells"]
    return Counter(cell["type"] for cell in cells.values())


def measure(name, top, folder, testbench, vectors, case_count):
    rtl = ROOT / "rtl" / f"{top}.v"
    bench = ROOT / "sim" / testbench
    executable = ROOT / "build" / folder / "obj" / f"V{top}"

    if not executable.is_file():
        raise RuntimeError(
            f"Missing simulation executable: {executable}"
        )

    if executable.stat().st_mtime < max(
        rtl.stat().st_mtime,
        bench.stat().st_mtime,
    ):
        raise RuntimeError(
            f"{name}: source changed; rebuild its simulation first."
        )

    output = run(
        [str(executable), str(vectors)],
        REPORTS / f"verification-{name}.txt",
    )

    cases = re.search(
        r"^PASS: (\d+) Python-reference cases$",
        output,
        re.M,
    )
    cycles = re.search(
        r"^Measured compute cycles per case: (\d+)$",
        output,
        re.M,
    )

    if not cases or not cycles or int(cases.group(1)) != case_count:
        raise RuntimeError(
            f"{name}: verification output was incomplete."
        )

    for status in (
        "PASS: input capture and ignored start while busy",
        "PASS: done pulse and output retention",
        "PASS: reset during processing and recovery",
    ):
        if status not in output:
            raise RuntimeError(
                f"{name}: missing control check: {status}"
            )

    operator_file = BUILD / f"{name}-operators.json"
    mapped_file = BUILD / f"{name}-mapped.json"

    flow = (
        f"read_verilog rtl/{top}.v; "
        f"hierarchy -check -top {top}; "
        "proc; opt; check -assert; "
        f"write_json build/resources/{name}-operators.json; "
        f"synth -top {top}; "
        "check -assert; "
        f"write_json build/resources/{name}-mapped.json"
    )

    print(f"Running Yosys for {name}...", flush=True)
    run(
        ["yosys", "-p", flow],
        BUILD / f"{name}-yosys.log",
    )

    operators = cell_counts(operator_file, top)
    mapped = cell_counts(mapped_file, top)

    if any(not kind.startswith("$_") for kind in mapped):
        raise RuntimeError(
            f"{name}: unmapped cells remain; inspect the Yosys log."
        )

    if any(kind.startswith("$_DLATCH") for kind in mapped):
        raise RuntimeError(
            f"{name}: unexpected latch found."
        )

    register_bits = sum(
        count
        for kind, count in mapped.items()
        if kind.startswith(("$_DFF", "$_SDFF", "$_ALDFF"))
    )

    return {
        "top_module": top,
        "verification": "passed",
        "reference_cases": int(cases.group(1)),
        "compute_cycles": int(cycles.group(1)),
        "high_level_multipliers": operators.get("$mul", 0),
        "generic_cells": sum(mapped.values()),
        "mapped_register_bits": register_bits,
        "mapped_cell_types": dict(sorted(mapped.items())),
        "rtl_sha256": sha256(rtl),
        "testbench_sha256": sha256(bench),
        "executable_sha256": sha256(executable),
        "synthesis_flow": flow,
    }


def main():
    REPORTS.mkdir(exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)

    vectors = ROOT / "build/seq/vectors.txt"
    case_count = sum(
        bool(line.strip())
        for line in vectors.read_text().splitlines()
    )

    if not case_count:
        raise RuntimeError("The reference vector file is empty.")

    report = {
        "schema_version": 1,
        "workload": {
            "matrix_shape": [4, 4],
            "input_bits": 8,
            "accumulator_bits": 18,
            "signed_inputs": True,
        },
        "measurement_basis": {
            "cycles": "Processing edges after input acceptance through done.",
            "resources": "Yosys default generic synthesis; no device library.",
            "limitations": (
                "No physical area, maximum clock speed, "
                "or power measurement."
            ),
        },
        "tools": {
            "python": sys.version.split()[0],
            "verilator": run(["verilator", "--version"]),
            "yosys": run(["yosys", "-V"]),
        },
        "reference_vectors": {
            "path": "build/seq/vectors.txt",
            "case_count": case_count,
            "sha256": sha256(vectors),
        },
        "architectures": {},
    }

    for name, (top, folder, bench) in DESIGNS.items():
        report["architectures"][name] = measure(
            name,
            top,
            folder,
            bench,
            vectors,
            case_count,
        )

    sequential = report["architectures"]["sequential"]
    parallel = report["architectures"]["parallel"]

    if (
        parallel["compute_cycles"] <= 0
        or sequential["generic_cells"] <= 0
    ):
        raise RuntimeError("Invalid cycle or resource measurement.")

    report["comparison"] = {
        "sequential_to_parallel_compute_cycle_ratio": (
            sequential["compute_cycles"] / parallel["compute_cycles"]
        ),
        "parallel_to_sequential_generic_cell_ratio": (
            parallel["generic_cells"] / sequential["generic_cells"]
        ),
    }

    destination = REPORTS / "architecture-comparison.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")

    print(
        "\nArchitecture  Cycles  Multipliers  Generic cells  Register bits"
    )

    for name, data in report["architectures"].items():
        print(
            f"{name:<13} {data['compute_cycles']:>6} "
            f"{data['high_level_multipliers']:>12} "
            f"{data['generic_cells']:>14} "
            f"{data['mapped_register_bits']:>14}"
        )

    ratio = report["comparison"][
        "sequential_to_parallel_compute_cycle_ratio"
    ]
    print(f"\nCompute-cycle ratio: {ratio:.2f}")
    print(f"Saved: {destination.relative_to(ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        raise SystemExit(f"ERROR: {error}")
