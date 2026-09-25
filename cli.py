"""
Command Line Interface for agent-escrow.
Simulates autonomous work mandates, sandboxed referee verification, and escrow disbursement.
"""

from __future__ import annotations
import argparse
import json
import os
import sys
from agent_escrow.mandate import AcceptanceCriteria, WorkMandate
from agent_escrow.referee import AutomatedReferee, WorkSubmission
from agent_escrow.settlement import ProgrammaticEscrowLedger


def run_demo(outdir: str):
    os.makedirs(outdir, exist_ok=True)
    ledger = ProgrammaticEscrowLedger(ledger_dir=os.path.join(outdir, "receipts"))

    print("\n" + "=" * 80)
    print("🤝 AGENT ESCROW: PROGRAMMATIC SETTLEMENT PROTOCOL FOR AI LABOR")
    print("=" * 80)

    # 1. Buyer creates Mandate
    criteria = AcceptanceCriteria(
        required_test_count=12,
        min_test_pass_rate=1.0,  # 100% pass rate
        max_token_budget=8_000,
        max_duration_seconds=120.0,
        forbidden_side_effects=["DROP_TABLE", "EXFILTRATE_DATA"],
    )
    mandate = WorkMandate(
        mandate_id="mandate-opt-sql-902",
        buyer_id="enterprise-fintech-corp",
        assigned_agent_id="autonomous-dba-agent-4",
        bounty_amount_usd=5_000.0,
        title="PostgreSQL Query Optimization & Indexing",
        description="Rewrite transaction reconciliation query and add non-blocking B-tree indexes.",
        criteria=criteria,
    )

    print(f"\n[Step 1] Creating Work Mandate: {mandate.mandate_id}")
    print(f"   Buyer: {mandate.buyer_id}")
    print(f"   Worker Agent: {mandate.assigned_agent_id}")
    print(f"   Bounty Amount: ${mandate.bounty_amount_usd:,.2f}")
    print(f"   Mandate Contract Hash: {mandate.mandate_hash}")

    # 2. Lock Escrow
    locked = ledger.lock_funds(mandate)
    print(f"\n[Step 2] Programmatic Escrow Deposit:")
    print(f"   Locked Funds: ${locked:,.2f} USD")
    print(f"   Vault Status: SECURED IN DUAL-CUSTODY VAULT")

    # 3. Scenario A: Flawed Agent Submission (Hallucinated / Regressed)
    print("\n[Step 3] Simulation Scenario A: Hallucinating / Regressed Agent Submission")
    bad_submission = WorkSubmission(
        mandate_id=mandate.mandate_id,
        agent_id=mandate.assigned_agent_id,
        deliverable_payload={"patch": "CREATE INDEX ON trans (id); -- untested query rewrite"},
        tokens_consumed=9_400,  # Over budget (limit 8,000)
        duration_seconds=45.2,
        tests_executed=12,
        tests_passed=10,  # 2 failed tests! (83.3% pass rate < 100%)
        side_effects_invoked=[],
    )
    verdict_bad = AutomatedReferee.evaluate(mandate, bad_submission)
    print(f"   Referee Status: {verdict_bad.status}")
    print(f"   Violations Detected: {verdict_bad.violations}")

    # Execute Settlement for Scenario A (Refund)
    receipt_a = ledger.execute_settlement(mandate, verdict_bad)
    print(f"   ⚡ Settlement Action: {receipt_a.action}")
    print(f"   Amount: ${receipt_a.amount_usd:,.2f} USD refunded to {receipt_a.buyer_id}")
    print(f"   Receipt Hash: {receipt_a.settlement_hash}")

    # 4. Scenario B: High-Assurance Verified Submission
    print("\n" + "-" * 80)
    print("[Step 4] Simulation Scenario B: High-Assurance Verified Agent Submission")
    # Re-lock escrow for new attempt
    ledger.lock_funds(mandate)
    good_submission = WorkSubmission(
        mandate_id=mandate.mandate_id,
        agent_id=mandate.assigned_agent_id,
        deliverable_payload={"patch": "CREATE INDEX CONCURRENTLY idx_reconciled ON trans (account_id, status);"},
        tokens_consumed=4_120,  # Well under 8,000 budget
        duration_seconds=28.4,
        tests_executed=12,
        tests_passed=12,  # 100% tests passed!
        side_effects_invoked=[],
    )
    verdict_good = AutomatedReferee.evaluate(mandate, good_submission)
    print(f"   Referee Status: {verdict_good.status}")
    print(f"   Test Pass Rate: {verdict_good.pass_rate*100:.1f}% (12/12 Passing)")
    print(f"   Tokens Consumed: {verdict_good.tokens_consumed:,} / {mandate.criteria.max_token_budget:,}")
    print(f"   Cryptographic Verdict Hash: {verdict_good.verdict_hash}")

    # Execute Settlement for Scenario B (Disbursement)
    receipt_b = ledger.execute_settlement(mandate, verdict_good)
    print(f"   ⚡ Settlement Action: {receipt_b.action}")
    print(f"   Amount: ${receipt_b.amount_usd:,.2f} USD DISBURSED to Agent {receipt_b.agent_id}")
    print(f"   Receipt Hash: {receipt_b.settlement_hash}")

    print("\n" + "=" * 80)
    print("✅ Agent Escrow simulation complete. Zero human friction, mathematical trust.")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Agent Escrow: Programmatic Settlement Protocol")
    subparsers = parser.add_subparsers(dest="command")

    demo_p = subparsers.add_parser("demo", help="Run end-to-end escrow mandate and settlement demo")
    demo_p.add_argument("--outdir", default="./output_escrow", help="Output directory for receipts")

    args = parser.parse_args()
    if not args.command or args.command == "demo":
        run_demo(getattr(args, "outdir", "./output_escrow"))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
