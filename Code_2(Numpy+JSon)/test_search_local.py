#!/usr/bin/env python3
"""Test search functionality with the local NumPy+JSON vector store.

Covers all four query modes: default, as_of, explicit_version, compare.
"""

import sys
from retrieval.local_retriever import VersionAwareLocalRetriever, search_documents


def test_search():
    print("Testing Version-Aware RAG Search (Local Store)")
    print("=" * 50)

    print("Creating retriever...")
    retriever = VersionAwareLocalRetriever(store_dir="./vector_store")
    print(f"Loaded {retriever.store.count()} chunks\n")

    # --- Mode 1: default (current versions only) ---
    print("--- DEFAULT MODE (current versions only) ---")
    test_queries = [
        "What is the current password policy?",
        "What are the password requirements?",
        "What is the incident response procedure?",
        "How often should passwords be changed?",
        "What is the data classification policy?",
        "What are the acceptable use guidelines?",
    ]

    passed = 0
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            results = retriever.search(query_text=query, limit=3)
            print(f"Found {len(results)} results:")
            for i, result in enumerate(results):
                meta = result['metadata']
                print(f"  {i+1}. Score: {result['score']:.3f}")
                print(f"     Text: {result['text'][:80]}...")
                print(f"     Metadata: doc_id={meta.get('doc_id')}, "
                      f"version={meta.get('version')}, "
                      f"is_current={meta.get('is_current')}")
            if results:
                passed += 1
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nDefault mode: {passed}/{len(test_queries)} queries returned results")

    # --- Mode 2: as_of (historical) ---
    print("\n" + "=" * 50)
    print("--- AS_OF MODE (point in time) ---")
    as_of_queries = [
        "What was the password policy as of 2025-08-01?",
        "What was the data classification policy as of 2025-06-01?",
        "What was the incident response procedure as of 2025-10-01?",
    ]

    for query in as_of_queries:
        print(f"\nQuery: {query}")
        results = retriever.search(query_text=query, limit=3)
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results):
            meta = result['metadata']
            print(f"  {i+1}. Score: {result['score']:.3f} | "
                  f"{meta.get('doc_id')} v{meta.get('version')} "
                  f"(effective {meta.get('effective_from')} to "
                  f"{meta.get('effective_to') or 'present'})")

    # --- Mode 3: explicit_version ---
    print("\n" + "=" * 50)
    print("--- EXPLICIT VERSION MODE ---")
    results = retriever.search(
        query_text="Show me the password policy according to v2.0",
        limit=3,
        doc_id="password-policy"
    )
    print(f"Query: Show me the password policy according to v2.0")
    print(f"Found {len(results)} results:")
    for i, result in enumerate(results):
        meta = result['metadata']
        print(f"  {i+1}. Score: {result['score']:.3f} | "
              f"{meta.get('doc_id')} v{meta.get('version')}")

    # --- Mode 4: compare ---
    print("\n" + "=" * 50)
    print("--- COMPARE MODE (two versions) ---")
    results = retriever.search(
        query_text="Compare version v1.0 and v3.0 of the password policy",
        limit=4,
        doc_id="password-policy"
    )
    print(f"Query: Compare version v1.0 and v3.0 of the password policy")
    print(f"Found {len(results)} results:")
    for i, result in enumerate(results):
        meta = result['metadata']
        print(f"  {i+1}. Score: {result['score']:.3f} | "
              f"{meta.get('doc_id')} v{meta.get('version')} "
              f"(query_mode={result.get('query_mode')})")

    # --- Convenience function ---
    print("\n" + "=" * 50)
    print("Testing convenience function...")
    results = search_documents(
        query_text="incident response procedures",
        limit=2,
        store_dir="./vector_store"
    )
    print(f"Convenience search found {len(results)} results for 'incident response procedures'")
    for i, result in enumerate(results):
        meta = result['metadata']
        print(f"  {i+1}. Score: {result['score']:.3f} | "
              f"{meta.get('doc_id')} v{meta.get('version')}")

    # --- Filter correctness checks ---
    print("\n" + "=" * 50)
    print("Filter correctness checks:")
    errors = []

    # Default mode must only return current versions
    results = retriever.search("password requirements", limit=10, score_threshold=0.0)
    non_current = [r for r in results if not r['metadata'].get('is_current')]
    if non_current:
        errors.append(f"Default mode returned {len(non_current)} non-current chunks")
    else:
        print("  > Default mode returns only current versions")

    # as_of 2025-08-01 must exclude v3.0 (starts 2026-01-01) and v1.0 (ended 2025-06-30)
    results = retriever.search("password", limit=10, query_mode='as_of',
                               query_params={'date': '2025-08-01'}, score_threshold=0.0)
    bad = [r for r in results
           if r['metadata'].get('doc_id') == 'password-policy'
           and r['metadata'].get('version') not in ('v2.0',)]
    if bad:
        errors.append(f"as_of mode returned wrong password versions: "
                      f"{[r['metadata'].get('version') for r in bad]}")
    else:
        print("  > as_of 2025-08-01 correctly returns only password-policy v2.0")

    # Explicit version must return only the requested version
    results = retriever.search("password", limit=10, query_mode='explicit_version',
                               query_params={'version': 'v1.0'},
                               doc_id='password-policy', score_threshold=0.0)
    bad = [r for r in results if r['metadata'].get('version') != 'v1.0']
    if bad:
        errors.append(f"explicit_version mode returned wrong versions")
    else:
        print(f"  > explicit_version v1.0 returns only v1.0 ({len(results)} chunks)")

    if errors:
        print("\nFILTER ERRORS:")
        for e in errors:
            print(f"  ! {e}")
        return 1

    print("\n" + "=" * 50)
    print("ALL LOCAL RETRIEVAL TESTS PASSED!")
    return 0


if __name__ == "__main__":
    sys.exit(test_search())
