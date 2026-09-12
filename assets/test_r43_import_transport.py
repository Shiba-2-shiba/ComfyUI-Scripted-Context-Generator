"""Import identity and context_json replay across clean interpreter boundaries."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "assets/fixtures/r43_import_probe.py"


def probe(root, mode, inputs, cwd):
    result = subprocess.run([sys.executable, "-I", "-B", str(PROBE), str(root), mode],
                            input=json.dumps(inputs), text=True, encoding="utf-8",
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, check=False)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return json.loads(result.stdout)


def copy_runtime(destination):
    destination.mkdir()
    for path in ROOT.iterdir():
        if path.is_file() and path.suffix in {".py", ".json", ".jsonl", ".txt"}:
            shutil.copyfile(path, destination / path.name)
    for name in ("core", "pipeline", "vocab", "rules"):
        shutil.copytree(ROOT / name, destination / name,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


class TestR43ImportTransport(unittest.TestCase):
    def test_package_without_root_path_matches_root_and_json_replay(self):
        inputs = [{"context": {"subj": "a solo girl", "loc": "station platform",
                               "action": "checking a transit card"},
                   "seed": seed, "composition_mode": mode}
                  for mode in (True, False) for seed in range(16)]
        # Include received Builder history, rather than only empty-history calls.
        with tempfile.TemporaryDirectory(prefix="scg-r43-import-") as temporary:
            flat = probe(ROOT, "root", inputs, temporary)
            inputs.append({"context": flat["rows"][0]["updated_context"], "seed": 19,
                           "composition_mode": True})
            flat = probe(ROOT, "root", inputs, temporary)
            package = probe(ROOT, "package", inputs, temporary)
        self.assertEqual(flat["rows"], package["rows"])
        self.assertEqual(flat["modules"], package["modules"])

    def test_independent_source_copies_resolve_their_own_modules(self):
        inputs = [{"context": {"subj": "a solo girl", "loc": "tea room", "action": "reading a book"},
                   "seed": 7, "composition_mode": True}]
        with tempfile.TemporaryDirectory(prefix="scg-r43-checkouts-") as temporary:
            results = []
            for name in ("checkout_a", "checkout_b"):
                root = Path(temporary) / name
                copy_runtime(root)
                results.append(probe(root, "package", inputs, temporary))
            self.assertEqual(results[0]["rows"], results[1]["rows"])
            for name in results[0]["modules"]:
                self.assertNotEqual(results[0]["modules"][name], results[1]["modules"][name])


if __name__ == "__main__":
    unittest.main()
