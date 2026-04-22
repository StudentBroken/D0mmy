from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.models.client import call_model

SCRATCHPAD_LIMIT = 5


@dataclass
class Turn:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class Scratchpad:
    session_id: str
    turns: list[Turn] = field(default_factory=list)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def append(self, role: str, content: str) -> None:
        self.turns.append(Turn(role=role, content=content))

    async def maybe_truncate(self) -> None:
        if len(self.turns) <= SCRATCHPAD_LIMIT:
            return
        async with self._lock:
            if len(self.turns) <= SCRATCHPAD_LIMIT:
                return
            await self._truncate()

    async def _truncate(self) -> None:
        from backend.models.client import call_model
        from backend.memory.rom import get_prompt

        overflow = self.turns[: len(self.turns) - SCRATCHPAD_LIMIT + 1]
        conversation_text = "\n".join(
            f"{t.role.upper()}: {t.content}" for t in overflow
        )
        summary = await call_model(
            role="daemon",
            messages=[
                {"role": "system", "content": get_prompt("truncation")},
                {"role": "user", "content": conversation_text},
            ],
        )
        summary_text = summary.get("content", "").strip()
        retained = self.turns[len(overflow):]
        self.turns = [Turn(role="system", content=f"[Summary] {summary_text}")] + retained

    def to_messages(self) -> list[dict]:
        return [{"role": t.role, "content": t.content} for t in self.turns]


class ScratchpadRegistry:
    def __init__(self) -> None:
        self._pads: dict[str, Scratchpad] = {}

    def get(self, session_id: str) -> Scratchpad:
        if session_id not in self._pads:
            self._pads[session_id] = Scratchpad(session_id=session_id)
        return self._pads[session_id]

    def clear(self, session_id: str) -> None:
        self._pads.pop(session_id, None)


scratchpads = ScratchpadRegistry()
