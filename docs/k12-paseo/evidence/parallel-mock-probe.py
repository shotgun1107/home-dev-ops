#!/usr/bin/env python3
"""Bounded synthetic process experiment; NOT a Paseo dispatcher or permission API.

--self-test checks the mock gate/ownership contract. --launch creates fresh local
repos and waits for explicitly supplied per-request mock decisions. Never calls
Paseo, a provider, network, services, or the host coordinator's receipt directory.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def write_new(path, value):
    fd, temporary = tempfile.mkstemp(prefix=".mock-publish-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)  # Atomic visibility, refuse an existing target.
    finally:
        os.unlink(temporary)  # Only this call's newly created temporary name.


def git(root, *args):
    env = {"PATH": os.environ["PATH"], "LANG": "C", "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "Synthetic mock writer", "GIT_AUTHOR_EMAIL": "mock@example.invalid",
           "GIT_COMMITTER_NAME": "Synthetic mock writer", "GIT_COMMITTER_EMAIL": "mock@example.invalid"}
    return subprocess.check_output(["git", "-c", "commit.gpgsign=false", "-C", str(root), *args],
                                   env=env, text=True, stderr=subprocess.PIPE, timeout=5).strip()


def expected(task):
    data = task["input"]
    if task["kind"] == "counts":
        return dict(sorted(Counter(data).items()))
    if task["kind"] == "unique-names":
        return sorted(set(data))
    raise ValueError("unknown-mock-task")


def request(task):
    operation = {"taskId": task["taskId"], "kind": "write-result-and-local-commit",
                 "root": task["root"], "output": "result.json", "resultHash": digest(expected(task))}
    return {"taskId": task["taskId"], "writerId": task["writerId"],
            "requestId": "permission-" + str(uuid.uuid4()), "operation": operation,
            "operationHash": digest(operation), "createdAt": now(), "createdMonotonic": time.monotonic()}


def check_decision(req, decision):
    fields = {"taskId", "writerId", "requestId", "operationHash", "decision", "actor", "reviewedAt"}
    if not isinstance(decision, dict) or set(decision) != fields:
        return False
    if not all(decision[key] == req[key] for key in ("taskId", "writerId", "requestId", "operationHash")):
        return False
    return (decision["decision"] in {"allow", "deny"} and decision["actor"] == "supervisor"
            and isinstance(decision["reviewedAt"], str) and bool(decision["reviewedAt"]))


def acquire(root):
    # Open without truncation; a losing contender does not mutate the owner file.
    fd = os.open(root / ".runtime/owner.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    return fd


def validate_task(root, task):
    return (root.is_absolute() and not root.is_symlink() and str(root.resolve()) == task.get("root")
            and task.get("branch") == "mock/" + task.get("kind", "")
            and git(root, "branch", "--show-current") == task["branch"]
            and git(root, "remote") == "" and (root / ".git").is_dir()
            and not (root / ".git").is_symlink())


def worker(root, seconds=120):
    fd = acquire(root)
    if fd is None:
        print(json.dumps({"state": "writer-busy", "exit": 75}), flush=True)
        return 75
    try:
        task = json.loads((root / "task.json").read_text())
        if not validate_task(root, task) or git(root, "status", "--porcelain"):
            return 76
        req = request(task)
        start = {"pid": os.getpid(), "taskId": task["taskId"], "writerId": task["writerId"],
                 "state": "waiting-mock-decision", "startedAt": now(), "monotonic": time.monotonic()}
        write_new(root / ".runtime/started.json", start)
        write_new(root / ".runtime/request.json", req)
        deadline = time.monotonic() + seconds
        decision_file = root / ".runtime/decision.json"
        while not decision_file.exists():
            if time.monotonic() >= deadline:
                return 77
            time.sleep(0.05)
        try:
            decision = json.loads(decision_file.read_text())
        except (OSError, ValueError):
            return 78
        if not check_decision(req, decision):
            return 78
        if decision["decision"] != "allow":
            return 79
        if time.monotonic() >= deadline:
            return 77
        # The request contains an exact local operation. It is never eval'd;
        # the only executable result path is this task's fixed result.json.
        write_new(root / "result.json", expected(task))
        git(root, "add", "result.json")
        git(root, "commit", "-qm", "Complete independent synthetic " + task["kind"])
        finish = {"state": "completed", "taskId": task["taskId"], "writerId": task["writerId"],
                  "head": git(root, "rev-parse", "HEAD"), "resultHash": digest(expected(task)),
                  "clean": not git(root, "status", "--porcelain"), "endedAt": now(),
                  "monotonic": time.monotonic(), "requestId": req["requestId"]}
        write_new(root / ".runtime/completed.json", finish)
        print(json.dumps(finish), flush=True)
        return 0
    finally:
        os.close(fd)


def create_task(parent, kind, data):
    root = parent / kind
    root.mkdir(mode=0o700)
    (root / ".runtime").mkdir(mode=0o700)
    empty = root / ".runtime/empty-template"
    empty.mkdir()
    git(root, "init", "-q", "--object-format=sha1", "--initial-branch=mock/" + kind,
        "--template=" + str(empty))
    task = {"taskId": "mock-" + str(uuid.uuid4()), "writerId": str(uuid.uuid4()),
            "kind": kind, "input": data, "root": str(root), "branch": "mock/" + kind}
    write_new(root / "task.json", task)
    (root / ".gitignore").write_text(".runtime/\n")
    git(root, "add", "task.json", ".gitignore")
    git(root, "commit", "-qm", "Create independent synthetic task")
    return root


def launch():
    parent = Path(tempfile.mkdtemp(prefix="k12-parallel-mock-"))
    roots = [create_task(parent, "counts", ["ok", "failed", "ok", "waiting"]),
             create_task(parent, "unique-names", ["beta", "alpha", "alpha"])]
    probe = Path(__file__).resolve()
    processes, streams = [], []
    meta = {"root": str(parent), "roots": list(map(str, roots)), "startedAt": now(),
            "probeSha256": hashlib.sha256(probe.read_bytes()).hexdigest(), "deadlineSeconds": 120}
    try:
        for root in roots:
            stream = (root / ".runtime/worker.log").open("x")
            streams.append(stream)
            processes.append(subprocess.Popen([sys.executable, "-I", "-B", str(probe), "--worker", str(root)],
                                              stdout=stream, stderr=subprocess.STDOUT,
                                              env={"PATH": os.environ["PATH"], "LANG": "C"}))
        meta["pids"] = [p.pid for p in processes]
        write_new(parent / "launch.json", meta)
        print(json.dumps(meta), flush=True)
        for process in processes:
            process.wait(timeout=130)
        result = {"endedAt": now(), "exitCodes": [p.returncode for p in processes],
                  "allOwnedChildrenReaped": all(p.poll() is not None for p in processes)}
        write_new(parent / "parent-result.json", result)
        print(json.dumps(result), flush=True)
        return 0 if all(p.returncode == 0 for p in processes) else 1
    finally:
        # Only children created by this call; no external PID/service control.
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
        for stream in streams:
            stream.close()


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="k12-parallel-contract-")
        self.addCleanup(self.temp.cleanup)
        self.root = create_task(Path(self.temp.name), "counts", ["ok", "ok", "failed"])
        self.task = json.loads((self.root / "task.json").read_text())
        self.req = request(self.task)
        self.decision = {k: self.req[k] for k in ("taskId", "writerId", "requestId", "operationHash")}
        self.decision.update(decision="allow", actor="supervisor", reviewedAt=now())

    def test_exact_request_is_bound(self):
        self.assertTrue(check_decision(self.req, self.decision))

    def test_each_foreign_identity_rejected(self):
        for key in ("taskId", "writerId", "requestId", "operationHash"):
            with self.subTest(key=key):
                d = dict(self.decision, **{key: "foreign"})
                self.assertFalse(check_decision(self.req, d))

    def test_missing_unknown_and_persistent_fields_rejected(self):
        for key in self.decision:
            d = dict(self.decision); del d[key]
            self.assertFalse(check_decision(self.req, d))
        for key in ("allowAll", "updatedPermissions", "prefix"):
            self.assertFalse(check_decision(self.req, dict(self.decision, **{key: True})))

    def test_no_implicit_actor_or_decision(self):
        for key, value in (("actor", "human"), ("decision", "always"), ("decision", None)):
            self.assertFalse(check_decision(self.req, dict(self.decision, **{key: value})))

    def test_deny_is_valid_but_not_allow(self):
        self.assertTrue(check_decision(self.req, dict(self.decision, decision="deny")))

    def test_duplicate_writer_excluded_and_lock_released(self):
        fd = acquire(self.root)
        self.assertIsNotNone(fd)
        try:
            self.assertIsNone(acquire(self.root))
        finally:
            os.close(fd)
        other = acquire(self.root)
        self.assertIsNotNone(other)
        os.close(other)

    def test_separate_roots_have_separate_locks_and_git_dirs(self):
        other = create_task(Path(self.temp.name), "unique-names", ["b", "a", "a"])
        a, b = acquire(self.root), acquire(other)
        try:
            self.assertIsNotNone(a); self.assertIsNotNone(b)
            self.assertNotEqual((self.root / ".git").stat().st_ino, (other / ".git").stat().st_ino)
            self.assertEqual(expected(json.loads((other / "task.json").read_text())), ["a", "b"])
        finally:
            os.close(a); os.close(b)

    def test_unknown_task_is_not_executed(self):
        with self.assertRaises(ValueError):
            expected(dict(self.task, kind="remote-push"))

    def test_task_path_and_branch_must_match(self):
        self.assertTrue(validate_task(self.root, self.task))
        self.assertFalse(validate_task(self.root, dict(self.task, root="/different")))
        self.assertFalse(validate_task(self.root, dict(self.task, branch="main")))

    def test_duplicate_request_generation_has_distinct_ids(self):
        newer = request(self.task)
        self.assertNotEqual(self.req["requestId"], newer["requestId"])
        self.assertFalse(check_decision(newer, self.decision))

    def test_publication_refuses_to_replace_existing_decision(self):
        path = self.root / ".runtime/decision.json"
        write_new(path, self.decision)
        with self.assertRaises(FileExistsError):
            write_new(path, dict(self.decision, decision="deny"))
        self.assertEqual(json.loads(path.read_text()), self.decision)

    def test_worker_without_decision_times_out_without_result(self):
        base = git(self.root, "rev-parse", "HEAD")
        self.assertEqual(worker(self.root, seconds=0), 77)
        self.assertFalse((self.root / "result.json").exists())
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), base)
        self.assertFalse(git(self.root, "status", "--porcelain"))

    def test_expired_gate_rejects_even_ready_decision(self):
        base = git(self.root, "rev-parse", "HEAD")
        write_new(self.root / ".runtime/decision.json", self.decision)
        with patch(__name__ + ".request", return_value=self.req):
            self.assertEqual(worker(self.root, seconds=0), 77)
        self.assertFalse((self.root / "result.json").exists())
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), base)

    def test_denied_worker_does_not_write_or_commit_result(self):
        base = git(self.root, "rev-parse", "HEAD")
        child = subprocess.Popen([sys.executable, "-I", "-B", str(Path(__file__).resolve()),
                                  "--worker", str(self.root)], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, env={"PATH": os.environ["PATH"], "LANG": "C"})
        try:
            deadline = time.monotonic() + 3
            while not (self.root / ".runtime/request.json").exists():
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.01)
            req = json.loads((self.root / ".runtime/request.json").read_text())
            response = {k: req[k] for k in ("taskId", "writerId", "requestId", "operationHash")}
            response.update(decision="deny", actor="supervisor", reviewedAt=now())
            write_new(self.root / ".runtime/decision.json", response)
            child.communicate(timeout=5)
            self.assertEqual(child.returncode, 79)
            self.assertFalse((self.root / "result.json").exists())
            self.assertEqual(git(self.root, "rev-parse", "HEAD"), base)
        finally:
            if child.poll() is None:
                child.kill(); child.communicate(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--launch", action="store_true")
    mode.add_argument("--worker", type=Path)
    args = parser.parse_args()
    if args.self_test:
        unittest.main(argv=[sys.argv[0], "-v"])
    elif args.launch:
        raise SystemExit(launch())
    else:
        raise SystemExit(worker(args.worker))
