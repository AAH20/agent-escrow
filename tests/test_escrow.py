"""
Comprehensive Unit Tests for agent-escrow.
Validates acceptance evaluation, referee decisions, atomic escrow release, and automated refunds.
"""

from __future__ import annotations
import shutil
import tempfile
import unittest
from agent_escrow.mandate import AcceptanceCriteria, WorkMandate
from agent_escrow.referee import AutomatedReferee, WorkSubmission
from agent_escrow.settlement import ProgrammaticEscrowLedger


class TestAgentEscrow(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.ledger = ProgrammaticEscrowLedger(ledger_dir=self.temp_dir)
        self.criteria = AcceptanceCriteria(
            required_test_count=5,
            min_test_pass_rate=1.0,
            max_token_budget=5000,
            max_duration_seconds=60.0,
            forbidden_side_effects=["DROP_DATABASE"],
        )
        self.mandate = WorkMandate(
            mandate_id="mandate-test-1",
            buyer_id="buyer-alice",
            assigned_agent_id="agent-bob",
            bounty_amount_usd=1500.0,
            title="Refactor auth middleware",
            description="Update JWT validation",
            criteria=self.criteria,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_mandate_hash_integrity(self):
        self.assertEqual(len(self.mandate.mandate_hash), 64)
        m_dict = self.mandate.to_dict()
        self.assertEqual(m_dict["bounty_amount_usd"], 1500.0)

    def test_escrow_deposit_and_release_success(self):
        # 1. Lock funds
        self.ledger.lock_funds(self.mandate)
        self.assertEqual(self.ledger.get_escrow_balance(self.mandate.mandate_id), 1500.0)

        # 2. Perfect submission
        submission = WorkSubmission(
            mandate_id=self.mandate.mandate_id,
            agent_id=self.mandate.assigned_agent_id,
            deliverable_payload={"diff": "clean code"},
            tokens_consumed=3200,
            duration_seconds=15.0,
            tests_executed=5,
            tests_passed=5,
            side_effects_invoked=[],
        )
        verdict = AutomatedReferee.evaluate(self.mandate, submission)
        self.assertTrue(verdict.is_approved)
        self.assertEqual(verdict.status, "APPROVED_FOR_RELEASE")

        # 3. Settlement disbursement
        receipt = self.ledger.execute_settlement(self.mandate, verdict)
        self.assertEqual(receipt.action, "DISBURSED_TO_AGENT")
        self.assertEqual(receipt.amount_usd, 1500.0)
        self.assertEqual(receipt.agent_id, "agent-bob")
        self.assertEqual(self.ledger.get_escrow_balance(self.mandate.mandate_id), 0.0)

    def test_escrow_refund_on_test_failure(self):
        self.ledger.lock_funds(self.mandate)

        # Flawed submission (1 test failed)
        submission = WorkSubmission(
            mandate_id=self.mandate.mandate_id,
            agent_id=self.mandate.assigned_agent_id,
            deliverable_payload={"diff": "broken code"},
            tokens_consumed=2000,
            duration_seconds=10.0,
            tests_executed=5,
            tests_passed=4,  # Failed 1 test!
            side_effects_invoked=[],
        )
        verdict = AutomatedReferee.evaluate(self.mandate, submission)
        self.assertFalse(verdict.is_approved)
        self.assertEqual(verdict.status, "REJECTED_TEST_FAILURE")

        # Settlement refund
        receipt = self.ledger.execute_settlement(self.mandate, verdict)
        self.assertEqual(receipt.action, "REFUNDED_TO_BUYER")
        self.assertEqual(receipt.buyer_id, "buyer-alice")

    def test_forbidden_side_effect_rejection(self):
        self.ledger.lock_funds(self.mandate)

        # Submission with forbidden side effect
        submission = WorkSubmission(
            mandate_id=self.mandate.mandate_id,
            agent_id=self.mandate.assigned_agent_id,
            deliverable_payload={},
            tokens_consumed=1000,
            duration_seconds=5.0,
            tests_executed=5,
            tests_passed=5,
            side_effects_invoked=["DROP_DATABASE"],
        )
        verdict = AutomatedReferee.evaluate(self.mandate, submission)
        self.assertFalse(verdict.is_approved)
        self.assertEqual(verdict.status, "REJECTED_FORBIDDEN_EFFECT")


if __name__ == "__main__":
    unittest.main()
