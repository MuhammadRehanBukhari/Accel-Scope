import copy
import unittest

from accelscope.reference import ACCUM_BITS, matvec


class TestMatvec(unittest.TestCase):
    def setUp(self):
        self.weights = [
            [1, 2, 3, 4],
            [-1, -2, -3, -4],
            [1, 1, 1, 1],
            [2, 0, -2, 0],
        ]
        self.vector = [1, 2, 3, 4]

    def test_hand_calculated_example(self):
        self.assertEqual(
            matvec(self.weights, self.vector),
            [30, -30, 10, -4],
        )

    def test_identity_preserves_vector(self):
        identity = [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ]
        self.assertEqual(
            matvec(identity, [-128, -1, 0, 127]),
            [-128, -1, 0, 127],
        )

    def test_zero_vector(self):
        self.assertEqual(
            matvec(self.weights, [0, 0, 0, 0]),
            [0, 0, 0, 0],
        )

    def test_largest_positive_sum(self):
        self.assertEqual(
            matvec([[-128] * 4 for _ in range(4)], [-128] * 4),
            [65536] * 4,
        )
        self.assertLess(65536, 1 << (ACCUM_BITS - 1))

    def test_most_negative_sum(self):
        self.assertEqual(
            matvec([[-128] * 4 for _ in range(4)], [127] * 4),
            [-65024] * 4,
        )

    def test_positive_and_negative_products_cancel(self):
        self.assertEqual(
            matvec([[127, 127, -127, -127]] * 4, [127] * 4),
            [0] * 4,
        )

    def test_wrong_matrix_row_count(self):
        with self.assertRaises(ValueError):
            matvec(self.weights[:3], self.vector)

    def test_ragged_matrix(self):
        self.weights[2] = [1, 2, 3]
        with self.assertRaises(ValueError):
            matvec(self.weights, self.vector)

    def test_wrong_vector_length(self):
        with self.assertRaises(ValueError):
            matvec(self.weights, [1, 2, 3])

    def test_out_of_range_inputs(self):
        for invalid in (-129, 128):
            with self.subTest(location="vector", value=invalid):
                with self.assertRaises(ValueError):
                    matvec(self.weights, [invalid, 0, 0, 0])

            with self.subTest(location="weights", value=invalid):
                weights = copy.deepcopy(self.weights)
                weights[0][0] = invalid
                with self.assertRaises(ValueError):
                    matvec(weights, self.vector)

    def test_non_integer_inputs(self):
        for invalid in (True, 1.5, "1"):
            with self.subTest(value=invalid):
                with self.assertRaises(TypeError):
                    matvec(self.weights, [invalid, 0, 0, 0])

    def test_non_sequence_inputs(self):
        with self.assertRaises(TypeError):
            matvec(None, self.vector)

        with self.assertRaises(TypeError):
            matvec(self.weights, "1234")

    def test_inputs_are_not_modified(self):
        weights_before = copy.deepcopy(self.weights)
        vector_before = self.vector.copy()

        matvec(self.weights, self.vector)

        self.assertEqual(self.weights, weights_before)
        self.assertEqual(self.vector, vector_before)


if __name__ == "__main__":
    unittest.main()
