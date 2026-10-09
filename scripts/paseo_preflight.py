#!/usr/bin/env python3
"""Read-only Paseo connectivity diagnosis; never starts or repairs a daemon.

Exit 0: CLI verified a reachable daemon. Exit 2: inconclusive/unreachable.
Only selected non-secret fields are emitted, never CLI stderr or credentials.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess


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
        "local_daemon_report": reported if reported in ("running", "stopped") else "unknown",
        "connection_verified": reachable,
        "recorded_pid": recorded_pid,
        "recorded_pid_visible": pid_visible,
        "next_step": "none" if reachable else "compare with an authorized host-side status check; do not start/restart",
    }


def diagnose(paseo_home):
    recorded_pid = None
    metadata_state = "unreadable-or-invalid"
    try:
        metadata = json.loads((paseo_home / "paseo.pid").read_text())
        value = metadata.get("pid") if isinstance(metadata, dict) else None
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            recorded_pid = value
            metadata_state = "present"
    except (OSError, ValueError):
        pass
    pid_visible = recorded_pid is not None and Path("/proc", str(recorded_pid)).is_dir()
    status = {}
    cli_result = "unavailable"
    try:
        result = subprocess.run(
            ["paseo", "--home", str(paseo_home), "status", "--json"],
            text=True, capture_output=True, timeout=15,
        )
        parsed = json.loads(result.stdout)
        if result.returncode == 0 and isinstance(parsed, dict):
            status = parsed
            cli_result = "ok"
        else:
            cli_result = "failed"
    except (OSError, ValueError, subprocess.TimeoutExpired):
        cli_result = "failed"
    return {**assess(status, recorded_pid, pid_visible),
            "pid_metadata": metadata_state, "cli_result": cli_result}


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
