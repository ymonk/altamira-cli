import json
from dataclasses import dataclass
from typing import Callable

from altamira.services.provider import get_provider
from altamira.skills.loader import load_skill


@dataclass
class ParagraphComment:
    paragraph_index: int
    paragraph_text: str
    comment: str


# Swap this type for a real LLM-backed implementation later
ReviewFn = Callable[[str], list[ParagraphComment]]

_MOCK_COMMENTS = [
    "Consider adding more sensory detail to ground the reader in this moment.",
    "This transition feels abrupt — try bridging it to the previous idea.",
    "Strong passage. The pacing here could be slowed to let the scene breathe.",
    "The voice shifts slightly. Consider aligning the tone with the opening.",
]


def llm_review(text: str) -> list[ParagraphComment]:
    """Call the active LLM provider and parse paragraph comments from the response."""
    body_paras = [
        p for p in text.split("\n\n")
        if p.strip() and not p.lstrip().startswith("#")
    ]

    skill_prompt = load_skill("chapter_reviewer") or ""
    # Replace the placeholder with the actual chapter text
    prompt = skill_prompt.replace("[PASTE CHAPTER HERE]", text)

    try:
        provider = get_provider()
        raw = provider(prompt)
    except Exception:
        return []

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return []

    comments = []
    for item in data:
        idx = item.get("paragraph_index")
        comment = item.get("comment", "")
        if not isinstance(idx, int) or idx < 0 or idx >= len(body_paras):
            continue
        comments.append(ParagraphComment(
            paragraph_index=idx,
            paragraph_text=body_paras[idx],
            comment=comment,
        ))
    return comments


def mock_review(text: str) -> list[ParagraphComment]:
    """Return mocked paragraph-level comments. Replace with an LLM call to go live."""
    body_paras = [
        (i, p)
        for i, p in enumerate(text.split("\n\n"))
        if p.strip() and not p.lstrip().startswith("#")
    ]
    return [
        ParagraphComment(
            paragraph_index=idx,
            paragraph_text=para,
            comment=_MOCK_COMMENTS[n % len(_MOCK_COMMENTS)],
        )
        for n, (idx, para) in enumerate(body_paras[:4])
    ]
