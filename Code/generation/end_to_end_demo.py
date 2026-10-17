"""
End-to-end demo showing how Generation phase would work with Retrieval phase
in the Version-Aware RAG system (simulated).
"""

# Handle imports for when run as script vs module
try:
    from generation.generator import Generator, AnswerFormat
    from generation.prompt_template import PromptTemplate
except ImportError:
    # When run directly from generation directory
    from generator import Generator, AnswerFormat
    from prompt_template import PromptTemplate


def simulate_retrieval_results(question: str) -> list:
    """
    Simulate what the retrieval phase would return for demonstration purposes.
    In a real implementation, this would call the actual retriever.
    """
    # Mock data based on what we know is in our policy documents
    mock_data = {
        "What is the current password policy?": [
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
        ],
        "What was the password policy as of 2025-08-01?": [
            {
                'text': '- Maximum password age: 90 days - Passwords must be changed every 90 days - Passwords must contain at least 8 characters - Passwords must include uppercase and lowercase letters',
                'metadata': {
                    'doc_id': 'password-policy',
                    'version': 'v2.0',
                    'effective_from': '2025-07-01',
                    'effective_to': '2025-12-31',
                    'is_current': False
                },
                'score': 0.78
            }
        ],
        "Show me the password policy according to v2.0": [
            {
                'text': '- Maximum password age: 90 days - Passwords must be changed every 90 days - Passwords must contain at least 8 characters - Passwords must include uppercase and lowercase letters - Passwords must not contain the username',
                'metadata': {
                    'doc_id': 'password-policy',
                    'version': 'v2.0',
                    'effective_from': '2025-07-01',
                    'effective_to': '2025-12-31',
                    'is_current': False
                },
                'score': 0.82
            }
        ],
        "Compare version v1.0 and v3.0 of the password policy": [
            {
                'text': '- Maximum password age: 365 days - Passwords must be changed yearly - Minimum length: 6 characters',
                'metadata': {
                    'doc_id': 'password-policy',
                    'version': 'v1.0',
                    'effective_from': '2025-01-01',
                    'effective_to': '2025-06-30',
                    'is_current': False
                },
                'score': 0.75
            },
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
    }

    # Return mock data if available, otherwise empty list
    return mock_data.get(question, [])


def end_to_end_demo():
    """Demo showing how generation phase works with retrieval phase."""
    print("Version-Aware RAG End-to-End Demo (Simulated)")
    print("=" * 60)

    # Initialize components
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
        print("-" * 50)

        try:
            # Step 1: Retrieval Phase (simulated)
            print("[Phase 1: Retrieval] Searching for relevant policy chunks...")
            search_results = simulate_retrieval_results(question)
            print(f"   Found {len(search_results)} relevant chunks")

            if search_results:
                for i, result in enumerate(search_results[:2]):  # Show first 2 results
                    metadata = result.get('metadata', {})
                    print(f"   Result {i+1}: {metadata.get('doc_id')} v{metadata.get('version')} "
                          f"(score: {result.get('score', 0):.3f})")

            # Step 2: Generation Phase
            print("\n[Phase 2: Generation] Creating answer with version attribution...")

            # Build prompt (show what would be sent to LLM)
            prompt = prompt_template.build_prompt(
                question=question,
                search_results=search_results,
                answer_format=AnswerFormat.NARRATIVE
            )
            print(f"   Prompt length: {len(prompt)} characters")

            # Generate answer
            answer_obj = generator.generate_answer(
                question=question,
                search_results=search_results,
                answer_format=AnswerFormat.NARRATIVE
            )

            print(f"   Answer generated (confidence: {answer_obj.confidence_score:.3f})")
            print(f"   Version attribution: {answer_obj.version_attribution}")

            # Show the final answer
            print(f"\nFinal Answer:")
            print(f"   {answer_obj.answer}")

            # Show alternative formats
            print(f"\nAlternative Formats:")
            bullet_answer = generator.generate_answer(
                question=question,
                search_results=search_results,
                answer_format=AnswerFormat.BULLET_POINTS
            )
            print(f"   Bullet Points: {bullet_answer.answer.split(chr(10))[0][:100]}...")

        except Exception as e:
            print(f"   Error: {e}")

    print("\n" + "=" * 60)
    print("✅ End-to-End Demo Complete!")
    print("\nWhat This Demonstrates:")
    print("   > Retrieval phase finds relevant policy chunks with version metadata")
    print("   > Generation phase creates contextual answers with version attribution")
    print("   > Multiple output formats available (narrative, bullet points, etc.)")
    print("   > Confidence scoring based on retrieval quality")
    print("   > Proper version handling for temporal queries")
    print("\n🔗 To Run the Actual System:")
    print("   1. Fix Qdrant storage access (resolve lock issue)")
    print("   2. Run ingestion: python run_ingestion.py")
    print("   3. Test retrieval: python test_search.py")
    print("   4. Test generation: python generation/demo.py")
    print("   5. End-to-end: Use retriever → generator pipeline")


if __name__ == "__main__":
    end_to_end_demo()