"""
Conflict report: query-mode-aware severity and human-readable notes.

Severity by query mode (per the spec's detection mechanism, section 3):
    default          - actionable. Superseded values must not drive answers;
                       the note says which current value was used instead.
    as_of            - informational. Historical values are the point of the
                       query; the note lists each version's value with dates.
    explicit_version - informational, same treatment as as_of.
    compare          - expected. Differences between the two requested
                       versions are the requested output.
"""

from dataclasses import dataclass, field
from typing import List

from .detector import Conflict
from .resolver import Resolution, resolve_conflicts


@dataclass
class ConflictReport:
    """Resolved conflicts for one query, with severity and notes."""
    query_mode: str
    resolved: List[tuple] = field(default_factory=list)  # (Conflict, Resolution)

    @property
    def conflict_count(self) -> int:
        return len(self.resolved)

    @property
    def needs_review_count(self) -> int:
        return sum(1 for _, resolution in self.resolved if resolution.needs_review)

    def has_conflicts(self) -> bool:
        return bool(self.resolved)

    def format_notes(self) -> List[str]:
        """Plain-ASCII note lines for display under an answer."""
        if not self.resolved:
            return []

        if self.query_mode == "compare":
            notes = []
            for conflict, _ in self.resolved:
                parts = [
                    f"{claims[0].version} -> {value}"
                    for value, claims in conflict.values()
                ]
                notes.append(
                    f"Compared '{conflict.topic}': "
                    f"{', '.join(parts)} (difference detected)"
                )
            return notes

        if self.query_mode in ("as_of", "explicit_version"):
            notes = []
            for conflict, resolution in self.resolved:
                parts = [
                    f"{claims[0].version} ({claims[0].effective_from}"
                    f" to {claims[0].effective_to or 'present'}): {value}"
                    for value, claims in conflict.values()
                ]
                winner = resolution.winner
                if winner is not None:
                    notes.append(
                        f"Note: '{conflict.topic}' varies across versions "
                        f"({'; '.join(parts)}). The value shown is from "
                        f"{winner.source_label()}."
                    )
                else:
                    notes.append(
                        f"Review required: '{conflict.topic}' varies "
                        f"({'; '.join(parts)}). {resolution.rationale}"
                    )
            return notes

        # default mode - actionable notes
        notes = []
        for conflict, resolution in self.resolved:
            if resolution.winner is not None:
                superseded = ", ".join(
                    f"{claim.source_label()} said {value}"
                    for value, claims in conflict.values()
                    for claim in claims
                    if claim is not resolution.winner and not claim.is_current
                )
                notes.append(
                    f"Conflicting values for '{conflict.topic}': using "
                    f"{resolution.winner.source_label()} "
                    f"(effective {resolution.winner.effective_from}): "
                    f"{resolution.winner.value}."
                    + (f" {superseded}." if superseded else "")
                )
            else:
                notes.append(
                    f"Review required: conflicting values for "
                    f"'{conflict.topic}'. {resolution.rationale}"
                )
        return notes


def analyze_results(
    search_results: List[dict],
    query_mode: str = "default",
) -> ConflictReport:
    """
    Detect and resolve conflicts among search results.

    Convenience entry point for the retrieval -> generation flow:
        report = analyze_results(results, query_mode)
        for note in report.format_notes(): ...

    Args:
        search_results: Search results from either retriever.
        query_mode: 'default', 'as_of', 'explicit_version', or 'compare'.

    Returns:
        ConflictReport with one (Conflict, Resolution) pair per conflict.
    """
    from .detector import detect_conflicts

    conflicts = detect_conflicts(search_results)
    return ConflictReport(
        query_mode=query_mode,
        resolved=resolve_conflicts(conflicts),
    )
