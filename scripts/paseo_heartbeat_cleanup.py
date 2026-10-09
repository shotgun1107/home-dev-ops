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
import stat
import subprocess
import time


class CleanupError(Exception):
    def __init__(self, reason, receipt=None):
        super().__init__(reason)
        self.receipt = receipt


UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
SCHEDULE_LIMIT = 65536


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CleanupError("invalid-schedule")
        result[key] = value
    return result


def timestamp(value):
    if value is None:
        return True
    if not isinstance(value, str) or len(value) > 40:
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def read_owned_schedule(path, schedule_id, agent_id):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise CleanupError("schedule-unreadable")
            raw = handle.read(SCHEDULE_LIMIT + 1)
        if len(raw) > SCHEDULE_LIMIT:
            raise CleanupError("schedule-too-large")
        schedule = json.loads(raw, object_pairs_hook=unique_object)
    except FileNotFoundError:
        raise CleanupError("schedule-not-found") from None
    except (OSError, ValueError, RecursionError):
        raise CleanupError("schedule-unreadable") from None
    if not isinstance(schedule, dict):
        raise CleanupError("invalid-schedule")
    target = schedule.get("target")
    if (schedule.get("id") != schedule_id or not isinstance(target, dict)
            or target.get("type") != "agent" or target.get("agentId") != agent_id):
        raise CleanupError("schedule-owner-mismatch")
    if type(schedule.get("maxRuns")) is not int or schedule["maxRuns"] != 1:
        raise CleanupError("requires-one-run-heartbeat")
    runs = schedule.get("runs")
    if not isinstance(runs, list) or not all(isinstance(run, dict) for run in runs):
        raise CleanupError("invalid-runs")
    if schedule.get("status") not in ("active", "paused", "completed") or not timestamp(schedule.get("expiresAt")):
        raise CleanupError("invalid-schedule")
    for item in runs:
        if item.get("status") not in ("running", "succeeded", "failed"):
            raise CleanupError("invalid-runs")
        for key in ("id", "agentId"):
            value = item.get(key)
            if value is not None and (not isinstance(value, str) or not UUID.fullmatch(value)):
                raise CleanupError("invalid-run-metadata")
        if not all(timestamp(item.get(key)) for key in ("scheduledFor", "startedAt", "endedAt")):
            raise CleanupError("invalid-run-metadata")
    return schedule


def cleanup(paseo_home, schedule_id, agent_id, timeout, *, run=subprocess.run,
            monotonic=time.monotonic, sleep=time.sleep):
    if not re.fullmatch(r"[0-9a-f]{8}", schedule_id):
        raise CleanupError("invalid-heartbeat-id")
    if not agent_id:
        raise CleanupError("missing-caller-agent")
    if not isinstance(agent_id, str) or not UUID.fullmatch(agent_id):
        raise CleanupError("invalid-caller-agent")
    if type(timeout) is not int or not 1 <= timeout <= 900:
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
    if not runs:
        outcome = "no-run"
    elif len(runs) != 1:
        outcome = "unexpected-run-count"
    elif runs[0].get("status") == "failed":
        outcome = "failed-run"
    elif runs[0].get("status") == "succeeded" and runs[0].get("agentId") == agent_id:
        outcome = "succeeded-one-run"
    else:
        outcome = "unconfirmed-run"
    receipt = {
        "id": schedule_id,
        "agentId": agent_id,
        "scheduleStatusBeforeDelete": schedule["status"],
        "maxRuns": schedule["maxRuns"],
        "expiresAt": schedule.get("expiresAt"),
        "runOutcome": outcome,
        "idleResumeVerifiedByReceipt": False,
        "runs": [{key: item.get(key) for key in (
            "id", "scheduledFor", "startedAt", "endedAt", "status", "agentId"
        )} for item in runs],
    }
    try:
        try:
            result = run(["paseo", "--home", str(paseo_home), "heartbeat", "delete",
                          schedule_id, "--json"], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            raise CleanupError("delete-command-unavailable") from None
        if result.returncode != 0:
            raise CleanupError("delete-command-failed")
        try:
            if len(result.stdout) > SCHEDULE_LIMIT:
                raise ValueError("oversized acknowledgement")
            acknowledgement = json.loads(result.stdout)
        except (ValueError, RecursionError):
            raise CleanupError("invalid-delete-acknowledgement") from None
        if not isinstance(acknowledgement, dict) or acknowledgement != {
                "id": schedule_id, "status": "deleted"}:
            raise CleanupError("unexpected-delete-acknowledgement")
        if path.exists():
            raise CleanupError("schedule-still-present")
    except CleanupError as error:
        error.receipt = receipt
        raise
    receipt.update(deleted=True, observedAt=datetime.now(timezone.utc).isoformat())
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--home", type=Path,
                        default=Path(os.environ.get("PASEO_HOME", str(Path.home() / ".paseo"))))
    args = parser.parse_args()
    try:
        receipt = cleanup(args.home, args.id,
                          os.environ.get("PASEO_AGENT_ID", ""), args.timeout)
    except CleanupError as error:
        print(json.dumps({"deletionConfirmed": False, "reason": str(error),
                          "preDeleteReceipt": error.receipt}))
        return 2
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
