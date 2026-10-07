"""AccelScope local hardware comparison workbench."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from accelscope.reference import matvec
from accelscope.selector import load_report, select_architecture

DESIGNS = {
    "sequential": ("accelscope_seq", "seq", "test_seq.cpp"),
    "parallel": ("accelscope_parallel", "parallel", "test_parallel.cpp"),
}

def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def live_test_issues(report):
    issues = []
    for name, (top, folder, bench) in DESIGNS.items():
        data = report["architectures"].get(name, {})
        files = (
            (ROOT / "rtl" / f"{top}.v", "rtl_sha256"),
            (ROOT / "sim" / bench, "testbench_sha256"),
            (ROOT / "build" / folder / "obj" / f"V{top}", "executable_sha256"),
        )
        if data.get("verification") != "passed":
            issues.append(f"{name.title()}: benchmark verification is unavailable.")
        for path, key in files:
            if not path.is_file():
                issues.append(f"{name.title()}: {path.name} is unavailable.")
            elif fingerprint(path) != data.get(key):
                issues.append(f"{name.title()}: {path.name} differs from the benchmark.")
    return issues

def run_live_test(report, weights, vector):
    expected = matvec(weights, vector)
    issues = live_test_issues(report)
    if issues:
        raise ValueError("Live test unavailable: " + " ".join(issues))
    destination = ROOT / "build/ui-tests"
    destination.mkdir(parents=True, exist_ok=True)
    results = {}
    with tempfile.TemporaryDirectory(dir=destination) as temporary:
        case_file = Path(temporary) / "custom.txt"
        values = [value for row in weights for value in row] + vector + expected
        case_file.write_text(
            "custom " + " ".join(map(str, values)) + "\n", encoding="utf-8"
        )
        for name, (top, folder, _) in DESIGNS.items():
            executable = ROOT / "build" / folder / "obj" / f"V{top}"
            completed = subprocess.run(
                [str(executable), str(case_file)],
                cwd=ROOT, capture_output=True, text=True, timeout=20,
            )
            log = completed.stdout + completed.stderr
            if completed.returncode:
                raise RuntimeError(f"{name.title()} simulation failed:\n{log[-2000:]}")
            if "PASS: 1 Python-reference cases" not in log.splitlines():
                raise RuntimeError(f"{name.title()}: custom-case verification was missing.")
            cycles = re.search(
                r"^Measured compute cycles per case: (\d+)$", log, re.M
            )
            if not cycles or int(cycles.group(1)) != report["architectures"][name]["compute_cycles"]:
                raise RuntimeError(f"{name.title()}: cycle count differs from the benchmark.")
            results[name] = {"cycles": int(cycles.group(1)), "log": log}
    return expected, results

st.set_page_config(page_title="AccelScope", page_icon="⚙️", layout="wide")
st.title("AccelScope")
st.caption("A verified AI hardware workbench · compare designs, set limits, test inputs")

try:
    report = load_report(ROOT / "reports/architecture-comparison.json")
except (OSError, ValueError) as error:
    st.error(f"The benchmark report could not be loaded: {error}")
    st.stop()

with st.sidebar:
    st.header("Design constraints")
    max_cycles = int(st.number_input(
        "Maximum processing cycles", min_value=1, value=16, step=1,
        key="max_cycles",
    ))
    use_cells = st.checkbox("Apply a generic-cell budget", key="use_cells")
    cell_value = int(st.number_input(
        "Maximum generic cells", min_value=1, value=4000, step=100,
        disabled=not use_cells, key="max_cells",
    ))
    max_cells = cell_value if use_cells else None
    st.caption(
        "Limits include their boundary values. The selector minimizes generic "
        "cells among verified designs that meet every limit."
    )

decision = select_architecture(report, max_cycles, max_cells)
designs = report["architectures"]
verified_count = sum(data.get("verification") == "passed" for data in designs.values())

summary = st.columns(3)
summary[0].metric("Verified designs", verified_count)
summary[1].metric("Reference cases per design", report["reference_vectors"]["case_count"])
summary[2].metric("Compute workload", "4 × 4 · signed 8-bit")

selection_tab, test_tab, evidence_tab = st.tabs(
    ["Choose a design", "Test your inputs", "Benchmark evidence"]
)

with selection_tab:
    winner = decision["recommendation"]
    if winner:
        st.success(f"Recommended architecture: {winner['architecture'].title()}")
        metrics = st.columns(2)
        metrics[0].metric("Processing cycles", winner["compute_cycles"])
        metrics[1].metric("Generic cells", f"{winner['generic_cells']:,}")
    else:
        st.warning("No supported design meets every limit. Review the reasons below.")

    rows = [
        {
            "Architecture": entry["architecture"].title(),
            "Processing cycles": entry["compute_cycles"],
            "Generic cells": entry["generic_cells"],
            "Eligible": entry["eligible"],
            "Explanation": " ".join(entry["reasons"]) or "Meets every limit.",
        }
        for entry in decision["evaluations"]
    ]
    st.dataframe(rows, hide_index=True, width="stretch")

    chart_data = [
        {
            "Architecture": name.title(),
            "Generic cells": data["generic_cells"],
            "Processing cycles": data["compute_cycles"],
        }
        for name, data in designs.items()
    ]
    charts = st.columns(2)
    with charts[0]:
        st.subheader("Logic resources")
        st.bar_chart(chart_data, x="Architecture", y="Generic cells", height=260)
    with charts[1]:
        st.subheader("Processing cycles")
        st.bar_chart(chart_data, x="Architecture", y="Processing cycles", height=260)

    st.download_button(
        "Export decision JSON",
        data=json.dumps(decision, indent=2),
        file_name="accelscope-decision.json",
        mime="application/json",
    )

with test_tab:
    st.subheader("Run a calculation through both circuits")
    st.caption(
        "Enter integer values from -128 to 127. Weights must contain four rows "
        "of four values; the input vector must contain four values."
    )
    editors = st.columns(2)
    with editors[0]:
        weights_text = st.text_area(
            "Weights W",
            value="[\n  [1, 2, 3, 4],\n  [-1, -2, -3, -4],\n  [1, 1, 1, 1],\n  [2, 0, -2, 0]\n]",
            height=180, key="weights",
        )
    with editors[1]:
        vector_text = st.text_area(
            "Input vector x", value="[1, 2, 3, 4]", height=100, key="vector",
        )
    valid_inputs = False
    try:
        weights = json.loads(weights_text)
        vector = json.loads(vector_text)
        expected = matvec(weights, vector)
        valid_inputs = True
        st.write("Python reference outputs")
        st.dataframe(
            [{"Output": f"y{row}", "Value": value} for row, value in enumerate(expected)],
            hide_index=True,
        )
    except (ValueError, TypeError) as error:
        st.error(f"Invalid input: {error}")

    issues = live_test_issues(report)
    if issues:
        st.info("Live simulation is unavailable. Saved benchmark comparisons remain available.")
        with st.expander("Live simulation availability"):
            for issue in issues:
                st.write(issue)

    if st.button(
        "Run both hardware simulations",
        type="primary", disabled=not valid_inputs or bool(issues),
        key="run_hardware",
    ):
        try:
            with st.spinner("Checking both simulated circuits against Python..."):
                expected, results = run_live_test(report, weights, vector)
            st.success("Both simulated hardware designs matched all four Python outputs.")
            st.dataframe(
                [
                    {
                        "Architecture": name.title(),
                        "Custom input": "Passed",
                        "Processing cycles": data["cycles"],
                    }
                    for name, data in results.items()
                ],
                hide_index=True,
            )
            with st.expander("Simulation verification logs"):
                for name, data in results.items():
                    st.write(name.title())
                    st.code(data["log"], language="text")
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            st.error(str(error))

with evidence_tab:
    st.subheader("Saved benchmark results")
    st.dataframe(
        [
            {
                "Architecture": name.title(),
                "Verification": data["verification"],
                "Reference cases": data["reference_cases"],
                "Processing cycles": data["compute_cycles"],
                "Multiplier operators": data["high_level_multipliers"],
                "Generic cells": data["generic_cells"],
                "Register bits": data["mapped_register_bits"],
            }
            for name, data in designs.items()
        ],
        hide_index=True, width="stretch",
    )
    st.write("Tool versions")
    st.json(report["tools"])
    st.download_button(
        "Download benchmark report",
        data=json.dumps(report, indent=2),
        file_name="architecture-comparison.json",
        mime="application/json",
    )
    with st.expander("How the architectures work"):
        st.write(
            "**Sequential:** one multiplier and accumulator process the rows in order. "
            "**Parallel:** four multiplier/accumulator units process four rows simultaneously."
        )

st.divider()
st.caption(
    "Processing cycles count edges after input acceptance through completion. "
    "Resource counts come from generic Yosys synthesis. Physical clock speed, "
    "chip area, and power consumption have not been measured."
)
