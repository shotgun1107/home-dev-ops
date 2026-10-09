#!/usr/bin/env python3
"""Delete this Paseo agent's one-run heartbeat after its run has finished.

This bounded cleanup command never starts an agent, edits a schedule file, or
changes daemon configuration. Run it independently of the scheduled agent turn:
waiting inside that turn would prevent the run from reaching completed status.
The JSON receipt contains only selected schedule fields, never raw CLI errors.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import time


class CleanupError(Exception):
    pass


def read_owned_schedule(path, schedule_id, agent_id):
    try:
        schedule = json.loads(path.read_text())
    except FileNotFoundError:
        raise CleanupError("schedule-not-found") from None
    except (OSError, ValueError):
        raise CleanupError("schedule-unreadable") from None
    if not isinstance(schedule, dict):
        raise CleanupError("invalid-schedule")
    target = schedule.get("target")
    if (schedule.get("id") != schedule_id or not isinstance(target, dict)
            or target.get("type") != "agent" or target.get("agentId") != agent_id):
        raise CleanupError("schedule-owner-mismatch")
    if schedule.get("maxRuns") != 1:
        raise CleanupError("requires-one-run-heartbeat")
    runs = schedule.get("runs")
    if not isinstance(runs, list) or not all(isinstance(run, dict) for run in runs):
        raise CleanupError("invalid-runs")
    return schedule


def cleanup(paseo_home, schedule_id, agent_id, timeout, *, run=subprocess.run,
            monotonic=time.monotonic, sleep=time.sleep):
    if not re.fullmatch(r"[0-9a-f]{8}", schedule_id):
        raise CleanupError("invalid-heartbeat-id")
    if not agent_id:
        raise CleanupError("missing-caller-agent")
    if not 1 <= timeout <= 900:
        raise CleanupError("invalid-timeout")
    path = paseo_home / "schedules" / f"{schedule_id}.json"
    deadline = monotonic() + timeout
    while True:
        schedule = read_owned_schedule(path, schedule_id, agent_id)
        runs = schedule["runs"]
        if schedule.get("status") == "completed" and all(
                item.get("status") in {"succeeded", "failed"} for item in runs):
            break
        if monotonic() >= deadline:
            raise CleanupError("waiting-for-completion-timed-out")
        sleep(1)
    # Keep the final run evidence before the supported API removes its record.
    receipt = {
        "id": schedule_id,
        "agentId": agent_id,
        "scheduleStatusBeforeDelete": schedule["status"],
        "maxRuns": schedule["maxRuns"],
        "expiresAt": schedule.get("expiresAt"),
        "runs": [{key: item.get(key) for key in (
            "id", "scheduledFor", "startedAt", "endedAt", "status", "agentId"
        )} for item in runs],
    }
    try:
        result = run(["paseo", "--home", str(paseo_home), "heartbeat", "delete",
                      schedule_id, "--json"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        raise CleanupError("delete-command-unavailable") from None
    if result.returncode != 0:
        raise CleanupError("delete-command-failed")
    try:
        acknowledgement = json.loads(result.stdout)
    except ValueError:
        raise CleanupError("invalid-delete-acknowledgement") from None
    if not isinstance(acknowledgement, dict) or acknowledgement != {
            "id": schedule_id, "status": "deleted"}:
        raise CleanupError("unexpected-delete-acknowledgement")
    if path.exists():
        raise CleanupError("schedule-still-present")
    receipt.update(deleted=True, observedAt=datetime.now(timezone.utc).isoformat())
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    try:
        receipt = cleanup(Path.home() / ".paseo", args.id,
                          os.environ.get("PASEO_AGENT_ID", ""), args.timeout)
    except CleanupError as error:
        print(json.dumps({"deletionConfirmed": False, "reason": str(error)}))
        return 2
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
