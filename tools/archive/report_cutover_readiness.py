import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.archive.cutover_plan import load_cutover_plan
from workflow_widget_validation import load_workflow
from workflow_samples import load_workflow_samples


def sample_node_types():
    result = {}
    for sample in load_workflow_samples():
        workflow = load_workflow(sample.path)
        result[sample.id] = {
            "surface": sample.surface,
            "recommended": sample.recommended,
            "path": sample.path.name,
            "node_types": {node.get("type") for node in workflow.get("nodes", [])},
        }
    return result


def automated_blockers(node, samples):
    blockers = []
    referenced_samples = [
        sample_id
        for sample_id in node.workflow_ids
        if node.node_name in samples[sample_id]["node_types"]
    ]

    if referenced_samples and "compat_sample_not_required" in node.gate_ids:
        blockers.append(
            "compat regression fixture still references node via: "
            + ", ".join(
                f"{sample_id} ({samples[sample_id]['path']})"
                for sample_id in referenced_samples
            )
        )

    if node.surface == "transition":
        transition_refs = [
            sample_id
            for sample_id, sample in samples.items()
            if node.node_name in sample["node_types"]
        ]
        if transition_refs:
            blockers.append(
                "workflow sample still contains transition node via: "
                + ", ".join(
                    f"{sample_id} ({samples[sample_id]['path']})"
                    for sample_id in transition_refs
                )
            )

    return blockers


def main():
    plan = load_cutover_plan()
    samples = sample_node_types()

    print("Cutover readiness report")
    print("=======================")
    print("")
    print("Workflow samples:")
    for sample_id, sample in samples.items():
        label = "recommended" if sample["recommended"] else sample["surface"]
        print(f"- {sample_id}: {sample['path']} [{label}]")

    print("")
    print("Retirement waves:")

    waves = sorted({node.retirement_wave for node in plan["nodes"]})
    if not waves:
        print("No remaining compat or transition nodes in the active cutover inventory.")
        return

    for wave in waves:
        print(f"Wave {wave}")
        for node in sorted(
            [entry for entry in plan["nodes"] if entry.retirement_wave == wave],
            key=lambda item: item.retirement_order,
        ):
            blockers = automated_blockers(node, samples)
            print(
                f"- [{node.retirement_order}] {node.node_name} ({node.surface}) -> {node.successor}"
            )
            if blockers:
                for blocker in blockers:
                    print(f"  blocker: {blocker}")
            else:
                print("  blocker: no workflow-sample blocker detected")
            print("  remaining gates: " + ", ".join(node.gate_ids))


if __name__ == "__main__":
    main()
