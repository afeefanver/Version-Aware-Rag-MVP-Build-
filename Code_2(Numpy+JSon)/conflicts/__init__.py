"""
Conflict detection and resolution for the Version-Aware RAG system.

Phase 5 module: finds policy facts that disagree across retrieved chunks
(different versions of one document, or different documents) and resolves
them with explainable precedence rules:

    current version  >  higher semantic version  >  later effective date
    cross-document disagreements are flagged for human review, never
    silently resolved.

Typical use in the retrieval -> generation flow:

    from conflicts import analyze_results

    report = analyze_results(search_results, query_mode=query_mode)
    for note in report.format_notes():
        print(note)   # shown under the generated answer
"""

from .detector import Claim, Conflict, detect_conflicts, extract_claims
from .resolver import Resolution, resolve_conflict, resolve_conflicts
from .report import ConflictReport, analyze_results

__all__ = [
    "Claim",
    "Conflict",
    "Resolution",
    "ConflictReport",
    "detect_conflicts",
    "extract_claims",
    "resolve_conflict",
    "resolve_conflicts",
    "analyze_results",
]
