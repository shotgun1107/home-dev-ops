#!/usr/bin/env python3
"""K12 Paseo 0.10.3: isolated, bounded Director smoke test.
Only creates a pilot directory, one Director agent, and one maxRuns=1
schedule for that Director. Never sends to or changes the existing Astra.
"""
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ASTRA = "c9bb4cb7-d656-4fb6-a6a5-e8fbcd3745cd"
# Workspace was created by the first failed smoke before the invalid Codex mode
# was rejected. Reuse it; do not create another workspace to recover.
PILOT_WORKSPACE = "wks_547e4dc9c21a5743"
ROOT = Path.home() / ".paseo-director-pilot"
WORK = ROOT / "workspace"
STATE = ROOT / "state.json"
REPORT = ROOT / "smoke-result.json"
MAX_SECONDS = 510


def call(*args, timeout=25):
    env = os.environ.copy()
    env.pop("PASEO_AGENT_ID", None)
    env.pop("PASEO_WORKSPACE_ID", None)
    done = subprocess.run(["paseo", *args], text=True, capture_output=True,
                          timeout=timeout, env=env, check=False)
    if done.returncode:
        raise RuntimeError(
            f"paseo {args[0]} {args[1] if len(args) > 1 else ''} "
            f"failed (exit {done.returncode}): {done.stderr.strip()[:350]}"
        )
    return done.stdout


def api(*args, timeout=25):
    raw = call(*args, "--json", timeout=timeout)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Unexpected Paseo JSON output") from exc


def inspect(agent):
    obj = api("agent", "inspect", agent)
    if not isinstance(obj, dict) or not obj.get("Id"):
        raise RuntimeError("Paseo agent inspect response missing Id")
    return obj


