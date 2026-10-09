#!/usr/bin/env python3
"""Run the reviewed synthetic Python suite; never invoke the K12-only Node tests.

The manifest is a review aid, not a security boundary against malicious tests.
The caller supplies a disposable environment and an outer wall-clock timeout.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import tempfile
import unittest
import uuid


class InvalidSuite(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise InvalidSuite(reason)


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item


def collect(root):
    require(not os.environ.get("K12_GUARD_UNDER_TEST"), "external-guard-override")
    manifest = json.loads((root / "tests/ci-manifest.json").read_text())
    require(isinstance(manifest, dict) and set(manifest) == {
        "schema", "python_version", "python", "k12_only"}, "manifest-schema")
    require(type(manifest["schema"]) is int and manifest["schema"] == 1, "manifest-schema")
    require(manifest["python_version"] == platform.python_version(), "python-version")
    expected, host_only = manifest["python"], manifest["k12_only"]
    require(isinstance(expected, dict) and bool(expected), "empty-python-manifest")
    require(all(re.fullmatch(r"test_[a-z0-9_]+\.py", name) and type(n) is int and n > 0
                for name, n in expected.items()), "python-manifest-entry")
    require(isinstance(host_only, list) and all(isinstance(name, str) and
            re.fullmatch(r"test_[a-z0-9_]+\.mjs", name) for name in host_only), "k12-manifest-entry")
    require(len(host_only) == len(set(host_only)), "duplicate-k12-entry")
    directory = root / "tests"
    files = list(directory.rglob("test_*"))
    files = [path for path in files if path.suffix in {".py", ".mjs"}]
    require(all(path.is_file() and not path.is_symlink() for path in files), "non-regular-test")
    require({str(path.relative_to(directory)) for path in files} == set(expected) | set(host_only),
            "test-file-inventory")
    loader = unittest.TestLoader()
    suite = loader.discover(str(directory), pattern="test_*.py", top_level_dir=str(directory))
    require(not loader.errors, "test-import-error")
    ids = [case.id() for case in cases(suite)]
    require(len(ids) == len(set(ids)), "duplicate-test-id")
    actual = Counter(test_id.split(".")[0] + ".py" for test_id in ids)
    require(dict(actual) == expected, "test-count-mismatch")
    return suite, manifest, ids


def hashes(root):
    paths = []
    for directory in (root / "scripts", root / "tests"):
        if directory.is_dir():
            paths.extend(path for path in directory.rglob("*") if path.is_file()
                         and "__pycache__" not in path.parts and path.suffix != ".pyc")
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def revision(root):
    # Ignore inherited Git discovery overrides; no remote or user config access.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_CEILING_DIRECTORIES=str(root.parent))
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, env=env,
                                text=True, capture_output=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40,64}", value) else None


def run_suite(root, run_id, report_path):
    """Child interpreter only: an abrupt exit must not be a parent success."""
    try:
        os.chdir(root)
        before = hashes(root)
        suite, manifest, ids = collect(root)
        stamp = {"runId": run_id, "startedAt": datetime.now(timezone.utc).isoformat(),
                 "python": platform.python_version(), "checkoutSha": revision(root),
                 "runnerSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 "filesSha256": before, "expected": len(ids), "cases": ids,
                 "k12OnlyNotRun": manifest["k12_only"]}
        print(json.dumps({"phase": "start", **stamp}, sort_keys=True), flush=True)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        unchanged = hashes(root) == before
        passed = (result.wasSuccessful() and result.testsRun == len(ids)
                  and not result.skipped and not result.expectedFailures and unchanged)
        finish = {"phase": "finish", "runId": stamp["runId"], "expected": len(ids),
                          "endedAt": datetime.now(timezone.utc).isoformat(),
                          "testsRun": result.testsRun, "failures": len(result.failures),
                          "errors": len(result.errors), "skipped": len(result.skipped),
                          "expectedFailures": len(result.expectedFailures),
                          "unexpectedSuccesses": len(result.unexpectedSuccesses),
                          "filesUnchanged": unchanged, "passed": passed}
        # The parent owns this fresh directory. This receipt is an accidental
        # early-exit check, not authentication against malicious fixture code.
        report_path.write_text(json.dumps(finish, sort_keys=True))
        print(json.dumps(finish, sort_keys=True), flush=True)
        return 0 if passed else 1
    except (InvalidSuite, OSError, ValueError, TypeError) as error:
        # Do not echo arbitrary fixture contents, paths or environment values.
        reason = str(error) if isinstance(error, InvalidSuite) else "invalid-suite-input"
        print(json.dumps({"phase": "rejected", "reason": reason}), flush=True)
        return 2


def completed_report(path, run_id):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                return False
            raw = handle.read(65537)
        if len(raw) > 65536:
            return False
        report = json.loads(raw)
        return (isinstance(report, dict) and report.get("phase") == "finish"
                and report.get("runId") == run_id and report.get("passed") is True
                and report.get("filesUnchanged") is True
                and type(report.get("expected")) is int and report["expected"] > 0
                and type(report.get("testsRun")) is int
                and report["testsRun"] == report["expected"]
                and all(type(report.get(key)) is int and report[key] == 0 for key in
                        ("failures", "errors", "skipped", "expectedFailures", "unexpectedSuccesses")))
    except (OSError, ValueError, RecursionError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--child-report", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--run-id", help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.child_report is not None or args.run_id is not None:
        if args.child_report is None or args.run_id is None:
            parser.error("incomplete child arguments")
        return run_suite(root, args.run_id, args.child_report)
    run_id = str(uuid.uuid4())
    with tempfile.TemporaryDirectory(prefix="k12-ci-completion-") as folder:
        report = Path(folder) / "finish.json"
        try:
            child = subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()),
                                    "--root", str(root), "--child-report", str(report),
                                    "--run-id", run_id], timeout=110)
        except (OSError, subprocess.TimeoutExpired):
            print(json.dumps({"phase": "incomplete", "reason": "child-unavailable-or-timeout"}), flush=True)
            return 1
        if child.returncode != 0:
            return 2 if child.returncode == 2 else 1
        if not completed_report(report, run_id):
            print(json.dumps({"phase": "incomplete", "reason": "completion-unconfirmed"}), flush=True)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
