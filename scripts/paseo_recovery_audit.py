#!/usr/bin/env python3
"""Offline recovery evidence check. Never executes, grants a lease, or repairs.

Input is an operator-curated snapshot, not authenticated live evidence. Exit 0
means reviewable/already completed within that snapshot, never permission to run.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat
import tempfile


LIMIT = 65536
IDENTITY = {"task", "job", "worktree", "runtime", "writer", "session", "branch", "epoch"}
EXTRA = {"localHead", "remoteHead", "prHead", "handoffHead", "observedAt", "clean",
         "writerState", "pendingPermissions", "children", "nativeComplete", "runtimeOwner",
         "effects", "receipt"}


class RecoveryError(Exception):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RecoveryError("invalid-snapshot")
        result[key] = value
    return result


def validate(data):
    def require(condition):
        if not condition:
            raise RecoveryError("invalid-snapshot")

    def sha(value):
        return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value)

    require(isinstance(data, dict) and set(data) == {"schema", "checkpoint", "observation"})
    require(type(data["schema"]) is int and data["schema"] == 1)
    c, o = data["checkpoint"], data["observation"]
    require(isinstance(c, dict) and set(c) == IDENTITY | {"head"})
    require(isinstance(o, dict) and set(o) == IDENTITY | EXTRA)
    for record in (c, o):
        for key in IDENTITY - {"epoch"}:
            require(isinstance(record[key], str) and
                    re.fullmatch(r"[A-Za-z0-9/][A-Za-z0-9_.:/-]{0,199}", record[key]))
        require(type(record["epoch"]) is int and record["epoch"] >= 0)
    require(sha(c["head"]))
    for key in ("localHead", "remoteHead", "prHead", "handoffHead"):
        require(o[key] is None or sha(o[key]))
    require(type(o["clean"]) is bool and type(o["nativeComplete"]) is bool)
    require(o["pendingPermissions"] is None or
            (type(o["pendingPermissions"]) is int and o["pendingPermissions"] >= 0))
    for key, allowed in {
        "writerState": ("idle", "running", "unknown"),
        "children": ("none", "present", "unknown"),
        "runtimeOwner": ("released", "previous", "other", "unknown"),
        "effects": ("absent", "verified", "unknown", "conflict"),
    }.items():
        require(o[key] in allowed)
    require(isinstance(o["observedAt"], str) and len(o["observedAt"]) <= 40)
    try:
        stamp = datetime.fromisoformat(o["observedAt"].replace("Z", "+00:00"))
        require(stamp.tzinfo is not None)
    except ValueError:
        raise RecoveryError("invalid-snapshot") from None
    receipt = o["receipt"]
    if receipt is not None:
        require(isinstance(receipt, dict) and set(receipt) == {"job", "head", "outcome"})
        require(isinstance(receipt["job"], str) and len(receipt["job"]) <= 200)
        require(sha(receipt["head"]) and receipt["outcome"] in ("succeeded", "failed"))
    return c, o, stamp


def assess(data, *, now=None):
    c, o, stamp = validate(data)
    reasons = []
    age = ((now or datetime.now(timezone.utc)) - stamp).total_seconds()
    if age < -5 or age > 60:
        reasons.append("observation-not-fresh")
    if any(c[key] != o[key] for key in IDENTITY):
        reasons.append("identity-or-ownership-mismatch")
    if c["branch"] in ("main", "master", "refs/heads/main", "refs/heads/master"):
        reasons.append("protected-branch")
    if any(o[key] != c["head"] for key in ("localHead", "remoteHead", "prHead", "handoffHead")):
        reasons.append("revision-unconfirmed")
    if not o["clean"]:
        reasons.append("uncommitted-state")
    if (o["writerState"] != "idle" or o["pendingPermissions"] != 0
            or o["children"] != "none" or not o["nativeComplete"]):
        reasons.append("previous-writer-not-quiescent")
    if o["runtimeOwner"] != "released":
        reasons.append("runtime-not-released")
    receipt = o["receipt"]
    if receipt and (receipt["job"] != c["job"] or receipt["head"] != c["head"]):
        reasons.append("receipt-mismatch")
    if reasons:
        decision = "blocked"
    elif receipt and receipt["outcome"] == "succeeded" and o["effects"] == "verified":
        decision = "already-completed"
    elif o["effects"] == "absent" and (not receipt or receipt["outcome"] == "failed"):
        decision = "retry-reviewable" if receipt else "handoff-reviewable"
    else:
        decision = "reconcile-effects"
        reasons.append("effects-or-outcome-unconfirmed")
    return {"decision": decision, "reasons": reasons, "automaticAction": "none",
            "snapshotAuthenticated": False, "liveLeaseAcquired": False}


def read_snapshot(path):
    # Reject symlinks and FIFOs rather than following unrelated data or hanging.
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise RecoveryError("invalid-snapshot")
        raw = handle.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise RecoveryError("invalid-snapshot")
    return json.loads(raw, object_pairs_hook=unique_object)


def publish_snapshot(path, data):
    """Candidate atomic publisher; caller must own path/dir. No CLI write mode.

    This task invokes it only in disposable fixtures. Failed temp files remain
    for investigation. Any error after replace means publication is uncertain;
    read the destination before retrying. This is not a multi-writer lock.
    """
    validate(data)
    raw = (json.dumps(data, sort_keys=True) + "\n").encode()
    if len(raw) > LIMIT:
        raise RecoveryError("invalid-snapshot")
    path = Path(path)
    try:
        fd, temporary = tempfile.mkstemp(prefix=".recovery-", suffix=".tmp", dir=path.parent)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except OSError:
        raise RecoveryError("publication-failed-or-uncertain") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    try:
        result = assess(read_snapshot(args.snapshot))
    except (OSError, ValueError, RecursionError, RecoveryError):
        result = {"decision": "blocked", "reasons": ["invalid-snapshot"],
                  "automaticAction": "none", "snapshotAuthenticated": False,
                  "liveLeaseAcquired": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["decision"] in ("handoff-reviewable", "retry-reviewable", "already-completed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
