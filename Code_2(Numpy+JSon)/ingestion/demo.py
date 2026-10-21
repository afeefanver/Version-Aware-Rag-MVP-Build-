"""
Demo script for the Version-Aware RAG ingestion pipeline.
Shows how the components work together without requiring external services.
"""

import sys
import os
from pathlib import Path

# Add the ingest directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from parsers import parse_document
from chunker import chunk_document_sections, create_chunk_metadata
from registry import VersionRegistry
from embedder import Embedder, create_content_hash
from utils import normalize_whitespace, extract_date_from_filename, calculate_similarity


def demo_parsing():
    """Demo the markdown parser."""
    print("=== PARSING DEMO ===")

    # Create a sample markdown file to parse
    sample_md = """# Sample Policy Document

## Introduction
This is a sample policy document for demonstration purposes.

## Main Procedures
Here we outline the main procedures that users should follow.

### Step 1: Initial Assessment
First, assess the situation carefully.

### Step 2: Take Action
Then, take appropriate action based on the assessment.

## Conclusion
Always follow the documented procedures.
"""

    # Write sample file
    sample_path = Path("../data/demo_sample.md")
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    with open(sample_path, 'w', encoding='utf-8') as f:
        f.write(sample_md)

    # Parse the document
    print(f"Parsing: {sample_path}")
    parsed = parse_document(sample_path)

    print(f"Metadata: {parsed['metadata']}")
    print(f"Content length: {len(parsed['content'])} characters")
    print(f"Number of sections: {len(parsed['sections'])}")

    for i, (title, content) in enumerate(parsed['sections']):
        print(f"  Section {i+1}: '{title}' ({len(content)} chars)")

    return parsed


def demo_chunking(parsed_doc):
    """Demo the chunking functionality."""
    print("\n=== CHUNKING DEMO ===")

    # Chunk the sections
    chunks = chunk_document_sections(parsed_doc['sections'])

    print(f"Created {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i+1}: [{chunk.chunk_id}] {chunk.token_estimate} tokens")
        print(f"    Section: {chunk.section_title}")
        print(f"    Text preview: '{chunk.text[:100]}{'...' if len(chunk.text) > 100 else ''}'")
        print()

    return chunks


def demo_registry():
    """Demo the version registry."""
    print("=== REGISTRY DEMO ===")

    manifest_path = Path("../data/manifest.json")
    if manifest_path.exists():
        print(f"Loading manifest from: {manifest_path}")
        registry = VersionRegistry(manifest_path)

        print(f"Found {len(registry.get_all_documents())} documents:")
        for doc_id in registry.get_all_documents():
            current = registry.get_current_version(doc_id)
            versions = registry.get_all_versions(doc_id)
            print(f"  {doc_id}: {len(versions)} versions (current: {current})")

            # Show an example of version info
            if versions:
                example_version = versions[0]
                info = registry.get_version_info(doc_id, example_version)
                if info:
                    print(f"    Example ({example_version}): {info['effective_from']} to {info['effective_to'] or 'present'}")
    else:
        print(f"Manifest not found at {manifest_path}")
        print("Skipping registry demo.")


def demo_embeddings(chunks):
    """Demo the embedding functionality."""
    print("=== EMBEDDING DEMO ===")

    # Prepare chunks for embedding
    chunks_for_embedding = []
    for chunk in chunks:
        chunk_metadata = create_chunk_metadata(
            chunk=chunk,
            doc_id="demo-doc",
            version="v1.0",
            effective_from="2025-01-01"
        )
        chunk_metadata['content_hash'] = create_content_hash(chunk.text)

        chunks_for_embedding.append({
            'id': chunk.chunk_id,
            'text': chunk.text,
            'metadata': chunk_metadata
        })

    # Create embedder (will use dummy model if sentence-transformers not available)
    print("Creating embedder...")
    embedder = Embedder()

    # Generate embeddings
    print(f"Generating embeddings for {len(chunks_for_embedding)} chunks...")
    embedded_chunks = embedder.embed_chunks(chunks_for_embedding)

    print(f"Generated {len(embedded_chunks)} embeddings:")
    for i, embedded in enumerate(embedded_chunks[:3]):  # Show first 3
        print(f"  Embedding {i+1}: {len(embedded.embedding)} dimensions")
        print(f"    Text: '{embedded.text[:50]}{'...' if len(embedded.text) > 50 else ''}'")
        print(f"    Metadata keys: {list(embedded.metadata.keys())}")

    # Test similarity search (will return empty if Qdrant not available)
    print("\nTesting similarity search...")
    results = embedder.search_similar("sample policy procedures", limit=2)
    print(f"Found {len(results)} similar chunks")

    return embedded_chunks


def demo_utils():
    """Demo utility functions."""
    print("\n=== UTILS DEMO ===")

    # Test whitespace normalization
    messy = "  This   has   irregular   spacing  "
    clean = normalize_whitespace(messy)
    print(f"Whitespace normalization: '{messy}' -> '{clean}'")

    # Test date extraction from filename
    test_file = "policy_v2025-03-15.pdf"
    date = extract_date_from_filename(test_file)
    print(f"Date extraction: '{test_file}' -> {date}")

    # Test similarity
    text1 = "Password must be changed every 90 days"
    text2 = "Password must be changed every 60 days"
    similarity = calculate_similarity(text1, text2)
    print(f"Similarity between policies: {similarity:.2f}")

    # Show that it detects the difference
    if similarity < 0.9:
        print("PASS: Correctly detected difference between policy versions")
    else:
        print("FAIL: Failed to detect difference between policy versions")


def main():
    """Run all demos."""
    print("Version-Aware RAG Ingestion Pipeline Demo")
    print("=" * 50)

    try:
        # Run demos in sequence
        parsed = demo_parsing()
        chunks = demo_chunking(parsed)
        demo_registry()
        demo_embeddings(chunks)
        demo_utils()

        print("\n" + "=" * 50)
        print("Demo completed successfully!")
        print("\nNext steps:")
        print("1. Set up Qdrant vector database (optional for testing)")
        print("2. Install sentence-transformers for real embeddings: pip install sentence-transformers")
        print("3. Run actual ingestion on your corpus documents")
        print("4. Proceed to Phase 3: Version-aware retrieval")

    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()