"""Cleanup must wait for completion and never delete another agent's schedule."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    "cleanup", Path(__file__).resolve().parents[1] / "scripts/paseo_heartbeat_cleanup.py")
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)
OWNER = "11111111-1111-4111-8111-111111111111"


class HeartbeatCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="k12-cleanup-test-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        (self.home / "schedules").mkdir()
        self.path = self.home / "schedules" / "abcdef12.json"
        self.schedule = {"id": "abcdef12", "target": {"type": "agent", "agentId": OWNER},
                         "maxRuns": 1, "status": "active", "runs": [{"status": "running"}]}
        self.calls = []
        self.now = 0

    def save(self):
        self.path.write_text(json.dumps(self.schedule))

    def advance(self, seconds):
        self.now += seconds

    def delete(self, command, **kwargs):
        self.calls.append(command)
        self.path.unlink()
        return subprocess.CompletedProcess(command, 0, '{"id":"abcdef12","status":"deleted"}', "")

    def invoke(self, **kwargs):
        self.save()
        return cleanup.cleanup(self.home, "abcdef12", OWNER, 2, run=kwargs.pop("run", self.delete),
                               monotonic=lambda: self.now,
                               sleep=kwargs.pop("sleep", self.advance), **kwargs)

    def test_waits_until_run_has_finished(self):
        def complete_after_first_poll(seconds):
            self.advance(seconds)
            self.schedule.update(status="completed", runs=[{"status": "succeeded", "agentId": OWNER}])
            self.save()
        receipt = self.invoke(sleep=complete_after_first_poll)
        self.assertEqual(self.now, 1)
        self.assertTrue(receipt["deleted"])
        self.assertEqual(receipt["runs"][0]["status"], "succeeded")
        self.assertEqual(receipt["runOutcome"], "succeeded-one-run")
        self.assertFalse(receipt["idleResumeVerifiedByReceipt"])
        self.assertEqual(len(self.calls), 1)

    def test_running_timeout_does_not_delete(self):
        with self.assertRaisesRegex(cleanup.CleanupError, "timed-out"):
            self.invoke()
        self.assertEqual(self.calls, [])
        self.assertTrue(self.path.exists())

    def test_wrong_owner_is_rejected_before_delete(self):
        self.schedule["target"]["agentId"] = "other"
        self.schedule["status"] = "completed"
        with self.assertRaisesRegex(cleanup.CleanupError, "owner-mismatch"):
            self.invoke()
        self.assertEqual(self.calls, [])

    def test_recurring_mission_is_not_a_cleanup_target(self):
        self.schedule["maxRuns"] = 72
        with self.assertRaisesRegex(cleanup.CleanupError, "requires-one-run"):
            self.invoke()
        self.assertEqual(self.calls, [])

    def test_failed_run_is_preserved_as_failed_in_receipt(self):
        self.schedule.update(status="completed", runs=[{"status": "failed", "error": "sensitive raw detail"}])
        receipt = self.invoke()
        self.assertEqual(receipt["runs"][0]["status"], "failed")
        self.assertEqual(receipt["runOutcome"], "failed-run")
        self.assertNotIn("sensitive", json.dumps(receipt))

    def test_cli_failure_is_redacted_and_does_not_claim_deletion(self):
        self.schedule.update(status="completed", runs=[])
        def fail(command, **kwargs):
            return subprocess.CompletedProcess(command, 1, "sensitive output", "sensitive error")
        with self.assertRaisesRegex(cleanup.CleanupError, "^delete-command-failed$"):
            self.invoke(run=fail)
        self.assertTrue(self.path.exists())

    def test_success_acknowledgement_does_not_replace_absence_check(self):
        self.schedule.update(status="completed", runs=[])
        def false_success(command, **kwargs):
            return subprocess.CompletedProcess(command, 0, '{"id":"abcdef12","status":"deleted"}', "")
        with self.assertRaisesRegex(cleanup.CleanupError, "schedule-still-present"):
            self.invoke(run=false_success)

    def test_expired_without_run_is_cleaned_but_not_a_resume_pass(self):
        self.schedule.update(status="completed", runs=[])
        receipt = self.invoke()
        self.assertTrue(receipt["deleted"])
        self.assertEqual(receipt["runOutcome"], "no-run")
        self.assertFalse(receipt["idleResumeVerifiedByReceipt"])

    def test_unknown_delete_response_preserves_finished_run_evidence(self):
        self.schedule.update(status="completed", runs=[{"status": "succeeded", "agentId": OWNER}])
        def delete_then_lose_response(command, **kwargs):
            self.path.unlink()
            raise subprocess.TimeoutExpired(command, 30, output="sensitive response")
        with self.assertRaisesRegex(cleanup.CleanupError, "delete-command-unavailable") as caught:
            self.invoke(run=delete_then_lose_response)
        self.assertFalse(self.path.exists())
        self.assertEqual(caught.exception.receipt["runOutcome"], "succeeded-one-run")
        self.assertNotIn("sensitive", json.dumps(caught.exception.receipt))

    def cli(self, agent=OWNER):
        binary = self.home / "bin"
        binary.mkdir(exist_ok=True)
        fake = binary / "paseo"
        fake.write_text('#!/bin/sh\necho called > "$0.called"\nexit 99\n')
        fake.chmod(0o700)
        result = subprocess.run([sys.executable, "-I", "-B", str(Path(cleanup.__file__)),
                                 "abcdef12", "--home", str(self.home), "--timeout", "1"],
                                env={"PATH": str(binary), "PASEO_AGENT_ID": agent},
                                capture_output=True, text=True, timeout=3)
        self.assertFalse((binary / "paseo.called").exists(), "invalid input reached delete command")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, "")
        self.assertNotIn("SYNTHETIC-NOT-FOR-OUTPUT", result.stdout)
        return json.loads(result.stdout)

    def test_schedule_file_inputs_fail_closed_without_cli(self):
        target = self.home / "synthetic.json"
        self.schedule.update(status="completed", runs=[])
        target.write_text(json.dumps(self.schedule))
        for kind in ("fifo", "symlink", "oversized", "deep", "directory"):
            with self.subTest(kind=kind):
                if kind == "fifo": os.mkfifo(self.path)
                elif kind == "symlink": self.path.symlink_to(target)
                elif kind == "oversized": self.path.write_text("x" * 65537)
                elif kind == "deep": self.path.write_text("[" * 2000 + "0" + "]" * 2000)
                else: self.path.mkdir()
                try:
                    reason = self.cli()["reason"]
                    if kind == "deep":
                        self.assertIn(reason, ("schedule-unreadable", "invalid-schedule"))
                    else:
                        self.assertEqual(reason, "schedule-unreadable")
                finally:
                    if kind == "directory": self.path.rmdir()
                    else: self.path.unlink()

    def test_boolean_maxruns_rejected(self):
        self.schedule.update(maxRuns=True, status="completed", runs=[])
        self.save()
        self.assertEqual(self.cli()["reason"], "requires-one-run-heartbeat")

    def test_untyped_receipt_fields_never_echo_or_delete(self):
        for key in ("expiresAt", "id", "agentId", "scheduledFor", "startedAt", "endedAt", "status"):
            with self.subTest(key=key):
                self.schedule.update(status="completed", expiresAt=None,
                                     runs=[{"status": "succeeded", "agentId": OWNER}])
                if key == "expiresAt": self.schedule[key] = {"raw": "SYNTHETIC-NOT-FOR-OUTPUT"}
                else: self.schedule["runs"][0][key] = {"raw": "SYNTHETIC-NOT-FOR-OUTPUT"}
                self.save()
                self.assertIn(self.cli()["reason"], ("invalid-schedule", "invalid-run-metadata", "invalid-runs"))

    def test_duplicate_schedule_keys_rejected(self):
        self.schedule.update(status="completed", runs=[])
        raw = json.dumps(self.schedule)
        self.path.write_text(raw[:-1] + ', "maxRuns": 1}')
        self.assertEqual(self.cli()["reason"], "invalid-schedule")

    def test_unexpected_acknowledgement_depth_and_size_preserves_evidence(self):
        self.schedule.update(status="completed", runs=[])
        for raw in ("[" * 2000 + "0" + "]" * 2000, "x" * 65537):
            def fake(command, **kwargs):
                return subprocess.CompletedProcess(command, 0, raw, "")
            with self.assertRaisesRegex(cleanup.CleanupError, "(?:invalid|unexpected)-delete-acknowledgement") as caught:
                self.invoke(run=fake)
            self.assertEqual(caught.exception.receipt["runOutcome"], "no-run")

    def test_caller_id_requires_full_uuid(self):
        self.schedule.update(status="completed", runs=[])
        self.save()
        self.assertEqual(self.cli("not-a-full-agent-id")["reason"], "invalid-caller-agent")


if __name__ == "__main__":
    unittest.main()
