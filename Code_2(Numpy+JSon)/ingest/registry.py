"""
Version registry for Version-Aware RAG system.
Loads and manages document version information from manifest.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class VersionRegistry:
    """Manages document version metadata."""

    def __init__(self, manifest_path: Path):
        """
        Initialize the registry from a manifest file.

        Args:
            manifest_path: Path to the manifest.json file
        """
        self.manifest_path = manifest_path
        self.documents: Dict[str, Dict] = {}
        self._load_manifest()

    def _load_manifest(self):
        """Load document version information from manifest."""
        try:
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)

            # Process each document in the manifest
            for doc_info in manifest_data.get('documents', []):
                doc_id = doc_info['doc_id']
                versions = {}

                for version_info in doc_info['versions']:
                    version = version_info['version']
                    versions[version] = {
                        'effective_from': version_info['effective_from'],
                        'effective_to': version_info['effective_to'],
                        'status': version_info['status'],
                        'source_path': version_info['source_path'],
                        'supersedes': version_info.get('supersedes')
                    }

                self.documents[doc_id] = {
                    'doc_id': doc_id,
                    'versions': versions
                }

        except FileNotFoundError:
            raise FileNotFoundError(f"Manifest file not found: {self.manifest_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in manifest: {e}")

    def get_document_versions(self, doc_id: str) -> Dict:
        """
        Get all version information for a document.

        Args:
            doc_id: Document identifier

        Returns:
            Dictionary of version information or empty dict if not found
        """
        return self.documents.get(doc_id, {}).get('versions', {})

    def get_version_info(self, doc_id: str, version: str) -> Optional[Dict]:
        """
        Get information for a specific document version.

        Args:
            doc_id: Document identifier
            version: Version string

        Returns:
            Version information dictionary or None if not found
        """
        versions = self.get_document_versions(doc_id)
        return versions.get(version)

    def get_current_version(self, doc_id: str) -> Optional[str]:
        """
        Get the current version of a document.

        Args:
            doc_id: Document identifier

        Returns:
            Current version string or None if not found/no current version
        """
        versions = self.get_document_versions(doc_id)
        for version, info in versions.items():
            if info['status'] == 'current':
                return version
        return None

    def is_version_current(self, doc_id: str, version: str) -> bool:
        """
        Check if a specific version is the current version.

        Args:
            doc_id: Document identifier
            version: Version string

        Returns:
            True if version is current, False otherwise
        """
        version_info = self.get_version_info(doc_id, version)
        if version_info:
            return version_info['status'] == 'current'
        return False

    def get_effective_dates(self, doc_id: str, version: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get effective dates for a document version.

        Args:
            doc_id: Document identifier
            version: Version string

        Returns:
            Tuple of (effective_from, effective_to)
        """
        version_info = self.get_version_info(doc_id, version)
        if version_info:
            return version_info['effective_from'], version_info['effective_to']
        return None, None

    def get_documents_at_date(self, target_date: str) -> List[Tuple[str, str]]:
        """
        Get all documents and their versions that were effective on a given date.

        Args:
            target_date: Date string in YYYY-MM-DD format

        Returns:
            List of (doc_id, version) tuples effective on target_date
        """
        effective_docs = []

        for doc_id, doc_info in self.documents.items():
            for version, version_info in doc_info['versions'].items():
                effective_from = version_info['effective_from']
                effective_to = version_info['effective_to']

                # Check if target_date is within the effective range
                if self._is_date_in_range(target_date, effective_from, effective_to):
                    effective_docs.append((doc_id, version))

        return effective_docs

    def _is_date_in_range(self, target_date: str, start_date: Optional[str], end_date: Optional[str]) -> bool:
        """
        Check if a target date falls within a date range.

        Args:
            target_date: Date to check (YYYY-MM-DD)
            start_date: Start of range (YYYY-MM-DD or None)
            end_date: End of range (YYYY-MM-DD or None, None means open-ended)

        Returns:
            True if target_date is in range
        """
        try:
            target = datetime.strptime(target_date, '%Y-%m-%d')

            if start_date:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                if target < start:
                    return False

            if end_date:
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if target > end:
                    return False

            return True
        except ValueError:
            # If date parsing fails, assume it's not in range
            return False

    def get_supersedes_chain(self, doc_id: str, version: str) -> List[str]:
        """
        Get the chain of versions that this version supersedes (oldest first).

        Args:
            doc_id: Document identifier
            version: Version string

        Returns:
            List of version strings from oldest to newest (including this version)
        """
        chain = []
        current_version = version

        # Follow the supersedes chain backwards
        while current_version:
            chain.insert(0, current_version)  # Insert at beginning to maintain order
            version_info = self.get_version_info(doc_id, current_version)
            if version_info:
                current_version = version_info.get('supersedes')
            else:
                break

        return chain

    def get_all_documents(self) -> List[str]:
        """Get list of all document IDs in the registry."""
        return list(self.documents.keys())

    def get_all_versions(self, doc_id: str) -> List[str]:
        """Get all version strings for a document, sorted by effective date."""
        versions = self.get_document_versions(doc_id)
        if not versions:
            return []

        # Sort by effective_from date
        sorted_versions = sorted(
            versions.items(),
            key=lambda x: x[1]['effective_from'] or '9999-12-31'
        )
        return [version for version, _ in sorted_versions]


# Convenience functions for backward compatibility
def load_registry(manifest_path: Path) -> VersionRegistry:
    """Load a version registry from manifest path."""
    return VersionRegistry(manifest_path)


def get_version_info(registry: VersionRegistry, doc_id: str, version: str) -> Optional[Dict]:
    """Get version information from registry."""
    return registry.get_version_info(doc_id, version)


def is_current_version(registry: VersionRegistry, doc_id: str, version: str) -> bool:
    """Check if version is current."""
    return registry.is_version_current(doc_id, version)


# Example usage and testing
if __name__ == "__main__":
    # Test with the manifest if it exists
    manifest_path = Path("../data/manifest.json")
    if manifest_path.exists():
        try:
            registry = VersionRegistry(manifest_path)
            print(f"Loaded registry with {len(registry.get_all_documents())} documents")

            for doc_id in registry.get_all_documents():
                current = registry.get_current_version(doc_id)
                print(f"  {doc_id}: current version = {current}")

                # Show version chain for first document as example
                if doc_id == registry.get_all_documents()[0]:
                    versions = registry.get_all_versions(doc_id)
                    print(f"    All versions: {', '.join(versions)}")

        except Exception as e:
            print(f"Error loading registry: {e}")
    else:
        print(f"Manifest not found at {manifest_path}")
        print("Run this script from the ingest directory or adjust the path.")