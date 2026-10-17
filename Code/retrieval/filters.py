"""
Version and date-based filtering for Version-Aware RAG retrieval.
Handles different query modes: default, as-of, explicit version, compare.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re


def build_default_filter() -> Dict[str, Any]:
    """
    Build filter for default mode: only current versions.

    Returns:
        Qdrant-compatible filter dictionary for is_current = true
    """
    return {
        "must": [
            {
                "key": "is_current",
                "match": {"value": True}
            }
        ]
    }


def build_as_of_filter(target_date: str) -> Dict[str, Any]:
    """
    Build filter for as-of mode: effective_from <= date AND (effective_to IS NULL OR effective_to >= date).

    Args:
        target_date: Date string in YYYY-MM-DD format

    Returns:
        Qdrant-compatible filter dictionary
    """
    # Validate date format
    try:
        datetime.strptime(target_date, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date format: {target_date}. Expected YYYY-MM-DD")

    return {
        "must": [
            {
                "key": "effective_from",
                "range": {"lte": target_date}
            }
        ],
        "should": [
            {
                "key": "effective_to",
                "range": {"gte": target_date}
            },
            {
                "key": "effective_to",
                "is_null": True
            }
        ]
    }


def build_explicit_version_filter(doc_id: str, version: str) -> Dict[str, Any]:
    """
    Build filter for explicit version mode: specific doc_id and version.

    Args:
        doc_id: Document identifier
        version: Version string

    Returns:
        Qdrant-compatible filter dictionary
    """
    return {
        "must": [
            {
                "key": "doc_id",
                "match": {"value": doc_id}
            },
            {
                "key": "version",
                "match": {"value": version}
            }
        ]
    }


def build_compare_filter(doc_id: str, version_a: str, version_b: str) -> List[Dict[str, Any]]:
    """
    Build filters for compare mode: two separate filters for two versions.

    Args:
        doc_id: Document identifier
        version_a: First version string
        version_b: Second version string

    Returns:
        List of two Qdrant-compatible filter dictionaries
    """
    filter_a = {
        "must": [
            {
                "key": "doc_id",
                "match": {"value": doc_id}
            },
            {
                "key": "version",
                "match": {"value": version_a}
            }
        ]
    }

    filter_b = {
        "must": [
            {
                "key": "doc_id",
                "match": {"value": doc_id}
            },
            {
                "key": "version",
                "match": {"value": version_b}
            }
        ]
    }

    return [filter_a, filter_b]


def extract_date_from_question(question: str) -> Optional[str]:
    """
    Extract date from question using regex patterns.
    Looks for patterns like: "on 2025-06-01", "as of 2025-06-01", "in June 2025", etc.

    Args:
        question: Input question string

    Returns:
        Date string in YYYY-MM-DD format if found, None otherwise
    """
    # Patterns for explicit dates
    date_patterns = [
        r'\b(\d{4})-(\d{2})-(\d{2})\b',  # YYYY-MM-DD
        r'\b(\d{2})/(\d{2})/(\d{4})\b',  # MM/DD/YYYY
        r'\b(\d{2})-(\d{2})-(\d{4})\b',  # MM-DD-YYYY
    ]

    for pattern in date_patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            if pattern == date_patterns[0]:  # YYYY-MM-DD
                year, month, day = match.groups()
                return f"{year}-{month}-{day}"
            elif pattern == date_patterns[1]:  # MM/DD/YYYY
                month, day, year = match.groups()
                return f"{year}-{month}-{day}"
            elif pattern == date_patterns[2]:  # MM-DD-YYYY
                month, day, year = match.groups()
                return f"{year}-{month}-{day}"

    # Patterns for month/year combinations
    month_patterns = [
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b',
        r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})\b'
    ]

    month_map = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
        'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12',
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
        'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
    }

    for pattern in month_patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            month_str, year = match.groups()
            month = month_map[month_str.lower()]
            return f"{year}-{month}-01"  # Default to first day of month

    return None


def extract_version_from_question(question: str) -> Optional[str]:
    """
    Extract version from question using regex patterns.
    Looks for patterns like: "version 2.0", "v2", "according to v2.1", etc.

    Args:
        question: Input question string

    Returns:
        Version string if found, None otherwise
    """
    # Patterns for version strings
    version_patterns = [
        r'\bv?(\d+\.\d+(?:\.\d+)?)\b',  # v1.0, v2.1.5, 3.0
        r'\bversion\s+v?(\d+\.\d+(?:\.\d+)?)\b',  # version 2.0
        r'\baccording\s+to\s+v?(\d+\.\d+(?:\.\d+)?)\b',  # according to v2.1
    ]

    for pattern in version_patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def detect_query_mode(question: str) -> Tuple[str, Dict[str, Any]]:
    """
    Detect the query mode and extract parameters from question.

    Args:
        question: Input question string

    Returns:
        Tuple of (mode, parameters) where mode is one of:
        - 'default': no special modifiers
        - 'as_of': contains date reference
        - 'explicit_version': contains version reference
        - 'compare': contains two version references for comparison
        - 'unknown': couldn't determine
    """
    question_lower = question.lower()

    # Check for explicit as-of patterns
    as_of_patterns = [
        r'as\s+of\s+',
        r'on\s+',
        r'in\s+',
        r'during\s+',
        r'at\s+',
        r'what\s+was.*on',
        r'what\s+was.*in',
        r'history.*as\s+of',
        r'historical.*as\s+of'
    ]

    for pattern in as_of_patterns:
        if re.search(pattern, question_lower):
            date = extract_date_from_question(question)
            if date:
                return ('as_of', {'date': date})

    # Check for explicit version patterns
    version_patterns = [
        r'according\s+to\s+',
        r'version\s+',
        r'v\d+',
        r'in\s+version\s+',
        r'use\s+version\s+',
        r'based\s+on\s+version\s+'
    ]

    for pattern in version_patterns:
        if re.search(pattern, question_lower):
            version = extract_version_from_question(question)
            if version:
                # Check if we need doc_id too - for now assume we need to get it from context
                return ('explicit_version', {'version': version})

    # Check for compare patterns (two versions)
    compare_patterns = [
        r'compare\s+.*v?\d+\.\d+.*v?\d+\.\d+',
        r'difference\s+between\s+.*v?\d+\.\d+.*and\s+.*v?\d+\.\d+',
        r'vs\s+v?\d+\.\d+\s+v?\d+\.\d+',
        r'change\s+between\s+.*v?\d+\.\d+.*and\s+.*v?\d+\.\d+'
    ]

    for pattern in compare_patterns:
        if re.search(pattern, question_lower):
            # Extract both versions
            versions = re.findall(r'v?(\d+\.\d+(?:\.\d+)?)', question)
            if len(versions) >= 2:
                return ('compare', {'version_a': versions[0], 'version_b': versions[1]})

    # Default mode
    return ('default', {})


def build_filter_for_mode(mode: str, params: Dict[str, Any], doc_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Build Qdrant filter based on query mode and parameters.

    Args:
        mode: Query mode ('default', 'as_of', 'explicit_version', 'compare')
        params: Parameters for the mode
        doc_id: Document ID (required for some modes)

    Returns:
        Qdrant-compatible filter dictionary or None for invalid combinations
    """
    if mode == 'default':
        return build_default_filter()

    elif mode == 'as_of':
        if 'date' not in params:
            return None
        return build_as_of_filter(params['date'])

    elif mode == 'explicit_version':
        if 'version' not in params or not doc_id:
            return None
        return build_explicit_version_filter(doc_id, params['version'])

    elif mode == 'compare':
        if 'version_a' not in params or 'version_b' not in params or not doc_id:
            return None
        # For compare mode, we return a list of filters to be used separately
        return build_compare_filter(doc_id, params['version_a'], params['version_b'])

    else:
        return None


