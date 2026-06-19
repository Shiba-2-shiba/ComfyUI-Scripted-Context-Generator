import ast
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(str(ROOT))

FACADE_MODULES = {
    "background_vocab",
    "clothing_vocab",
    "improved_pose_emotion_vocab",
    "pipeline.content_pipeline",
}

FACADE_FILES = {
    Path("background_vocab.py"),
    Path("clothing_vocab.py"),
    Path("improved_pose_emotion_vocab.py"),
    Path("pipeline/content_pipeline.py"),
}

RUNTIME_SCAN_ROOTS = (
    Path("__init__.py"),
    Path("asset_validator.py"),
    Path("character_service.py"),
    Path("clothing_service.py"),
    Path("history_service.py"),
    Path("location_service.py"),
    Path("nodes_context.py"),
    Path("nodes_prompt_cleaner.py"),
    Path("object_focus_service.py"),
    Path("prompt_renderer.py"),
    Path("registry.py"),
    Path("scene_service.py"),
    Path("workflow_class_map.py"),
    Path("workflow_samples.py"),
    Path("workflow_widget_validation.py"),
    Path("core"),
    Path("pipeline"),
    Path("vocab"),
)


def _runtime_python_files():
    for relative_root in RUNTIME_SCAN_ROOTS:
        root = ROOT / relative_root
        if root.is_file() and root.suffix == ".py":
            yield relative_root
            continue
        if root.is_dir():
            for path in root.rglob("*.py"):
                relative = path.relative_to(ROOT)
                if relative not in FACADE_FILES:
                    yield relative


def _module_name_for_path(relative_path):
    return ".".join(relative_path.with_suffix("").parts)


def _resolve_import_from_module(relative_path, node):
    module = node.module or ""
    if not node.level:
        return module

    current_module = _module_name_for_path(relative_path)
    package_parts = current_module.split(".")[:-1]
    keep = max(len(package_parts) - node.level + 1, 0)
    base = package_parts[:keep]
    if module:
        base.extend(module.split("."))
    return ".".join(part for part in base if part)


def _imported_facades(relative_path):
    tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"), filename=str(relative_path))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FACADE_MODULES:
                    found.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(relative_path, node)
            if module in FACADE_MODULES:
                found.append(module)
            if module == "pipeline":
                for alias in node.names:
                    candidate = f"pipeline.{alias.name}"
                    if candidate in FACADE_MODULES:
                        found.append(candidate)
            if node.level and not node.module:
                for alias in node.names:
                    if alias.name in FACADE_MODULES:
                        found.append(alias.name)
    return sorted(set(found))


class TestCompatibilityBoundaries(unittest.TestCase):
    def test_runtime_code_does_not_import_compatibility_facades(self):
        violations = {}
        for relative_path in sorted(_runtime_python_files()):
            imported = _imported_facades(relative_path)
            if imported:
                violations[str(relative_path).replace("\\", "/")] = imported

        self.assertEqual(
            {},
            violations,
            msg=(
                "Runtime code should import the narrower implementation modules, "
                f"not compatibility facades: {violations}"
            ),
        )


if __name__ == "__main__":
    unittest.main()
