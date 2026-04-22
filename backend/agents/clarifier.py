from __future__ import annotations
import logging
from backend.models.client import call_model
from backend.memory.rom import get_prompt, get_schema

logger = logging.getLogger(__name__)


async def generate_questions(intent: str) -> list[dict]:
    """
    Daemon generates targeted clarifying questions for the given intent.
    Returns list of {id, question, hint} dicts.
    """
    result = await call_model(
        role="daemon",
        messages=[
            {"role": "system", "content": get_prompt("clarifier")},
            {"role": "user", "content": f"User intent: {intent}"},
        ],
        schema=get_schema("clarification"),
        agent="clarifier",
        goal="Surface architectural ambiguities before planning",
    )

    parsed = result.get("parsed")
    if not parsed or not parsed.get("questions"):
        logger.warning("Clarifier returned no questions — skipping clarification step")
        return []

    questions = parsed["questions"]
    logger.info("Clarifier generated %d questions for intent", len(questions))
    return questions