# Example usage and testing
if __name__ == "__main__":
    # Test filter building
    print("Testing filter building...")

    # Default filter
    default_filter = build_default_filter()
    print(f"Default filter: {default_filter}")

    # As-of filter
    as_of_filter = build_as_of_filter("2025-06-01")
    print(f"As-of filter (2025-06-01): {as_of_filter}")

    # Explicit version filter
    version_filter = build_explicit_version_filter("password-policy", "v2.0")
    print(f"Explicit version filter (password-policy v2.0): {version_filter}")

    # Compare filter
    compare_filters = build_compare_filter("password-policy", "v1.0", "v3.0")
    print(f"Compare filter (password-policy v1.0 vs v3.0): {compare_filters}")

    # Test question parsing
    test_questions = [
        "What is the current password policy?",
        "What was the password policy as of 2025-06-01?",
        "What was the policy on January 15, 2025?",
        "Show me the password policy according to v2.0",
        "Compare version v1.0 and v3.0 of the password policy",
        "What changed between v1.0 and v2.0?",
        "How does v2.1 differ from v2.0?",
        "Tell me about the incident response procedure"
    ]

    print("\nTesting question parsing:")
    for question in test_questions:
        mode, params = detect_query_mode(question)
        print(f"Q: '{question}'")
        print(f"  Mode: {mode}, Params: {params}")
        if mode in ['explicit_version', 'compare']:
            # For these modes, we'd need a doc_id to build filter
            filter_result = build_filter_for_mode(mode, params, "password-policy")
            print(f"  Filter: {filter_result}")
        elif mode == 'as_of':
            filter_result = build_filter_for_mode(mode, params)
            print(f"  Filter: {filter_result}")
        else:
            filter_result = build_filter_for_mode(mode, params)
            print(f"  Filter: {filter_result}")
        print()