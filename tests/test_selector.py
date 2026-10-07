import copy
import unittest

from accelscope.selector import select_architecture


def example_report():
    return {
        "schema_version": 1,
        "workload": {
            "matrix_shape": [4, 4],
            "input_bits": 8,
            "accumulator_bits": 18,
            "signed_inputs": True,
        },
        "reference_vectors": {"case_count": 1006},
        "architectures": {
            "sequential": {
                "verification": "passed",
                "reference_cases": 1006,
                "compute_cycles": 16,
                "generic_cells": 1123,
            },
            "parallel": {
                "verification": "passed",
                "reference_cases": 1006,
                "compute_cycles": 4,
                "generic_cells": 3133,
            },
        },
    }


class TestSelector(unittest.TestCase):
    def setUp(self):
        self.report = example_report()

    def test_selects_smallest_feasible_design(self):
        result = select_architecture(self.report, 16)
        self.assertEqual(
            result["recommendation"]["architecture"],
            "sequential",
        )

    def test_tighter_cycle_limit_selects_parallel(self):
        result = select_architecture(self.report, 8)
        self.assertEqual(
            result["recommendation"]["architecture"],
            "parallel",
        )

    def test_exact_parallel_cycle_boundary_is_allowed(self):
        result = select_architecture(self.report, 4)
        self.assertEqual(
            result["recommendation"]["architecture"],
            "parallel",
        )

    def test_exact_sequential_cell_boundary_is_allowed(self):
        result = select_architecture(self.report, 16, 1123)
        self.assertEqual(
            result["recommendation"]["architecture"],
            "sequential",
        )

    def test_impossible_cycle_limit_has_no_recommendation(self):
        result = select_architecture(self.report, 3)
        self.assertEqual(result["status"], "no_feasible_design")
        self.assertIsNone(result["recommendation"])

    def test_combined_constraints_can_exclude_both(self):
        result = select_architecture(self.report, 8, 2000)
        self.assertEqual(result["status"], "no_feasible_design")
        self.assertTrue(
            all(
                not entry["eligible"]
                for entry in result["evaluations"]
            )
        )

    def test_cell_budget_below_smallest_design_is_infeasible(self):
        result = select_architecture(self.report, 16, 1122)
        self.assertIsNone(result["recommendation"])

    def test_unverified_design_cannot_be_selected(self):
        self.report["architectures"]["sequential"]["verification"] = "failed"

        result = select_architecture(self.report, 16)

        self.assertEqual(
            result["recommendation"]["architecture"],
            "parallel",
        )

        entry = next(
            item
            for item in result["evaluations"]
            if item["architecture"] == "sequential"
        )

        self.assertIn(
            "Functional verification has not passed.",
            entry["reasons"],
        )

    def test_invalid_cycle_limits_are_rejected(self):
        for value in (0, -1, True, 1.5, "16"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    select_architecture(self.report, value)

    def test_invalid_cell_limits_are_rejected(self):
        for value in (0, -1, True, 1.5, "1123"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    select_architecture(self.report, 16, value)

    def test_invalid_resource_measurement_is_rejected(self):
        self.report["architectures"]["sequential"]["generic_cells"] = -1

        with self.assertRaises(ValueError):
            select_architecture(self.report, 16)

    def test_mismatched_reference_case_count_is_rejected(self):
        self.report["architectures"]["parallel"]["reference_cases"] = 1

        with self.assertRaises(ValueError):
            select_architecture(self.report, 16)

    def test_equal_cell_counts_favor_fewer_cycles(self):
        self.report["architectures"]["parallel"]["generic_cells"] = 1123

        result = select_architecture(self.report, 16)

        self.assertEqual(
            result["recommendation"]["architecture"],
            "parallel",
        )

    def test_report_is_not_modified(self):
        before = copy.deepcopy(self.report)
        select_architecture(self.report, 8, 2000)
        self.assertEqual(self.report, before)


if __name__ == "__main__":
    unittest.main()
