"""
Demo script for the Version-Aware RAG retrieval system.
Shows how the retrieval components work together.
"""

import sys
import os
from pathlib import Path

# Add the project root to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from retrieval.filters import (
    build_default_filter, build_as_of_filter, build_explicit_version_filter,
    build_compare_filter, detect_query_mode, extract_date_from_question,
    extract_version_from_question, build_filter_for_mode
)
try:
    from retrieval.retriever import VersionAwareRetriever, search_documents
except ImportError:
    # Fallback for when running as standalone script
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from retrieval.retriever import VersionAwareRetriever, search_documents


def demo_filters():
    """Demo the filtering functionality."""
    print("=== FILTERS DEMO ===")

    # Test default filter
    default_filter = build_default_filter()
    print(f"Default filter (is_current = true): {default_filter}")

    # Test as-of filter
    as_of_filter = build_as_of_filter("2025-06-01")
    print(f"As-of filter (2025-06-01): {as_of_filter}")

    # Test explicit version filter
    version_filter = build_explicit_version_filter("password-policy", "v2.0")
    print(f"Explicit version filter (password-policy v2.0): {version_filter}")

    # Test compare filter
    compare_filters = build_compare_filter("password-policy", "v1.0", "v3.0")
    print(f"Compare filter (password-policy v1.0 vs v3.0): {compare_filters}")

    print()


def demo_question_parsing():
    """Demo question parsing functionality."""
    print("=== QUESTION PARSING DEMO ===")

    test_questions = [
        "What is the current password policy?",
        "What was the password policy as of 2025-06-01?",
        "What was the policy on January 15, 2025?",
        "Show me the password policy according to v2.0",
        "Compare version v1.0 and v3.0 of the password policy",
        "What changed between v1.0 and v2.0?",
        "How does v2.1 differ from v2.0?",
        "Tell me about the incident response procedure in March 2025",
        "When did the password policy change to require 12 characters?",
        "What are the current incident response procedures?"
    ]

    print("Testing question parsing:")
    for question in test_questions:
        mode, params = detect_query_mode(question)
        print(f"Q: '{question}'")
        print(f"  Detected mode: {mode}")
        print(f"  Parameters: {params}")

        # Show what filter would be built (if applicable)
        if mode in ['default', 'as_of', 'explicit_version']:
            # For these modes, we need a doc_id to build complete filter
            filter_dict = build_filter_for_mode(mode, params, "password-policy")
            print(f"  Filter for password-policy: {filter_dict}")
        elif mode == 'compare':
            filter_dict = build_filter_for_mode(mode, params, "password-policy")
            print(f"  Filters for password-policy compare: {filter_dict}")
        print()


def demo_retriever():
    """Demo the retriever functionality."""
    print("=== RETRIEVER DEMO ===")

    # Create retriever with local storage (will create storage directory if needed)
    print("Creating retriever with local storage...")
    retriever = VersionAwareRetriever(
        collection_name="version_aware_rag",
        qdrant_path="./qdrant_local_storage"  # Use local storage
    )

    # Test search (will return empty results if no data indexed yet)
    print("\nTesting search...")
    results = retriever.search(
        query_text="password policy requirements",
        limit=5
    )
    print(f"Search for 'password policy requirements': {len(results)} results")

    # Test as-of search
    print("\nTesting as-of search...")
    results = retriever.search(
        query_text="password policy",
        limit=5,
        query_mode="as_of",
        query_params={"date": "2025-06-01"}
    )
    print(f"As-of search (2025-06-01) for 'password policy': {len(results)} results")

    # Test explicit version search
    print("\nTesting explicit version search...")
    results = retriever.search(
        query_text="password policy",
        limit=5,
        query_mode="explicit_version",
        query_params={"version": "v2.0"},
        doc_id="password-policy"
    )
    print(f"Explicit version search (v2.0) for 'password policy': {len(results)} results")

    # Test compare search
    print("\nTesting compare search...")
    results = retriever.search(
        query_text="password policy",
        limit=5,
        query_mode="compare",
        query_params={"version_a": "v1.0", "version_b": "v3.0"},
        doc_id="password-policy"
    )
    print(f"Compare search (v1.0 vs v3.0) for 'password policy': {len(results)} results")

    # Test auto-detection
    print("\nTesting auto-detection...")
    test_queries = [
        "What is the current password policy?",
        "What was the password policy as of 2025-06-01?",
        "Show me the password policy according to v2.0"
    ]

    for query in test_queries:
        results = retriever.search(
            query_text=query,
            limit=3
        )
        print(f"Q: '{query}'")
        print(f"  Auto-detected and returned {len(results)} results")

    print()


def demo_convenience_functions():
    """Demo convenience functions."""
    print("=== CONVENIENCE FUNCTIONS DEMO ===")

    # Test the convenience search function with local storage
    print("Testing convenience search function...")
    results = search_documents(
        query_text="incident response procedures",
        limit=3,
        qdrant_path="./qdrant_local_storage"  # Use local storage
    )
    print(f"Convenience search for 'incident response procedures': {len(results)} results")

    print()


def main():
    """Run all demos."""
    print("Version-Aware RAG Retrieval System Demo")
    print("=" * 50)

    try:
        # Run demos in sequence
        demo_filters()
        demo_question_parsing()
        demo_retriever()
        demo_convenience_functions()

        print("=" * 50)
        print("Retrieval demo completed successfully!")
        print("\nNext steps:")
        print("1. Run ingestion pipeline to populate the local vector store")
        print("2. Test retrieval with actual embedded documents")
        print("3. Proceed to Phase 4: Versioned answer generation")

    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()