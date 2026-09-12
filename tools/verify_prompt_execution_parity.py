"""Verify strict-runner output against a pinned, real ComfyUI execution.

The verifier installs only temporary custom-node links/copies in the pinned
checkout and removes only entries that it created.  It never changes the
product node registry.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_prompt_runner import (  # noqa: E402
    WorkflowValidationError,
    build_canonical_record,
    canonical_json_bytes,
    derive_randomized_seed,
    execute_workflow,
    load_profile,
)
from workflow_widget_validation import load_workflow  # noqa: E402


SCHEMA_VERSION = "prompt-execution-parity/v1"
DEFAULT_PROFILE = ROOT / "verification" / "fixtures" / "prompt_quality_supported_profile.json"


class ParityError(RuntimeError):
    def __init__(self, code: str, message: str, **details: Any):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(sorted(details.items()))

    def envelope(self) -> dict[str, Any]:
        return {
            "error": {"code": self.code, "details": self.details, "message": self.message},
            "schema_version": SCHEMA_VERSION,
            "status": "error",
        }


def _read_json(path: Path, code: str = "invalid_environment") -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParityError(code, "could not read JSON object", path=str(path), error=type(exc).__name__) from None
    if not isinstance(value, Mapping):
        raise ParityError(code, "JSON root must be an object", path=str(path))
    return value


def _resolve(root: Path, value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ParityError("invalid_environment", "path field must be non-empty text", field=field)
    path = Path(value)
    return path if path.is_absolute() else root / path


def _git_head(path: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ParityError("version_unavailable", "could not read checkout commit", path=str(path), error=type(exc).__name__) from None
    return completed.stdout.strip().lower()


def validate_environment(environment_path: Path) -> dict[str, Any]:
    environment_path = environment_path.resolve()
    manifest = _read_json(environment_path)
    root = environment_path.parent.parent
    repositories = manifest.get("repositories")
    sink = manifest.get("sink")
    parity = manifest.get("parity")
    if not isinstance(repositories, Mapping) or not isinstance(sink, Mapping) or not isinstance(parity, Mapping):
        raise ParityError("invalid_environment", "environment must declare repositories, sink and parity")

    resolved_repositories: dict[str, dict[str, Any]] = {}
    for name in ("comfyui", "comfyui_frontend"):
        spec = repositories.get(name)
        if not isinstance(spec, Mapping):
            raise ParityError("invalid_environment", "repository declaration is missing", repository=name)
        checkout = _resolve(root, spec.get("path"), f"repositories.{name}.path")
        if not checkout.is_dir() or not (checkout / ".git").exists():
            raise ParityError("missing_checkout", "pinned checkout is not present", repository=name, path=str(checkout))
        expected = str(spec.get("commit", "")).lower()
        if len(expected) != 40:
            raise ParityError("invalid_environment", "repository commit must be a full SHA-1", repository=name)
        actual = _git_head(checkout)
        if actual != expected:
            raise ParityError("version_mismatch", "checkout commit does not match the pin", repository=name, expected=expected, actual=actual)
        resolved_repositories[name] = {**dict(spec), "path": checkout}

    sink_source = _resolve(root, sink.get("source"), "sink.source")
    if not sink_source.is_dir() or not (sink_source / "__init__.py").is_file() or not (sink_source / "nodes.py").is_file():
        raise ParityError("sink_unavailable", "verification-only sink source is incomplete", path=str(sink_source))
    if type(sink.get("version")) is not int or int(sink["version"]) < 1:
        raise ParityError("invalid_environment", "sink version must be a positive integer")
    if not isinstance(sink.get("node_type"), str) or not sink["node_type"]:
        raise ParityError("invalid_environment", "sink node_type must be non-empty text")
    workflow_path = _resolve(root, parity.get("workflow"), "parity.workflow")
    if not workflow_path.is_file():
        raise ParityError("missing_workflow", "parity workflow is not present", path=str(workflow_path))
    seeds = parity.get("sentinel_seeds")
    required = parity.get("required_outputs")
    if not isinstance(seeds, list) or len(seeds) != 8 or len(set(seeds)) != 8 or any(type(seed) is not int for seed in seeds):
        raise ParityError("invalid_environment", "parity must declare eight unique integer sentinel seeds")
    if not isinstance(required, list) or not required or any(not isinstance(item, str) for item in required):
        raise ParityError("invalid_environment", "required_outputs must be a non-empty string array")
    return {
        "environment_id": str(manifest.get("environment_id", "")),
        "manifest": manifest,
        "parity": {**dict(parity), "required_outputs": list(required), "sentinel_seeds": list(seeds), "workflow": workflow_path},
        "repositories": resolved_repositories,
        "root": root,
        "sink": {**dict(sink), "source": sink_source},
    }


def canonical_outputs(value: Mapping[str, Any], required: Sequence[str], seed: int) -> dict[str, Any]:
    missing = sorted(set(required) - set(value))
    if missing:
        raise ParityError("required_output_missing", "execution did not expose every required output", run_seed=seed, outputs=missing)
    context = value.get("final_context")
    if isinstance(context, str):
        try:
            context = json.loads(context)
        except json.JSONDecodeError:
            raise ParityError("invalid_output", "final_context is not valid JSON", run_seed=seed) from None
    if not isinstance(context, Mapping):
        raise ParityError("invalid_output", "final_context must be an object", run_seed=seed)
    result = {name: copy.deepcopy(value[name]) for name in required}
    result["final_context"] = dict(context)
    return result


def _api_prompt(workflow: Mapping[str, Any], seed: int, profile: Any, sink_type: str) -> dict[str, Any]:
    executed = execute_workflow(workflow, seed, profile=profile)
    trace = {int(item["node_id"]): item for item in executed["execution_trace"]}
    nodes = {int(node["id"]): node for node in workflow.get("nodes", [])}
    links = {int(link[0]): link for link in workflow.get("links", [])}
    prompt: dict[str, Any] = {}
    for node_id, item in trace.items():
        inputs = copy.deepcopy(item["inputs"])
        node = nodes[node_id]
        for input_item in node.get("inputs", []):
            link_id = input_item.get("link")
            if link_id is not None:
                link = links[int(link_id)]
                inputs[str(input_item["name"])] = [str(link[1]), int(link[2])]
        prompt[str(node_id)] = {"class_type": item["node_type"], "inputs": inputs}
    sink_nodes = [node for node in nodes.values() if node.get("type") == sink_type]
    if len(sink_nodes) != 1:
        raise ParityError("sink_registration_failed", "workflow must contain exactly one verification sink", count=len(sink_nodes))
    sink_node = sink_nodes[0]
    sink_inputs: dict[str, Any] = {}
    for input_item in sink_node.get("inputs", []):
        link_id = input_item.get("link")
        if link_id is None or int(link_id) not in links:
            raise ParityError("sink_registration_failed", "sink input is not linked", input_name=str(input_item.get("name", "")))
        link = links[int(link_id)]
        sink_inputs[str(input_item["name"])] = [str(link[1]), int(link[2])]
    prompt[str(sink_node["id"])] = {"class_type": sink_type, "inputs": sink_inputs}
    return prompt


def _request_json(url: str, method: str = "GET", payload: Mapping[str, Any] | None = None, timeout: float = 10) -> Any:
    data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise ParityError("execution_failed", "ComfyUI request failed", url=url, error=type(exc).__name__) from None


def _extract_sink_output(history: Mapping[str, Any], prompt_id: str, sink_node_id: str, required: Sequence[str], seed: int) -> dict[str, Any]:
    prompt_history = history.get(prompt_id)
    if not isinstance(prompt_history, Mapping):
        raise ParityError("execution_failed", "ComfyUI history omitted completed prompt", prompt_id=prompt_id, run_seed=seed)
    status = prompt_history.get("status", {})
    if isinstance(status, Mapping) and status.get("status_str") == "error":
        raise ParityError("execution_failed", "ComfyUI reported an execution error", prompt_id=prompt_id, run_seed=seed)
    outputs = prompt_history.get("outputs", {})
    node_output = outputs.get(sink_node_id) if isinstance(outputs, Mapping) else None
    if not isinstance(node_output, Mapping):
        raise ParityError("required_output_missing", "verification sink produced no observable history output", run_seed=seed, node_id=int(sink_node_id))
    candidates = node_output.get("canonical_outputs")
    if isinstance(candidates, list):
        candidates = candidates[0] if candidates else None
    if isinstance(candidates, str):
        try:
            candidates = json.loads(candidates)
        except json.JSONDecodeError:
            raise ParityError("invalid_output", "verification sink output is not valid JSON", run_seed=seed) from None
    if not isinstance(candidates, Mapping):
        raise ParityError("required_output_missing", "verification sink history lacks canonical_outputs", run_seed=seed)
    return canonical_outputs(candidates, required, seed)


def execute_via_http(base_url: str, workflow: Mapping[str, Any], seeds: Sequence[int], profile: Any, sink_type: str, sink_module: str, required: Sequence[str], timeout: float) -> list[dict[str, Any]]:
    object_info = _request_json(f"{base_url}/object_info")
    if not isinstance(object_info, Mapping) or sink_type not in object_info:
        raise ParityError("sink_registration_failed", "verification sink is not registered by ComfyUI", node_type=sink_type)
    sink_info = object_info[sink_type]
    actual_module = sink_info.get("python_module") if isinstance(sink_info, Mapping) else None
    if actual_module != sink_module:
        raise ParityError(
            "sink_registration_failed",
            "verification sink was registered from an unexpected custom-node path",
            actual_module=actual_module,
            expected_module=sink_module,
            node_type=sink_type,
        )
    sink_node = next(node for node in workflow["nodes"] if node.get("type") == sink_type)
    results: list[dict[str, Any]] = []
    for seed in seeds:
        queued = _request_json(
            f"{base_url}/prompt",
            "POST",
            {"client_id": f"prompt-parity-{uuid.uuid4().hex}", "prompt": _api_prompt(workflow, seed, profile, sink_type)},
        )
        prompt_id = queued.get("prompt_id") if isinstance(queued, Mapping) else None
        if not isinstance(prompt_id, str):
            raise ParityError("execution_failed", "ComfyUI did not return a prompt id", run_seed=seed)
        deadline = time.monotonic() + timeout
        while True:
            history = _request_json(f"{base_url}/history/{prompt_id}")
            if isinstance(history, Mapping) and prompt_id in history:
                results.append(_extract_sink_output(history, prompt_id, str(sink_node["id"]), required, seed))
                break
            if time.monotonic() >= deadline:
                raise ParityError("execution_timeout", "ComfyUI prompt did not finish in time", run_seed=seed, prompt_id=prompt_id)
            time.sleep(0.2)
    return results


def _same_tree(left: Path, right: Path) -> bool:
    names = {path.relative_to(left) for path in left.rglob("*") if path.is_file()}
    return names == {path.relative_to(right) for path in right.rglob("*") if path.is_file()} and all(
        (left / name).read_bytes() == (right / name).read_bytes() for name in names
    )


def _write_registration_marker(marker: Path, token: str, target: Path, source: Path) -> None:
    marker.write_bytes(
        canonical_json_bytes(
            {
                "schema_version": SCHEMA_VERSION,
                "source": str(source.resolve()),
                "target": str(target.absolute()),
                "token": token,
            }
        )
    )


def _create_product_registration(target: Path, source: Path, marker: Path, token: str, platform: str = os.name) -> str:
    """Create a temporary link, using an unprivileged directory junction on Windows."""

    _write_registration_marker(marker, token, target, source)
    try:
        target.symlink_to(source, target_is_directory=True)
        return "symlink"
    except OSError as symlink_error:
        if platform != "nt":
            marker.unlink(missing_ok=True)
            raise ParityError(
                "product_registration_failed",
                "could not create temporary product custom-node link",
                path=str(target),
                error=type(symlink_error).__name__,
            ) from None
    try:
        completed = subprocess.run(
            ["cmd.exe", "/d", "/s", "/c", "mklink", "/J", str(target), str(source)],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        marker.unlink(missing_ok=True)
        raise ParityError(
            "product_registration_failed",
            "could not create temporary product custom-node junction",
            path=str(target),
            error=type(exc).__name__,
        ) from None
    if completed.returncode != 0 or not target.exists() or target.resolve() != source.resolve():
        marker.unlink(missing_ok=True)
        raise ParityError(
            "product_registration_failed",
            "temporary product custom-node junction was not created correctly",
            path=str(target),
            returncode=completed.returncode,
        )
    return "junction"


def _remove_product_registration(target: Path, source: Path, marker: Path, token: str, kind: str) -> None:
    try:
        ownership = _read_json(marker, code="cleanup_failed")
    except ParityError:
        raise ParityError("cleanup_failed", "product registration ownership marker is unavailable", path=str(marker)) from None
    expected = {
        "schema_version": SCHEMA_VERSION,
        "source": str(source.resolve()),
        "target": str(target.absolute()),
        "token": token,
    }
    if dict(ownership) != expected or not target.exists() or target.resolve() != source.resolve():
        raise ParityError("cleanup_failed", "temporary product registration ownership could not be proven", path=str(target))
    try:
        if kind == "symlink":
            target.unlink()
        elif kind == "junction":
            os.rmdir(target)
        else:
            raise ValueError("unknown registration kind")
        marker.unlink()
    except (OSError, ValueError) as exc:
        raise ParityError("cleanup_failed", "could not remove owned temporary product registration", path=str(target), error=type(exc).__name__) from None


@contextlib.contextmanager
def verification_install(context: Mapping[str, Any]) -> Iterator[None]:
    comfy = context["repositories"]["comfyui"]["path"]
    custom_nodes = comfy / "custom_nodes"
    sink_target = _resolve(context["root"], context["sink"].get("install_path"), "sink.install_path")
    try:
        sink_target.resolve().relative_to(custom_nodes.resolve())
    except ValueError:
        raise ParityError(
            "invalid_environment",
            "sink install_path must remain inside the pinned ComfyUI custom_nodes directory",
            path=str(sink_target),
        ) from None
    product_target = custom_nodes / "ComfyUI-Scripted-Context-Generator"
    created_sink = False
    product_registration: tuple[Path, str, Path, str] | None = None
    try:
        custom_nodes.mkdir(parents=True, exist_ok=True)
        if sink_target.exists():
            if not sink_target.is_dir() or not _same_tree(context["sink"]["source"], sink_target):
                raise ParityError("sink_registration_failed", "existing sink install differs from verification source", path=str(sink_target))
        else:
            shutil.copytree(context["sink"]["source"], sink_target)
            created_sink = True
        if product_target.exists():
            if product_target.resolve() != context["root"].resolve():
                raise ParityError("product_registration_failed", "existing product custom-node path targets another directory", path=str(product_target))
        else:
            token = uuid.uuid4().hex
            marker = custom_nodes / f".prompt-parity-registration-{token}.json"
            kind = _create_product_registration(product_target, context["root"], marker, token)
            product_registration = (marker, kind, context["root"], token)
        yield
    finally:
        cleanup_error: ParityError | None = None
        if product_registration is not None:
            marker, kind, source, token = product_registration
            try:
                _remove_product_registration(product_target, source, marker, token, kind)
            except ParityError as exc:
                cleanup_error = exc
        if created_sink and sink_target.exists():
            try:
                shutil.rmtree(sink_target)
            except OSError as exc:
                if cleanup_error is None:
                    cleanup_error = ParityError(
                        "cleanup_failed",
                        "could not remove owned temporary verification sink",
                        path=str(sink_target),
                        error=type(exc).__name__,
                    )
        if cleanup_error is not None:
            raise cleanup_error


@contextlib.contextmanager
def local_comfyui(context: Mapping[str, Any], python: str, port: int, startup_timeout: float) -> Iterator[str]:
    comfy = context["repositories"]["comfyui"]["path"]
    with tempfile.TemporaryDirectory(prefix="prompt-parity-") as temp_name, verification_install(context):
        temp = Path(temp_name)
        for directory in (temp / "user", temp / "output", temp / "temp"):
            directory.mkdir()
        command = [python, "main.py", "--cpu", "--disable-auto-launch", "--listen", "127.0.0.1", "--port", str(port), "--user-directory", str(temp / "user"), "--output-directory", str(temp / "output"), "--temp-directory", str(temp / "temp")]
        stderr_path = temp / "comfyui.stderr.log"
        with (temp / "comfyui.stdout.log").open("w", encoding="utf-8") as stdout_log, stderr_path.open("w", encoding="utf-8") as stderr_log:
            try:
                process = subprocess.Popen(command, cwd=comfy, stdout=stdout_log, stderr=stderr_log, text=True)
            except OSError as exc:
                raise ParityError(
                    "comfyui_start_failed",
                    "could not launch the pinned ComfyUI process",
                    error=type(exc).__name__,
                    python=python,
                ) from None
            try:
                deadline = time.monotonic() + startup_timeout
                while True:
                    if process.poll() is not None:
                        stderr_log.flush()
                        stderr = stderr_path.read_text(encoding="utf-8", errors="replace")[-4000:]
                        raise ParityError("comfyui_start_failed", "pinned ComfyUI process exited during startup", returncode=process.returncode, stderr=stderr)
                    try:
                        _request_json(f"http://127.0.0.1:{port}/object_info", timeout=1)
                        break
                    except ParityError:
                        if time.monotonic() >= deadline:
                            raise ParityError("comfyui_start_failed", "pinned ComfyUI did not become ready", port=port)
                        time.sleep(0.25)
                yield f"http://127.0.0.1:{port}"
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)


def verify(context: Mapping[str, Any], base_url: str, profile: Any, timeout: float) -> dict[str, Any]:
    workflow = load_workflow(context["parity"]["workflow"])
    seeds = context["parity"]["sentinel_seeds"]
    required = context["parity"]["required_outputs"]
    strict = [canonical_outputs(build_canonical_record(workflow, seed, profile), required, seed) for seed in seeds]
    install_name = Path(str(context["sink"]["install_path"])).name
    sink_module = f"custom_nodes.{install_name}"
    actual = execute_via_http(base_url.rstrip("/"), workflow, seeds, profile, str(context["sink"]["node_type"]), sink_module, required, timeout)
    mismatches = []
    for seed, expected, observed in zip(seeds, strict, actual):
        fields = [name for name in required if expected[name] != observed[name]]
        if fields:
            mismatches.append({"fields": fields, "run_seed": seed})
    if mismatches:
        raise ParityError("parity_mismatch", "real ComfyUI output differs from the strict runner", mismatches=mismatches)
    return {
        "environment_id": context["environment_id"],
        "required_outputs": list(required),
        "schema_version": SCHEMA_VERSION,
        "sentinel_seeds": list(seeds),
        "status": "ok",
        "verified_runs": len(seeds),
    }


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify strict prompt execution parity against pinned ComfyUI.")
    parser.add_argument("--environment", default=str(ROOT / "verification" / "environment.json"))
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--comfyui-url", help="Use an already-running pinned ComfyUI instead of launching the checkout")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--port", type=int, default=8191)
    parser.add_argument("--startup-timeout", type=float, default=90.0)
    parser.add_argument("--execution-timeout", type=float, default=90.0)
    args = parser.parse_args(argv)
    try:
        context = validate_environment(Path(args.environment))
        profile = load_profile(args.profile)
        if args.comfyui_url:
            result = verify(context, args.comfyui_url, profile, args.execution_timeout)
        else:
            with local_comfyui(context, args.python, args.port, args.startup_timeout) as base_url:
                result = verify(context, base_url, profile, args.execution_timeout)
        sys.stdout.buffer.write(canonical_json_bytes(result))
        return 0
    except ParityError as exc:
        sys.stdout.buffer.write(canonical_json_bytes(exc.envelope()))
        return 2
    except WorkflowValidationError as exc:
        wrapped = ParityError("strict_runner_failed", "strict runner rejected the parity workflow", runner_error=exc.to_envelope()["error"])
        sys.stdout.buffer.write(canonical_json_bytes(wrapped.envelope()))
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
