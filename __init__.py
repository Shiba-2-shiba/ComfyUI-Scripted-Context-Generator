import importlib
import traceback


def log_import_error(name, error):
    print(f"\033[91m[ComfyUI-Nodes] Error importing {name}:\033[0m")
    traceback.print_exc()


NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
NODE_SURFACE_GROUPS = {
    "primary": (
        "nodes_context",
    ),
    "transition": (),
    "compat": (),
    "utility": (
        "nodes_prompt_cleaner",
    ),
}


def _import_node_module(module_name):
    if __package__:
        return importlib.import_module(f".{module_name}", __package__)
    return importlib.import_module(module_name)


def _register_node_module(module_name, error_name, warning_message=None):
    try:
        module = _import_node_module(module_name)
        NODE_CLASS_MAPPINGS.update(getattr(module, "NODE_CLASS_MAPPINGS", {}))
        NODE_DISPLAY_NAME_MAPPINGS.update(getattr(module, "NODE_DISPLAY_NAME_MAPPINGS", {}))
    except ImportError as error:
        log_import_error(error_name, error)
        if warning_message:
            print(warning_message)


_REGISTERED_MODULES = (
    ("nodes_context", "ContextNodes", "\033[93m[ComfyUI-Nodes] Warning: nodes_context.py import failed.\033[0m"),
    ("nodes_prompt_cleaner", "PromptCleaner", "\033[93m[ComfyUI-Nodes] Warning: nodes_prompt_cleaner.py import failed.\033[0m"),
)

for module_name, error_name, warning_message in _REGISTERED_MODULES:
    _register_node_module(module_name, error_name, warning_message)

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "NODE_SURFACE_GROUPS"]
