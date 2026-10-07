"""Select a verified accelerator under processing-cycle and cell limits."""

import argparse
import json
from pathlib import Path

from accelscope.selector import load_report, select_architecture

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--max-cycles", type=int, required=True)
    parser.add_argument("--max-cells", type=int, default=None)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports/architecture-comparison.json",
    )

    args = parser.parse_args()

    try:
        report = load_report(args.report)
        result = select_architecture(
            report,
            args.max_cycles,
            args.max_cells,
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
