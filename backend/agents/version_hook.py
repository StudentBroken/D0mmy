"""
Pre-generation version hook.
Scans messages for version-like tokens, verifies each through the Oracle,
and injects a VERIFIED REFERENCES block into the system context.
This prevents the AI from hallucinating version numbers in generated code.
"""

from __future__ import annotations
import re
import asyncio
import logging

logger = logging.getLogger(__name__)

# Matches: fastapi==0.115.0  pydantic>=2.7  numpy~=1.26
_PIP_PIN = re.compile(r'\b([A-Za-z][A-Za-z0-9_-]+)\s*(?:==|>=|~=|<=)\s*([0-9]+\.[0-9]+[.\w]*)')

# Matches: "react": "^18.0.0"  "@xyflow/react": "12.0.0"
_NPM_PIN = re.compile(r'"(@?[a-z][a-z0-9_/@-]+)"\s*:\s*"[\^~]?([0-9]+\.[0-9]+[.\w]*)"')

# Matches model-like references: gemini-3.1-pro-preview, gemma-4-31b-it, gpt-4o, etc.
_MODEL_REF = re.compile(
    r'\b(gemini|gemma|gpt|claude|llama|mistral|palm|bard)[-\s][0-9a-zA-Z._ -]{1,30}',
    re.IGNORECASE,
)


def _extract_tokens(messages: list[dict]) -> list[str]:
    tokens: list[str] = []
    for m in messages:
        text = m.get("content", "")
        tokens += [m.group(0) for m in _PIP_PIN.finditer(text)]
        tokens += [m.group(0) for m in _NPM_PIN.finditer(text)]
        tokens += [m.group(0).strip() for m in _MODEL_REF.finditer(text)]
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for t in tokens:
        key = t.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique


async def inject_verified_context(messages: list[dict]) -> list[dict]:
    """
    Scan messages for version tokens, verify each through the Oracle,
    and prepend a VERIFIED REFERENCES system message.
    Returns the augmented message list.
    """
    from backend.agents.version_oracle import resolve

    tokens = _extract_tokens(messages)
    if not tokens:
        return messages

    logger.info("Version hook: found %d token(s) to verify: %s", len(tokens), tokens)

    refs = await asyncio.gather(*[resolve(t) for t in tokens])

    lines = ["[VERIFIED REFERENCES — use these exact names in generated code]"]
    for ref in refs:
        if ref.verified:
            lines.append(
                f"  ✓ '{ref.input_name}' → canonical: '{ref.canonical}'"
                + (f" v{ref.version}" if ref.version not in ("unknown", "N/A", "latest") else "")
                + (f" | source: {ref.source}" if ref.source else "")
            )
        else:
            lines.append(
                f"  ✗ '{ref.input_name}' COULD NOT BE VERIFIED — do not use in code. "
                f"Reason: {ref.notes}"
            )

    verification_block = "\n".join(lines)
    augmented = [{"role": "system", "content": verification_block}] + messages
    return augmented
