"""
Formal Work Mandate & Acceptance Specification Models.
Defines binding criteria for autonomous agent task execution and escrow release.
"""

from __future__ import annotations
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AcceptanceCriteria:
    required_test_count: int
    min_test_pass_rate: float = 1.0  # 100% passing required
    max_token_budget: int = 10_000
    max_duration_seconds: float = 300.0
    forbidden_side_effects: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "required_test_count": self.required_test_count,
            "min_test_pass_rate": self.min_test_pass_rate,
            "max_token_budget": self.max_token_budget,
            "max_duration_seconds": self.max_duration_seconds,
            "forbidden_side_effects": self.forbidden_side_effects,
        }


@dataclass
class WorkMandate:
    mandate_id: str
    buyer_id: str
    assigned_agent_id: str
    bounty_amount_usd: float
    title: str
    description: str
    criteria: AcceptanceCriteria
    created_at: float = field(default_factory=time.time)
    mandate_hash: str = ""

    def __post_init__(self):
        if not self.mandate_hash:
            canonical = json.dumps(
                {
                    "mandate_id": self.mandate_id,
                    "buyer_id": self.buyer_id,
                    "agent_id": self.assigned_agent_id,
                    "bounty_usd": self.bounty_amount_usd,
                    "criteria": self.criteria.to_dict(),
                    "created_at": self.created_at,
                },
                sort_keys=True,
            )
            self.mandate_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return {
            "mandate_id": self.mandate_id,
            "buyer_id": self.buyer_id,
            "assigned_agent_id": self.assigned_agent_id,
            "bounty_amount_usd": self.bounty_amount_usd,
            "title": self.title,
            "description": self.description,
            "criteria": self.criteria.to_dict(),
            "created_at": self.created_at,
            "mandate_hash": self.mandate_hash,
        }
