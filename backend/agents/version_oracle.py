"""
Version Oracle — resolves fuzzy model names, package versions, and API references
to their current verified canonical form using Gemini with Google Search grounding.

Usage:
  ref = await resolve("gemini 3.1 pro")
  ref.canonical  → "gemini-3.1-pro-preview"
  ref.verified   → True
  ref.source     → "https://ai.google.dev/gemini-api/docs/models"
"""

from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, asdict

import google.genai as genai
from google.genai import types

from backend.config import get_settings

logger = logging.getLogger(__name__)

_CACHE_TTL = 60 * 60 * 24  # 24 hours


@dataclass
class VerifiedRef:
    input_name: str
    canonical: str
    version: str
    kind: str
    verified: bool
    source: str
    notes: str
    verified_at: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def unverified(cls, input_name: str, reason: str) -> "VerifiedRef":
        return cls(
            input_name=input_name,
            canonical=input_name,
            version="unknown",
            kind="unknown",
            verified=False,
            source="",
            notes=reason,
            verified_at=time.time(),
        )


_oracle_cache: dict[str, VerifiedRef] = {}


def _cache_key(name: str) -> str:
    return name.lower().strip()


def _get_cached(name: str) -> VerifiedRef | None:
    ref = _oracle_cache.get(_cache_key(name))
    if ref and (time.time() - ref.verified_at) < _CACHE_TTL:
        return ref
    return None


def _set_cached(ref: VerifiedRef) -> None:
    _oracle_cache[_cache_key(ref.input_name)] = ref


_ORACLE_PROMPT = '''You are a version verification agent with Google Search access.

A developer referenced: "{name}"

Search for the CURRENT official canonical identifier. Return ONLY this JSON (no prose, no fences):
{{
  "canonical": "<exact official API name / model ID / package identifier>",
  "version": "<latest stable version or N/A>",
  "kind": "<model | package | api_endpoint | framework>",
  "verified": <true if you found an authoritative source, false if uncertain>,
  "source": "<direct URL to official docs>",
  "notes": "<one sentence: what this is, or why unverified>"
}}

Rules:
- Search before answering. Never rely on training data alone for version facts.
- If uncertain, set verified=false and use the input as canonical.
- For Google AI models: canonical = exact string used in the model= API parameter.
- For PyPI: use pypi.org for latest stable version.
'''.strip()


async def resolve(name: str) -> VerifiedRef:
    cached = _get_cached(name)
    if cached:
        logger.debug("Oracle cache hit: %s → %s", name, cached.canonical)
        return cached

    cfg = get_settings()
    client = genai.Client(api_key=cfg.google_api_key)

    try:
        response = await client.aio.models.generate_content(
            model=cfg.heavy_model,
            contents=_ORACLE_PROMPT.format(name=name),
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_mime_type="application/json",
            ),
        )

        raw = response.text.strip() if response.text else ""
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()

        parsed = json.loads(raw)
        ref = VerifiedRef(
            input_name=name,
            canonical=parsed.get("canonical", name),
            version=parsed.get("version", "unknown"),
            kind=parsed.get("kind", "unknown"),
            verified=bool(parsed.get("verified", False)),
            source=parsed.get("source", ""),
            notes=parsed.get("notes", ""),
            verified_at=time.time(),
        )

        if ref.verified:
            logger.info("Oracle: '%s' → '%s'  %s", name, ref.canonical, ref.source)
        else:
            logger.warning("Oracle: could not verify '%s': %s", name, ref.notes)

        _set_cached(ref)
        return ref

    except json.JSONDecodeError as e:
        logger.error("Oracle bad JSON for '%s': %s", name, e)
        ref = VerifiedRef.unverified(name, f"Non-JSON response: {e}")
        _set_cached(ref)
        return ref
    except Exception as e:
        logger.error("Oracle failed for '%s': %s", name, e)
        return VerifiedRef.unverified(name, f"Search failed: {e}")


async def resolve_many(names: list[str]) -> dict[str, VerifiedRef]:
    import asyncio
    results = await asyncio.gather(*[resolve(n) for n in names])
    return dict(zip(names, results))


def assert_verified(ref: VerifiedRef) -> str:
    if not ref.verified:
        raise RuntimeError(
            f"[Version Oracle] '{ref.input_name}' could not be verified.\n"
            f"Reason: {ref.notes}\n"
            f"Fix: set the exact model ID in your .env or Settings panel."
        )
    return ref.canonical
