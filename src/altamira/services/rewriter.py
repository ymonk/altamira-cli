from typing import Callable

from altamira.services.provider import get_provider

# Swap this type for a real LLM-backed implementation without touching the command.
RewriteFn = Callable[[str], str]

_SUBSTITUTIONS = [
    ("very ",         "quite "),
    (" born ",        " raised "),
    ("long hours",    "extended hours"),
    ("small ",        "modest "),
    (" worked ",      " labored "),
    ("only child",    "sole child"),
    ("lively",        "vibrant"),
    ("tired",         "weary"),
    ("memorized",     "committed to memory"),
    ("stories",       "narratives"),
    ("big ",          "considerable "),
    ("grew up",       "came of age"),
]


_REWRITE_PROMPT = """\
You are a memoir editor. Rewrite the chapter below to improve clarity, pacing, \
and voice consistency.

Rules:
- Preserve all factual details and the author's voice exactly
- Tighten sentences that are overlong or passive
- Improve paragraph transitions so the narrative flows naturally
- Do NOT add invented details, dialogue, or scenes
- Return ONLY the rewritten chapter text — no commentary, no revision notes

Chapter:
"""


def llm_rewrite(text: str) -> str:
    """Call the active LLM provider and return the rewritten chapter text."""
    provider = get_provider()  # let EnvironmentError / ImportError / ValueError propagate
    try:
        return provider(_REWRITE_PROMPT + text)
    except Exception:
        return text


def mock_rewrite(text: str) -> str:
    """Apply simple substitutions to body paragraphs. Replace with an LLM call to go live."""
    paragraphs = text.split("\n\n")
    result = []
    for para in paragraphs:
        if para.strip() and not para.lstrip().startswith("#"):
            changed = False
            for old, new in _SUBSTITUTIONS:
                if old in para:
                    para = para.replace(old, new, 1)
                    changed = True
                    break
            if not changed:
                para = para.rstrip() + " The memory of this period remains clear."
        result.append(para)
    return "\n\n".join(result)
