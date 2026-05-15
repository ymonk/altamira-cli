from typing import Callable

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
