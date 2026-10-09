"""Failure-inject only owned fixture suites in short-lived child interpreters."""
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / "scripts/run_ops_ci.py"
PASS = "import unittest\nclass Example(unittest.TestCase):\n    def test_one(self): pass\n"


class OpsCiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="k12-ci-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "tests").mkdir()
        self.test = self.root / "tests/test_example.py"
        self.test.write_text(PASS)
        self.manifest = {"schema": 1, "python_version": platform.python_version(),
                         "python": {"test_example.py": 1}, "k12_only": []}

    def run_fixture(self, code=0, override=None):
        (self.root / "tests/ci-manifest.json").write_text(json.dumps(self.manifest))
        env = {"PATH": os.environ["PATH"], "LANG": "C", "TMPDIR": str(self.root)}
        if override is not None:
            env["K12_GUARD_UNDER_TEST"] = override
        result = subprocess.run([sys.executable, "-I", "-B", str(RUNNER), "--root", str(self.root)],
                                env=env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return [json.loads(line) for line in result.stdout.splitlines()]

    def test_complete_run_has_matching_provenance(self):
        start, finish = self.run_fixture()
        self.assertEqual(start["runId"], finish["runId"])
        self.assertEqual(start["expected"], finish["testsRun"])
        self.assertEqual(start["cases"], ["test_example.Example.test_one"])
        self.assertIsNone(start["checkoutSha"])
        self.assertIn("tests/test_example.py", start["filesSha256"])
        self.assertTrue(finish["filesUnchanged"])
        self.assertTrue(finish["passed"])

    def test_empty_suite_rejected(self):
        self.test.write_text("")
        self.assertEqual(self.run_fixture(2)[0]["reason"], "test-count-mismatch")

    def test_missing_file_rejected(self):
        self.test.unlink()
        self.assertEqual(self.run_fixture(2)[0]["reason"], "test-file-inventory")

    def test_unlisted_test_rejected(self):
        (self.root / "tests/test_new.py").write_text(PASS)
        self.assertEqual(self.run_fixture(2)[0]["reason"], "test-file-inventory")

    def test_partial_suite_rejected(self):
        self.manifest["python"]["test_example.py"] = 2
        self.assertEqual(self.run_fixture(2)[0]["reason"], "test-count-mismatch")

    def test_import_error_rejected(self):
        self.test.write_text("raise RuntimeError('synthetic import failure')\n")
        self.assertEqual(self.run_fixture(2)[0]["reason"], "test-import-error")

    def test_skipped_is_not_pass(self):
        self.test.write_text(PASS.replace("def test_one", "@unittest.skip('synthetic')\n    def test_one"))
        self.assertEqual(self.run_fixture(1)[-1]["skipped"], 1)

    def test_expected_failure_is_not_pass(self):
        self.test.write_text(PASS.replace("def test_one", "@unittest.expectedFailure\n    def test_one").replace(": pass", ": self.fail('synthetic')"))
        self.assertEqual(self.run_fixture(1)[-1]["expectedFailures"], 1)

    def test_unexpected_success_is_not_pass(self):
        self.test.write_text(PASS.replace("def test_one", "@unittest.expectedFailure\n    def test_one"))
        self.assertEqual(self.run_fixture(1)[-1]["unexpectedSuccesses"], 1)

    def test_assertion_failure_is_not_pass(self):
        self.test.write_text(PASS.replace(": pass", ": self.fail('synthetic')"))
        self.assertEqual(self.run_fixture(1)[-1]["failures"], 1)

    def test_test_error_is_not_pass(self):
        self.test.write_text(PASS.replace(": pass", ": raise RuntimeError('synthetic')"))
        self.assertEqual(self.run_fixture(1)[-1]["errors"], 1)

    def test_k12_only_is_explicitly_unexecuted(self):
        (self.root / "tests/test_host.mjs").write_text("throw new Error('must not run');\n")
        self.manifest["k12_only"] = ["test_host.mjs"]
        self.assertEqual(self.run_fixture()[0]["k12OnlyNotRun"], ["test_host.mjs"])

    def test_unknown_node_file_rejected(self):
        (self.root / "tests/test_host.mjs").write_text("")
        self.assertEqual(self.run_fixture(2)[0]["reason"], "test-file-inventory")

    def test_external_guard_override_rejected_without_echo(self):
        result = self.run_fixture(2, override="synthetic-value-not-for-output")
        self.assertEqual(result, [{"phase": "rejected", "reason": "external-guard-override"}])

    def test_version_mismatch_rejected(self):
        self.manifest["python_version"] = "0.0.0"
        self.assertEqual(self.run_fixture(2)[0]["reason"], "python-version")

    def test_manifest_count_types_fail_closed(self):
        for value in (True, 0, -1, "1"):
            with self.subTest(value=value):
                self.manifest["python"]["test_example.py"] = value
                self.assertEqual(self.run_fixture(2)[0]["reason"], "python-manifest-entry")

    def test_duplicate_load_tests_is_rejected(self):
        self.test.write_text(PASS + "\ndef load_tests(loader, tests, pattern):\n    return unittest.TestSuite([tests, tests])\n")
        self.assertEqual(self.run_fixture(2)[0]["reason"], "duplicate-test-id")

    def test_source_mutation_invalidates_result(self):
        self.test.write_text(PASS.replace(": pass", ":\n        from pathlib import Path\n        p = Path(__file__)\n        p.write_text(p.read_text() + '# synthetic mutation\\n')"))
        self.assertFalse(self.run_fixture(1)[-1]["filesUnchanged"])
