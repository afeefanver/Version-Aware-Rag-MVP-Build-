#!/usr/bin/env python3
"""
Local-store ingestion pipeline for Version-Aware RAG.

Reuses the existing parse + chunk components unchanged, embeds in batch,
and writes to the lock-free NumPy+JSON store (vector_store/) instead of
Qdrant. The Qdrant ingestion path (run_ingestion.py) remains available
and untouched.

Output layout:
    vector_store/chunks.json      chunk metadata (aligned by row)
    vector_store/embeddings.npy   float32 matrix, row i <-> chunks.json[i]
"""

import sys
from pathlib import Path

from ingest.parsers import parse_document
from ingest.chunker import chunk_document_sections, create_chunk_metadata
from ingest.embedder import create_content_hash
from retrieval.vector_store import LocalVectorStore
from retrieval.local_embedder import LocalEmbedder


def ingest_all_local(
    manifest_path: Path,
    store_dir: str = "./vector_store",
    force_reingest: bool = False
) -> dict:
    """
    Ingest all document versions from the manifest into the local store.

    Args:
        manifest_path: Path to manifest.json
        store_dir: Directory for the NumPy+JSON store
        force_reingest: If True, rebuild the store from scratch

    Returns:
        Summary dictionary with per-version ingestion details
    """
    import json

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    data_root = manifest_path.parent

    store = LocalVectorStore(store_dir=store_dir)
    if force_reingest:
        store.chunks = []
        store.embeddings = store.embeddings[:0]  # empty, keep dtype/shape

    embedder = LocalEmbedder()
    dim = embedder.embedding_dim

    results = {
        'total_documents': 0,
        'total_versions': 0,
        'successful_ingestions': 0,
        'failed_ingestions': 0,
        'chunks_created': 0,
        'details': []
    }

    for doc in manifest.get('documents', []):
        doc_id = doc['doc_id']
        results['total_documents'] += 1

        for version_info in doc.get('versions', []):
            version = version_info['version']
            results['total_versions'] += 1

            try:
                file_path = data_root / version_info['source_path']
                if not file_path.exists():
                    raise FileNotFoundError(f"Document file not found: {file_path}")

                # Parse and chunk (existing components, unchanged)
                parsed = parse_document(file_path)
                text_chunks = chunk_document_sections(parsed['sections'])

                # Build metadata per chunk (same shape as the Qdrant payloads)
                chunks_meta = []
                for chunk in text_chunks:
                    meta = create_chunk_metadata(
                        chunk=chunk,
                        doc_id=doc_id,
                        version=version,
                        effective_from=version_info['effective_from'],
                        effective_to=version_info['effective_to'],
                    )
                    meta['content_hash'] = create_content_hash(chunk.text)
                    chunks_meta.append(meta)

                # Batch-embed all chunks of this version at once
                texts = [c['text'] for c in chunks_meta]
                embeddings = embedder.embed_texts(texts)

                assigned = store.add_chunks(chunks_meta, embeddings)

                results['successful_ingestions'] += 1
                results['chunks_created'] += len(assigned)
                results['details'].append({
                    'doc_id': doc_id,
                    'version': version,
                    'status': 'success',
                    'chunks_created': len(assigned),
                })
                print(f"  OK {doc_id} v{version}: {len(assigned)} chunks")

            except Exception as e:
                results['failed_ingestions'] += 1
                results['details'].append({
                    'doc_id': doc_id,
                    'version': version,
                    'status': 'failed',
                    'error': str(e),
                })
                print(f"  FAIL {doc_id} v{version}: {e}")

    store.save()
    return results


def main():
    print("Version-Aware RAG - Local Store Ingestion")
    print("=" * 50)

    manifest_path = Path("./data/manifest.json")
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found at {manifest_path}")
        return 1

    print(f"Using manifest: {manifest_path}")
    print("Writing to local store: ./vector_store\n")

    results = ingest_all_local(manifest_path)

    print("\nIngestion Results:")
    print(f"  Documents: {results['total_documents']}")
    print(f"  Versions:  {results['total_versions']}")
    print(f"  Succeeded: {results['successful_ingestions']}")
    print(f"  Failed:    {results['failed_ingestions']}")
    print(f"  Chunks:    {results['chunks_created']}")

    # Show final store summary
    store = LocalVectorStore(store_dir="./vector_store")
    print("\nStore contents:")
    for line in store.info()['doc_versions']:
        print(f"  {line}")

    print("\nIngestion completed!")
    return 0 if results['failed_ingestions'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
