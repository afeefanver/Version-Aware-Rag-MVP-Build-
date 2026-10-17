
from retrieval.retriever import VersionAwareRetriever

r = VersionAwareRetriever(
    qdrant_path="./qdrant_local_storage"
)

info = r.embedder.get_collection_info()

print("Vectors stored:", info.get("vectors_count", 0))
print("Status:", info.get("status", "unknown"))
