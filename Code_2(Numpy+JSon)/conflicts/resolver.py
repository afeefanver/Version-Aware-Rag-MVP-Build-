"""
Conflict resolution with explainable precedence rules.

For every detected conflict, picks the winning claim and records why:

Intra-document (same policy, different versions):
    1. The current version wins (is_current = True).
    2. Failing that, the higher semantic version wins (v2.1 > v2.0 > v1.0).
    3. Failing that, the later effective_from wins.
    4. Still tied -> no resolution; flagged for human review.

Cross-document (two different policies disagree):
    Never resolved silently - both claims are reported and the conflict
    is flagged needs_review. Choosing between two currently-effective
    policies is a governance decision, not a retrieval decision.

Historical queries (as_of / explicit_version / compare):
    Conflicts among historical versions are expected - the winner is
    still computed the same way, but the report marks the severity as
    informational rather than actionable.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from .detector import Claim, Conflict


@dataclass
class Resolution:
    """Outcome of resolving one conflict."""
    winner: Optional[Claim]          # None when unresolved (needs review)
    losers: List[Claim] = field(default_factory=list)
    rationale: str = ""
    needs_review: bool = False


def _version_key(version: str):
    """'v2.1' -> (2, 1); non-numeric versions sort as (0,)."""
    numbers = tuple(int(n) for n in re.findall(r"\d+", str(version)))
    return numbers if numbers else (0,)


def _effective_key(claim: Claim):
    """Claims without an effective date sort earliest."""
    return claim.effective_from or "0000-00-00"


def resolve_conflict(conflict: Conflict) -> Resolution:
    """
    Resolve one conflict using the precedence rules.

    Args:
        conflict: A Conflict from the detector.

    Returns:
        Resolution with winner, losers, rationale, and needs_review.
    """
    values = conflict.values()
    all_claims = [c for _, claims in values for c in claims]

    if conflict.kind == "cross_document":
        first = values[0][1][0]
        others = ", ".join(
            f"{claims[0].doc_id} {claims[0].version} says {value}"
            for value, claims in values[1:]
        )
        return Resolution(
            winner=None,
            losers=[],
            rationale=(
                f"Cross-document disagreement on '{conflict.topic}': "
                f"{first.doc_id} {first.version} says {values[0][0]}; {others}. "
                f"Both sources are treated as authoritative for their own "
                f"domain - human review required to reconcile them."
            ),
            needs_review=True,
        )

    # --- intra-document precedence -------------------------------------
    current = [c for c in all_claims if c.is_current]
    if current and len({c.value for c in current}) == 1:
        winner = current[0]
        superseded = [
            f"{c.doc_id} {c.version} ({c.effective_from} to {c.effective_to or 'present'})"
            for c in all_claims if not c.is_current
        ]
        rationale = (
            f"{winner.doc_id} {winner.version} is the current version "
            f"(effective {winner.effective_from})"
            + (f"; superseded: {' vs '.join(superseded)}" if superseded else "")
        )
        return Resolution(
            winner=winner,
            losers=[c for c in all_claims if c is not winner],
            rationale=rationale,
            needs_review=False,
        )

    # No current claim (or current claims disagree) - fall through to
    # version recency among whatever claims exist.
    ranked = sorted(all_claims, key=lambda c: (_version_key(c.version), _effective_key(c)))
    winner = ranked[-1]
    runner_up = ranked[-2] if len(ranked) > 1 else None

    if runner_up and _version_key(winner.version) == _version_key(runner_up.version) \
            and _effective_key(winner) == _effective_key(runner_up):
        return Resolution(
            winner=None,
            losers=[],
            rationale=(
                f"Cannot resolve '{conflict.topic}': equally-ranked sources "
                f"disagree ({winner.source_label()} vs {runner_up.source_label()})."
            ),
            needs_review=True,
        )

    rationale = (
        f"No current version among the claims; selected the most recent: "
        f"{winner.doc_id} {winner.version} (effective {winner.effective_from})"
    )
    if current and len({c.value for c in current}) > 1:
        rationale = (
            f"Current-version claims disagree within {winner.doc_id}; "
            f"selected the most recent: {winner.source_label()}"
        )
    return Resolution(
        winner=winner,
        losers=[c for c in all_claims if c is not winner],
        rationale=rationale,
        needs_review=bool(current),  # disagreeing current claims are a data issue
    )


def resolve_conflicts(conflicts: List[Conflict]) -> List[tuple]:
    """
    Resolve every conflict.

    Args:
        conflicts: List of Conflict objects.

    Returns:
        List of (Conflict, Resolution) pairs in the same order.
    """
    return [(conflict, resolve_conflict(conflict)) for conflict in conflicts]
