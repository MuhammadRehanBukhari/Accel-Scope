"""Generate exact Python reference cases for the sequential RTL simulation."""

import argparse
from pathlib import Path
import random

from accelscope.reference import matvec


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/seq/vectors.txt"),
    )
    parser.add_argument("--random-cases", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    if args.random_cases < 0:
        parser.error("--random-cases must be nonnegative")

    sample = [
        [1, 2, 3, 4],
        [-1, -2, -3, -4],
        [1, 1, 1, 1],
        [2, 0, -2, 0],
    ]
    identity = [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ]

    cases = [
        ("example", sample, [1, 2, 3, 4]),
        ("zero", sample, [0, 0, 0, 0]),
        ("identity", identity, [-128, -1, 0, 127]),
        ("max_positive", [[-128] * 4 for _ in range(4)], [-128] * 4),
        ("most_negative", [[-128] * 4 for _ in range(4)], [127] * 4),
        ("cancellation", [[127, 127, -127, -127]] * 4, [127] * 4),
    ]

    rng = random.Random(args.seed)

    for index in range(args.random_cases):
        weights = [
            [rng.randint(-128, 127) for _ in range(4)]
            for _ in range(4)
        ]
        vector = [rng.randint(-128, 127) for _ in range(4)]
        cases.append((f"random_{index:04d}", weights, vector))

    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", encoding="utf-8") as output:
        for name, weights, vector in cases:
            flat = [value for row in weights for value in row]
            values = flat + vector + matvec(weights, vector)
            output.write(
                name + " " + " ".join(map(str, values)) + "\n"
            )

    print(f"Generated {len(cases)} cases: {args.output}")
    print(f"Random seed: {args.seed}")


if __name__ == "__main__":
    main()
