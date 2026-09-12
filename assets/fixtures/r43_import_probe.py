"""Fresh-process Builder probe; invoked by tests, never imported by runtime."""
import importlib
import importlib.util
import json
from pathlib import Path
import sys


def main():
    root = Path(sys.argv[1]).resolve()
    mode = sys.argv[2]
    inputs = json.load(sys.stdin)
    if mode == "package":
        assert str(root) not in sys.path
        spec = importlib.util.spec_from_file_location("scg_probe", root / "__init__.py",
                                                     submodule_search_locations=[str(root)])
        package = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = package
        spec.loader.exec_module(package)
        assert "ContextPromptBuilder" in package.NODE_CLASS_MAPPINGS
        prefix = "scg_probe."
    else:
        sys.path.insert(0, str(root))
        prefix = ""

    schema = importlib.import_module(prefix + "core.schema")
    orchestrator = importlib.import_module(prefix + "pipeline.prompt_orchestrator")
    nodes = importlib.import_module(prefix + "nodes_context")
    cleaner = importlib.import_module(prefix + "nodes_prompt_cleaner").PromptCleaner()
    rows = []
    for item in inputs:
        context = schema.PromptContext.from_dict(item["context"])
        original = context.to_dict()
        kwargs = dict(template=item.get("template", ""), composition_mode=item["composition_mode"], seed=item["seed"])
        updated, prompt = orchestrator.build_prompt_from_context(context, **kwargs)
        transported = schema.PromptContext.from_dict(json.loads(context.to_json()))
        replay, replay_prompt = orchestrator.build_prompt_from_context(transported, **kwargs)
        assert prompt == replay_prompt and updated.to_dict() == replay.to_dict()
        assert nodes.ContextPromptBuilder().build_prompt_context(context_json=context.to_json(), **kwargs) == (prompt,)
        assert context.to_dict() == original
        rows.append({"raw_prompt": prompt, "cleaned_prompt": cleaner.clean(text=prompt)[0],
                     "updated_context": updated.to_dict(), "upstream_context": original})

    modules = {}
    for name in ("core.schema", "pipeline.prompt_orchestrator", "pipeline.prompt_realizer",
                 "pipeline.v2_candidate_bridge", "pipeline.v2_direct_provenance", "prompt_renderer",
                 "vocab.seed_utils", "nodes_context"):
        module = sys.modules[prefix + name]
        path = Path(module.__file__).resolve()
        assert path.is_relative_to(root), (name, str(path))
        modules[name] = str(path)
        if mode == "package":
            assert name not in sys.modules, name
    realizer = sys.modules[prefix + "pipeline.prompt_realizer"]
    assert realizer.ActionFrame is schema.ActionFrame
    assert sys.modules[prefix + "pipeline.v2_candidate_bridge"].realize_content_plan is realizer.realize_content_plan
    print(json.dumps({"rows": rows, "modules": modules}, sort_keys=True))


if __name__ == "__main__":
    main()
