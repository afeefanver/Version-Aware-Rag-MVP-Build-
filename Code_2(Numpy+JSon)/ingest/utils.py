"""
Utility functions for the Version-Aware RAG ingestion pipeline.
"""

import re
import hashlib
from typing import List, Tuple, Optional
from datetime import datetime


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text.

    Args:
        text: Input text

    Returns:
        Text with normalized whitespace
    """
    # Replace multiple whitespace characters with single space
    text = re.sub(r'\s+', ' ', text)
    # Strip leading and trailing whitespace
    return text.strip()


def extract_date_from_filename(filename: str) -> Optional[str]:
    """
    Try to extract a date from a filename.
    Looks for patterns like YYYY-MM-DD, YYYY_MM_DD, etc.

    Args:
        filename: Filename to search

    Returns:
        Date string in YYYY-MM-DD format if found, None otherwise
    """
    # Patterns for dates in filenames
    patterns = [
        r'(\d{4})[-_](\d{2})[-_](\d{2})',  # YYYY-MM-DD or YYYY_MM_DD
        r'(\d{4})(\d{2})(\d{2})',          # YYYYMMDD
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            year, month, day = match.groups()
            # Validate that it's a reasonable date
            try:
                datetime(int(year), int(month), int(day))
                return f"{year}-{month}-{day}"
            except ValueError:
                continue

    return None


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate simple similarity between two texts based on character overlap.
    This is a placeholder - for production use proper similarity metrics.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score between 0 and 1
    """
    if not text1 or not text2:
        return 0.0

    # Simple Jaccard similarity on character sets
    set1 = set(text1.lower())
    set2 = set(text2.lower())

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    if union == 0:
        return 0.0

    return intersection / union


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def validate_date_string(date_str: str) -> bool:
    """
    Validate that a string is a valid date in YYYY-MM-DD format.

    Args:
        date_str: Date string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def chunk_list(items: List, chunk_size: int) -> List[List]:
    """
    Split a list into chunks of specified size.

    Args:
        items: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunks
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


# Example usage
if __name__ == "__main__":
    # Test utility functions
    print("Testing utility functions...")

    # Test normalize_whitespace
    test_text = "  This   is    a   test   "
    normalized = normalize_whitespace(test_text)
    print(f"Normalize whitespace: '{test_text}' -> '{normalized}'")

    # Test date extraction
    test_files = [
        "policy_v2025-01-15.md",
        "document_20250322.txt",
        "report-2024-12-01.pdf",
        "no_date_here.docx"
    ]

    for filename in test_files:
        date = extract_date_from_filename(filename)
        print(f"Date in '{filename}': {date}")

    # Test similarity
    text1 = "The quick brown fox jumps over the lazy dog"
    text2 = "The quick brown fox leaps over the sleepy dog"
    text3 = "Completely different content here"

    sim12 = calculate_similarity(text1, text2)
    sim13 = calculate_similarity(text1, text3)
    print(f"Similarity ('{text1[:20]}...', '{text2[:20]}...'): {sim12:.2f}")
    print(f"Similarity ('{text1[:20]}...', '{text3[:20]}...'): {sim13:.2f}")

    # Test date validation
    print(f"Valid date '2025-06-15': {validate_date_string('2025-06-15')}")
    print(f"Invalid date '2025-13-15': {validate_date_string('2025-13-15')}")

    print("Utility function tests completed.")