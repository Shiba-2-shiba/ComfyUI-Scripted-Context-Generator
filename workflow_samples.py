import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "workflow_samples.json"


@dataclass(frozen=True)
class WorkflowSample:
    id: str
    path: Path
    surface: str
    recommended: bool
    expected_node_types: tuple[str, ...]


def load_workflow_samples() -> list[WorkflowSample]:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return [
        WorkflowSample(
            id=item["id"],
            path=ROOT / item["path"],
            surface=item["surface"],
            recommended=bool(item["recommended"]),
            expected_node_types=tuple(item["expected_node_types"]),
        )
        for item in payload
    ]


def get_recommended_workflow_sample() -> WorkflowSample:
    for sample in load_workflow_samples():
        if sample.recommended:
            return sample
    raise RuntimeError("No recommended workflow sample configured")
