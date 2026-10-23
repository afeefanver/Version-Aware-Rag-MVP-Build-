"""
Document parsers for Version-Aware RAG system.
Supports Markdown, with placeholders for PDF and DOCX.
"""

import re
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import frontmatter


def parse_markdown(file_path: Path) -> Dict:
    """
    Parse a markdown file and extract metadata and content.

    Args:
        file_path: Path to the markdown file

    Returns:
        Dictionary containing:
        - metadata: File metadata (from frontmatter if present)
        - content: Clean text content
        - sections: List of (section_title, section_content) tuples
        - raw_content: Original markdown content
    """
    try:
        # Parse frontmatter if present
        with open(file_path, 'r', encoding='utf-8') as f:
            parsed = frontmatter.load(f)

        metadata = parsed.metadata if parsed.metadata else {}
        content = parsed.content

    except Exception:
        # If frontmatter parsing fails, treat as plain markdown
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        metadata = {}

    # Extract sections based on markdown headers
    sections = _extract_sections(content)

    # Clean content (normalize whitespace, etc.)
    clean_content = _clean_text(content)

    return {
        'metadata': metadata,
        'content': clean_content,
        'sections': sections,
        'raw_content': content,
        'file_path': str(file_path),
        'file_name': file_path.name
    }


def _extract_sections(content: str) -> List[Tuple[str, str]]:
    """
    Extract sections from markdown content based on headers.

    Returns:
        List of (section_title, section_content) tuples
    """
    # Pattern to match markdown headers (### Header, ## Header, # Header)
    header_pattern = r'^(#{1,6})\s+(.+)$'

    lines = content.split('\n')
    sections = []
    current_section_title = "Introduction"
    current_section_content = []

    for line in lines:
        header_match = re.match(header_pattern, line)
        if header_match:
            # Save previous section
            if current_section_content:
                sections.append((
                    current_section_title,
                    '\n'.join(current_section_content).strip()
                ))

            # Start new section
            current_section_title = header_match.group(2).strip()
            current_section_content = []
        else:
            current_section_content.append(line)

    # Don't forget the last section
    if current_section_content:
        sections.append((
            current_section_title,
            '\n'.join(current_section_content).strip()
        ))

    # If no sections were found, treat entire content as one section
    if not sections:
        sections = [("Document", content.strip())]

    return sections


def _clean_text(text: str) -> str:
    """
    Clean text by normalizing whitespace and removing extra blank lines.
    """
    # Replace multiple spaces/newlines with single space/newline
    text = re.sub(r'\s+', ' ', text)
    # Remove whitespace at start and end
    text = text.strip()
    return text


def parse_document(file_path: Path) -> Dict:
    """
    Main parser function that dispatches based on file extension.

    Args:
        file_path: Path to the document

    Returns:
        Parsed document dictionary
    """
    extension = file_path.suffix.lower()

    if extension == '.md' or extension == '.markdown':
        return parse_markdown(file_path)
    elif extension == '.pdf':
        # TODO: Implement PDF parser using pypdf or similar
        raise NotImplementedError("PDF parser not yet implemented")
    elif extension in ['.docx', '.doc']:
        # TODO: Implement DOCX parser using python-docx
        raise NotImplementedError("DOCX parser not yet implemented")
    elif extension == '.txt':
        # Treat as plain text
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            'metadata': {},
            'content': _clean_text(content),
            'sections': [("Document", content.strip())],
            'raw_content': content,
            'file_path': str(file_path),
            'file_name': file_path.name
        }
    else:
        raise ValueError(f"Unsupported file extension: {extension}")


# Example usage and testing
if __name__ == "__main__":
    # Test with a sample file if available
    import sys
    if len(sys.argv) > 1:
        test_path = Path(sys.argv[1])
        if test_path.exists():
            result = parse_document(test_path)
            print(f"Parsed: {result['file_name']}")
            print(f"Sections found: {len(result['sections'])}")
            for title, content in result['sections'][:3]:  # Show first 3 sections
                print(f"- {title}: {len(content)} chars")
        else:
            print(f"File not found: {test_path}")
    else:
        print("Usage: python parsers.py <file_path>")