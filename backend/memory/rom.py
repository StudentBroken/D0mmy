from functools import lru_cache
from pathlib import Path
import json

_ROOT = Path(__file__).resolve().parents[2]
_PROMPTS = _ROOT / "prompts"
_SCHEMAS = _ROOT / "schemas"


@lru_cache(maxsize=None)
def get_prompt(name: str) -> str:
    path = _PROMPTS / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def get_schema(name: str) -> dict:
    path = _SCHEMAS / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))
