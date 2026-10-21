"""
Prompt templates for Version-Aware RAG answer generation.
Handles version attribution and structured output formatting.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class AnswerFormat(str, Enum):
    """Output format options for generated answers."""
    NARRATIVE = "narrative"
    BULLET_POINTS = "bullet_points"
    STRUCTURED = "structured"
    VERSION_COMPARISON = "version_comparison"


@dataclass
class GeneratedAnswer:
    """Structure for generated answers with version attribution."""
    question: str
    answer: str
    format: AnswerFormat
    sources: List[Dict[str, Any]]
    version_attribution: Dict[str, str]
    confidence_score: float
    metadata: Dict[str, Any]


class PromptTemplate:
    """Handles prompt templating for version-aware answer generation."""

    def __init__(self):
        self.templates = {
            AnswerFormat.NARRATIVE: self._narrative_template,
            AnswerFormat.BULLET_POINTS: self._bullet_point_template,
            AnswerFormat.STRUCTURED: self._structured_template,
            AnswerFormat.VERSION_COMPARISON: self._version_comparison_template
        }

    def build_prompt(
        self,
        question: str,
        search_results: List[Dict[str, Any]],
        answer_format: AnswerFormat = AnswerFormat.NARRATIVE,
        include_version_attribution: bool = True
    ) -> str:
        """
        Build a prompt for answer generation based on search results.

        Args:
            question: Original user question
            search_results: List of search results from retriever
            answer_format: Desired output format
            include_version_attribution: Whether to include version info in prompt

        Returns:
            Formatted prompt string
        """
        if not search_results:
            return self._build_no_results_prompt(question)

        # Prepare context from search results
        context_blocks = []
        version_info = {}

        for i, result in enumerate(search_results):
            metadata = result.get('metadata', {})
            doc_id = metadata.get('doc_id', 'unknown')
            version = metadata.get('version', 'unknown')
            text = result.get('text', '')
            score = result.get('score', 0.0)

            # Build context block
            context_parts = [f"[Source {i+1}]"]
            if include_version_attribution:
                context_parts.append(f"Document: {doc_id}")
                context_parts.append(f"Version: {version}")
                # Track version info for attribution
                if doc_id not in version_info:
                    version_info[doc_id] = version
                elif version_info[doc_id] != version:
                    # Handle case where same doc has multiple versions
                    version_info[doc_id] = f"{version_info[doc_id]}/{version}"

            context_parts.append(f"Relevance: {score:.3f}")
            context_parts.append(f"Content: {text}")
            context_blocks.append("\n".join(context_parts))

        context = "\n\n".join(context_blocks)

        # Build the prompt using selected template
        template_func = self.templates.get(answer_format, self._narrative_template)
        return template_func(question, context, version_info)

    def _narrative_template(self, question: str, context: str, version_info: Dict[str, str]) -> str:
        """Template for narrative-style answers."""
        version_attribution_text = ""
        if version_info:
            version_attribution_text = "\n\nVersion Information:\n" + "\n".join(
                [f"- {doc_id}: {version}" for doc_id, version in version_info.items()]
            )

        return f"""You are an IT Security Policy assistant. Answer the user's question based on the provided policy sources.

Question: {question}

Relevant Policy Sources:
{context}{version_attribution_text}

Instructions:
1. Provide a clear, accurate answer based ONLY on the provided sources
2. Include version attribution when referencing specific policy information
3. If sources conflict, note the discrepancies and indicate which version is current
4. If the sources don't contain sufficient information, state what information is missing
5. Write in a professional, helpful tone appropriate for IT security policy inquiries

Answer:"""

    def _bullet_point_template(self, question: str, context: str, version_info: Dict[str, str]) -> str:
        """Template for bullet-point style answers."""
        version_attribution_text = ""
        if version_info:
            version_attribution_text = "\n\nVersion Information:\n" + "\n".join(
                [f"- {doc_id}: {version}" for doc_id, version in version_info.items()]
            )

        return f"""You are an IT Security Policy assistant. Answer the user's question in bullet point format based on the provided policy sources.

Question: {question}

Relevant Policy Sources:
{context}{version_attribution_text}

Instructions:
1. Provide answer as clear, concise bullet points
2. Each bullet point should cite its source(s) using [Source X] notation
3. Include version information when relevant
4. Focus on actionable information and policy requirements
5. If sources conflict, note the discrepancies
6. If insufficient information, state what's missing

Answer (bullet points):"""

    def _structured_template(self, question: str, context: str, version_info: Dict[str, str]) -> str:
        """Template for structured answers with sections."""
        version_attribution_text = ""
        if version_info:
            version_attribution_text = "\n\nVersion Information:\n" + "\n".join(
                [f"- {doc_id}: {version}" for doc_id, version in version_info.items()]
            )

        return f"""You are an IT Security Policy assistant. Provide a structured answer to the user's question based on the provided policy sources.

Question: {question}

Relevant Policy Sources:
{context}{version_attribution_text}

Instructions:
Structure your answer with the following sections:
1. **Direct Answer**: Clear, concise response to the question
2. **Policy Details**: Specific requirements, procedures, or guidelines from sources
3. **Version Information**: Relevant version details and current status
4. **Additional Notes**: Any caveats, conflicts, or missing information
5. **Sources**: Reference to source documents used

Answer:"""

    def _version_comparison_template(self, question: str, context: str, version_info: Dict[str, str]) -> str:
        """Template for version comparison answers."""
        return f"""You are an IT Security Policy assistant. Compare and contrast policy versions based on the user's question and provided sources.

Question: {question}

Relevant Policy Sources:
{context}

Instructions:
1. Organize answer by version/document for easy comparison
2. Clearly indicate which version is current vs. historical
3. Highlight differences, additions, deletions, and modifications between versions
4. Note the effective dates for each version
5. If the question asks about a specific aspect, focus the comparison on that aspect
6. Use clear version labels and timestamps

Answer:"""

    def _build_no_results_prompt(self, question: str) -> str:
        """Build prompt when no search results are found."""
        return f"""You are an IT Security Policy assistant. The user asked a question but no relevant policy sources were found.

Question: {question}

Instructions:
1. Clearly state that no relevant policy information was found in the available sources
2. Suggest what types of policies might contain this information
3. Recommend how the user might refine their question
4. Offer to help with related policy questions that might be in the knowledge base
5. Be helpful and professional in your response

Answer:"""


def create_prompt_template() -> PromptTemplate:
    """Factory function to create a PromptTemplate instance."""
    return PromptTemplate()


# Example usage and testing
if __name__ == "__main__":
    # Test the prompt template
    print("Testing PromptTemplate...")

    template = PromptTemplate()

    # Mock search results
    mock_results = [
        {
            'text': '- Maximum password age: 60 days - Passwords must be changed every 60 days - Passwords must contain at least 12 characters',
            'metadata': {
                'doc_id': 'password-policy',
                'version': 'v3.0',
                'effective_from': '2026-01-01',
                'effective_to': None,
                'is_current': True
            },
            'score': 0.85
        },
        {
            'text': '- Maximum password age: 90 days - Passwords must be changed every 90 days - Passwords must contain at least 8 characters',
            'metadata': {
                'doc_id': 'password-policy',
                'version': 'v2.0',
                'effective_from': '2025-07-01',
                'effective_to': '2025-12-31',
                'is_current': False
            },
            'score': 0.72
        }
    ]

    # Test different formats
    test_question = "What is the current password policy?"

    for fmt in AnswerFormat:
        print(f"\n--- {fmt.value.upper()} FORMAT ---")
        prompt = template.build_prompt(test_question, mock_results, fmt)
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)