#!/usr/bin/env python3
"""Read-only Paseo connectivity diagnosis; never starts or repairs a daemon.

Exit 0: CLI verified a reachable daemon. Exit 2: inconclusive/unreachable.
Only selected non-secret fields are emitted, never CLI stderr or credentials.
"""
import argparse
import json
import os
from pathlib import Path
import stat
import subprocess


def read_pid_metadata(paseo_home):
    """Bounded observation only; no lock removal or process ownership claim."""
    try:
        fd = os.open(paseo_home / "paseo.pid", os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                return None, "unreadable-or-invalid"
            raw = handle.read(65537)
        if len(raw) > 65536:
            return None, "unreadable-or-invalid"
        metadata = json.loads(raw)
        value = metadata.get("pid") if isinstance(metadata, dict) else None
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            started = metadata.get("startedAt")
            # Compare the identity stamp, but never echo it or treat PID visibility
            # as proof that the process is the expected daemon.
            return (value, started if isinstance(started, str) else None), "present"
    except (OSError, ValueError, RecursionError):
        pass
    return None, "unreadable-or-invalid"


def assess(status, recorded_pid, pid_visible):
    reachable = status.get("connectedDaemon") == "reachable"
    reported = status.get("localDaemon")
    if reachable:
        verdict = "reachable"
    elif recorded_pid is not None and not pid_visible:
        verdict = "recorded-pid-not-visible"
    else:
        verdict = "unconfirmed"
    return {
        "verdict": verdict,
        "cli_local_daemon_raw": reported if reported in ("running", "stopped") else "unknown",
        "connection_verified": reachable,
        "recorded_pid": recorded_pid,
        "recorded_pid_visible": pid_visible,
        "next_step": "none" if reachable else "compare with an authorized host-side status check; do not start/restart",
    }


def diagnose(paseo_home, *, proc_root=Path("/proc")):
    before, metadata_state = read_pid_metadata(paseo_home)
    recorded_pid = before[0] if before else None
    pid_visible = recorded_pid is not None and (proc_root / str(recorded_pid)).is_dir()
    status = {}
    cli_result = "failed"
    try:
        result = subprocess.run(
            ["paseo", "--home", str(paseo_home), "status", "--json"],
            text=True, capture_output=True, timeout=15,
        )
        if result.returncode != 0:
            cli_result = "nonzero-exit"
        else:
            if len(result.stdout) > 1048576:
                raise ValueError("oversized status")
            parsed = json.loads(result.stdout)
            if isinstance(parsed, dict):
                status = parsed
                cli_result = "ok"
            else:
                cli_result = "invalid-output"
    except FileNotFoundError:
        cli_result = "unavailable"
    except subprocess.TimeoutExpired:
        cli_result = "timeout"
    except OSError:
        cli_result = "execution-error"
    except (ValueError, RecursionError):
        cli_result = "invalid-output"
    after, after_state = read_pid_metadata(paseo_home)
    changed = before != after or metadata_state != after_state
    result = assess(status, recorded_pid, pid_visible)
    if changed:
        result.update(verdict="observation-changed", connection_verified=False,
                      next_step="repeat read-only identity/status comparison; do not start/restart")
    result.update(pid_metadata=metadata_state, cli_result=cli_result,
                  observation_changed=changed, pid_identity_verified=False,
                  cli_connection_reachable=status.get("connectedDaemon") == "reachable")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path,
                        default=Path(os.environ.get("PASEO_HOME", str(Path.home() / ".paseo"))))
    args = parser.parse_args()
    result = diagnose(args.home)
    print(json.dumps(result, indent=2))
    return 0 if result["connection_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
