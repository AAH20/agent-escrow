"""
Automated Cryptographic Referee & Sandbox Verification Engine.
Audits submitted agent work against formal mandate criteria before escrow disbursement.
"""

from __future__ import annotations
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from agent_escrow.mandate import WorkMandate


@dataclass
class WorkSubmission:
    mandate_id: str
    agent_id: str
    deliverable_payload: Dict[str, Any]
    tokens_consumed: int
    duration_seconds: float
    tests_executed: int
    tests_passed: int
    side_effects_invoked: List[str]
    submitted_at: float = 0.0

    def __post_init__(self):
        if not self.submitted_at:
            self.submitted_at = time.time()


@dataclass
class VerificationVerdict:
    mandate_id: str
    status: str  # "APPROVED_FOR_RELEASE", "REJECTED_TEST_FAILURE", "REJECTED_BUDGET_OVERRUN", "REJECTED_FORBIDDEN_EFFECT"
    is_approved: bool
    pass_rate: float
    tokens_consumed: int
    duration_seconds: float
    violations: List[str]
    verdict_hash: str
    verified_at: float

    def to_dict(self) -> dict:
        return {
            "mandate_id": self.mandate_id,
            "status": self.status,
            "is_approved": self.is_approved,
            "pass_rate": round(self.pass_rate, 4),
            "tokens_consumed": self.tokens_consumed,
            "duration_seconds": round(self.duration_seconds, 2),
            "violations": self.violations,
            "verdict_hash": self.verdict_hash,
            "verified_at": self.verified_at,
        }


class AutomatedReferee:
    """
    Independent referee verifying that autonomous agent labor strictly satisfies contract acceptance terms.
    """

    @staticmethod
    def evaluate(mandate: WorkMandate, submission: WorkSubmission) -> VerificationVerdict:
        violations: List[str] = []

        # 1. Test Verification
        pass_rate = (
            (submission.tests_passed / submission.tests_executed)
            if submission.tests_executed > 0
            else 0.0
        )

        if submission.tests_executed < mandate.criteria.required_test_count:
            violations.append(
                f"Insufficient test execution count: {submission.tests_executed} < {mandate.criteria.required_test_count} required"
            )

        if pass_rate < mandate.criteria.min_test_pass_rate:
            violations.append(
                f"Test pass rate failure: {pass_rate*100:.1f}% < {mandate.criteria.min_test_pass_rate*100:.1f}% required"
            )

        # 2. Token Budget Bound
        if submission.tokens_consumed > mandate.criteria.max_token_budget:
            violations.append(
                f"Token budget exceeded: {submission.tokens_consumed} > {mandate.criteria.max_token_budget} limit"
            )

        # 3. Execution Latency Bound
        if submission.duration_seconds > mandate.criteria.max_duration_seconds:
            violations.append(
                f"Execution duration exceeded: {submission.duration_seconds:.1f}s > {mandate.criteria.max_duration_seconds:.1f}s SLA"
            )

        # 4. Forbidden Side Effects
        forbidden_set = set(mandate.criteria.forbidden_side_effects)
        invoked_forbidden = [effect for effect in submission.side_effects_invoked if effect in forbidden_set]
        if invoked_forbidden:
            violations.append(f"Forbidden side effects invoked: {', '.join(invoked_forbidden)}")

        # Decision
        is_approved = len(violations) == 0
        if is_approved:
            status = "APPROVED_FOR_RELEASE"
        elif any("Test pass rate" in v for v in violations):
            status = "REJECTED_TEST_FAILURE"
        elif any("Token budget" in v for v in violations):
            status = "REJECTED_BUDGET_OVERRUN"
        elif any("Forbidden side effects" in v for v in violations):
            status = "REJECTED_FORBIDDEN_EFFECT"
        else:
            status = "REJECTED_VERIFICATION_FAILED"

        now = time.time()
        canonical = json.dumps(
            {
                "mandate_id": mandate.mandate_id,
                "status": status,
                "approved": is_approved,
                "pass_rate": pass_rate,
                "violations": violations,
                "verified_at": now,
            },
            sort_keys=True,
        )
        verdict_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        return VerificationVerdict(
            mandate_id=mandate.mandate_id,
            status=status,
            is_approved=is_approved,
            pass_rate=pass_rate,
            tokens_consumed=submission.tokens_consumed,
            duration_seconds=submission.duration_seconds,
            violations=violations,
            verdict_hash=verdict_hash,
            verified_at=now,
        )
