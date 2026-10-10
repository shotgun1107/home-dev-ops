"""Actual Git hook dispatch, using only disposable local repositories.

No network, real repository configuration, main ref, or force push is used.
The trace/replay shim and downstream stub are test fixtures, not installers or
an LFS implementation. Bypass cases document why a local hook is not a server
security boundary. All subprocesses and synthetic pushes have bounded waits.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


GUARD = Path(__file__).resolve().parents[1] / "scripts/k12-pre-push"


class GitGuardIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="k12-git-hook-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "writer"
        self.remote = self.root / "destination.git"
        self.repo.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update({
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_ALLOW_PROTOCOL": "file", "GIT_TERMINAL_PROMPT": "0",
            "GIT_AUTHOR_NAME": "K12 fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "K12 fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        })
        self.git("init", "--quiet", "--template=", "--object-format=sha1",
                 "--initial-branch=mock-topic")
        self.git("init", "--quiet", "--bare", "--template=", "--object-format=sha1",
                 "--initial-branch=fixture-default", str(self.remote))
        self.git("commit", "--quiet", "--allow-empty", "-m", "fixture base")
        self.base = self.git("rev-parse", "HEAD").stdout.strip()
        self.guard = self.root / "guard"
        shutil.copyfile(GUARD, self.guard)
        self.trace = self.root / "guard-input.json"
        self.downstream = self.root / "synthetic-downstream"
        self.downstream_trace = self.root / "downstream-input.json"
        self.hook = self.repo / ".git/hooks/pre-push"
        self.hook.parent.mkdir()
        self.write_hook(self.hook)

    def git(self, *args, cwd=None, check=True):
        return subprocess.run(["git", *args], cwd=cwd or self.repo, env=self.env,
                              text=True, capture_output=True, timeout=10, check=check)

    def write_hook(self, target):
        # Replaying stdin is necessary: merely invoking hooks sequentially
        # leaves the second consumer at EOF. This is a fixture-only shim.
        target.write_text(f'''#!{sys.executable}
import json, pathlib, subprocess, sys
data = sys.stdin.buffer.read()
pathlib.Path({str(self.trace)!r}).write_text(json.dumps({{"argv": sys.argv[1:], "stdin": data.decode("ascii")}}))
result = subprocess.run(["bash", {str(self.guard)!r}, *sys.argv[1:]], input=data, timeout=5)
if result.returncode:
    sys.exit(result.returncode)
downstream = pathlib.Path({str(self.downstream)!r})
if downstream.exists():
    result = subprocess.run([str(downstream), *sys.argv[1:]], input=data, timeout=5)
    sys.exit(result.returncode)
''')
        target.chmod(0o700)

    def write_downstream(self, status):
        self.downstream.write_text(f'''#!{sys.executable}
import json, pathlib, sys
data = sys.stdin.buffer.read()
pathlib.Path({str(self.downstream_trace)!r}).write_text(json.dumps({{"argv": sys.argv[1:], "stdin": data.decode("ascii")}}))
sys.exit({status})
''')
        self.downstream.chmod(0o700)

    def push(self, *options, cwd=None):
        return self.git("push", "--porcelain", *options, str(self.remote),
                        "HEAD:refs/heads/mock-topic", cwd=cwd, check=False)

    def delete_topic(self, *options, cwd=None, config=()):
        return self.git(*config, "push", "--porcelain", *options, str(self.remote),
                        ":refs/heads/mock-topic", cwd=cwd, check=False)

    def remote_ref(self):
        r = self.git("--git-dir=" + str(self.remote), "rev-parse", "--verify",
                     "refs/heads/mock-topic", check=False)
        return r.stdout.strip() if r.returncode == 0 else None

    def seed(self):
        r = self.push()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.remote_ref(), self.base)
        self.trace.unlink()

    def test_git_dispatches_exact_input_for_new_branch_and_fast_forward(self):
        self.seed()
        self.git("commit", "--quiet", "--allow-empty", "-m", "fixture child")
        child = self.git("rev-parse", "HEAD").stdout.strip()
        r = self.push()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.remote_ref(), child)
        observed = json.loads(self.trace.read_text())
        self.assertEqual(observed["argv"], [str(self.remote), str(self.remote)])
        self.assertEqual(observed["stdin"],
                         f"HEAD {child} refs/heads/mock-topic {self.base}\n")

    def test_linked_worktree_uses_common_hook_and_blocks_deletion(self):
        self.seed()
        linked = self.root / "linked-writer"
        self.git("worktree", "add", "--quiet", "-b", "mock-linked", str(linked))
        common = self.git("rev-parse", "--path-format=absolute", "--git-common-dir",
                          cwd=linked).stdout.strip()
        self.assertEqual(Path(common), self.repo / ".git")
        r = self.delete_topic(cwd=linked)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("branch deletion", r.stderr)
        self.assertEqual(self.remote_ref(), self.base)
        self.assertTrue(self.trace.is_file())

    def test_explicit_hooks_path_dispatches_selected_hook(self):
        self.seed()
        custom = self.root / "custom-hooks"
        custom.mkdir()
        self.write_hook(custom / "pre-push")
        r = self.delete_topic(config=("-c", f"core.hooksPath={custom}"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("branch deletion", r.stderr)
        self.assertEqual(self.remote_ref(), self.base)
        self.assertTrue(self.trace.is_file())

    def test_no_verify_bypasses_only_disposable_local_hook(self):
        self.seed()
        r = self.delete_topic("--no-verify")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIsNone(self.remote_ref())
        self.assertFalse(self.trace.exists())

    def test_empty_hooks_path_bypasses_only_disposable_local_hook(self):
        self.seed()
        empty = self.root / "empty-hooks"
        empty.mkdir()
        r = self.delete_topic(config=("-c", f"core.hooksPath={empty}"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIsNone(self.remote_ref())
        self.assertFalse(self.trace.exists())

    def test_nonexecutable_hook_is_not_enforced(self):
        self.seed()
        self.hook.chmod(0o600)
        r = self.delete_topic()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIsNone(self.remote_ref())
        self.assertFalse(self.trace.exists())

    def test_chain_replays_identical_stdin_and_arguments(self):
        self.write_downstream(0)
        r = self.push()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.remote_ref(), self.base)
        self.assertEqual(json.loads(self.trace.read_text()),
                         json.loads(self.downstream_trace.read_text()))
        self.assertIn("refs/heads/mock-topic", json.loads(self.trace.read_text())["stdin"])

    def test_downstream_refusal_prevents_remote_update(self):
        self.write_downstream(42)
        r = self.push()
        self.assertNotEqual(r.returncode, 0)
        self.assertIsNone(self.remote_ref())
        self.assertEqual(json.loads(self.trace.read_text()),
                         json.loads(self.downstream_trace.read_text()))


if __name__ == "__main__":
    unittest.main()
