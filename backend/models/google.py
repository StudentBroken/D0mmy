from __future__ import annotations
import asyncio
import json
import logging
from functools import lru_cache

import google.genai as genai
from google.genai import types

logger = logging.getLogger(__name__)

from backend.config import get_settings


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    return genai.Client(api_key=get_settings().google_api_key)


def ensure_configured() -> None:
    _client()  # forces construction / key validation


def _role_to_model(role: str) -> str:
    cfg = get_settings()
    if role == "heavy":
        return cfg.heavy_model
    if role == "worker":
        return cfg.worker_model
    return cfg.daemon_model


def _build_contents(messages: list[dict]) -> list[dict]:
    """Convert {role, content} dicts to the google.genai contents format."""
    out = []
    for m in messages:
        if m["role"] == "system":
            continue  # handled via system_instruction
        role = "user" if m["role"] == "user" else "model"
        out.append({"role": role, "parts": [{"text": m["content"]}]})
    return out


def _system_instruction(messages: list[dict]) -> str | None:
    parts = [m["content"] for m in messages if m["role"] == "system"]
    return "\n\n".join(parts) if parts else None


def _clean_json_response(text: str) -> str:
    """Extract the first complete JSON object/array from the response."""
    text = text.strip()

    # Strip markdown fences
    if text.startswith("```"):
        first_newline = text.find("\n")
        text = text[first_newline:].strip() if first_newline != -1 else text[3:].strip()
        if text.endswith("```"):
            text = text[:-3].strip()

    # Find outermost JSON object or array, discarding trailing prose
    start = -1
    open_ch, close_ch = None, None
    for i, ch in enumerate(text):
        if ch in ('{', '['):
            start = i
            open_ch = ch
            close_ch = '}' if ch == '{' else ']'
            break

    if start == -1:
        return text  # no JSON found, return as-is and let caller handle parse error

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]

    return text[start:]  # truncated — return what we have


# Keys that are JSON Schema metadata but not valid in Gemini's response_schema subset.
# "title" is intentionally NOT here — it may also be a legitimate property name (e.g. sprint.title).
_SCHEMA_STRIP_KEYS = {"$schema", "additionalProperties", "additional_properties", "default", "examples"}


def _prune_schema(obj: object, _inside_properties: bool = False) -> object:
    """
    Recursively sanitize a JSON Schema for Gemini's response_schema:
    - Strip metadata keys ($schema, additionalProperties, default, examples)
    - Strip top-level "title" ONLY when not inside a properties dict (where it's a field name)
    - Add "type":"string" to any enum field that lacks an explicit type
    """
    if isinstance(obj, dict):
        result: dict = {}
        for k, v in obj.items():
            if k in _SCHEMA_STRIP_KEYS:
                continue
            # "title" at schema-object level is metadata; inside properties it's a field name key
            if k == "title" and not _inside_properties:
                continue
            # Recurse: if we're entering a "properties" dict, children are field names, not schemas
            if k == "properties" and isinstance(v, dict):
                result[k] = {
                    prop_name: _prune_schema(prop_schema, _inside_properties=False)
                    for prop_name, prop_schema in v.items()
                }
            else:
                result[k] = _prune_schema(v, _inside_properties=False)

        # Gemini requires explicit "type":"string" alongside any enum
        if "enum" in result and "type" not in result:
            result["type"] = "string"

        return result
    elif isinstance(obj, list):
        return [_prune_schema(i, _inside_properties=False) for i in obj]
    return obj


async def _generate_with_retry(
    client: genai.Client,
    model_id: str,
    contents: list,
    cfg: types.GenerateContentConfig,
    max_retries: int = 3,
) -> object:
    """generate_content with exponential backoff for 429/502/503 server errors."""
    for attempt in range(max_retries):
        try:
            return await client.aio.models.generate_content(
                model=model_id, contents=contents, config=cfg,
            )
        except Exception as exc:
            code = getattr(exc, 'status_code', None) or getattr(exc, 'code', None)
            is_retryable = (
                code in (429, 502, 503)
                or "502" in str(exc)
                or "503" in str(exc)
                or "429" in str(exc)
                or "quota" in str(exc).lower()
            )
            if is_retryable and attempt < max_retries - 1:
                wait = 2 ** attempt * 5  # 5s, 10s, 20s
                logger.warning("API error (attempt %d/%d), retrying in %ds: %s", attempt + 1, max_retries, wait, exc)
                await asyncio.sleep(wait)
            else:
                raise


async def call_google(
    role: str,
    messages: list[dict],
    schema: dict | None = None,
    model_name: str | None = None,
    run_version_hook: bool = True,
) -> dict:
    if run_version_hook:
        from backend.agents.version_hook import inject_verified_context
        messages = await inject_verified_context(messages)

    model_id = model_name or _role_to_model(role)
    client = _client()

    config_kwargs: dict = {
        "max_output_tokens": 8192,
    }
    sys = _system_instruction(messages)
    if sys:
        config_kwargs["system_instruction"] = sys
    if schema:
        pruned_schema = _prune_schema(schema)
        config_kwargs["response_mime_type"] = "application/json"
        config_kwargs["response_schema"] = pruned_schema

    cfg = types.GenerateContentConfig(**config_kwargs)
    contents = _build_contents(messages)

    response = await _generate_with_retry(client, model_id, contents, cfg)

    raw = response.text.strip() if response.text else ""

    def _token_counts(resp) -> dict:
        um = getattr(resp, "usage_metadata", None)
        if not um:
            return {"token_in": 0, "token_out": 0}
        return {
            "token_in": getattr(um, "prompt_token_count", 0) or 0,
            "token_out": getattr(um, "candidates_token_count", 0) or 0,
        }

    if schema:
        raw = _clean_json_response(raw)
        try:
            return {"content": raw, "parsed": json.loads(raw), **_token_counts(response)}
        except json.JSONDecodeError:
            # One retry with explicit correction
            correction_contents = contents + [
                {"role": "model", "parts": [{"text": raw}]},
                {"role": "user", "parts": [{"text": (
                    "Your response was not valid JSON. "
                    f"Output ONLY a JSON object matching this schema: {json.dumps(schema)}"
                )}]},
            ]
            retry = await _generate_with_retry(client, model_id, correction_contents, cfg)
            raw = retry.text.strip() if retry.text else ""
            try:
                return {"content": raw, "parsed": json.loads(raw), **_token_counts(retry)}
            except json.JSONDecodeError:
                return {"content": raw, "parsed": None, "parse_error": True, **_token_counts(retry)}

    return {"content": raw, **_token_counts(response)}


def embed(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    client = _client()
    cfg = get_settings()
    result = client.models.embed_content(
        model=cfg.embedding_model,
        contents=texts,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    return [e.values for e in result.embeddings]
