"""Exercise an uninstalled guard against Git objects in a disposable local repo.

Set K12_GUARD_UNDER_TEST to test the existing Kerbe hook read-only.
No remote connection or push is performed; inputs are Git's pre-push protocol.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


GUARD = Path(os.environ.get(
    "K12_GUARD_UNDER_TEST",
    str(Path(__file__).resolve().parents[1] / "scripts/k12-pre-push"),
)).resolve()
ZERO = "0" * 40


class PrePushGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="k12-guard-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.cwd = Path(cls.temp.name)
        cls.env = os.environ.copy()
        for key in list(cls.env):
            if key.startswith("GIT_"):
                del cls.env[key]
        cls.env.update({
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_NAME": "K12 isolated test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "K12 isolated test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
        })
        cls.git("init", "--quiet", "--object-format=sha1", "--initial-branch=test-fixture")
        cls.git("commit", "--quiet", "--allow-empty", "-m", "base")
        cls.base = cls.git("rev-parse", "HEAD")
        cls.git("commit", "--quiet", "--allow-empty", "-m", "child")
        cls.child = cls.git("rev-parse", "HEAD")
        tree = cls.git("rev-parse", "HEAD^{tree}")
        cls.other = cls.git("commit-tree", tree, "-m", "unrelated root")

    @classmethod
    def git(cls, *args):
        return subprocess.check_output(["git", *args], cwd=cls.cwd,
                                       env=cls.env, text=True).strip()

    def invoke(self, records):
        return subprocess.run(["bash", str(GUARD), "origin", "/unused-local-remote"],
                              input=records, text=True, capture_output=True,
                              cwd=self.cwd, env=self.env, timeout=10)

    def record(self, local, remote, ref="refs/heads/topic"):
        return f"refs/heads/topic {local} {ref} {remote}\n"

    def assert_blocked(self, records, diagnostic):
        result = self.invoke(records)
        self.assertNotEqual(result.returncode, 0, result)
        self.assertIn(diagnostic, result.stderr)

    def test_main_creation_blocked(self):
        self.assert_blocked(self.record(self.child, ZERO, "refs/heads/main"), "direct push to main")

    def test_main_fast_forward_blocked(self):
        self.assert_blocked(self.record(self.child, self.base, "refs/heads/main"), "direct push to main")

    def test_branch_deletion_blocked(self):
        self.assert_blocked(f"(delete) {ZERO} refs/heads/topic {self.base}\n", "branch deletion")

    def test_new_topic_allowed(self):
        self.assertEqual(self.invoke(self.record(self.child, ZERO)).returncode, 0)

    def test_fast_forward_allowed(self):
        self.assertEqual(self.invoke(self.record(self.child, self.base)).returncode, 0)

    def test_unchanged_allowed(self):
        self.assertEqual(self.invoke(self.record(self.base, self.base)).returncode, 0)

    def test_rewind_blocked(self):
        self.assert_blocked(self.record(self.base, self.child), "non-fast-forward")

    def test_divergence_blocked(self):
        self.assert_blocked(self.record(self.other, self.base), "non-fast-forward")

    def test_unknown_remote_object_blocked(self):
        self.assert_blocked(self.record(self.child, "f" * 40), "cannot verify fast-forward")

    def test_mixed_refs_preserve_failure(self):
        self.assert_blocked(self.record(self.child, ZERO) +
                            self.record(self.child, ZERO, "refs/heads/main"), "direct push to main")

    def test_tags_outside_branch_policy(self):
        self.assertEqual(self.invoke(self.record(self.child, ZERO, "refs/tags/test")).returncode, 0)

    def test_empty_input(self):
        self.assertEqual(self.invoke("").returncode, 0)


if __name__ == "__main__":
    unittest.main()
