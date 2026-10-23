#!/usr/bin/env python3
"""Phase 5 test: conflict detection + resolution on synthetic and real data.

Synthetic cases verify the ground truth (90 vs 60 days, cross-document
review, mode-aware notes). Real-data cases run retrieval through the
local NumPy+JSON store and feed the results into the conflict pipeline.
"""

import sys

from conflicts import analyze_results, detect_conflicts, resolve_conflict
from retrieval.local_retriever import VersionAwareLocalRetriever


def _result(doc_id, version, effective_from, effective_to, is_current,
            text, score=0.6):
    return {
        "text": text,
        "score": score,
        "metadata": {
            "doc_id": doc_id,
            "version": version,
            "effective_from": effective_from,
            "effective_to": effective_to,
            "is_current": is_current,
            "chunk_id": f"{doc_id}_{version}",
        },
    }


def synthetic_tests():
    print("SYNTHETIC TESTS (known ground truth)")
    print("=" * 50)
    failures = []

    # --- 1. intra-document conflict: 90 days (v1.0) vs 60 days (v3.0) ---
    results = [
        _result("password-policy", "v1.0", "2025-01-01", "2025-06-30", False,
                "- Maximum password age: 90 days\n"
                "- Passwords must be changed every 90 days\n"
                "- Password history: Remember last 5 passwords"),
        _result("password-policy", "v3.0", "2026-01-01", None, True,
                "- Maximum password age: 60 days (maintained from v2.0)\n"
                "- Passwords must be changed every 60 days\n"
                "- Password history: Remember last 24 passwords (increased from 10)"),
    ]
    conflicts = detect_conflicts(results)
    topics = {c.topic for c in conflicts}
    expected_topics = {
        "maximum password age",
        "passwords must be changed every",
        "password history",
    }
    print(f"1. Intra-document: {len(conflicts)} conflicts on {sorted(topics)}")
    if not expected_topics <= topics:
        failures.append(f"expected topics {expected_topics}, got {topics}")

    age = next(c for c in conflicts if c.topic == "maximum password age")
    resolution = resolve_conflict(age)
    if resolution.winner is None or resolution.winner.value != "60 days":
        failures.append(f"password age should resolve to 60 days, got {resolution.winner}")
    if resolution.needs_review:
        failures.append("intra-document current-wins should not need review")
    print(f"   Resolution: {resolution.winner.value} <- {resolution.rationale}")

    # --- 2. cross-document conflict -> needs_review, no silent winner ---
    results = [
        _result("doc-alpha", "v2.0", "2025-01-01", None, True,
                "- Session timeout: 15 minutes"),
        _result("doc-beta", "v1.2", "2025-02-01", None, True,
                "- Session timeout: 30 minutes"),
    ]
    conflicts = detect_conflicts(results)
    if len(conflicts) != 1 or conflicts[0].kind != "cross_document":
        failures.append(f"cross-document conflict not detected: {conflicts}")
    else:
        resolution = resolve_conflict(conflicts[0])
        if resolution.winner is not None or not resolution.needs_review:
            failures.append("cross-document conflict must need review, not resolve")
        print(f"2. Cross-document: flagged needs_review - OK")

    # --- 3. unanimous values -> no conflict ---
    results = [
        _result("password-policy", "v2.0", "2025-07-01", "2025-12-31", False,
                "- Maximum password age: 60 days"),
        _result("password-policy", "v3.0", "2026-01-01", None, True,
                "- Maximum password age: 60 days (maintained from v2.0)"),
    ]
    conflicts = detect_conflicts(results)
    if conflicts:
        failures.append(f"unanimous value flagged as conflict: {conflicts}")
    print("3. Unanimous values: no conflict - OK")

    # --- 4. default-mode note text ---
    results = [
        _result("password-policy", "v1.0", "2025-01-01", "2025-06-30", False,
                "- Maximum password age: 90 days"),
        _result("password-policy", "v3.0", "2026-01-01", None, True,
                "- Maximum password age: 60 days"),
    ]
    notes = analyze_results(results, query_mode="default").format_notes()
    note = notes[0] if notes else ""
    print(f"4. Default-mode note: {note}")
    if "60 days" not in note or "v3.0" not in note:
        failures.append(f"default note should name current winner: {note}")

    # --- 5. compare-mode note format ---
    notes = analyze_results(results, query_mode="compare").format_notes()
    note = notes[0] if notes else ""
    print(f"5. Compare-mode note: {note}")
    if "v1.0 -> 90 days" not in note or "v3.0 -> 60 days" not in note:
        failures.append(f"compare note format wrong: {note}")

    # --- 6. tie-break on effective date when versions equal ---
    results = [
        _result("password-policy", "v2.0", "2025-07-01", "2025-12-31", False,
                "- Maximum password age: 60 days"),
        _result("password-policy", "v2.0", "2025-07-01", "2025-12-31", False,
                "- Maximum password age: 45 days"),
    ]
    conflicts = detect_conflicts(results)
    # same doc+version asserting two values from different chunks: the
    # detector only conflicts across DIFFERENT sources, so this is not one
    if conflicts:
        failures.append("same-source disagreement should not be a conflict")
    else:
        print("6. Same-source disagreement: not a conflict - OK")

    return failures


