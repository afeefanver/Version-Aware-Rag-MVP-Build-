"""
Answer generator for Version-Aware RAG system.
Creates formatted answers from retrieved context with version attribution.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
try:
    from .prompt_template import PromptTemplate, AnswerFormat, GeneratedAnswer
except ImportError:
    # When running as a script, import directly
    from prompt_template import PromptTemplate, AnswerFormat, GeneratedAnswer
import json
import re


class Generator:
    """Generates answers from retrieved context with version attribution."""

    def __init__(self, answer_format: AnswerFormat = AnswerFormat.NARRATIVE):
        """
        Initialize the generator.

        Args:
            answer_format: Default format for generated answers
        """
        self.prompt_template = PromptTemplate()
        self.answer_format = answer_format

    def generate_answer(
        self,
        question: str,
        search_results: List[Dict[str, Any]],
        answer_format: Optional[AnswerFormat] = None,
        include_version_attribution: bool = True
    ) -> GeneratedAnswer:
        """
        Generate an answer from search results.

        Args:
            question: Original user question
            search_results: List of search results from retriever
            answer_format: Output format (uses default if None)
            include_version_attribution: Whether to include version info

        Returns:
            GeneratedAnswer object with formatted answer and metadata
        """
        fmt = answer_format or self.answer_format

        # Build prompt
        prompt = self.prompt_template.build_prompt(
            question=question,
            search_results=search_results,
            answer_format=fmt,
            include_version_attribution=include_version_attribution
        )

        # In a real implementation, this would call an LLM
        # For now, we'll create a template-based answer
        answer_text = self._create_template_answer(
            question=question,
            search_results=search_results,
            answer_format=fmt
        )

        # Extract version attribution from results
        version_attribution = self._extract_version_attribution(search_results)

        # Calculate confidence score based on result scores
        confidence_score = self._calculate_confidence(search_results)

        # Prepare sources for citation
        sources = self._prepare_sources(search_results)

        # Create generated answer
        generated_answer = GeneratedAnswer(
            question=question,
            answer=answer_text,
            format=fmt,
            sources=sources,
            version_attribution=version_attribution,
            confidence_score=confidence_score,
            metadata={
                'num_sources': len(search_results),
                'answer_format': fmt.value,
                'has_version_attribution': include_version_attribution
            }
        )

        return generated_answer

    def _create_template_answer(
        self,
        question: str,
        search_results: List[Dict[str, Any]],
        answer_format: AnswerFormat
    ) -> str:
        """
        Create an answer using template-based approach (placeholder for LLM).
        In production, this would be replaced with actual LLM calls.
        """
        if not search_results:
            return "I could not find any relevant policy information to answer your question. Please try rephrasing or check if the topic is covered in the available security policies."

        # Extract and organize information by version/document
        version_groups = {}
        for result in search_results:
            metadata = result.get('metadata', {})
            doc_id = metadata.get('doc_id', 'unknown')
            version = metadata.get('version', 'unknown')
            text = result.get('text', '').strip()

            key = f"{doc_id}_v{version}"
            if key not in version_groups:
                version_groups[key] = {
                    'doc_id': doc_id,
                    'version': version,
                    'texts': [],
                    'is_current': metadata.get('is_current', False),
                    'effective_from': metadata.get('effective_from'),
                    'effective_to': metadata.get('effective_to')
                }
            version_groups[key]['texts'].append(text)

        # Generate answer based on format
        if answer_format == AnswerFormat.BULLET_POINTS:
            return self._generate_bullet_point_answer(question, version_groups)
        elif answer_format == AnswerFormat.VERSION_COMPARISON:
            return self._generate_comparison_answer(question, version_groups)
        elif answer_format == AnswerFormat.STRUCTURED:
            return self._generate_structured_answer(question, version_groups)
        else:  # NARRATIVE (default)
            return self._generate_narrative_answer(question, version_groups)

    def _generate_narrative_answer(
        self,
        question: str,
        version_groups: Dict[str, Dict]
    ) -> str:
        """Generate a narrative-style answer."""
        # Sort by current status first, then by effective date
        sorted_groups = sorted(
            version_groups.values(),
            key=lambda x: (not x['is_current'], x['effective_from'] or '9999-99-99'),
            reverse=True
        )

        # Build answer
        answer_parts = []

        # Add direct answer based on most current/relevant source
        if sorted_groups:
            primary_group = sorted_groups[0]
            answer_parts.append(self._extract_key_information(question, primary_group['texts'][0]))

            # Add version context if multiple versions
            if len(sorted_groups) > 1:
                version_info = []
                for group in sorted_groups:
                    status = "CURRENT" if group['is_current'] else f"effective {group['effective_from']} to {group['effective_to'] or 'present'}"
                    version_info.append(f"{group['doc_id']} v{group['version']} ({status})")

                answer_parts.append(f"\n\nThis information spans multiple versions: {'; '.join(version_info)}.")

                # Add specific version details if question implies version awareness
                if any(word in question.lower() for word in ['current', 'now', 'present']):
                    current_versions = [g for g in sorted_groups if g['is_current']]
                    if current_versions:
                        current_info = current_versions[0]
                        answer_parts.append(f"The current version ({current_info['doc_id']} v{current_info['version']}) is effective from {current_info['effective_from']}.")
                elif any(word in question.lower() for word in ['was', 'previous', 'before', 'historical']):
                    historical_versions = [g for g in sorted_groups if not g['is_current']]
                    if historical_versions:
                        hist_info = historical_versions[0]
                        answer_parts.append(f"This reflects the historical version ({hist_info['doc_id']} v{hist_info['version']}) effective from {hist_info['effective_from']} to {hist_info['effective_to'] or 'present'}.")

        return " ".join(answer_parts) if answer_parts else "I found relevant policy information but could not formulate a specific answer. Please consult the source documents directly."

    def _generate_bullet_point_answer(
        self,
        question: str,
        version_groups: Dict[str, Dict]
    ) -> str:
        """Generate a bullet-point style answer."""
        bullets = []

        # Group by document for cleaner presentation
        doc_groups = {}
        for group in version_groups.values():
            doc_id = group['doc_id']
            if doc_id not in doc_groups:
                doc_groups[doc_id] = []
            doc_groups[doc_id].append(group)

        # Generate bullets for each document
        for doc_id, groups in doc_groups.items():
            # Sort versions within document (current first)
            sorted_groups = sorted(groups, key=lambda x: not x['is_current'])

            for group in sorted_groups:
                version_status = " (CURRENT)" if group['is_current'] else f" (v{group['version']})"
                key_info = self._extract_key_information(question, group['texts'][0])
                bullets.append(f"• {key_info} [{doc_id}{version_status}]")

        if not bullets:
            return "• No specific policy information found to answer this question."

        return "\n".join(bullets)

    def _generate_comparison_answer(
        self,
        question: str,
        version_groups: Dict[str, Dict]
    ) -> str:
        """Generate a version comparison answer."""
        if len(version_groups) < 2:
            return self._generate_narrative_answer(question, version_groups)

        # Organize by document
        doc_versions = {}
        for group in version_groups.values():
            doc_id = group['doc_id']
            if doc_id not in doc_versions:
                doc_versions[doc_id] = []
            doc_versions[doc_id].append(group)

        answer_parts = ["Version Comparison:"]

        for doc_id, versions in doc_versions.items():
            # Sort by version or effective date
            sorted_versions = sorted(
                versions,
                key=lambda x: (
                    [int(n) for n in re.findall(r'\d+', x['version'])],
                    x['effective_from'] or '9999-99-99'
                )
            )

            answer_parts.append(f"\n{doc_id.upper()}:")
            for version in sorted_versions:
                status = "CURRENT" if version['is_current'] else f"{version['effective_from']} to {version['effective_to'] or 'present'}"
                key_info = self._extract_key_information(question, version['texts'][0])
                answer_parts.append(f"  v{version['version']} ({status}): {key_info}")

        return "\n".join(answer_parts)

    def _generate_structured_answer(
        self,
        question: str,
        version_groups: Dict[str, Dict]
    ) -> str:
        """Generate a structured answer with sections."""
        sections = []

        # Executive Summary
        if version_groups:
            primary_group = list(version_groups.values())[0]
            summary = self._extract_key_information(question, primary_group['texts'][0])
            sections.append(f"**Direct Answer**: {summary}")

        # Policy Details
        details = []
        for group in version_groups.values():
            status = "Current" if group['is_current'] else f"Version {group['version']}"
            detail = f"- {group['doc_id']} {status}: {self._extract_key_information(question, group['texts'][0])}"
            details.append(detail)

        if details:
            sections.append("**Policy Details**:\n" + "\n".join(details))

        # Version Information
        version_details = []
        for group in version_groups.values():
            if group['is_current']:
                version_details.append(f"- {group['doc_id']} v{group['version']}: CURRENT (effective from {group['effective_from']})")
            else:
                version_details.append(f"- {group['doc_id']} v{group['version']}: {group['effective_from']} to {group['effective_to'] or 'present'}")

        if version_details:
            sections.append("**Version Information**:\n" + "\n".join(version_details))

        # Sources
        sources = []
        for group in version_groups.values():
            sources.append(f"- {group['doc_id']} v{group['version']}")

        if sources:
            sections.append("**Sources**:\n" + "\n".join(sources))

        return "\n\n".join(sections)

    def _extract_key_information(self, question: str, text: str) -> str:
        """Extract key information from text that answers the question."""
        # Simple extraction - in production, this would be more sophisticated
        # For now, return the first sentence or two that seems relevant
        sentences = re.split(r'[.!?]+', text)
        relevant_sentences = []

        # Look for sentences that contain keywords from the question
        question_words = set(question.lower().split())
        # Remove common words
        stop_words = {'what', 'is', 'the', 'of', 'for', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'a', 'an'}
        question_words = question_words - stop_words

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_words = set(sentence.lower().split())
            # Check if sentence shares significant vocabulary with question
            if len(sentence_words & question_words) >= min(2, len(question_words) // 2):
                relevant_sentences.append(sentence)

        if relevant_sentences:
            # Return first 1-2 relevant sentences
            result = '. '.join(relevant_sentences[:2])
            if not result.endswith('.'):
                result += '.'
            return result
        else:
            # Fallback to first sentence
            first_sentence = sentences[0].strip() if sentences else text[:100]
            if not first_sentence.endswith('.'):
                first_sentence += '.'
            return first_sentence

    def _extract_version_attribution(
        self,
        search_results: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Extract version attribution from search results."""
        attribution = {}
        for result in search_results:
            metadata = result.get('metadata', {})
            doc_id = metadata.get('doc_id', 'unknown')
            version = metadata.get('version', 'unknown')
            if doc_id not in attribution:
                attribution[doc_id] = version
            elif attribution[doc_id] != version:
                # Handle multiple versions of same doc
                attribution[doc_id] = f"{attribution[doc_id]}/{version}"
        return attribution

    def _calculate_confidence(
        self,
        search_results: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence score based on result scores."""
        if not search_results:
            return 0.0

        # Average of top 3 scores, or all if less than 3
        scores = [result.get('score', 0.0) for result in search_results]
        scores.sort(reverse=True)
        top_scores = scores[:min(3, len(scores))]

        if not top_scores:
            return 0.0

        return sum(top_scores) / len(top_scores)

    def _prepare_sources(
        self,
        search_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prepare source information for citation."""
        sources = []
        for i, result in enumerate(search_results):
            metadata = result.get('metadata', {})
            source = {
                'id': i + 1,
                'doc_id': metadata.get('doc_id', 'unknown'),
                'version': metadata.get('version', 'unknown'),
                'text_preview': result.get('text', '')[:100] + ('...' if len(result.get('text', '')) > 100 else ''),
                'score': result.get('score', 0.0),
                'is_current': metadata.get('is_current', False),
                'effective_from': metadata.get('effective_from'),
                'effective_to': metadata.get('effective_to')
            }
            sources.append(source)
        return sources

    def generate_structured_output(
        self,
        generated_answer: GeneratedAnswer
    ) -> Dict[str, Any]:
        """
        Convert GeneratedAnswer to structured dictionary for API/output.

        Args:
            generated_answer: GeneratedAnswer object

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return asdict(generated_answer)

    def save_answer_to_file(
        self,
        generated_answer: GeneratedAnswer,
        file_path: str
    ) -> bool:
        """
        Save generated answer to a JSON file.

        Args:
            generated_answer: GeneratedAnswer object to save
            file_path: Path to save the JSON file

        Returns:
            True if successful, False otherwise
        """
        try:
            structured_data = self.generate_structured_output(generated_answer)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving answer to file: {e}")
            return False


def create_generator(answer_format: AnswerFormat = AnswerFormat.NARRATIVE) -> Generator:
    """Factory function to create a Generator instance."""
    return Generator(answer_format=answer_format)


# Example usage and testing
if __name__ == "__main__":
    # Test the generator
    print("Testing Generator...")

    generator = Generator()

    # Mock search results (similar to what retriever would return)
    mock_results = [
        {
            'id': 'test-uuid-1',
            'text': '- Maximum password age: 60 days - Passwords must be changed every 60 days - Passwords must contain at least 12 characters - Passwords must include uppercase, lowercase, numbers, and special characters',
            'metadata': {
                'doc_id': 'password-policy',
                'version': 'v3.0',
                'effective_from': '2026-01-01',
                'effective_to': None,
                'is_current': True,
                'chunk_id': 'password-policy_v3.0_0'
            },
            'score': 0.85,
            'query_mode': 'default',
            'query_params': {}
        },
        {
            'id': 'test-uuid-2',
            'text': '- Maximum password age: 90 days - Passwords must be changed every 90 days - Passwords must contain at least 8 characters - Passwords must include uppercase and lowercase letters',
            'metadata': {
                'doc_id': 'password-policy',
                'version': 'v2.0',
                'effective_from': '2025-07-01',
                'effective_to': '2025-12-31',
                'is_current': False,
                'chunk_id': 'password-policy_v2.0_0'
            },
            'score': 0.72,
            'query_mode': 'default',
            'query_params': {}
        }
    ]

    test_question = "What is the current password policy?"

    print(f"Question: {test_question}")
    print("-" * 50)

    # Test different formats
    for fmt in AnswerFormat:
        print(f"\n{fmt.value.upper()} FORMAT:")
        print("=" * 30)
        answer = generator.generate_answer(
            question=test_question,
            search_results=mock_results,
            answer_format=fmt
        )

        print(f"Answer:\n{answer.answer}")
        print(f"\nConfidence: {answer.confidence_score:.3f}")
        print(f"Version Attribution: {answer.version_attribution}")
        print(f"Sources: {len(answer.sources)} source(s)")