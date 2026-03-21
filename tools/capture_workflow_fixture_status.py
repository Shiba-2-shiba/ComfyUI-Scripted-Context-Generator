from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from workflow_class_map import build_class_map_for_samples
from workflow_samples import load_workflow_samples
from workflow_widget_validation import load_workflow, validate_workflow_roundtrip, validate_workflow_widgets


DEFAULT_OUTPUT = PROJECT_ROOT / "assets" / "results" / "workflow_fixture_status.txt"


def collect_workflow_fixture_status() -> list[dict[str, object]]:
    samples = load_workflow_samples()
    class_map = build_class_map_for_samples(samples)
    status_rows: list[dict[str, object]] = []

    for sample in samples:
        workflow = load_workflow(sample.path)
        widget_problems = validate_workflow_widgets(workflow, class_map)
        roundtrip_problems = validate_workflow_roundtrip(workflow, class_map)
        status_rows.append(
            {
                "id": sample.id,
                "surface": sample.surface,
                "path": str(sample.path.relative_to(PROJECT_ROOT)),
                "node_count": len(workflow.get("nodes", [])),
                "widget_status": "ok" if not widget_problems else f"problems:{len(widget_problems)}",
                "roundtrip_status": "ok" if not roundtrip_problems else f"problems:{len(roundtrip_problems)}",
            }
        )

    return status_rows


def build_workflow_fixture_status_text(status_rows: list[dict[str, object]]) -> str:
    lines = [f"sample_count: {len(status_rows)}"]
    for row in status_rows:
        lines.append(
            (
                f"{row['id']}|surface={row['surface']}|nodes={row['node_count']}|"
                f"widgets={row['widget_status']}|roundtrip={row['roundtrip_status']}|path={row['path']}"
            )
        )
    return "\n".join(lines) + "\n"


def capture_workflow_fixture_status(output_path: Path = DEFAULT_OUTPUT) -> Path:
    status_rows = collect_workflow_fixture_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_workflow_fixture_status_text(status_rows), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture the current workflow fixture load/widget/roundtrip status into a repeatable artifact."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to the workflow fixture status artifact to write.",
    )
    args = parser.parse_args()

    output_path = capture_workflow_fixture_status(args.output)
    print(f"Wrote workflow fixture status to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
