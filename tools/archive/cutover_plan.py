import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PLAN_PATH = ROOT / "cutover_plan.json"


@dataclass(frozen=True)
class CutoverGate:
    id: str
    description: str


@dataclass(frozen=True)
class CutoverNode:
    node_name: str
    module: str
    surface: str
    retirement_wave: int
    retirement_order: int
    successor: str
    workflow_ids: tuple[str, ...]
    gate_ids: tuple[str, ...]


def load_cutover_plan():
    payload = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    gates = tuple(CutoverGate(**item) for item in payload["gates"])
    nodes = tuple(
        CutoverNode(
            node_name=item["node_name"],
            module=item["module"],
            surface=item["surface"],
            retirement_wave=int(item["retirement_wave"]),
            retirement_order=int(item["retirement_order"]),
            successor=item["successor"],
            workflow_ids=tuple(item.get("workflow_ids", [])),
            gate_ids=tuple(item["gate_ids"]),
        )
        for item in payload["nodes"]
    )
    return {"gates": gates, "nodes": nodes}


def gate_map():
    return {gate.id: gate for gate in load_cutover_plan()["gates"]}


def node_map():
    return {node.node_name: node for node in load_cutover_plan()["nodes"]}
