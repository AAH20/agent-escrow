"""
Programmatic Dual-Custody Escrow & Settlement Ledger.
Automates conditional fund release and refunds based on cryptographic referee verdicts.
"""

from __future__ import annotations
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional
from agent_escrow.mandate import WorkMandate
from agent_escrow.referee import VerificationVerdict


@dataclass
class SettlementReceipt:
    settlement_id: str
    mandate_id: str
    buyer_id: str
    agent_id: str
    action: str  # "DISBURSED_TO_AGENT" or "REFUNDED_TO_BUYER"
    amount_usd: float
    verdict_hash: str
    settlement_hash: str
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "settlement_id": self.settlement_id,
            "mandate_id": self.mandate_id,
            "buyer_id": self.buyer_id,
            "agent_id": self.agent_id,
            "action": self.action,
            "amount_usd": self.amount_usd,
            "verdict_hash": self.verdict_hash,
            "settlement_hash": self.settlement_hash,
            "timestamp": self.timestamp,
        }


class ProgrammaticEscrowLedger:
    """
    Manages locked escrow balances and executes atomic releases or refunds based on referee attestation.
    """

    def __init__(self, ledger_dir: Optional[str] = None):
        self.ledger_dir = ledger_dir or "/tmp/agent_escrow_ledger"
        os.makedirs(self.ledger_dir, exist_ok=True)
        self._escrow_vault: Dict[str, float] = {}  # mandate_id -> locked USD
        self._settlement_history: List[SettlementReceipt] = []

    def lock_funds(self, mandate: WorkMandate) -> float:
        """Locks buyer bounty funds into programmatically controlled escrow."""
        self._escrow_vault[mandate.mandate_id] = mandate.bounty_amount_usd
        return mandate.bounty_amount_usd

    def get_escrow_balance(self, mandate_id: str) -> float:
        return self._escrow_vault.get(mandate_id, 0.0)

    def execute_settlement(
        self,
        mandate: WorkMandate,
        verdict: VerificationVerdict,
    ) -> SettlementReceipt:
        """
        Executes atomic settlement.
        If verdict is approved, disburses bounty to agent.
        If verdict fails, refunds 100% of escrow back to buyer.
        """
        locked_amount = self._escrow_vault.pop(mandate.mandate_id, 0.0)
        if locked_amount <= 0:
            raise ValueError(f"No active escrow funds found for mandate {mandate.mandate_id}")

        settlement_id = f"settle-{uuid.uuid4().hex[:8]}"
        action = "DISBURSED_TO_AGENT" if verdict.is_approved else "REFUNDED_TO_BUYER"
        recipient = mandate.assigned_agent_id if verdict.is_approved else mandate.buyer_id
        now = time.time()

        canonical = json.dumps(
            {
                "settlement_id": settlement_id,
                "mandate_id": mandate.mandate_id,
                "recipient": recipient,
                "amount": locked_amount,
                "action": action,
                "verdict_hash": verdict.verdict_hash,
                "timestamp": now,
            },
            sort_keys=True,
        )
        settlement_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        receipt = SettlementReceipt(
            settlement_id=settlement_id,
            mandate_id=mandate.mandate_id,
            buyer_id=mandate.buyer_id,
            agent_id=mandate.assigned_agent_id,
            action=action,
            amount_usd=locked_amount,
            verdict_hash=verdict.verdict_hash,
            settlement_hash=settlement_hash,
            timestamp=now,
        )

        self._settlement_history.append(receipt)

        # Write receipt to disk
        out_file = os.path.join(self.ledger_dir, f"{settlement_id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(receipt.to_dict(), f, indent=2)

        return receipt