def real_data_tests():
    print("\nREAL DATA TESTS (local vector store)")
    print("=" * 50)
    failures = []

    retriever = VersionAwareLocalRetriever(store_dir="./vector_store")

    # --- A. default mode: current-only -> zero conflicts expected ---
    results = retriever.search("What is the maximum password age?", limit=5)
    report = analyze_results(results, query_mode="default")
    print(f"A. Default mode: {len(results)} chunks -> "
          f"{report.conflict_count} conflicts")
    if report.conflict_count:
        failures.append(f"default mode should be conflict-free, got "
                        f"{report.format_notes()}")

    # --- B. compare mode: real conflicts between v1.0 and v3.0 ---
    results = retriever.search(
        "Compare version v1.0 and v3.0 of the password policy",
        limit=6, query_mode="compare",
        query_params={"version_a": "v1.0", "version_b": "v3.0"},
        doc_id="password-policy",
    )
    report = analyze_results(results, query_mode="compare")
    print(f"B. Compare mode: {len(results)} chunks -> "
          f"{report.conflict_count} conflicts")
    for note in report.format_notes():
        print(f"   {note}")
    topics = {conflict.topic for conflict, _ in report.resolved}
    if "maximum password age" not in topics:
        failures.append(f"compare mode should find password-age conflict, got {topics}")

    # --- C. mixed historical retrieval (as_of across supersession) ---
    results = retriever.search(
        "What was the password policy as of 2025-08-01?",
        limit=5, query_mode="as_of", query_params={"date": "2025-08-01"},
    )
    report = analyze_results(results, query_mode="as_of")
    print(f"C. as_of mode: {len(results)} chunks -> "
          f"{report.conflict_count} conflicts")
    for note in report.format_notes():
        print(f"   {note}")

    # --- D. incident response timeline drift (real v1.1 vs v2.1) ---
    old = retriever.get_chunks_by_doc_and_version("incident-response", "v1.1")
    new = retriever.get_chunks_by_doc_and_version("incident-response", "v2.1")
    combined = [
        {"text": c["text"], "score": 0.5, "metadata": c["metadata"]}
        for c in old[:6] + new[:6]
    ]
    report = analyze_results(combined, query_mode="compare")
    print(f"D. Incident-response v1.1 vs v2.1: {report.conflict_count} conflicts")
    for note in report.format_notes():
        print(f"   {note}")
    topics = {conflict.topic for conflict, _ in report.resolved}
    if "initial triage" not in topics:
        failures.append(f"triage drift (15 vs 2 min) not detected; got {topics}")

    return failures


def main():
    synthetic_failures = synthetic_tests()
    real_failures = real_data_tests()

    failures = synthetic_failures + real_failures
    print("\n" + "=" * 50)
    if not failures:
        print("ALL PHASE 5 CONFLICT TESTS PASSED!")
        return 0
    print("FAILURES:")
    for failure in failures:
        print(f"  ! {failure}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
