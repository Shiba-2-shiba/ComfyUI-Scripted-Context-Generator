import __init__ as package_registry

from workflow_widget_validation import load_workflow


def collect_workflow_node_types(workflow: dict) -> set[str]:
    return {
        node_type
        for node in workflow.get("nodes", [])
        if (node_type := node.get("type"))
    }


def build_class_map_for_workflows(workflows: list[dict]) -> dict[str, type]:
    node_types = set()
    for workflow in workflows:
        node_types.update(collect_workflow_node_types(workflow))
    return {
        node_type: package_registry.NODE_CLASS_MAPPINGS[node_type]
        for node_type in sorted(node_types)
        if node_type in package_registry.NODE_CLASS_MAPPINGS
    }


def build_class_map_for_samples(samples) -> dict[str, type]:
    workflows = [load_workflow(sample.path) for sample in samples]
    return build_class_map_for_workflows(workflows)
