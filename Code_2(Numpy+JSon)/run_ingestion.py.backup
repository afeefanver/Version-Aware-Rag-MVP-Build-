#!/usr/bin/env python3
"""
Script to run the actual ingestion pipeline for all documents.
"""

import sys
from pathlib import Path
from ingest.pipeline import ingest_all_documents

def main():
    print("Starting Version-Aware RAG Ingestion Pipeline")
    print("=" * 50)

    # Path to manifest
    manifest_path = Path("./data/manifest.json")

    if not manifest_path.exists():
        print(f"ERROR: Manifest not found at {manifest_path}")
        return 1

    print(f"Using manifest: {manifest_path}")

    try:
        # Run ingestion for all documents
        results = ingest_all_documents(manifest_path, force_reingest=False)

        print("\nIngestion Results:")
        print(f"Total documents: {results['total_documents']}")
        print(f"Total versions: {results['total_versions']}")
        print(f"Successful ingestions: {results['successful_ingestions']}")
        print(f"Failed ingestions: {results['failed_ingestions']}")

        if results['failed_ingestions'] > 0:
            print("\nFailed ingestions:")
            for detail in results['details']:
                if detail.get('status') == 'failed':
                    print(f"  - {detail['doc_id']} v{detail['version']}: {detail.get('error', 'Unknown error')}")

        if results['successful_ingestions'] > 0:
            print("\nSuccessfully ingested versions:")
            for detail in results['details']:
                if detail.get('status') == 'success':
                    print(f"  - {detail['doc_id']} v{detail['version']} ({detail['chunks_created']} chunks)")

        print("\nIngestion completed!")
        return 0 if results['failed_ingestions'] == 0 else 1

    except Exception as e:
        print(f"ERROR: Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())