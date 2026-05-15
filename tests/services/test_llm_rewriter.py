from unittest.mock import patch


CHAPTER = """# The Early Years

My grandmother kept a garden behind the house, thick with mint and rosemary.

She never spoke about the war directly, but some evenings she would grow quiet.
"""

REWRITTEN = """# The Early Years

My grandmother tended a garden behind the house — mint, rosemary, the smell of both.

She rarely spoke about the war, but on certain evenings a stillness would settle over her.
"""


def _make_provider(response: str):
    return lambda prompt: response


def test_llm_rewrite_returns_string():
    with patch("altamira.services.rewriter.get_provider", return_value=_make_provider(REWRITTEN)):
        from altamira.services.rewriter import llm_rewrite
        result = llm_rewrite(CHAPTER)
    assert isinstance(result, str)
    assert len(result) > 0


def test_llm_rewrite_returns_provider_response():
    with patch("altamira.services.rewriter.get_provider", return_value=_make_provider(REWRITTEN)):
        from altamira.services.rewriter import llm_rewrite
        result = llm_rewrite(CHAPTER)
    assert result == REWRITTEN


def test_llm_rewrite_falls_back_to_original_on_error():
    def bad_provider(prompt):
        raise RuntimeError("API error")

    with patch("altamira.services.rewriter.get_provider", return_value=bad_provider):
        from altamira.services.rewriter import llm_rewrite
        result = llm_rewrite(CHAPTER)
    assert result == CHAPTER


def test_llm_rewrite_propagates_provider_config_error():
    with patch("altamira.services.rewriter.get_provider", side_effect=EnvironmentError("No API key")):
        from altamira.services.rewriter import llm_rewrite
        import pytest
        with pytest.raises(EnvironmentError):
            llm_rewrite(CHAPTER)
