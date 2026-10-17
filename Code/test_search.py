#!/usr/bin/env python3
"""Test search functionality with the Version-Aware RAG system."""

from retrieval.retriever import VersionAwareRetriever, search_documents

def test_search():
    print("Testing Version-Aware RAG Search")
    print("=" * 40)

    # Create retriever with local storage
    print("Creating retriever...")
    retriever = VersionAwareRetriever(
        collection_name="version_aware_rag",
        qdrant_path="./qdrant_local_storage"
    )

    # Test queries
    test_queries = [
        "What is the current password policy?",
        "What are the password requirements?",
        "What is the incident response procedure?",
        "How often should passwords be changed?",
        "What is the data classification policy?",
        "What are the acceptable use guidelines?"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            results = retriever.search(query_text=query, limit=3)
            print(f"Found {len(results)} results:")
            for i, result in enumerate(results):
                print(f"  {i+1}. Score: {result['score']:.3f}")
                print(f"     Text: {result['text'][:100]}...")
                if result['metadata']:
                    print(f"     Metadata: doc_id={result['metadata'].get('doc_id')}, "
                          f"version={result['metadata'].get('version')}")
        except Exception as e:
            print(f"Error: {e}")

    # Test convenience function
    print("\n" + "=" * 40)
    print("Testing convenience function...")
    results = search_documents(
        query_text="incident response procedures",
        limit=2,
        qdrant_path="./qdrant_local_storage"
    )
    print(f"Convenience search found {len(results)} results for 'incident response procedures'")

if __name__ == "__main__":
    test_search()