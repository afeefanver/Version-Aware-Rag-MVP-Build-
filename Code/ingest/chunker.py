"""
Heading-aware text chunker for Version-Aware RAG system.
Creates chunks of ~300-500 tokens with overlap, preserving section information.
"""

import re
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class TextChunk:
    """Represents a text chunk with metadata."""
    text: str
    chunk_id: str
    section_title: str
    start_char: int
    end_char: int
    token_estimate: int


def chunk_text(
    text: str,
    section_title: str,
    chunk_size: int = 400,
    overlap: int = 50
) -> List[TextChunk]:
    """
    Chunk text into overlapping segments while preserving section information.

    Args:
        text: The text to chunk
        section_title: Title of the section this text belongs to
        chunk_size: Target chunk size in tokens (approximate)
        overlap: Overlap between chunks in tokens (approximate)

    Returns:
        List of TextChunk objects
    """
    # Simple token estimation: ~4 characters per token for English
    # This is a rough estimate - for production, use a proper tokenizer
    chars_per_token = 4
    target_chunk_chars = chunk_size * chars_per_token
    target_overlap_chars = overlap * chars_per_token

    if len(text) <= target_chunk_chars:
        # Text is small enough to be one chunk
        return [TextChunk(
            text=text,
            chunk_id=f"{section_title}_0",
            section_title=section_title,
            start_char=0,
            end_char=len(text),
            token_estimate=len(text) // chars_per_token
        )]

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        # Calculate end position for this chunk
        end = start + target_chunk_chars

        # If this would go beyond the text, adjust to end
        if end > len(text):
            end = len(text)
        else:
            # Try to break at a sentence boundary near the target
            # Look for sentence endings (.!?) within the last 20% of the chunk
            search_start = max(start + int(target_chunk_chars * 0.8), start)
            sentence_end = _find_sentence_boundary(text, search_end, end)
            if sentence_end != -1:
                end = sentence_end

        # Extract the chunk text
        chunk_text = text[start:end]

        # Create chunk object
        chunk = TextChunk(
            text=chunk_text,
            chunk_id=f"{section_title}_{chunk_index}",
            section_title=section_title,
            start_char=start,
            end_char=end,
            token_estimate=len(chunk_text) // chars_per_token
        )
        chunks.append(chunk)

        # Move start position for next chunk (with overlap)
        if end >= len(text):
            break

        start = end - target_overlap_chars
        # Ensure we move forward at least a little
        if start <= chunks[-1].start_char:
            start = chunks[-1].end_char

        chunk_index += 1

    return chunks


def _find_sentence_boundary(text: str, start: int, end: int) -> int:
    """
    Find the best sentence boundary between start and end positions.
    Looks for ., !, ? followed by space or newline.
    """
    # Search backward from end to start for sentence endings
    for i in range(end - 1, max(start, end - 100) - 1, -1):
        if i < len(text) and text[i] in '.!?':
            # Check if followed by space, newline, or end of text
            if i + 1 >= len(text) or text[i + 1] in ' \n\t':
                return i + 1  # Include the punctuation
    return -1  # No good boundary found


def chunk_document_sections(sections: List[Tuple[str, str]]) -> List[TextChunk]:
    """
    Chunk all sections of a document.

    Args:
        sections: List of (section_title, section_content) tuples

    Returns:
        List of all TextChunk objects from all sections
    """
    all_chunks = []

    for section_title, section_content in sections:
        if not section_content.strip():
            continue

        chunks = chunk_text(section_content, section_title)
        all_chunks.extend(chunks)

    return all_chunks


def create_chunk_metadata(
    chunk: TextChunk,
    doc_id: str,
    version: str,
    effective_from: str,
    effective_to: Optional[str] = None
) -> Dict:
    """
    Create metadata dictionary for a chunk that includes version information.

    Args:
        chunk: The TextChunk object
        doc_id: Document identifier
        version: Version string
        effective_from: Start date of version effectiveness
        effective_to: End date of version effectiveness (None for current)

    Returns:
        Dictionary with chunk metadata including version info
    """
    # Determine if this is the current version
    is_current = effective_to is None

    return {
        'chunk_id': chunk.chunk_id,
        'text': chunk.text,
        'section_title': chunk.section_title,
        'doc_id': doc_id,
        'version': version,
        'effective_from': effective_from,
        'effective_to': effective_to,
        'is_current': is_current,
        'start_char': chunk.start_char,
        'end_char': chunk.end_char,
        'token_estimate': chunk.token_estimate
    }


# Example usage and testing
if __name__ == "__main__":
    # Simple test
    sample_text = """
    This is the first paragraph. It contains some information.

    This is the second paragraph with more details. It talks about various things.

    This is the third paragraph. It concludes the discussion.
    """

    chunks = chunk_text(sample_text, "Test Section", chunk_size=50, overlap=10)
    print(f"Created {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i}: {chunk.token_estimate} tokens, '{chunk.text[:50]}...'")