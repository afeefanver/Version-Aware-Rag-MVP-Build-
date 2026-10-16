"""
Main ingestion pipeline for Version-Aware RAG system.
Orchestrates parsing, chunking, versioning, embedding, and storage.
"""

import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json
import logging

from .parsers import parse_document
from .chunker import chunk_document_sections, create_chunk_metadata
from .registry import VersionRegistry
from .embedder import Embedder, create_content_hash, chunks_have_changed


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class IngestionPipeline:
    """Main ingestion pipeline for version-aware documents."""

    def __init__(
        self,
        manifest_path: Path,
        embedder: Optional[Embedder] = None,
        data_root: Optional[Path] = None
    ):
        """
        Initialize the ingestion pipeline.

        Args:
            manifest_path: Path to manifest.json file
            embedder: Embedder instance (if None, creates default)
            data_root: Root directory for data files (if None, uses manifest parent)
        """
        self.manifest_path = manifest_path
        self.data_root = data_root or manifest_path.parent
        self.registry = VersionRegistry(manifest_path)
        self.embedder = embedder or Embedder()

        logger.info(f"IngestionPipeline initialized with manifest: {manifest_path}")

    def resolve_file_path(self, source_path: str) -> Path:
        """
        Resolve a source path from manifest to actual file path.

        Args:
            source_path: Path from manifest (relative to data_root)

        Returns:
            Absolute Path to the file
        """
        # If source_path is already absolute, use it as-is
        path = Path(source_path)
        if path.is_absolute():
            return path

        # Otherwise, treat as relative to data_root
        return self.data_root / source_path

    def ingest_document(
        self,
        doc_id: str,
        version: str,
        force_reingest: bool = False
    ) -> Dict[str, Any]:
        """
        Ingest a specific document version.

        Args:
            doc_id: Document identifier
            version: Version string
            force_reingest: If True, re-ingest even if content hasn't changed

        Returns:
            Dictionary with ingestion results
        """
        logger.info(f"Ingesting {doc_id} version {version}")

        # Get version information from registry
        version_info = self.registry.get_version_info(doc_id, version)
        if not version_info:
            raise ValueError(f"Version {version} not found for document {doc_id}")

        source_path = version_info['source_path']
        effective_from = version_info['effective_from']
        effective_to = version_info['effective_to']

        # Resolve actual file path
        file_path = self.resolve_file_path(source_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")

        # Check if we need to re-ingest (unless forced)
        if not force_reingest:
            # TODO: Implement content hash checking to avoid re-ingesting unchanged docs
            # For now, we'll always ingest but this is where we'd check hashes
            pass

        # Parse the document
        try:
            parsed_doc = parse_document(file_path)
            logger.info(f"Parsed document: {len(parsed_doc['sections'])} sections")
        except Exception as e:
            logger.error(f"Failed to parse document {file_path}: {e}")
            raise

        # Chunk the document sections
        try:
            text_chunks = chunk_document_sections(parsed_doc['sections'])
            logger.info(f"Created {len(text_chunks)} text chunks")
        except Exception as e:
            logger.error(f"Failed to chunk document: {e}")
            raise

        # Prepare chunks for embedding with metadata
        chunks_for_embedding = []
        for chunk in text_chunks:
            # Create chunk metadata with version information
            chunk_metadata = create_chunk_metadata(
                chunk=chunk,
                doc_id=doc_id,
                version=version,
                effective_from=effective_from,
                effective_to=effective_to
            )

            # Add content hash for change detection
            chunk_metadata['content_hash'] = create_content_hash(chunk.text)

            chunks_for_embedding.append({
                'id': chunk.chunk_id,
                'text': chunk.text,
                'metadata': chunk_metadata
            })

        # Generate embeddings
        try:
            embedded_chunks = self.embedder.embed_chunks(chunks_for_embedding)
            logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

        # Store embeddings in vector store
        try:
            storage_success = self.embedder.store_embeddings(embedded_chunks)
            if not storage_success:
                logger.warning("Failed to store some embeddings")
        except Exception as e:
            logger.error(f"Failed to store embeddings: {e}")
            raise

        # Return ingestion summary
        result = {
            'doc_id': doc_id,
            'version': version,
            'file_path': str(file_path),
            'sections_parsed': len(parsed_doc['sections']),
            'chunks_created': len(text_chunks),
            'embeddings_stored': len(embedded_chunks),
            'effective_from': effective_from,
            'effective_to': effective_to,
            'is_current': version_info['status'] == 'current'
        }

        logger.info(f"Ingestion complete: {result}")
        return result

    def ingest_document_from_manifest(self, doc_id: str, version: str) -> Dict[str, Any]:
        """
        Ingest a document version using manifest information.
        This is the main public method for ingesting documents.
        """
        return self.ingest_document(doc_id, version)

    def ingest_all_documents(self, force_reingest: bool = False) -> Dict[str, Any]:
        """
        Ingest all documents and versions from the manifest.

        Args:
            force_reingest: If True, re-ingest all documents even if unchanged

        Returns:
            Summary of ingestion results
        """
        logger.info("Starting ingestion of all documents from manifest")

        results = {
            'total_documents': 0,
            'total_versions': 0,
            'successful_ingestions': 0,
            'failed_ingestions': 0,
            'details': []
        }

        # Get all documents from registry
        doc_ids = self.registry.get_all_documents()
        results['total_documents'] = len(doc_ids)

        for doc_id in doc_ids:
            versions = self.registry.get_all_versions(doc_id)
            results['total_versions'] += len(versions)

            for version in versions:
                try:
                    result = self.ingest_document(doc_id, version, force_reingest)
                    result['status'] = 'success'
                    results['successful_ingestions'] += 1
                    results['details'].append(result)
                    logger.info(f"Successfully ingested {doc_id} v{version}")
                except Exception as e:
                    logger.error(f"Failed to ingest {doc_id} v{version}: {e}")
                    results['failed_ingestions'] += 1
                    results['details'].append({
                        'doc_id': doc_id,
                        'version': version,
                        'status': 'failed',
                        'error': str(e)
                    })

        logger.info(f"Ingestion complete: {results['successful_ingestions']}/{results['total_versions']} versions successful")
        return results

    def publish_version(
        self,
        doc_id: str,
        version: str,
        effective_from: str
    ) -> bool:
        """
        Publish a new version of a document, marking the previous version as superseded.

        Args:
            doc_id: Document identifier
            version: New version string
            effective_from: Date when this version becomes effective (YYYY-MM-DD)

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Publishing {doc_id} version {version} effective from {effective_from}")

        try:
            # Load current manifest
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)

            # Find the document in manifest
            doc_found = False
            for doc_info in manifest_data.get('documents', []):
                if doc_info['doc_id'] == doc_id:
                    doc_found = True
                    versions = doc_info['versions']

                    # Check if version already exists
                    if version in versions:
                        logger.warning(f"Version {version} already exists for {doc_id}")
                        # Update effective date if needed
                        versions[version]['effective_from'] = effective_from
                        versions[version]['effective_to'] = None
                        versions[version]['status'] = 'current'
                    else:
                        # Add new version
                        versions[version] = {
                            'effective_from': effective_from,
                            'effective_to': None,
                            'status': 'current',
                            'source_version': f"policies/{doc_id}_{version}.md",
                            'supersedes': None  # Will be set below
                        }

                    # Find current version and mark it as superseded
                    current_version = None
                    for v, info in versions.items():
                        if info['status'] == 'current' and v != version:
                            current_version = v
                            break

                    if current_version:
                        # Mark previous version as superseded
                        versions[current_version]['status'] = 'superseded'
                        versions[current_version]['effective_to'] = effective_from
                        # Set the new version's supersedes field
                        versions[version]['supersedes'] = current_version
                        logger.info(f"Marked version {current_version} as superseded by {version}")

                    break

            if not doc_found:
                logger.error(f"Document {doc_id} not found in manifest")
                return False

            # Save updated manifest
            with open(self.manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, indent=2)

            # Reload registry to reflect changes
            self.registry = VersionRegistry(self.manifest_path)

            logger.info(f"Successfully published {doc_id} version {version}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish version: {e}")
            return False

    def get_ingestion_status(self) -> Dict[str, Any]:
        """
        Get status of what has been ingested vs what's available.

        Returns:
            Dictionary with ingestion status information
        """
        # This would typically check what's in the vector store vs manifest
        # For now, return basic registry information
        doc_ids = self.registry.get_all_documents()

        status = {
            'total_documents': len(doc_ids),
            'documents': {}
        }

        for doc_id in doc_ids:
            versions = self.registry.get_all_versions(doc_id)
            current_version = self.registry.get_current_version(doc_id)

            status['documents'][doc_id] = {
                'versions': versions,
                'current_version': current_version,
                'version_count': len(versions)
            }

        return status


# Convenience functions
def ingest_document(
    manifest_path: Path,
    doc_id: str,
    version: str,
    embedder: Optional[Embedder] = None
) -> Dict[str, Any]:
    """
    Convenience function to ingest a single document version.

    Args:
        manifest_path: Path to manifest.json
        doc_id: Document identifier
        version: Version string
        embedder: Embedder instance (optional)

    Returns:
        Ingestion result dictionary
    """
    pipeline = IngestionPipeline(manifest_path, embedder=embedder)
    return pipeline.ingest_document(doc_id, version)


def ingest_all_documents(
    manifest_path: Path,
    embedder: Optional[Embedder] = None,
    force_reingest: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to ingest all documents from manifest.

    Args:
        manifest_path: Path to manifest.json
        embedder: Embedder instance (optional)
        force_reingest: If True, re-ingest all documents

    Returns:
        Ingestion summary dictionary
    """
    pipeline = IngestionPipeline(manifest_path, embedder=embedder)
    return pipeline.ingest_all_documents(force_reingest)


def publish_version(
    manifest_path: Path,
    doc_id: str,
    version: str,
    effective_from: str
) -> bool:
    """
    Convenience function to publish a new document version.

    Args:
        manifest_path: Path to manifest.json
        doc_id: Document identifier
        version: New version string
        effective_from: Effective date (YYYY-MM-DD)

    Returns:
        True if successful, False otherwise
    """
    pipeline = IngestionPipeline(manifest_path)
    return pipeline.publish_version(doc_id, version, effective_from)


# Example usage and testing
if __name__ == "__main__":
    # Test with the manifest if it exists
    manifest_path = Path("../data/manifest.json")
    if manifest_path.exists():
        print("Testing IngestionPipeline...")

        try:
            # Initialize pipeline
            pipeline = IngestionPipeline(manifest_path)

            # Show what documents are available
            status = pipeline.get_ingestion_status()
            print(f"Found {status['total_documents']} documents in manifest:")
            for doc_id, info in status['documents'].items():
                print(f"  {doc_id}: {info['version_count']} versions (current: {info['current_version']})")

            # Test ingesting one document (first version of first doc)
            if status['documents']:
                first_doc = list(status['documents'].keys())[0]
                first_version = status['documents'][first_doc]['versions'][0] if status['documents'][first_doc]['versions'] else None

                if first_version:
                    print(f"\nTesting ingestion of {first_doc} version {first_version}...")
                    # Note: This would actually try to ingest the file
                    # For testing without real files, we'll skip the actual ingestion
                    print("Skipping actual ingestion (would require real files)")
                else:
                    print("No versions found for first document")

        except Exception as e:
            print(f"Error testing pipeline: {e}")
    else:
        print(f"Manifest not found at {manifest_path}")
        print("Please ensure you've run the corpus creation steps first.")