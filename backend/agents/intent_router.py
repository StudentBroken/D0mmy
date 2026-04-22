from __future__ import annotations
import logging
from backend.models.client import call_model
from backend.memory.rom import get_prompt, get_schema

logger = logging.getLogger(__name__)


async def classify(intent_text: str) -> dict:
    """
    Zero-shot intent classification using Gemma 4 mini (daemon role).
    Returns {"intent": "hardware|software|mixed", "confidence": 0.0-1.0}
    """
    result = await call_model(
        role="daemon",
        messages=[
            {"role": "system", "content": get_prompt("intent_router")},
            {"role": "user", "content": intent_text},
        ],
        schema=get_schema("intent"),
        agent="intent_router",
        goal="Classify intent as hardware / software / mixed",
    )

    parsed = result.get("parsed")
    if not parsed:
        logger.warning("Intent router returned unparseable output, defaulting to 'mixed'")
        return {"intent": "mixed", "confidence": 0.0}

    logger.info("Intent classified: %s (confidence=%.2f)", parsed["intent"], parsed["confidence"])
    return parsed
