"""
Thin multi-provider LLM client. The model is chosen with LLM_MODEL=<provider>:<model>,
e.g. "openai:gpt-4.1-mini" or "anthropic:haiku5.5".
"""

import logging
import re

from backend.config import ANTHROPIC_API_KEY, LLM_MODEL, OPENAI_API_KEY

logger = logging.getLogger(__name__)

_ANTHROPIC_SHORT = re.compile(r"^(haiku|sonnet|opus|fable)-?(\d+)(?:[.-](\d+))?$")


def parse_model(spec: str) -> tuple[str, str]:
    """Split "provider:model" and normalise the model name to the API id.

    "anthropic:haiku5.5" -> ("anthropic", "claude-haiku-5-5")
    "openai:gpt4.1-mini" -> ("openai", "gpt-4.1-mini")
    A bare model name defaults to OpenAI. Full API ids pass through unchanged.
    """
    provider, sep, model = spec.strip().partition(":")
    if not sep:
        provider, model = "openai", spec.strip()
    provider, model = provider.lower(), model.strip()
    if provider == "anthropic":
        m = _ANTHROPIC_SHORT.match(model.lower())
        if m:
            fam, major, minor = m.groups()
            model = f"claude-{fam}-{major}" + (f"-{minor}" if minor else "")
    elif provider == "openai":
        model = re.sub(r"^gpt(?=\d)", "gpt-", model)
    else:
        raise ValueError(
            f"Unknown LLM provider '{provider}' in LLM_MODEL (use openai: or anthropic:)"
        )
    if not model:
        raise ValueError("LLM_MODEL has no model name")
    return provider, model


class LLM:
    """generate(system, user) -> text, for either provider."""

    def __init__(self, spec: str = LLM_MODEL):
        self.provider, self.model = parse_model(spec)
        if self.provider == "anthropic":
            if not ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY is required for LLM_MODEL=anthropic:*")
            import anthropic

            self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        else:
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required for LLM_MODEL=openai:*")
            from openai import OpenAI

            self._client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info(f"LLM: {self.provider}:{self.model}")

    def generate(self, system: str, user: str, max_tokens: int = 1000) -> str:
        if self.provider == "anthropic":
            kwargs = dict(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            try:
                resp = self._client.messages.create(temperature=0.1, **kwargs)
            except Exception as e:
                # some models reject sampling parameters: retry with defaults
                if "temperature" not in str(e).lower():
                    raise
                resp = self._client.messages.create(**kwargs)
            return "".join(b.text for b in resp.content if b.type == "text")

        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""
