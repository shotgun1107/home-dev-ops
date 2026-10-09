import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "paseo_preflight", Path(__file__).resolve().parents[1] / "scripts/paseo_preflight.py")
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class PreflightTests(unittest.TestCase):
    def test_namespace_invisible_pid_does_not_claim_stopped_or_running(self):
        result = preflight.assess({"localDaemon": "stopped", "connectedDaemon": "not_probed"}, 2316, False)
        self.assertEqual(result["verdict"], "recorded-pid-not-visible")
        self.assertFalse(result["connection_verified"])

    def test_stale_pid_is_inconclusive_too(self):
        result = preflight.assess({}, 99999999, False)
        self.assertFalse(result["connection_verified"])
        self.assertIn("do not start/restart", result["next_step"])

    def test_visible_process_without_probe_is_not_success(self):
        result = preflight.assess({"localDaemon": "running", "connectedDaemon": "not_probed"}, 2316, True)
        self.assertEqual(result["verdict"], "unconfirmed")

    def test_only_successful_connection_is_pass(self):
        result = preflight.assess({"localDaemon": "running", "connectedDaemon": "reachable"}, 2316, True)
        self.assertTrue(result["connection_verified"])

    def test_cli_failure_and_secret_output_are_not_echoed(self):
        with tempfile.TemporaryDirectory(prefix="k12-preflight-") as folder:
            root = Path(folder)
            (root / "paseo.pid").write_text('{"pid":2316,"token":"DO-NOT-EMIT"}')
            fake = subprocess.CompletedProcess([], 1, '{"password":"DO-NOT-EMIT"}', "DO-NOT-EMIT")
            with patch.object(preflight.subprocess, "run", return_value=fake) as run:
                result = preflight.diagnose(root)
            self.assertNotIn("DO-NOT-EMIT", json.dumps(result))
            self.assertFalse(result["connection_verified"])
            self.assertEqual(run.call_args.args[0], ["paseo", "--home", folder, "status", "--json"])

    def test_malformed_metadata_and_timeout_remain_unconfirmed(self):
        with tempfile.TemporaryDirectory(prefix="k12-preflight-") as folder:
            root = Path(folder)
            (root / "paseo.pid").write_text("[]")
            with patch.object(preflight.subprocess, "run", side_effect=subprocess.TimeoutExpired("paseo", 15)):
                result = preflight.diagnose(root)
            self.assertEqual(result["verdict"], "unconfirmed")
            self.assertIsNone(result["recorded_pid"])


if __name__ == "__main__":
    unittest.main()
