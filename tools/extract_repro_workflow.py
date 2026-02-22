import json
from pathlib import Path


TARGET_TYPES = {
    "DictionaryExpand",
    "ThemeLocationExpander",
    "PromptCleaner",
}


def load_workflow(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_link_maps(links: list) -> tuple[dict, dict]:
    link_by_id = {}
    origin_by_link = {}
    target_by_link = {}
    for link in links:
        if not isinstance(link, list) or len(link) < 4:
            continue
        link_id = link[0]
        origin_id = link[1]
        target_id = link[3]
        link_by_id[link_id] = link
        origin_by_link[link_id] = origin_id
        target_by_link[link_id] = target_id
    return link_by_id, origin_by_link


def collect_upstream(nodes_by_id: dict, link_by_id: dict, origin_by_link: dict, start_ids: set) -> set:
    keep_ids = set(start_ids)
    stack = list(start_ids)
    while stack:
        node_id = stack.pop()
        node = nodes_by_id.get(node_id)
        if not node:
            continue
        for input_item in node.get("inputs", []) or []:
            link_id = input_item.get("link")
            if link_id is None:
                continue
            origin_id = origin_by_link.get(link_id)
            if origin_id is None:
                continue
            if origin_id not in keep_ids:
                keep_ids.add(origin_id)
                stack.append(origin_id)
    return keep_ids


def main():
    src_path = Path("ComfyUI-workflow-exmaple.json")
    dst_path = Path("workflow_repro_widgets_values.json")

    workflow = load_workflow(src_path)
    nodes = workflow.get("nodes", [])
    links = workflow.get("links", [])

    nodes_by_id = {n.get("id"): n for n in nodes if "id" in n}
    link_by_id, origin_by_link = build_link_maps(links)

    target_ids = {n["id"] for n in nodes if n.get("type") in TARGET_TYPES}
    keep_ids = collect_upstream(nodes_by_id, link_by_id, origin_by_link, target_ids)

    new_nodes = [n for n in nodes if n.get("id") in keep_ids]
    new_links = [l for l in links if isinstance(l, list) and l and l[0] in link_by_id and link_by_id[l[0]][1] in keep_ids and link_by_id[l[0]][3] in keep_ids]

    new_workflow = dict(workflow)
    new_workflow["nodes"] = new_nodes
    new_workflow["links"] = new_links
    new_workflow["last_node_id"] = max((n.get("id", 0) for n in new_nodes), default=0)

    dst_path.write_text(json.dumps(new_workflow, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {dst_path}")


if __name__ == "__main__":
    main()
