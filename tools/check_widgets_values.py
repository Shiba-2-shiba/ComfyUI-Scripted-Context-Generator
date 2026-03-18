import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from workflow_samples import load_workflow_samples
from workflow_class_map import build_class_map_for_samples
from workflow_widget_validation import load_workflow, validate_workflow_roundtrip, validate_workflow_widgets


def main():
    workflow_samples = load_workflow_samples()
    class_map = build_class_map_for_samples(workflow_samples)
    any_problems = False

    for sample in workflow_samples:
        wf = load_workflow(sample.path)
        nodes = wf.get("nodes", [])
        problems = []

        for node in nodes:
            ntype = node.get("type")
            cls = class_map.get(ntype)
            if not cls:
                continue
            widget_issues = validate_workflow_widgets({"nodes": [node]}, class_map)
            roundtrip_issues = validate_workflow_roundtrip({"nodes": [node]}, class_map)
            if widget_issues or roundtrip_issues:
                issue_bucket = []
                widget_seq = []
                widget_vals = node.get("widgets_values")
                if widget_issues:
                    _, _, issues, widget_seq, widget_vals = widget_issues[0]
                    issue_bucket.extend(issues)
                if roundtrip_issues:
                    _, _, issues, widget_seq, widget_vals, _serialized_values = roundtrip_issues[0]
                    issue_bucket.extend(issues)
                problems.append((node.get("id"), ntype, issue_bucket, widget_seq, widget_vals))

        if not problems:
            print(f"OK: no widget_values issues detected for {sample.path.name} [{sample.surface}].")
            continue

        any_problems = True
        print(f"Detected widget_values issues in {sample.path.name} [{sample.surface}]:")
        for node_id, ntype, issues, widget_seq, widget_vals in problems:
            print(f"- Node {node_id} ({ntype})")
            print(f"  widgets_values: {widget_vals}")
            print(f"  expected widgets: {[name for name, _, _ in widget_seq]}")
            for issue in issues:
                print(f"  - {issue}")

    if any_problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