def save_json(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def state_data():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {}


def safe_mode(mode):
    text = str(mode or "").lower()
    return "full-access" not in text and "bypass" not in text and bool(text)


def main():
    start = time.monotonic()
    report = {"experiment": "K12 Director 10-minute smoke",
              "startedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
              "astraId": ASTRA, "verdict": "INCOMPLETE", "phases": {}}
    state = {}
    try:
        version = call("--version").strip()
        report["paseoVersion"] = version
        if "0.10.3" not in version:
            raise RuntimeError("Expected Paseo 0.10.3; review CLI before proceeding")
        astra = inspect(ASTRA)
        report["phases"]["astraPreflight"] = "PASS"
        report["astraInitialStatus"] = astra.get("Status")
        report["astraMode"] = astra.get("Mode")
        if astra["Id"] != ASTRA:
            raise RuntimeError("Unexpected Astra agent ID")

        ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
        WORK.mkdir(mode=0o700, parents=True, exist_ok=True)
        (WORK / "AGENTS.md").write_text(
            "# K12 Director pilot: observation only\n"
            "You are above the existing Astra Max ONLY for a bounded pilot.\n"
            "You are NOT a writer and must not edit repositories or runtime.\n"
            "Do not send messages to any agent, create subagents, approve permissions, "
            "edit settings, start services, or modify Git/GitHub.\n"
            "When an agent is running, choose DEFER; never interrupt it.\n"
            "Report facts separately from unverified assumptions.\n"
            "This pilot does NOT authorize a permanent Director or a four-hour mission.\n"
        )
        save_json(WORK / "snapshot.json", {
            "existingSupervisor": {
                "id": ASTRA, "status": astra.get("Status"),
                "model": astra.get("Model"), "thinking": astra.get("Thinking")
            },
            "currentTask": "read-only Director lifecycle and Heartbeat smoke"
        })
        state = state_data()
        if state.get("workspaceId") not in (None, PILOT_WORKSPACE):
            raise RuntimeError("Pilot workspace state mismatch; stop for review")
        state["workspaceId"] = PILOT_WORKSPACE
        save_json(STATE, state)
        director_id = state.get("directorId")
        if director_id:
            director = inspect(director_id)
            if director.get("Name") != "K12 Director | bounded pilot":
                raise RuntimeError("State points to unrelated agent")
            report["phases"]["directorCreate"] = "REUSED"
        else:
            prompt = (
                "K12 DIRECTOR PILOT (read-only). Read AGENTS.md and snapshot.json "
                "in the current directory. Inspect the existing Astra agent "
                + ASTRA + " using read-only Paseo CLI only if available without "
                "elevated permission. Never request an approval, never send a "
                "message, never modify files or services. If live inspection "
                "is blocked, say so explicitly. Decide DEFER if the original "
                "Supervisor is running. Finish with exact line "
                "K12_DIRECTOR_INITIAL_COMPLETE."
            )
            data = api(
                "agent", "run", "--background", "--title",
                "K12 Director | bounded pilot", "--provider",
                "codex/gpt-6-astra", "--thinking", "max",
                "--mode", "auto", "--workspace", PILOT_WORKSPACE,
                "--cwd", str(WORK), "--label", "k12_role=director_pilot",
                prompt, timeout=40
            )
            director_id = data.get("agentId")
            if not director_id:
                raise RuntimeError("Director was not created")
            state["directorId"] = director_id
            save_json(STATE, state)
            director = inspect(director_id)
            report["phases"]["directorCreate"] = "PASS"
        report["directorId"] = director_id
        report["directorMode"] = director.get("Mode")
        report["directorModel"] = director.get("Model")
        report["directorThinking"] = director.get("Thinking")
        if director["Id"] != director_id or not safe_mode(director.get("Mode")):
            raise RuntimeError("Director mode not verified safe (no full-access/bypass)")
        if str(Path(director.get("Cwd", "")).resolve()) != str(WORK.resolve()):
            raise RuntimeError("Director cwd differs from isolated pilot directory")
        if director.get("Model") != "gpt-6-astra":
            raise RuntimeError("Unexpected Director model")
        if director.get("Mode") != "auto":
            raise RuntimeError("Director mode must be Codex auto/on-request")
        # Codex auto is workspace-write, NOT technically read-only.
        # This pilot is only instruction-restricted inside an isolated workspace.
        report["limitations"] = [
            "Codex auto is on-request/workspace-write, not technical read-only",
            "No Director-to-Astra delegation performed",
            "Existing workspace reused after original rejected agent creation"
        ]
        report["phases"]["directorIsolation"] = "PASS"

        if director.get("Status") != "idle":
            wait = api("agent", "wait", director_id,
                       "--timeout", "160s", timeout=180)
            report["initialWait"] = wait.get("status")
            if wait.get("status") != "idle":
                raise RuntimeError("Director did not become idle: " + str(wait.get("status")))
        director = inspect(director_id)
        if director.get("Status") != "idle" or director.get("PendingPermissions"):
            raise RuntimeError("Director not idle or has pending permissions")
        report["phases"]["initialAgentTurn"] = "PASS"

        heartbeat_id = state.get("heartbeatId")
        if heartbeat_id:
            report["phases"]["heartbeatCreate"] = "REUSED"
        else:
            tick = (
                "K12 Director pilot: one read-only automatic resumption. "
                "Read AGENTS.md; do not send, write, or request approvals. "
                "Report the safe action as DEFER and finish with "
                "K12_DIRECTOR_HEARTBEAT_COMPLETE."
            )
            schedule = api("schedule", "create", tick, "--target",
                           director_id, "--cron", "* * * * *",
                           "--timezone", "Asia/Seoul",
                           "--max-runs", "1", "--expires-in", "6m",
                           "--name", "K12 Director one-shot smoke", timeout=35)
            heartbeat_id = schedule.get("id")
            if not heartbeat_id:
                raise RuntimeError("Schedule create returned no ID")
            state["heartbeatId"] = heartbeat_id
            save_json(STATE, state)
            report["phases"]["heartbeatCreate"] = "PASS"
        report["heartbeatId"] = heartbeat_id
        schedule_file = Path.home() / ".paseo" / "schedules" / (heartbeat_id + ".json")
        deadline = min(start + MAX_SECONDS, time.monotonic() + 235)
        schedule_status = None
        while time.monotonic() < deadline:
            try:
                observed = json.loads(schedule_file.read_text())
                target = observed.get("target", {})
                if target.get("type") != "agent" or target.get("agentId") != director_id:
                    raise RuntimeError("Schedule target mismatch")
                if observed.get("maxRuns") != 1:
                    raise RuntimeError("Schedule is not bounded to one run")
                schedule_status = observed.get("status")
                runs = observed.get("runs", [])
                if schedule_status == "completed" and runs:
                    run = runs[-1]
                    report["heartbeatRun"] = {
                        "status": run.get("status"),
                        "agentId": run.get("agentId"),
                        "endedAt": run.get("endedAt")
                    }
                    if run.get("status") != "succeeded" or run.get("agentId") != director_id:
                        raise RuntimeError("Heartbeat finished unsuccessfully")
                    break
            except FileNotFoundError:
                pass
            except json.JSONDecodeError:
                pass
            time.sleep(4)
        else:
            raise RuntimeError("Heartbeat did not complete before smoke deadline: " + str(schedule_status))
        report["phases"]["automaticResumption"] = "PASS"
        director = inspect(director_id)
        if director.get("PendingPermissions"):
            raise RuntimeError("Director left a pending permission")
        if not safe_mode(director.get("Mode")):
            raise RuntimeError("Director mode changed unsafely")
        still_there = inspect(ASTRA)
        if still_there.get("Id") != ASTRA:
            raise RuntimeError("Existing Astra no longer accessible")
        report["astraFinalStatus"] = still_there.get("Status")
        report["phases"]["astraUnaffectedByThisScript"] = "PASS"
        report["verdict"] = "PASS_LIFECYCLE_ONLY"
    except Exception as exc:
        report["verdict"] = "FAIL_OR_BLOCKED"
        report["problem"] = str(exc)[:450]
    finally:
        report["elapsedSeconds"] = round(time.monotonic() - start, 2)
        report["endedAt"] = dt.datetime.now(dt.timezone.utc).isoformat()
        save_json(REPORT, report)
        print("\n=== K12 DIRECTOR SMOKE ===")
        print("RESULT:", report["verdict"])
        print("DIRECTOR:", report.get("directorId", "not-created"))
        print("WORKSPACE:", PILOT_WORKSPACE, "(reused)")
        print("ASTRA:", ASTRA[:8], "(never messaged)")
        print("HEARTBEAT:", report.get("heartbeatId", "not-created"))
        print("PHASES:", json.dumps(report["phases"], ensure_ascii=False))
        if report.get("problem"):
            print("PROBLEM:", report["problem"])
        print("ELAPSED:", report["elapsedSeconds"], "seconds")
        print("REPORT:", REPORT)
        print("LIMIT: No Director->Astra dispatch or 4-hour endurance test was performed.")
        print("No additional recurring schedule is activated.")
    return 0 if report["verdict"] == "PASS_LIFECYCLE_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
