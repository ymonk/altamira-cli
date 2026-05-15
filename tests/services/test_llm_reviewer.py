import json
from unittest.mock import patch

import pytest


CHAPTER = """# The Early Years

My grandmother kept a garden behind the house, thick with mint and rosemary.

She never spoke about the war directly, but some evenings she would grow quiet.

We ate dinner late, the radio always on.

A photograph of her as a girl sat on the mantle, faded but unmistakable.
"""


def _make_provider(response: str):
    return lambda prompt: response


def test_llm_review_returns_paragraph_comments():
    mock_json = json.dumps([
        {"paragraph_index": 0, "comment": "Strong sensory opening."},
        {"paragraph_index": 2, "comment": "Pacing is too fast here."},
    ])
    with patch("altamira.services.reviewer.get_provider", return_value=_make_provider(mock_json)):
        from altamira.services.reviewer import llm_review
        comments = llm_review(CHAPTER)
    assert len(comments) == 2
    assert comments[0].paragraph_index == 0
    assert comments[0].comment == "Strong sensory opening."
    assert "grandmother" in comments[0].paragraph_text
    assert comments[1].paragraph_index == 2
    assert "radio" in comments[1].paragraph_text


def test_llm_review_includes_correct_paragraph_text():
    mock_json = json.dumps([{"paragraph_index": 1, "comment": "Good restraint."}])
    with patch("altamira.services.reviewer.get_provider", return_value=_make_provider(mock_json)):
        from altamira.services.reviewer import llm_review
        comments = llm_review(CHAPTER)
    assert comments[0].paragraph_index == 1
    assert "war" in comments[0].paragraph_text


def test_llm_review_ignores_out_of_range_indices():
    mock_json = json.dumps([
        {"paragraph_index": 99, "comment": "This index does not exist."},
        {"paragraph_index": 0, "comment": "Valid comment."},
    ])
    with patch("altamira.services.reviewer.get_provider", return_value=_make_provider(mock_json)):
        from altamira.services.reviewer import llm_review
        comments = llm_review(CHAPTER)
    assert len(comments) == 1
    assert comments[0].paragraph_index == 0


def test_llm_review_returns_empty_on_bad_json():
    with patch("altamira.services.reviewer.get_provider", return_value=_make_provider("not json")):
        from altamira.services.reviewer import llm_review
        comments = llm_review(CHAPTER)
    assert comments == []


def test_llm_review_returns_empty_on_non_list_json():
    with patch("altamira.services.reviewer.get_provider", return_value=_make_provider('{"key": "val"}')):
        from altamira.services.reviewer import llm_review
        comments = llm_review(CHAPTER)
    assert comments == []
