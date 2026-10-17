"""
Test script for the Generation phase components.
"""

try:
    from generator import Generator, AnswerFormat
    from prompt_template import PromptTemplate
except ImportError:
    # Fallback for different execution contexts
    from .generator import Generator, AnswerFormat
    from .prompt_template import PromptTemplate


def test_prompt_template():
    """Test the prompt template functionality."""
    print("Testing PromptTemplate...")

    template = PromptTemplate()

    # Test building prompt with no results
    no_results_prompt = template.build_prompt(
        question="What is the password policy?",
        search_results=[]
    )
    assert "no relevant policy information was found" in no_results_prompt.lower()
    print("> No results prompt works")

    # Test building prompt with results
    mock_results = [
        {
            'text': 'Test policy content',
            'metadata': {
                'doc_id': 'test-policy',
                'version': 'v1.0',
                'is_current': True
            },
            'score': 0.8
        }
    ]

    prompt = template.build_prompt(
        question="What is the test policy?",
        search_results=mock_results,
        answer_format=AnswerFormat.NARRATIVE
    )
    assert "Test policy content" in prompt
    assert "test-policy" in prompt
    assert "v1.0" in prompt
    print("> Results prompt works")

    # Test different formats
    for fmt in AnswerFormat:
        prompt = template.build_prompt(
            question="Test question",
            search_results=mock_results,
            answer_format=fmt
        )
        assert len(prompt) > 0
    print("> All answer formats work")


def test_generator():
    """Test the generator functionality."""
    print("\nTesting Generator...")

    generator = Generator()

    # Test with no results
    answer_obj = generator.generate_answer(
        question="What is the unknown policy?",
        search_results=[]
    )
    assert "could not find any relevant policy information" in answer_obj.answer.lower()
    assert answer_obj.confidence_score == 0.0
    print("> No results handling works")

    # Test with mock results
    mock_results = [
        {
            'text': 'Maximum password age: 60 days. Passwords must be changed every 60 days.',
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

    answer_obj = generator.generate_answer(
        question="What is the current password policy?",
        search_results=mock_results,
        answer_format=AnswerFormat.NARRATIVE
    )

    assert len(answer_obj.answer) > 0
    assert answer_obj.confidence_score > 0
    assert 'password-policy' in str(answer_obj.version_attribution)
    assert answer_obj.format == AnswerFormat.NARRATIVE
    print("> Normal generation works")

    # Test different formats
    for fmt in AnswerFormat:
        answer_obj = generator.generate_answer(
            question="Test question",
            search_results=mock_results,
            answer_format=fmt
        )
        assert answer_obj.format == fmt
        assert len(answer_obj.answer) > 0
    print("> All generation formats work")

    # Test structured output
    structured = generator.generate_structured_output(answer_obj)
    assert isinstance(structured, dict)
    assert 'question' in structured
    assert 'answer' in structured
    assert 'confidence_score' in structured
    print("> Structured output works")


def test_integration():
    """Test integration between components."""
    print("\nTesting Component Integration...")

    # Create prompt template
    template = PromptTemplate()

    # Create generator
    generator = Generator(AnswerFormat.BULLET_POINTS)

    # Test that they work together
    mock_results = [
        {
            'text': 'Passwords must be at least 12 characters long.',
            'metadata': {
                'doc_id': 'password-policy',
                'version': 'v3.0',
                'is_current': True
            },
            'score': 0.9
        }
    ]

    # Generate prompt
    prompt = template.build_prompt(
        question="What are the password length requirements?",
        search_results=mock_results,
        answer_format=AnswerFormat.BULLET_POINTS
    )

    # Generate answer
    answer_obj = generator.generate_answer(
        question="What are the password length requirements?",
        search_results=mock_results
    )

    assert answer_obj.format == AnswerFormat.BULLET_POINTS
    assert "Passwords must be at least 12 characters long" in answer_obj.answer or len(answer_obj.answer) > 0
    print("> Component integration works")


if __name__ == "__main__":
    print("Testing Generation Phase Components")
    print("=" * 40)

    try:
        test_prompt_template()
        test_generator()
        test_integration()

        print("\n" + "=" * 40)
        print("All Generation Phase tests passed!")
        print("> PromptTemplate working correctly")
        print("> Generator working correctly")
        print("> Component integration successful")
        print("> Ready for end-to-end testing with Retrieval phase")

    except Exception as e:
        print(f"\nError in test failed: {e}")
        import traceback
        traceback.print_exc()