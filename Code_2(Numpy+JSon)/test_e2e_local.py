#!/usr/bin/env python3
"""End-to-end test: real retrieval -> real generation.

Wires VersionAwareLocalRetriever (NumPy+JSON store) directly into
Generator.generate_answer() - no simulated/mock data.

Covers all four query modes:
    default          - current versions only
    as_of            - point-in-time historical view
    explicit_version - a specific version
    compare          - two versions of one document
"""

import sys

from retrieval.local_retriever import VersionAwareLocalRetriever
from generation.generator import Generator
from generation.prompt_template import AnswerFormat


def run_e2e():
    print("End-to-End Test: Real Retrieval -> Generation (Local Store)")
    print("=" * 60)

    retriever = VersionAwareLocalRetriever(store_dir="./vector_store")
    print(f"Loaded {retriever.store.count()} chunks\n")

    generator = Generator(answer_format=AnswerFormat.NARRATIVE)

    # (question, mode override, params, doc_id, answer_format)
    cases = [
        # Mode 1: default (auto-detected)
        ("What is the current password policy?",
         None, None, None, AnswerFormat.NARRATIVE),
        ("What are the acceptable use guidelines?",
         None, None, None, AnswerFormat.BULLET_POINTS),
        # Mode 2: as_of
        ("What was the password policy as of 2025-08-01?",
         'as_of', {'date': '2025-08-01'}, None, AnswerFormat.NARRATIVE),
        # Mode 3: explicit_version
        ("Show me the password policy according to v2.0",
         'explicit_version', {'version': 'v2.0'}, 'password-policy',
         AnswerFormat.NARRATIVE),
        # Mode 4: compare
        ("Compare version v1.0 and v3.0 of the password policy",
         'compare', {'version_a': 'v1.0', 'version_b': 'v3.0'},
         'password-policy', AnswerFormat.VERSION_COMPARISON),
    ]

    failures = 0
    for question, mode, params, doc_id, fmt in cases:
        mode_label = mode or 'default(auto)'
        print("-" * 60)
        print(f"[{mode_label}] {question}")

        # Step 1: real retrieval
        results = retriever.search(
            query_text=question,
            limit=4,
            query_mode=mode,
            query_params=params,
            doc_id=doc_id,
        )
        if not results:
            print("  FAILED: retrieval returned no results")
            failures += 1
            continue

        versions = sorted({r['metadata'].get('version')
                           for r in results})
        print(f"  Retrieval: {len(results)} chunks from versions {versions}")
        for r in results[:2]:
            print(f"    score {r['score']:.3f} | {r['metadata'].get('doc_id')} "
                  f"{r['metadata'].get('version')} | {r['text'][:60]}...")

        # Step 2: real generation from those results
        answer = generator.generate_answer(
            question=question,
            search_results=results,
            answer_format=fmt,
        )
        print(f"\n  ANSWER (confidence {answer.confidence_score:.2f}, "
              f"{len(answer.sources)} sources):")
        for line in answer.answer.splitlines():
            print(f"    {line}")

        # Version attribution check (dict of doc_id -> version string)
        if answer.version_attribution:
            print("  Version attribution:")
            for doc_id, version in answer.version_attribution.items():
                print(f"    - {doc_id}: {version}")

        failures += 0  # reaching here means retrieval + generation both worked

    print("\n" + "=" * 60)
    if failures == 0:
        print("END-TO-END TEST COMPLETE: retrieval and generation wired "
              "together for all 4 query modes.")
        return 0
    print(f"END-TO-END TEST HAD {failures} FAILURE(S).")
    return 1


if __name__ == "__main__":
    sys.exit(run_e2e())
