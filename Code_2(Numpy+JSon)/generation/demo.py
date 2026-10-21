"""
Demo script showing how the Generation phase works with Retrieval phase
in the Version-Aware RAG system.
"""

from typing import List, Dict, Any
try:
    from retrieval.retriever import search_documents
except ImportError:
    # Fallback for when retrieval is not available
    def search_documents(*args, **kwargs):
        return []

# Handle imports for when run as script vs module
try:
    from generation.generator import Generator, AnswerFormat
    from generation.prompt_template import PromptTemplate
except ImportError:
    # When run directly from generation directory
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from generator import Generator, AnswerFormat
    from prompt_template import PromptTemplate


def demo_generation_phase():
    """Demo showing generation phase working with retrieval."""
    print("Version-Aware RAG Generation Phase Demo")
    print("=" * 50)

    # Initialize generator
    generator = Generator()
    prompt_template = PromptTemplate()

    # Demo questions
    demo_questions = [
        "What is the current password policy?",
        "What was the password policy as of 2025-08-01?",
        "Show me the password policy according to v2.0",
        "Compare version v1.0 and v3.0 of the password policy"
    ]

    for question in demo_questions:
        print(f"\nQuestion: {question}")
        print("-" * 40)

        try:
            # Step 1: Retrieve relevant documents (this would use the actual retriever)
            # For demo, we'll simulate what the retriever would return
            # In real usage: search_results = search_documents(question, limit=3)

            # Instead, let's show what the prompt would look like
            print("[Retrieval Phase] Would search for relevant policy chunks...")

            # Step 2: Show prompt construction
            print("\n[Generation Phase] Building prompt...")
            # We'd normally pass actual search results here
            # For demo, we'll show the prompt structure

            # Step 3: Show what answer would be generated
            print("\n[Generation Phase] Generating answer...")

            # Since we can't actually search without Qdrant working,
            # let's show the generation capability with mock data
            gen = Generator(AnswerFormat.NARRATIVE)

            # Mock results for demonstration
            mock_results = [
                {
                    'text': '- Maximum password age: 60 days - Passwords must be changed every 60 days - Passwords must contain at least 12 characters - Passwords must include uppercase, lowercase, numbers, and special characters',
                    'metadata': {
                        'doc_id': 'password-policy',
                        'version': 'v3.0',
                        'effective_from': '2026-01-01',
                        'effective_to': None,
                        'is_current': True
                    },
                    'score': 0.85
                }
            ]

            # Generate answer
            answer_obj = gen.generate_answer(
                question=question,
                search_results=mock_results,
                answer_format=AnswerFormat.NARRATIVE
            )

            print(f"   Answer: {answer_obj.answer}")
            print(f"   Confidence: {answer_obj.confidence_score:.3f}")
            print(f"   Version Info: {answer_obj.version_attribution}")

        except Exception as e:
            print(f"   Error: {e}")

    print("\n" + "=" * 50)
    print("Generation Phase Capabilities Demonstrated:")
    print("   > Prompt templating with version attribution")
    print("   > Multiple output formats (narrative, bullet points, structured, comparison)")
    print("   > Version-aware answer generation")
    print("   > Confidence scoring based on retrieval quality")
    print("   > Structured output for API consumption")
    print("\nTo complete the full RAG pipeline:")
    print("   1. Fix Qdrant storage access (resolve lock issue)")
    print("   2. Run ingestion: python run_ingestion.py")
    print("   3. Test retrieval: python test_search.py")
    print("   4. Test generation: python generation/demo.py")
    print("   5. End-to-end: retrieval -> generation -> formatted answer")


def show_prompt_examples():
    """Show examples of the prompt templates."""
    print("\nPrompt Template Examples:")
    print("=" * 40)

    # Handle imports for when run as script vs module
    try:
        from generation.prompt_template import PromptTemplate, AnswerFormat
    except ImportError:
        # When run directly from generation directory
        from prompt_template import PromptTemplate, AnswerFormat

    template = PromptTemplate()

    # Mock context
    mock_context = """[Source 1]
Document: password-policy
Version: v3.0
Relevance: 0.85
Content: - Maximum password age: 60 days - Passwords must be changed every 60 days - Passwords must contain at least 12 characters - Passwords must include uppercase, lowercase, numbers, and special characters

[Source 2]
Document: password-policy
Version: v2.0
Relevance: 0.72
Content: - Maximum password age: 90 days - Passwords must be changed every 90 days - Passwords must contain at least 8 characters - Passwords must include uppercase and lowercase letters"""

    version_info = {"password-policy": "v3.0/v2.0"}
    question = "What is the current password policy and how has it changed?"

    for fmt in AnswerFormat:
        print(f"\n--- {fmt.value.upper()} ---")
        prompt = template.build_prompt(question, [{"text": mock_context.split('Content: ')[1].split('\n')[0], 'metadata': {}, 'score': 0.8}], fmt)
        # Show first few lines
        lines = prompt.split('\n')
        for line in lines[:8]:  # Show first 8 lines
            print(line)
        print("   ...")


if __name__ == "__main__":
    demo_generation_phase()
    show_prompt_examples()