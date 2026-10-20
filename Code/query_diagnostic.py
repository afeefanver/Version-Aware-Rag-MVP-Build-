from retrieval.retriever import VersionAwareRetriever

retriever = VersionAwareRetriever(
    collection_name="version_aware_rag",
    qdrant_path="./qdrant_local_storage"
)

test_queries = [
    "What is the current password policy?",
    "What are the password requirements?",
    "What is the incident response procedure?",
    "How often should passwords be changed?",
    "What is the data classification policy?",
    "What are the acceptable use guidelines?"
]

for i, query in enumerate(test_queries):
    print(f"\n[{i+1}/6] Query: {query}")
    try:
        results = retriever.search(query_text=query, limit=3)
        print(f"Found {len(results)} results:")
        for j, result in enumerate(results[:2]):
            print(f"  {j+1}. Score: {result['score']:.3f}")
            if result["text"]:
                print(f"     Text: {result['text'][:100]}...")
            if result["metadata"]:
                print(
                    f"     Metadata: doc_id={result['metadata'].get('doc_id')}, "
                    f"version={result['metadata'].get('version')}"
                )
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")