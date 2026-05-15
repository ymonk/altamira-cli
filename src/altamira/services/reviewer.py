from dataclasses import dataclass
from typing import Callable


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
