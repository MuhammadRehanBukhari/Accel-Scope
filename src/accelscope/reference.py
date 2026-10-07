"""Exact integer reference for AccelScope's 4x4 matrix-vector calculation."""

from collections.abc import Sequence

DIM = 4
INPUT_BITS = 8
ACCUM_BITS = 18
INPUT_MIN = -(1 << (INPUT_BITS - 1))
INPUT_MAX = (1 << (INPUT_BITS - 1)) - 1


def _check_sequence(value: object, name: str) -> None:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence such as a list or tuple.")


def _check_input(value: object, name: str) -> None:
    if type(value) is not int:
        raise TypeError(
            f"{name} must be a Python integer; booleans are not accepted."
        )
    if not INPUT_MIN <= value <= INPUT_MAX:
        raise ValueError(
            f"{name} must be between {INPUT_MIN} and {INPUT_MAX}."
        )


def matvec(
    weights: Sequence[Sequence[int]],
    vector: Sequence[int],
) -> list[int]:
    """Return W*x, with signed 8-bit inputs and exact, unrounded sums.

    There is no bias, activation, scaling, saturation, or wrapping.
    Inputs are validated before arithmetic and are never modified.
    """
    _check_sequence(weights, "weights")
    _check_sequence(vector, "vector")

    if len(weights) != DIM:
        raise ValueError(f"weights must have exactly {DIM} rows.")

    if len(vector) != DIM:
        raise ValueError(f"vector must have exactly {DIM} values.")

    for column, value in enumerate(vector):
        _check_input(value, f"vector[{column}]")

    for row_index, row in enumerate(weights):
        _check_sequence(row, f"weights[{row_index}]")

        if len(row) != DIM:
            raise ValueError(
                f"weights[{row_index}] must have exactly {DIM} values."
            )

        for column, value in enumerate(row):
            _check_input(value, f"weights[{row_index}][{column}]")

    return [
        sum(
            weights[row][column] * vector[column]
            for column in range(DIM)
        )
        for row in range(DIM)
    ]
