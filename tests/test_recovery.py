import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = load("paseo_recovery_audit")
preflight = load("paseo_preflight")
NOW = datetime(2026, 10, 9, 20, 0, tzinfo=timezone.utc)
SHA = "a" * 40


def snapshot():
    identity = dict(task="synthetic-task", job="synthetic-job-1", worktree="/synthetic/worktree",
                    runtime="synthetic-runtime", writer="synthetic-writer", session="synthetic-session",
                    branch="task/synthetic-recovery", epoch=1)
    return {"schema": 1, "checkpoint": {**identity, "head": SHA},
            "observation": {**identity, "localHead": SHA, "remoteHead": SHA, "prHead": SHA,
                            "handoffHead": SHA, "observedAt": NOW.isoformat(), "clean": True,
                            "writerState": "idle", "pendingPermissions": 0, "children": "none",
                            "nativeComplete": True, "runtimeOwner": "released", "effects": "absent",
                            "receipt": None}}


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="k12-recovery-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def check(self, data):
        result = audit.assess(data, now=NOW)
        self.assertEqual(result["automaticAction"], "none")
        self.assertFalse(result["liveLeaseAcquired"])
        return result

    def cli(self, path):
        return subprocess.run([sys.executable, "-B", str(ROOT / "scripts/paseo_recovery_audit.py"), str(path)],
                              capture_output=True, text=True, timeout=5)

    def test_complete_handoff_reviewable_without_grant(self):
        r = self.check(snapshot())
        self.assertEqual(r["decision"], "handoff-reviewable")
        self.assertFalse(r["snapshotAuthenticated"])

    def test_interrupted_writer_quiescence_checks_are_independent(self):
        for key, value in [("writerState", "running"), ("writerState", "unknown"),
                           ("children", "present"), ("children", "unknown"),
                           ("pendingPermissions", 1), ("pendingPermissions", None), ("nativeComplete", False)]:
            with self.subTest(key=key, value=value):
                data = snapshot(); data["observation"][key] = value
                self.assertIn("previous-writer-not-quiescent", self.check(data)["reasons"])

    def test_all_identity_fields_must_match_including_epoch(self):
        for key in audit.IDENTITY:
            with self.subTest(key=key):
                data = snapshot(); data["observation"][key] = 2 if key == "epoch" else "different"
                self.assertIn("identity-or-ownership-mismatch", self.check(data)["reasons"])

    def test_each_revision_must_match_not_only_local_head(self):
        for key in ("localHead", "remoteHead", "prHead", "handoffHead"):
            for value in (None, "b" * 40):
                data = snapshot(); data["observation"][key] = value
                self.assertIn("revision-unconfirmed", self.check(data)["reasons"])

    def test_unknown_runtime_owner_does_not_transfer(self):
        for owner in ("previous", "other", "unknown"):
            data = snapshot(); data["observation"]["runtimeOwner"] = owner
            self.assertIn("runtime-not-released", self.check(data)["reasons"])

    def test_dirty_state_not_discarded(self):
        data = snapshot(); data["observation"]["clean"] = False
        self.assertIn("uncommitted-state", self.check(data)["reasons"])

    def test_stale_future_and_boundary_observations(self):
        for seconds, allowed in [(-61, False), (-60, True), (5, True), (6, False)]:
            data = snapshot(); data["observation"]["observedAt"] = (NOW + timedelta(seconds=seconds)).isoformat()
            self.assertEqual(self.check(data)["decision"] == "handoff-reviewable", allowed)

    def test_main_is_never_reviewable(self):
        for branch in ("main", "master", "refs/heads/main", "refs/heads/master"):
            data = snapshot(); data["checkpoint"]["branch"] = data["observation"]["branch"] = branch
            self.assertIn("protected-branch", self.check(data)["reasons"])

    def test_unknown_effects_after_lost_completion_never_retries(self):
        for state in ("unknown", "conflict", "verified"):
            data = snapshot(); data["observation"]["effects"] = state
            self.assertEqual(self.check(data)["decision"], "reconcile-effects")

    def test_success_receipt_requires_effect_confirmation(self):
        data = snapshot(); data["observation"]["receipt"] = dict(job="synthetic-job-1", head=SHA, outcome="succeeded")
        self.assertEqual(self.check(data)["decision"], "reconcile-effects")
        data["observation"]["effects"] = "verified"
        self.assertEqual(self.check(data)["decision"], "already-completed")

    def test_failed_receipt_is_not_side_effect_rollback(self):
        data = snapshot(); data["observation"]["receipt"] = dict(job="synthetic-job-1", head=SHA, outcome="failed")
        data["observation"]["effects"] = "unknown"
        self.assertEqual(self.check(data)["decision"], "reconcile-effects")
        data["observation"]["effects"] = "absent"
        self.assertEqual(self.check(data)["decision"], "retry-reviewable")

    def test_foreign_or_old_receipt_rejected(self):
        for key, value in [("job", "other-job"), ("head", "b" * 40)]:
            data = snapshot(); receipt = dict(job="synthetic-job-1", head=SHA, outcome="succeeded")
            receipt[key] = value; data["observation"]["receipt"] = receipt
            self.assertIn("receipt-mismatch", self.check(data)["reasons"])

    def test_invalid_types_missing_fields_and_extra_keys_fail_closed(self):
        variants = []
        d = snapshot(); d["schema"] = True; variants.append(d)
        d = snapshot(); d["observation"]["pendingPermissions"] = False; variants.append(d)
        d = snapshot(); del d["checkpoint"]["head"]; variants.append(d)
        d = snapshot(); d["observation"]["observedAt"] = "2026-10-09T20:00:00"; variants.append(d)
        d = snapshot(); d["secret"] = "SYNTHETIC-DO-NOT-EMIT"; variants.append(d)
        for data in variants:
            with self.assertRaisesRegex(audit.RecoveryError, "^invalid-snapshot$"):
                self.check(data)

    def test_cli_partial_oversized_duplicate_and_special_files_no_secret_output(self):
        path = self.root / "snapshot.json"
        samples = [b'{"SYNTHETIC-DO-NOT-EMIT":', b'x' * 65537,
                   b'{"schema":1,"schema":1}', b'\xff', b'[]']
        for raw in samples:
            path.write_bytes(raw); r = self.cli(path)
            self.assertEqual(r.returncode, 2); self.assertEqual(r.stderr, "")
            self.assertEqual(json.loads(r.stdout)["reasons"], ["invalid-snapshot"])
            self.assertNotIn("SYNTHETIC-DO-NOT-EMIT", r.stdout)
        symlink = self.root / "symlink"; symlink.symlink_to(path)
        fifo = self.root / "fifo"; os.mkfifo(fifo)
        for p in (symlink, fifo, self.root, self.root / "missing"):
            self.assertEqual(self.cli(p).returncode, 2)

    def test_atomic_publication_errors_preserve_readable_destination(self):
        path = self.root / "checkpoint.json"; old = snapshot(); audit.publish_snapshot(path, old)
        new = copy.deepcopy(old); new["checkpoint"]["epoch"] = 2
        with patch.object(audit.os, "replace", side_effect=OSError("SYNTHETIC-DO-NOT-EMIT")):
            with self.assertRaisesRegex(audit.RecoveryError, "^publication-failed-or-uncertain$"):
                audit.publish_snapshot(path, new)
        self.assertEqual(audit.read_snapshot(path), old)
        self.assertEqual(len(list(self.root.glob(".recovery-*.tmp"))), 1)

    def test_directory_sync_error_after_replace_is_uncertain_not_rollback(self):
        path = self.root / "checkpoint.json"; old = snapshot(); audit.publish_snapshot(path, old)
        new = copy.deepcopy(old); new["checkpoint"]["epoch"] = 2
        original = audit.os.fsync
        def fsync(fd):
            if audit.stat.S_ISDIR(os.fstat(fd).st_mode):
                raise OSError("synthetic directory sync failure")
            return original(fd)
        with patch.object(audit.os, "fsync", side_effect=fsync):
            with self.assertRaisesRegex(audit.RecoveryError, "^publication-failed-or-uncertain$"):
                audit.publish_snapshot(path, new)
        self.assertEqual(audit.read_snapshot(path), new)

    def test_abrupt_owned_child_exit_before_and_after_atomic_replace(self):
        # os._exit terminates only a freshly spawned test process, never a service.
        worker = self.root / "worker.py"
        worker.write_text('''import importlib.util,json,os,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("audit",sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
data=json.loads(Path(sys.argv[2]).read_text());path=Path(sys.argv[3]);stage=sys.argv[4]
if stage=="partial":
 with path.open("w") as f:f.write('{"partial":');f.flush();os.fsync(f.fileno())
 os._exit(73)
original=m.os.replace
def replace(a,b):
 if stage=="before":os._exit(73)
 original(a,b)
 if stage=="after":os._exit(73)
m.os.replace=replace;m.publish_snapshot(path,data)
''')
        path = self.root / "checkpoint.json"; source = self.root / "input.json"
        old = snapshot(); new = copy.deepcopy(old); new["checkpoint"]["epoch"] = new["observation"]["epoch"] = 2
        source.write_text(json.dumps(new))
        for stage in ("partial", "before", "after"):
            audit.publish_snapshot(path, old)
            r = subprocess.run([sys.executable, "-B", str(worker), str(ROOT / "scripts/paseo_recovery_audit.py"),
                                str(source), str(path), stage], capture_output=True, timeout=5)
            self.assertEqual(r.returncode, 73); self.assertEqual(r.stderr, b"")
            if stage == "partial":
                self.assertEqual(self.cli(path).returncode, 2)
            else:
                self.assertEqual(audit.read_snapshot(path), old if stage == "before" else new)

    def test_effect_without_receipt_is_reconciled_by_fresh_process(self):
        effect = self.root / "synthetic-effect"; effect.write_text("performed-once")
        path = self.root / "snapshot.json"; data = snapshot()
        data["observation"]["effects"] = "unknown"
        data["observation"]["observedAt"] = datetime.now(timezone.utc).isoformat()
        audit.publish_snapshot(path, data)
        r = self.cli(path); self.assertEqual(json.loads(r.stdout)["decision"], "reconcile-effects")
        self.assertEqual(effect.read_text(), "performed-once")
        data["observation"]["effects"] = "verified"
        data["observation"]["receipt"] = dict(job="synthetic-job-1", head=SHA, outcome="succeeded")
        audit.publish_snapshot(path, data)
        r = self.cli(path); self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)["decision"], "already-completed")
        self.assertEqual(effect.read_text(), "performed-once")

    def test_remote_push_ack_loss_recovered_by_actual_local_bare_ref(self):
        # No network, user config, signing or common hooks; only fresh local Git dirs.
        empty = self.root / "empty"; empty.mkdir()
        env = {"PATH": os.environ["PATH"], "LANG": "C", "GIT_CONFIG_NOSYSTEM": "1",
               "GIT_CONFIG_GLOBAL": str(empty / "config"), "GIT_TERMINAL_PROMPT": "0"}
        repo = self.root / "repo"; remote = self.root / "remote.git"
        def git(*args, cwd=None):
            return subprocess.check_output(["git", "-c", f"core.hooksPath={empty}", "-c", "commit.gpgsign=false",
                                            "-c", "user.name=Synthetic", "-c", "user.email=fixture@example.invalid",
                                            *args], cwd=cwd, env=env, stderr=subprocess.DEVNULL, text=True, timeout=5).strip()
        git("init", "--bare", f"--template={empty}", str(remote))
        git("init", "-b", "task/synthetic-recovery", f"--template={empty}", str(repo))
        (repo / "task.txt").write_text("synthetic handoff\n"); git("add", "task.txt", cwd=repo)
        git("commit", "-m", "synthetic checkpoint", cwd=repo); head = git("rev-parse", "HEAD", cwd=repo)
        git("push", str(remote), "HEAD:refs/heads/task/synthetic-recovery", cwd=repo)  # receipt deliberately discarded
        actual = git("ls-remote", str(remote), "refs/heads/task/synthetic-recovery").split()[0]
        data = snapshot(); data["checkpoint"]["head"] = head
        for key in ("localHead", "remoteHead", "prHead", "handoffHead"):data["observation"][key] = actual
        self.assertEqual(self.check(data)["decision"], "handoff-reviewable")
        # PR observation is synthetic, not a GitHub fixture or a real push-loss test.
        (repo / "task.txt").write_text("dirty after interruption\n")
        data["observation"]["clean"] = not bool(git("status", "--porcelain", cwd=repo))
        self.assertEqual(self.check(data)["decision"], "blocked")
        self.assertEqual((repo / "task.txt").read_text(), "dirty after interruption\n")


class PreflightRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="k12-recovery-pid-"); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.proc = self.root / "proc"; self.proc.mkdir()
        self.pid = self.root / "paseo.pid"
        self.pid.write_text(json.dumps({"pid": 900001, "startedAt": "2026-10-09T20:00:00Z"}))

    def diagnose(self, result=None, side_effect=None):
        if result is None:result = {"connectedDaemon": "reachable", "localDaemon": "running"}
        fake = subprocess.CompletedProcess([], 0, json.dumps(result), "")
        with patch.object(preflight.subprocess, "run", return_value=fake, side_effect=side_effect) as run:
            r = preflight.diagnose(self.root, proc_root=self.proc)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0], ["paseo", "--home", str(self.root), "status", "--json"])
        self.assertEqual(run.call_args.kwargs["timeout"], 15)
        return r

    def test_changed_identity_during_probe_no_longer_claims_stable_connection(self):
        for change in ({"pid": 900002}, {"pid": 900001, "startedAt": "2026-10-09T20:00:01Z"}):
            self.pid.write_text(json.dumps({"pid": 900001, "startedAt": "2026-10-09T20:00:00Z"}))
            def fake(*args, **kwargs):
                self.pid.write_text(json.dumps(change))
                return subprocess.CompletedProcess([], 0, '{"connectedDaemon":"reachable"}', "")
            r = self.diagnose(side_effect=fake)
            self.assertEqual(r["verdict"], "observation-changed"); self.assertFalse(r["connection_verified"])
            self.assertTrue(r["cli_connection_reachable"])

    def test_disappearing_metadata_during_probe_is_unconfirmed(self):
        def fake(*args, **kwargs):
            self.pid.unlink(); return subprocess.CompletedProcess([], 0, '{"connectedDaemon":"reachable"}', "")
        self.assertFalse(self.diagnose(side_effect=fake)["connection_verified"])

    def test_stale_or_namespace_hidden_pid_cannot_be_distinguished(self):
        r = self.diagnose({"connectedDaemon": "not_probed", "localDaemon": "stopped"})
        self.assertEqual(r["verdict"], "recorded-pid-not-visible")
        self.assertFalse(r["connection_verified"])

    def test_visible_reused_pid_does_not_prove_daemon_identity(self):
        (self.proc / "900001").mkdir()
        r = self.diagnose({"connectedDaemon": "not_probed", "localDaemon": "running"})
        self.assertTrue(r["recorded_pid_visible"]); self.assertFalse(r["pid_identity_verified"])
        self.assertFalse(r["connection_verified"])

    def test_auth_failures_not_retried_or_echoed(self):
        for value in ("auth_required", "auth_failed", "unreachable"):
            r = self.diagnose({"connectedDaemon": value, "note": "SYNTHETIC-DO-NOT-EMIT"})
            self.assertFalse(r["connection_verified"]); self.assertNotIn("SYNTHETIC-DO-NOT-EMIT", json.dumps(r))

    def test_metadata_symlink_fifo_and_size_are_rejected_without_hang(self):
        self.pid.write_text("x" * 65537)
        self.assertEqual(preflight.read_pid_metadata(self.root)[1], "unreadable-or-invalid")
        self.pid.unlink(); os.mkfifo(self.pid)
        self.assertEqual(preflight.read_pid_metadata(self.root)[1], "unreadable-or-invalid")
        self.pid.unlink(); self.pid.symlink_to(self.proc)
        self.assertEqual(preflight.read_pid_metadata(self.root)[1], "unreadable-or-invalid")

    def test_parser_recursion_fault_returns_fixed_inconclusive_result(self):
        with patch.object(preflight.json, "loads", side_effect=RecursionError("SYNTHETIC-DO-NOT-EMIT")):
            with patch.object(preflight.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "{}", "")):
                r = preflight.diagnose(self.root, proc_root=self.proc)
        self.assertEqual(r["cli_result"], "invalid-output"); self.assertFalse(r["connection_verified"])
        self.assertNotIn("SYNTHETIC-DO-NOT-EMIT", json.dumps(r))

    def test_oversized_cli_output_not_accepted(self):
        r = self.diagnose({"connectedDaemon": "reachable", "note": "x" * 1048576})
        self.assertEqual(r["cli_result"], "invalid-output"); self.assertFalse(r["connection_verified"])


if __name__ == "__main__":
    unittest.main()
