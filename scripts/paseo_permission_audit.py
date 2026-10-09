#!/usr/bin/env python3
"""Offline accounting of selected permission evidence; never grants permission.

Input must be curated, non-secret evidence, not raw session logs. Actor evidence
is a caller-supplied citation, not cryptographic authentication. A user approval
channel, a native rejection label, and a completed command are different facts.
No network, subprocess, provider/config access, or output-file writes.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys


UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
ACTORS = {"human", "supervisor", "auto-review", "provider", "unknown"}
FIELDS = {
    "eventId", "agentId", "requestId", "operationId", "kind", "outcome",
    "label", "actor", "actorEvidence", "evidence", "inputAdjusted",
}
DENIED_RESULTS = {
    "denied", "denied with factual corrections",
    "denied with corrected runtime instructions, no mode/permission config change",
}


def require(condition, code):
    if not condition:
        # Do not echo invalid values: callers may accidentally supply raw logs.
        raise ValueError(code)


def token(value):
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9_.:/#\[\]-]{1,240}", value))


def codex_route(context):
    """Describe eligible routing from an observed native context, not UI mode."""
    policy = context.get("approval_policy")
    reviewer = context.get("approvals_reviewer")
    sandbox = context.get("sandbox_policy", {})
    sandbox = sandbox.get("type") if isinstance(sandbox, dict) else None
    if policy == "never":
        return "no-interactive-review"
    if policy != "on-request" or sandbox not in {"read-only", "workspace-write"}:
        return "unconfirmed"
    if reviewer == "user":
        return "user-channel-actor-unconfirmed"
    if reviewer in {"auto_review", "guardian_subagent"}:
        return "eligible-auto-review-not-an-observed-decision"
    return "unconfirmed"


def attribute(event):
    """Never infer a human click or exact deny rule from a transport label."""
    actor = event.get("actor", "unknown")
    if actor != "unknown" and event.get("actorEvidence"):
        return actor
    if event["kind"] == "denial" and event.get("label") in {"permission-rule", "forbidden"}:
        return "provider"
    return "unknown"


def audit_events(events):
    require(isinstance(events, list) and len(events) <= 10000, "invalid-event-list")
    counts = Counter()
    by_agent = {}
    seen_events = {}
    seen_operations = {}
    for event in events:
        require(isinstance(event, dict) and not (set(event) - FIELDS), "invalid-event-fields")
        require(token(event.get("eventId")) and token(event.get("evidence")), "missing-evidence-id")
        require(isinstance(event.get("agentId"), str) and
                re.fullmatch(UUID, event["agentId"]), "full-agent-id-required")
        kind = event.get("kind")
        require(kind in {"response", "denial", "execution"}, "invalid-event-kind")
        require(event.get("actor", "unknown") in ACTORS, "invalid-actor")
        require("actorEvidence" not in event or token(event["actorEvidence"]), "invalid-actor-evidence")
        require("inputAdjusted" not in event or type(event["inputAdjusted"]) is bool, "invalid-adjustment")
        if kind == "response":
            require(isinstance(event.get("requestId"), str) and
                    re.fullmatch(r"permission-(?:(?:exec|file|plan|question|mcp)-)?" + UUID,
                                 event["requestId"]), "full-request-id-required")
            require(event.get("outcome") in {"allow", "deny"}, "invalid-response")
            require(not event.get("inputAdjusted") or event["outcome"] == "allow", "adjusted-denial")
            require("operationId" not in event and "label" not in event, "mixed-event-kinds")
            identity = (event["agentId"], kind, event["requestId"])
        else:
            require(token(event.get("operationId")), "operation-id-required")
            require("requestId" not in event and "inputAdjusted" not in event, "mixed-event-kinds")
            identity = (event["agentId"], kind, event["operationId"])
            if kind == "execution":
                require(event.get("outcome") in {"success", "error", "interrupted", "unknown"}, "invalid-execution")
                require("label" not in event, "mixed-event-kinds")
            else:
                require(event.get("label") in {"permission-rule", "forbidden", "user-rejected", "auto-mode-bypass", "unknown"}, "invalid-denial-label")
                require("outcome" not in event, "mixed-event-kinds")
        event_key = (event["agentId"], event["eventId"])
        if event_key in seen_events:
            require(seen_events[event_key] == event, "conflicting-event-id")
            counts["duplicateObservations"] += 1
            continue
        seen_events[event_key] = event
        actor = attribute(event)
        signature = (event.get("outcome"), event.get("label"), actor, event.get("inputAdjusted", False))
        if identity in seen_operations:
            require(seen_operations[identity] == signature, "conflicting-operation-evidence")
            counts["duplicateObservations"] += 1
            continue
        seen_operations[identity] = signature
        counters = by_agent.setdefault(event["agentId"], Counter())
        if kind == "response":
            keys = ["responses", "allowed" if event["outcome"] == "allow" else "denied",
                    "responseActor:" + actor]
            if event.get("inputAdjusted"):
                keys.append("inputAdjustments")
        elif kind == "execution":
            keys = ["executionObservations", "execution:" + event["outcome"], "executionActor:" + actor]
        else:
            keys = ["denialObservations", "denialLabel:" + event["label"], "denialActor:" + actor]
        for key in keys:
            counts[key] += 1
            counters[key] += 1
    return {
        "schemaVersion": 1,
        "counts": dict(sorted(counts.items())),
        "byAgent": {k: dict(sorted(v.items())) for k, v in sorted(by_agent.items())},
        "limits": ["selected evidence only; absent observations are unconfirmed",
                   "responses are not executions; adjustments are a subset of allows",
                   "actor citations require independent verification",
                   "provider denial label does not identify the matching rule or classifier"],
    }


def ledger_events(ledger, actor="unknown", actor_evidence=None):
    """Adapt the checked-in S/M selected ledgers without emitting tool input."""
    require(isinstance(ledger, dict), "invalid-ledger")
    records = ledger.get("requests")
    require(isinstance(records, list) and len(records) <= 10000, "invalid-ledger-requests")
    events = []
    for index, record in enumerate(records):
        require(isinstance(record, dict), "invalid-ledger-record")
        result = record.get("result")
        require(isinstance(result, str) and (result == "allowed" or result in DENIED_RESULTS), "unknown-ledger-result")
        event = {
            "eventId": f"ledger:{index}",
            "agentId": record.get("agentId", ledger.get("agentId")),
            "requestId": record.get("requestId", record.get("id")),
            "kind": "response", "outcome": "allow" if result == "allowed" else "deny",
            "inputAdjusted": bool(record.get("inputAdjustment")),
            "actor": actor, "evidence": f"ledger/requests/{index}",
        }
        if actor_evidence is not None:
            event["actorEvidence"] = actor_evidence
        events.append(event)
    return events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["events", "ledger"])
    parser.add_argument("path", type=Path)
    parser.add_argument("--actor", choices=sorted(ACTORS), default="unknown")
    parser.add_argument("--actor-evidence", help="reviewed citation for ledger actor; never inferred")
    args = parser.parse_args()
    try:
        with args.path.open("rb") as stream:
            raw = stream.read(2 * 1024 * 1024 + 1)
        require(len(raw) <= 2 * 1024 * 1024, "input-too-large")
        data = json.loads(raw)
        events = ledger_events(data, args.actor, args.actor_evidence) if args.kind == "ledger" else data
        report = audit_events(events)
    except (OSError, ValueError, TypeError, KeyError):
        print('{"status":"invalid-evidence"}', file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
