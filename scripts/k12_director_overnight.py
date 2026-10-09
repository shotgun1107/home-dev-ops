#!/usr/bin/env python3
"""K12 Paseo Director -> Astra overnight runner (Paseo 0.10.3).

Runs only as the current user. Deterministic host-side dispatch gates protect
the existing Astra from interrupts. A separate Codex-auto Director selects
from an allowlist of operational audits. No automatic merges, main pushes,
credential/permission changes, Kerbe edits, daemon or Minecraft operations.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path.home() / ".paseo-director-pilot"
WORK = ROOT / "workspace"
NIGHT = ROOT / "overnight"
RECEIPTS = NIGHT / "receipts"
STATE = NIGHT / "state.json"
STATUS = NIGHT / "status.json"
DECISION = WORK / "director-decision.json"
SNAPSHOT = WORK / "director-snapshot.json"
LOG = NIGHT / "controller.log"
LOCK = NIGHT / "controller.lock"
ASTRA = "c9bb4cb7-d656-4fb6-a6a5-e8fbcd3745cd"
DIRECTOR = "e2f92291-4ca9-445e-b94b-47de32029af7"
WORKSPACE = "wks_547e4dc9c21a5743"
VERSION = "0.10.3"
HOURS = 7
TASK_LIMIT_SEC = 65 * 60
DIRECTOR_LIMIT_SEC = 210
POLL = 12

# These are operational validation tasks, not product development tasks.
TASKS = {
    "P0_HEARTBEAT": (
        "Investigate long-lived heartbeat correctness, expiry, duplicate tick, and "
        "crash/active-run behavior, using only bounded isolated simulations and "
        "existing Paseo evidence; no daemon restarts or auth changes. "
        "Produce reproducible evidence and candidate docs/tests."
    ),
    "P0_PERMISSIONS": (
        "Audit effective permission approval routing, Codex auto/auto-review "
        "and Claude deny behavior from saved evidence and installed sources. "
        "Do not run risky merge/push probes. Build synthetic regression checks "
        "for decision attribution and accurate permission accounting."
    ),
    "P0_RECOVERY": (
        "Design and execute failure-injection tests in isolated temporary dirs "
        "for handoff interruption, stale PID/daemon visibility, and job recovery. "
        "Leave existing sessions and services untouched. Validate fixes "
        "with bounded regression tests and independent review."
    ),
    "OPS_CI": (
        "Reconcile home-dev-ops Draft PR #1 latest test code with stale "
        "ops CI Draft PR #2 (21 vs 30 tests). Verify candidate workflow "
        "in an isolated test branch/worktree if safe; only Draft PR, no Ready "
        "or merge. If a repository protection issue prevents safe writes, "
        "document an exact human-ready proposal instead."
    ),
    "P1_PARALLEL_ISOLATED": (
        "Set up two strictly independent disposable mock tasks in isolated "
        "directories, each with one writer and no shared dirty worktree. "
        "Test scheduling/concurrent coordination and approval burden. "
        "Do NOT edit Kerbe, do not claim formal P1 parallel completion before "
        "its main-merge prerequisite, and do not weaken gates."
    ),
    "REVIEW_INDEPENDENT": (
        "Independently review newest operational scripts, tests, control "
        "assumptions, and security boundaries at a fixed SHA via a separate "
        "read-only-by-policy reviewer. Record actual reader limitations and "
        "fix/review any verified problems safely."
    ),
    "DOCS_RECONCILE": (
        "Consolidate measured operational findings into existing Draft "
        "home-dev-ops PR #1 (STATUS/EVIDENCE/RECOVERY/REVISION) without "
        "overwriting source v2.4. Verify references, sha, check status, "
        "contradictions, and document exactly what's still blocked."
    ),
    "OVERNIGHT_REPORT": (
        "Prepare a precise overnight handoff in home-dev-ops Draft PR #1. "
        "Include tested outcomes, remaining gaps, exact SHA/PR links, "
        "cost/approval counts, and next safe actions; do not mark untested "
        "items passed, merge/Ready, or alter Kerbe."
    ),
}

AGENTS = """# K12 Director: isolated, user-authorized overnight operations
The previous 1-shot smoke is complete. The user has authorized a *new*
7-hour bounded orchestration phase that supersedes the smoke-only restriction
on writing LOCAL pilot decision files. All other safety restrictions remain.
You are the Director, not a code writer.
You may read director-snapshot.json and write ONLY director-decision.json
inside this isolated pilot workspace. Do not modify any repository or
credential, call Git/Paseo to send/cancel agents, grant permissions, change
mode, schedule runs, or control services.
A deterministic host-side controller validates your selected task ID and
only it may send a prewritten, allowlisted task to the existing Astra when
Astra is confirmed idle and without pending approval.
The business user's Kerbe repo is frozen: local company-only changes exist.
No Kerbe main/branch/PR modifications. No Ready/Merge/main push anywhere.
Never invent a 'passed' test. Report uncertain outcomes as blocked.
"""

GLOBAL_GATES = """Mandatory safety constraints for this overnight K12 ops evaluation:
- Keep existing Astra Max, Director, workspaces, and user services intact.
- Never edit any Kerbe code or branch, never Ready/Merge Kerbe PR #2/#5.
  Company-local Git changes are not yet synced.
