"""Synthetic permission evidence only: no agents, credentials, or remote Git."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/paseo_permission_audit.py"
spec = importlib.util.spec_from_file_location("permission_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
A = "11111111-1111-4111-8111-111111111111"
B = "22222222-2222-4222-8222-222222222222"
R = "permission-exec-33333333-3333-4333-8333-333333333333"


def response(**changes):
    return dict(eventId="response-1", agentId=A, requestId=R, kind="response",
                outcome="allow", evidence="synthetic/receipt/1", **changes)


def observation(kind="denial", **changes):
    event = dict(eventId="observation-1", agentId=A, operationId="synthetic-tool-1",
                 kind=kind, evidence="synthetic/native/1")
    event.update({"label": "user-rejected"} if kind == "denial" else {"outcome": "interrupted"})
    event.update(changes)
    return event


class AttributionTests(unittest.TestCase):
    def counts(self, events):
        return audit.audit_events(events)["counts"]

    def test_user_rejected_does_not_mean_human(self):
        self.assertEqual(self.counts([observation()])["denialActor:unknown"], 1)

    def test_actor_without_citation_stays_unknown(self):
        self.assertEqual(self.counts([response(actor="human")])["responseActor:unknown"], 1)

    def test_correlated_supervisor_response(self):
        counts = self.counts([response(actor="supervisor", actorEvidence="synthetic/supervisor/1")])
        self.assertEqual(counts["responseActor:supervisor"], 1)
        self.assertNotIn("responseActor:human", counts)

    def test_explicit_human_and_auto_review_need_their_own_receipts(self):
        for actor in ["human", "auto-review"]:
            with self.subTest(actor=actor):
                self.assertEqual(self.counts([response(actor=actor, actorEvidence="synthetic/decision/1")])["responseActor:" + actor], 1)

    def test_permission_rule_only_proves_provider_layer(self):
        report = audit.audit_events([observation(label="permission-rule")])
        self.assertEqual(report["counts"]["denialActor:provider"], 1)
        self.assertIn("does not identify", report["limits"][-1])

    def test_auto_mode_bypass_label_does_not_identify_classifier(self):
        self.assertEqual(self.counts([observation(label="auto-mode-bypass")])["denialActor:unknown"], 1)

    def test_approval_followed_by_supervisor_interruption(self):
        counts = self.counts([response(actor="supervisor", actorEvidence="synthetic/permit/1"),
                              observation("execution", actor="supervisor", actorEvidence="synthetic/send/1")])
        self.assertEqual(counts["allowed"], 1)
        self.assertEqual(counts["execution:interrupted"], 1)
        self.assertNotIn("denied", counts)
        self.assertNotIn("execution:success", counts)

    def test_approval_does_not_imply_execution(self):
        self.assertNotIn("executionObservations", self.counts([response()]))

    def test_error_after_allow_is_not_permission_denial(self):
        counts = self.counts([response(), observation("execution", outcome="error")])
        self.assertEqual(counts["execution:error"], 1)
        self.assertNotIn("denied", counts)

    def test_exact_duplicate_and_replayed_response_count_once(self):
        event = response()
        replay = dict(event, eventId="response-2", evidence="synthetic/replay/1")
        counts = self.counts([event, copy.deepcopy(event), replay])
        self.assertEqual(counts["allowed"], 1)
        self.assertEqual(counts["duplicateObservations"], 2)

    def test_same_request_id_on_different_agents_is_not_deduplicated(self):
        self.assertEqual(self.counts([response(), dict(response(), agentId=B)])["allowed"], 2)

    def test_conflicting_response_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "conflicting-operation"):
            self.counts([response(), dict(response(), eventId="deny-1", outcome="deny")])

    def test_conflicting_actor_is_not_silently_chosen(self):
        with self.assertRaisesRegex(ValueError, "conflicting-operation"):
            self.counts([response(actor="human", actorEvidence="synthetic/a"),
                         dict(response(actor="supervisor", actorEvidence="synthetic/b"), eventId="response-2")])

    def test_conflicting_event_id_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "conflicting-event-id"):
            self.counts([response(), dict(response(), outcome="deny")])

    def test_adjustment_is_subset_of_allow_count(self):
        counts = self.counts([response(inputAdjusted=True)])
        self.assertEqual(counts["responses"], 1)
        self.assertEqual(counts["allowed"], 1)
        self.assertEqual(counts["inputAdjustments"], 1)

    def test_denial_cannot_be_input_adjustment(self):
        with self.assertRaisesRegex(ValueError, "adjusted-denial"):
            self.counts([dict(response(inputAdjusted=True), outcome="deny")])

    def test_full_ids_required(self):
        for field, value in [("agentId", A[:8]), ("requestId", "permission-"), ("requestId", "--all"), ("requestId", None)]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.counts([dict(response(), **{field: value})])

    def test_raw_fields_rejected(self):
        for name in ["prompt", "command", "updatedPermissions", "token"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.counts([dict(response(), **{name: "SYNTHETIC_SECRET"})])

    def test_response_and_native_denial_are_separate_observations(self):
        counts = self.counts([dict(response(), outcome="deny"), observation()])
        self.assertEqual(counts["denied"], 1)
        self.assertEqual(counts["denialObservations"], 1)

    def test_mixed_event_fields_rejected(self):
        with self.assertRaisesRegex(ValueError, "mixed-event-kinds"):
            self.counts([dict(response(), label="user-rejected")])

    def test_empty_input_does_not_claim_zero_human_interventions(self):
        report = audit.audit_events([])
        self.assertEqual(report["counts"], {})
        self.assertIn("unconfirmed", report["limits"][0])


class RoutingTests(unittest.TestCase):
    def context(self, **changes):
        return dict(approval_policy="on-request", approvals_reviewer="user",
                    sandbox_policy={"type": "workspace-write"}, **changes)

    def test_user_channel_is_not_human_attribution(self):
        self.assertEqual(audit.codex_route(self.context()), "user-channel-actor-unconfirmed")

    def test_auto_review_is_route_not_decision(self):
        for reviewer in ["auto_review", "guardian_subagent"]:
            self.assertEqual(audit.codex_route(dict(self.context(), approvals_reviewer=reviewer)),
                             "eligible-auto-review-not-an-observed-decision")

    def test_never_has_no_interactive_review_even_with_auto_reviewer(self):
        self.assertEqual(audit.codex_route(dict(self.context(), approval_policy="never", approvals_reviewer="auto_review")),
                         "no-interactive-review")

    def test_missing_reviewer_or_ui_mode_not_enough(self):
        for context in [{"mode": "auto-review"}, {"approval_policy": "on-request", "sandbox_policy": {"type": "workspace-write"}}, {}]:
            self.assertEqual(audit.codex_route(context), "unconfirmed")

    def test_unvalidated_policy_or_sandbox_not_guessed(self):
        for change in [{"approval_policy": {"granular": {}}}, {"sandbox_policy": {"type": "danger-full-access"}}, {"sandbox_policy": None}]:
            self.assertEqual(audit.codex_route(dict(self.context(), **change)), "unconfirmed")


class LedgerAndCliTests(unittest.TestCase):
    def ledger(self):
        return {"agentId": A, "requests": [{"id": R, "result": "allowed",
                    "actualInput": "SYNTHETIC_SECRET", "inputAdjustment": "selected correction"}]}

    def test_old_ledger_schema_and_raw_input_omission(self):
        events = audit.ledger_events(self.ledger())
        self.assertNotIn("SYNTHETIC_SECRET", json.dumps(events))
        self.assertEqual(audit.audit_events(events)["counts"]["responseActor:unknown"], 1)

    def test_per_request_agent_and_id_schema(self):
        ledger = {"requests": [{"agentId": A, "requestId": R, "result": "denied with factual corrections"}]}
        report = audit.audit_events(audit.ledger_events(ledger, "supervisor", "synthetic/supervisor"))
        self.assertEqual(report["counts"]["denied"], 1)
        self.assertEqual(report["counts"]["responseActor:supervisor"], 1)

    def test_unknown_result_cannot_be_counted_by_substring(self):
        for result in ["not allowed", "denied?", "allowed then failed", None]:
            ledger = self.ledger()
            ledger["requests"][0]["result"] = result
            with self.subTest(result=result), self.assertRaises(ValueError):
                audit.ledger_events(ledger)

    def cli(self, data):
        with tempfile.TemporaryDirectory(prefix="k12-permission-audit-test-") as directory:
            path = Path(directory) / "selected.json"
            path.write_text(data)
            return subprocess.run([sys.executable, "-B", str(SCRIPT), "events", str(path)],
                                  capture_output=True, text=True, timeout=5)

    def test_cli_valid_and_deterministic(self):
        result = self.cli(json.dumps([response()]))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["counts"]["allowed"], 1)

    def test_cli_bad_input_never_echoes_raw_content(self):
        for data in ['{"SYNTHETIC_SECRET":', json.dumps([dict(response(), command="SYNTHETIC_SECRET")]), json.dumps([dict(response(), actor=["SYNTHETIC_SECRET"])])]:
            with self.subTest(data=data):
                result = self.cli(data)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr.strip(), '{"status":"invalid-evidence"}')

    def test_cli_size_bound(self):
        self.assertEqual(self.cli(" " * (2 * 1024 * 1024 + 1)).returncode, 2)


if __name__ == "__main__":
    unittest.main()
