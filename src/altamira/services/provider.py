import os
from typing import Callable

# Swap this type for any provider — the rest of the codebase only depends on this shape.
ProviderFn = Callable[[str], str]

_ANTHROPIC_DEFAULT = "claude-sonnet-4-6"
_OPENAI_DEFAULT = "gpt-4o"

# Curated list of models shown by --llm-list / /llm list.
MODEL_CATALOG: dict[str, list[str]] = {
    "anthropic": [
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "o3",
        "o4-mini",
    ],
}

_PROVIDER_DEFAULTS: dict[str, str] = {
    "anthropic": _ANTHROPIC_DEFAULT,
    "openai": _OPENAI_DEFAULT,
}


def get_effective_model() -> tuple[str, str]:
    """Return (provider_name, model_name) reflecting current env vars."""
    provider = os.environ.get("ALTAMIRA_PROVIDER", "anthropic").lower()
    model = os.environ.get("ALTAMIRA_MODEL", _PROVIDER_DEFAULTS.get(provider, ""))
    return provider, model


def find_provider_for_model(model: str) -> str | None:
    """Return the provider that owns *model*, or None if not in the catalog."""
    for provider, models in MODEL_CATALOG.items():
        if model in models:
            return provider
    return None


def anthropic_provider(system: str = "") -> ProviderFn:
    """Return a Claude-backed provider.

    Reads:
      ANTHROPIC_API_KEY  — required
      ALTAMIRA_MODEL     — optional, defaults to claude-sonnet-4-6
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set. "
            "Export it in your shell before running this command."
        )

    model = os.environ.get("ALTAMIRA_MODEL", _ANTHROPIC_DEFAULT)

    try:
        import anthropic
    except ImportError:
        raise ImportError("The 'anthropic' package is not installed. Run: pip install anthropic")

    client = anthropic.Anthropic(api_key=api_key)

    def call(prompt: str) -> str:
        kwargs: dict = dict(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system
        message = client.messages.create(**kwargs)
        return message.content[0].text

    return call


def openai_provider(system: str = "") -> ProviderFn:
    """Return an OpenAI-backed provider.

    Reads:
      OPENAI_API_KEY  — required
      ALTAMIRA_MODEL  — optional, defaults to gpt-4o
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY is not set. "
            "Export it in your shell before running this command."
        )

    model = os.environ.get("ALTAMIRA_MODEL", _OPENAI_DEFAULT)

    try:
        import openai
    except ImportError:
        raise ImportError("The 'openai' package is not installed. Run: pip install openai")

    client = openai.OpenAI(api_key=api_key)

    def call(prompt: str) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=model,
            max_tokens=4096,
            messages=messages,
        )
        return response.choices[0].message.content or ""

    return call


_PROVIDERS = {
    "anthropic": anthropic_provider,
    "openai": openai_provider,
}


def get_provider(system: str = "") -> ProviderFn:
    """Return the active provider based on ALTAMIRA_PROVIDER (default: anthropic)."""
    name = os.environ.get("ALTAMIRA_PROVIDER", "anthropic").lower()
    factory = _PROVIDERS.get(name)
    if factory is None:
        valid = ", ".join(_PROVIDERS)
        raise ValueError(f"Unknown provider '{name}'. Valid options: {valid}")
    return factory(system=system)
