from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from app.workflow import store


async def stream_session_events(session_id: str) -> AsyncIterator[str]:
    cursor = 0
    while True:
        state = store.get(session_id)
        while cursor < len(state.events):
            event = state.events[cursor]
            cursor += 1
            yield f"event: {event['event']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.5)

