"""
Loads system prompts from prompts.md at the project root.

Usage:
    from utils.prompt_loader import get_prompt
    SYSTEM_PROMPT = get_prompt("content_extractor")

Each ## heading in prompts.md becomes a key (lowercased, spaces → underscores).
Prompts are cached in memory after the first read — no repeated disk I/O.
Call reload_prompts() to clear the cache during development.
"""
import re
from pathlib import Path

_PROMPTS_PATH = Path(__file__).parent.parent / "prompts.md"
_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    text = _PROMPTS_PATH.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    for m in re.finditer(r"^## (.+)$", text, re.MULTILINE):
        key = m.group(1).strip().lower().replace(" ", "_")
        start = m.end()
        nxt = re.search(r"^## ", text[start:], re.MULTILINE)
        end = start + nxt.start() if nxt else len(text)
        sections[key] = text[start:end].strip()
    _cache = sections
    return _cache


def get_prompt(key: str) -> str:
    """Return the system prompt for *key*. Raises KeyError if the section is missing."""
    prompts = _load()
    if key not in prompts:
        raise KeyError(
            f"System prompt '{key}' not found in prompts.md. "
            f"Available keys: {sorted(prompts.keys())}"
        )
    return prompts[key]


def reload_prompts() -> None:
    """Clear the in-memory cache so prompts.md is re-read on the next call."""
    global _cache
    _cache = None
