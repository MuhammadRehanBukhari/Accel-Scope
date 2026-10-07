"""Choose an accelerator from measured, verified report data."""

from collections.abc import Mapping
import json
from pathlib import Path


def _positive_integer(value, name):
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer.")


def _validate_report(report):
    if (
        not isinstance(report, Mapping)
        or type(report.get("schema_version")) is not int
        or report["schema_version"] != 1
    ):
        raise ValueError("Unsupported comparison report schema.")

    expected_workload = {
        "matrix_shape": [4, 4],
        "input_bits": 8,
        "accumulator_bits": 18,
        "signed_inputs": True,
    }

    if report.get("workload") != expected_workload:
        raise ValueError(
            "The report must describe the supported signed 4x4 workload."
        )

    designs = report.get("architectures")
    if not isinstance(designs, Mapping) or not designs:
        raise ValueError("The report contains no architectures.")

    vectors = report.get("reference_vectors")
    if not isinstance(vectors, Mapping):
        raise ValueError(
            "The report is missing reference-vector information."
        )

    _positive_integer(vectors.get("case_count"), "reference case count")

    for name, data in designs.items():
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(data, Mapping)
        ):
            raise ValueError("Invalid architecture entry.")

        for field in (
            "compute_cycles",
            "generic_cells",
            "reference_cases",
        ):
            _positive_integer(data.get(field), f"{name}.{field}")

        if data["reference_cases"] != vectors["case_count"]:
            raise ValueError(
                f"{name}: reference case count does not match the report."
            )


def load_report(path):
    report = json.loads(
        Path(path).read_text(encoding="utf-8")
    )
    _validate_report(report)
    return report


def select_architecture(report, max_cycles, max_cells=None):
    """Minimize generic cells subject to inclusive cycle/cell limits."""

    _positive_integer(max_cycles, "max_cycles")

    if max_cells is not None:
        _positive_integer(max_cells, "max_cells")

    _validate_report(report)

    evaluations = []
    feasible = []

    for name, data in sorted(report["architectures"].items()):
        reasons = []

        if data.get("verification") != "passed":
            reasons.append(
                "Functional verification has not passed."
            )

        if data["compute_cycles"] > max_cycles:
            reasons.append(
                f"{data['compute_cycles']} compute cycles "
                f"exceeds the limit of {max_cycles}."
            )

        if (
            max_cells is not None
            and data["generic_cells"] > max_cells
        ):
            reasons.append(
                f"{data['generic_cells']} generic cells "
                f"exceeds the limit of {max_cells}."
            )

        entry = {
            "architecture": name,
            "compute_cycles": data["compute_cycles"],
            "generic_cells": data["generic_cells"],
            "eligible": not reasons,
            "reasons": reasons,
        }

        evaluations.append(entry)

        if not reasons:
            feasible.append(entry)

    feasible.sort(
        key=lambda entry: (
            entry["generic_cells"],
            entry["compute_cycles"],
            entry["architecture"],
        )
    )

    winner = feasible[0] if feasible else None

    return {
        "status": "selected" if winner else "no_feasible_design",
        "objective": "minimum_generic_cells",
        "constraints": {
            "max_compute_cycles": max_cycles,
            "max_generic_cells": max_cells,
        },
        "recommendation": (
            {
                key: winner[key]
                for key in (
                    "architecture",
                    "compute_cycles",
                    "generic_cells",
                )
            }
            if winner else None
        ),
        "evaluations": evaluations,
        "measurement_note": (
            "Uses saved processing-cycle and generic-synthesis measurements; "
            "physical clock speed, area, and power are unmeasured."
        ),
    }