- Never Ready/Merge any GitHub PR; never push directly to main or force push.
- Never change permissions, rulesets, auth/token, common hooks, config, model
  or provider privileges. Don't auto-archive or prune anything.
- Never restart, stop, or reconfigure Paseo, Minecraft, Docker, SSH, Tailscale.
- Do not touch real credential stores, personal token ledgers, DB or volumes.
- Only synthetic fixtures and task-owned disposable directories for tests.
- Max two writers overall, one writer/worktree. Separate reviewer and writer.
- Use only an authorized task branch/isolated worktree and existing ops
  Draft PR #1 for outcomes; log exact SHA/conditions/test results.
- If a prerequisite needs human decision, mark blocked and move on.
- Supervisor approvals must be reviewed per-request with full IDs; never
  allow-all or persistent rules; never auto approve risky classes.
- A live user message can interrupt running Paseo tasks. This controller
  dispatches only when the existing Astra is truly idle.
"""


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def atomic_json(path: Path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temp = path.with_suffix(".part")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


def read_json(path: Path, fallback=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return fallback


def log(message):
    line = utc() + " " + str(message)
    with LOG.open("a") as f:
        f.write(line + "\n")


def cli(*args, timeout=35):
    env = dict(os.environ)
    env.pop("PASEO_AGENT_ID", None)
    env.pop("PASEO_WORKSPACE_ID", None)
    p = subprocess.run(["paseo", *args, "--json"], text=True, capture_output=True,
                       timeout=timeout, env=env)
    if p.returncode:
        raise RuntimeError(
            "Paseo " + " ".join(args[:2]) + " exit=" + str(p.returncode)
            + ": " + p.stderr.strip()[-350:])
    try:
        return json.loads(p.stdout)
    except ValueError as exc:
        raise RuntimeError("Unexpected Paseo JSON output") from exc


def agent(agent_id):
    response = cli("agent", "inspect", agent_id)
    if not isinstance(response, dict) or response.get("Id") != agent_id:
        raise RuntimeError("Agent ID mismatch or missing: " + agent_id)
    return response


def pending(agent_snapshot):
    return bool(agent_snapshot.get("PendingPermissions"))


def idle(agent_snapshot):
    return agent_snapshot.get("Status") == "idle" and not pending(agent_snapshot)


def check_identities():
    a = agent(ASTRA)
    d = agent(DIRECTOR)
    if a.get("Model") != "gpt-6-astra" or a.get("Thinking") != "max":
        raise RuntimeError("Existing Astra identity changed")
    if d.get("Model") != "gpt-6-astra" or d.get("Mode") != "auto":
        raise RuntimeError("Director identity/mode changed")
    if Path(d.get("Cwd") or "/nonexistent").resolve() != WORK.resolve():
        raise RuntimeError("Director workspace path changed")
    if d.get("Mode") == "full-access":
        raise RuntimeError("Director unexpectedly full access")
    return a, d


def no_unknown_pending():
    # Do not authorize anything; report pending approvals in later status.
    try:
        q = cli("permit", "ls", timeout=15)
        # CLI shape is a version-specific list or structured object.
        if isinstance(q, list):
            return not bool(q)
        if isinstance(q, dict):
            if "data" in q and isinstance(q["data"], list):
                return not bool(q["data"])
            if "permissions" in q and isinstance(q["permissions"], list):
                return not bool(q["permissions"])
        return True
    except Exception:
        return False


def send(target, prompt):
    response = cli("agent", "send", target, "--prompt", prompt, "--no-wait")
    if response.get("status") != "sent":
        raise RuntimeError("Agent message not accepted")
    return response


def choose_task(state, currently_available):
    decision = None
    director_mode = "FALLBACK"
    d = agent(DIRECTOR)
    if not idle(d):
        return currently_available[0], "DIRECTOR_NOT_IDLE"
    ticket = uuid.uuid4().hex
    snap = {
        "ticket": ticket, "timestamp": utc(),
        "availableTasks": [{"id": k, "objective": TASKS[k]} for k in currently_available],
        "completed": state.get("completed", []),
        "failures": state.get("failures", []),
        "astra": {"id": ASTRA, "status": "idle"},
        "decisionFile": str(DECISION),
        "limitations": "one choice only; cannot dispatch to Astra directly"
    }
    SNAPSHOT.write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n")
    DECISION.unlink(missing_ok=True)
    prompt = (
        "Night Director task selection, newly authorized by human. "
        "Read AGENTS.md and director-snapshot.json. Select exactly one "
        "available task based on impact and dependencies. Write ONLY "
        "director-decision.json atomically containing {\"ticket\":\""
        + ticket + "\",\"taskId\":\"<one available ID>\","
        "\"reason\":\"<brief reason>\"}. Never send or execute another "
        "agent yourself. Return immediately once the JSON file exists."
    )
    try:
        send(DIRECTOR, prompt)
        until = time.monotonic() + DIRECTOR_LIMIT_SEC
        while time.monotonic() < until:
            decision = read_json(DECISION)
            if isinstance(decision, dict):
                task_id = decision.get("taskId")
                if decision.get("ticket") == ticket and task_id in currently_available:
                    director_mode = "DIRECTOR"
                    break
            if pending(agent(DIRECTOR)):
                log("Director awaiting permission; use deterministic fallback")
                break
            time.sleep(6)
    except Exception as exc:
        log("Director selection failed: " + str(exc)[:180])
    if director_mode != "DIRECTOR":
        return currently_available[0], "FALLBACK_NO_DECISION"
    return decision["taskId"], director_mode


def receipt_path(task_id):
    return RECEIPTS / (task_id + ".json")


def run_task(state, task_id, by, deadline):
    receipt = receipt_path(task_id)
    receipt.unlink(missing_ok=True)
    message = (
        "K12 NIGHT OPS TASK: " + task_id + "\n"
        "Objective: " + TASKS[task_id] + "\n\n" + GLOBAL_GATES
        + "\nFollow existing v2.4 and v2.4.1 Draft. "
        "Use existing home-dev-ops ops Worktree and Draft PR #1; "
        "do not edit the Kerbe repo. Use synthetic fixtures and bounded "
        "tests. If blocked, record facts and continue to a safe alternate "
        "within this same objective. Conduct independent fixed-SHA "
        "review on changes as needed. Record verified results on the "
        "home-dev-ops Draft PR #1; keep it Draft. "
        "IMPORTANT: Finally write JSON atomically at "
        + str(receipt)
        + " with fields {\"taskId\":\"" + task_id
        + "\",\"status\":\"completed|blocked|failed\","
        "\"summary\":\"...\",\"evidence\":\"...\"} "
        "without raw secrets. This receipt is required for the host "
        "coordinator to move to the next task. Only you write the receipt; "
        "no other agent must write it. Do not await human approval if an "
        "alternate safe analysis is possible. This is an authorized "
        "overnight user job, not a request to merge anything."
    )
    a = agent(ASTRA)
    if not idle(a) or not no_unknown_pending():
        raise RuntimeError("Astra is not idle or some permission is pending")
    state["active"] = {"taskId": task_id, "dispatchedAt": utc(), "by": by}
    atomic_json(STATE, state)
    send(ASTRA, message)
    log("Dispatched " + task_id + " via " + by)
    until = min(deadline, time.monotonic() + TASK_LIMIT_SEC)
    saw_running = False
    while time.monotonic() < until:
        time.sleep(POLL)
        a = agent(ASTRA)
        if a["Status"] == "running":
            saw_running = True
        if pending(a):
            # Supervisor can handle child permissions in its normal run. 
            # Do not inject a message while it is busy.
            continue
        saved = read_json(receipt)
        if isinstance(saved, dict) and saved.get("taskId") == task_id:
            if idle(a):
                status = saved.get("status")
                if status not in {"completed", "blocked", "failed"}:
                    raise RuntimeError("Malformed task receipt for " + task_id)
                state["active"] = None
                item = {"taskId": task_id, "status": status,
                        "finishedAt": utc(), "by": by, "summary": str(saved.get("summary", ""))[:260],
                        "evidence": str(saved.get("evidence", ""))[:360]}
                if status == "completed":
                    state["completed"].append(item)
                else:
                    state["failures"].append(item)
                atomic_json(STATE, state)
                log("Finished " + task_id + " => " + status)
                return
        if idle(a) and saw_running and saved is None:
            # Give a short grace period for a delayed receipt, but do not
            # invent completion and never send another task into ambiguity.
            if time.monotonic() > until - 25:
                break
    raise RuntimeError("Astra completion not confirmed for " + task_id
                       + "; leaving state for human, no duplicate dispatch")


def write_status(state, kind, details=None):
    msg = {
        "state": kind,
        "updatedAt": utc(),
        "startedAt": state.get("startedAt"),
        "completed": len(state.get("completed", [])),
        "failures": len(state.get("failures", [])),
        "remainingTasks": [t for t in TASKS if t not in {
            x["taskId"] for x in state.get("completed", []) + state.get("failures", [])
        }],
        "active": state.get("active"),
        "directorId": DIRECTOR, "astraId": ASTRA,
        "note": details
    }
    atomic_json(STATUS, msg)


def run():
    NIGHT.mkdir(mode=0o700, parents=True, exist_ok=True)
    RECEIPTS.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = LOCK.open("w")
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("Second controller prevented by flock")
        return 1
    state = read_json(STATE)
    if not isinstance(state, dict):
        raise RuntimeError("Controller state is missing/corrupt")
    deadline = time.monotonic() + HOURS * 3600
    log("Overnight controller started; cap " + str(HOURS) + " hours")
    try:
        if state.get("active"):
            raise RuntimeError("Previous active task unresolved; refuse duplicate dispatch")
        while time.monotonic() < deadline:
            write_status(state, "running")
            remain = [task for task in TASKS if task not in {
                v["taskId"] for v in state["completed"] + state["failures"]
            }]
            if not remain:
                write_status(state, "complete")
                log("All allowlisted tasks attempted")
                return 0
            a, _ = check_identities()
            if pending(a):
                log("Astra has pending permission; pause and inspect later")
                time.sleep(30)
                continue
            if not idle(a):
                # Never message a running Astra; this is an intentional wait.
                time.sleep(30)
                continue
            if not no_unknown_pending():
                time.sleep(30)
                continue
            task, by = choose_task(state, remain)
            # A human message could have started Astra during selection:
            a = agent(ASTRA)
            if not idle(a):
                continue
            run_task(state, task, by, deadline)
            write_status(state, "running")
    except Exception as exc:
        reason = str(exc)[:450]
        log("STOPPED: " + reason)
        write_status(state, "blocked", reason)
        return 1
    write_status(state, "expired", "Time limit reached; no new dispatches")
    log("Time limit reached")
    return 0


def start():
    for path in (ROOT, WORK, NIGHT, RECEIPTS):
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if shutil.which("paseo") is None or shutil.which("systemd-run") is None:
        raise RuntimeError("paseo or systemd-run missing")
    version = subprocess.run(["paseo", "--version"], text=True, capture_output=True, timeout=8)
    if VERSION not in version.stdout:
        raise RuntimeError("Unexpected Paseo version; no start")
    a, d = check_identities()
    if not idle(d):
        raise RuntimeError("Director is not idle; don't interrupt its running task")
    if pending(a) or not no_unknown_pending():
        raise RuntimeError("Pending approval exists; cannot safely start")
    old = read_json(STATE)
    if isinstance(old, dict) and old.get("active"):
        raise RuntimeError("Previous dispatch unconfirmed; refuse second run")
    if isinstance(old, dict) and old.get("startedAt") and old.get("endStatus") != "complete":
        raise RuntimeError("Previous overnight job exists; inspect status before restarting")
    WORK.joinpath("AGENTS.md").write_text(AGENTS)
    # Files under WORK are the ONLY files the Director can edit.
    (WORK / "AGENTS.md").chmod(0o600)
    state = {"startedAt": utc(), "directorId": DIRECTOR, "astraId": ASTRA,
             "completed": [], "failures": [], "active": None}
    atomic_json(STATE, state)
    write_status(state, "starting")
    # Clear previous test's one-shot completed heartbeat? No; preserve evidence.
    # No new cron/heartbeat is needed; the bounded user service wakes agents.
    python = sys.executable
    source = str(Path(__file__).resolve())
    unit = "k12-director-night"
    cmd = [
        "systemd-run", "--user", "--unit=" + unit, "--collect",
        "--property=RuntimeMaxSec=" + str(HOURS * 3600 + 120),
        "--setenv=PATH=" + os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        python, source, "run"
    ]
    p = subprocess.run(cmd, text=True, capture_output=True, timeout=20)
    if p.returncode:
        write_status(state, "start-failed", p.stderr.strip()[:500])
        raise RuntimeError("user systemd-run failed: " + p.stderr.strip()[:450])
    print("STARTED: " + unit)
    print("DIRECTOR:", DIRECTOR)
    print("ASTRA:", ASTRA)
    print("MAX_RUNTIME:", HOURS, "hours")
    print("SCHEDULED_TASKS:", len(TASKS))
    print("STATUS:", STATUS)
    print("LOG: journalctl --user -u " + unit + " -n 20 --no-pager")
    print("NOTE: Existing Astra is never interrupted; only idle dispatch.")
    return 0


def show_status():
    s = read_json(STATUS)
    if not isinstance(s, dict):
        print("No controller state file yet")
        return 1
    print(json.dumps(s, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "start"
    try:
        if action == "start":
            sys.exit(start())
        if action == "run":
            sys.exit(run())
        if action == "status":
            sys.exit(show_status())
        raise ValueError("Usage: start | run | status")
    except Exception as e:
        print("ERROR:", str(e)[:450], file=sys.stderr)
        sys.exit(1)
