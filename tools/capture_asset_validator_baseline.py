from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from asset_validator import validate_assets


DEFAULT_OUTPUT = PROJECT_ROOT / "assets" / "results" / "asset_validator_baseline.txt"


def build_validator_baseline_text(warnings: list[str]) -> str:
    lines = [f"warning_count: {len(warnings)}"]
    lines.extend(warnings)
    return "\n".join(lines) + "\n"


def capture_validator_baseline(output_path: Path = DEFAULT_OUTPUT) -> Path:
    warnings = validate_assets()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_validator_baseline_text(warnings), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture the current asset validator warnings into a repeatable baseline artifact."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to the baseline artifact to write.",
    )
    args = parser.parse_args()

    output_path = capture_validator_baseline(args.output)
    warning_count = len(validate_assets())
    print(f"Wrote {warning_count} validator warnings to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
