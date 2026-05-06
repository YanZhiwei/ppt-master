from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.models import Phase, RetryScope, StepStatus


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StepState:
    name: str
    status: StepStatus = StepStatus.pending
    message: str = ""
    updated_at: str = field(default_factory=utc_now)


@dataclass
class SessionState:
    session_id: str
    title: str | None
    created_at: str = field(default_factory=utc_now)
    phase: Phase = Phase.planning
    blocked_confirmation: bool = True
    project_id: str = field(default_factory=lambda: f"proj_{uuid4().hex[:10]}")
    steps: list[StepState] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)


class WorkflowStore:
    def __init__(self) -> None:
        self.sessions: dict[str, SessionState] = {}

    def create_session(self, title: str | None) -> SessionState:
        session_id = f"sess_{uuid4().hex[:10]}"
        state = SessionState(
            session_id=session_id,
            title=title,
            steps=[
                StepState("strategist_confirm", StepStatus.blocked, "Awaiting confirmation"),
                StepState("render_pages", StepStatus.pending, ""),
                StepState("quality_gate", StepStatus.pending, ""),
                StepState("export", StepStatus.pending, ""),
            ],
        )
        self.sessions[session_id] = state
        self._emit(state, "phase_changed", {"phase": state.phase.value})
        return state

    def get(self, session_id: str) -> SessionState:
        return self.sessions[session_id]

    def _emit(self, state: SessionState, event: str, payload: dict[str, Any]) -> None:
        state.events.append(
            {
                "event_id": uuid4().hex,
                "ts": utc_now(),
                "session_id": state.session_id,
                "event": event,
                "phase": state.phase.value,
                "payload": payload,
            }
        )

    def apply_message(self, session_id: str, message_type: str, _message: str) -> str:
        state = self.get(session_id)
        trace_id = f"trace_{uuid4().hex[:12]}"

        if message_type == "confirm" and state.blocked_confirmation:
            state.blocked_confirmation = False
            state.steps[0].status = StepStatus.completed
            state.steps[0].updated_at = utc_now()
            self._emit(state, "step_updated", {"step": "strategist_confirm", "status": "completed"})

            state.phase = Phase.rendering
            self._emit(state, "phase_changed", {"phase": state.phase.value})
            state.steps[1].status = StepStatus.running
            self._emit(state, "step_updated", {"step": "render_pages", "status": "running"})
            return trace_id

        if state.blocked_confirmation:
            self._emit(state, "warning", {"message": "Workflow blocked by strategist confirmation gate"})
            return trace_id

        self._emit(state, "step_updated", {"step": "render_pages", "status": "running"})
        return trace_id

    def retry(self, session_id: str, scope: RetryScope, target: str) -> str:
        state = self.get(session_id)
        trace_id = f"trace_{uuid4().hex[:12]}"
        if scope == RetryScope.phase:
            state.phase = Phase[target] if target in Phase.__members__ else Phase.rendering
            self._emit(state, "phase_changed", {"phase": state.phase.value, "retry_scope": "phase"})
        else:
            self._emit(state, "step_updated", {"step": "render_pages", "status": "running", "page": target})
        return trace_id


def can_transition(current: Phase, nxt: Phase) -> bool:
    allowed: dict[Phase, set[Phase]] = {
        Phase.planning: {Phase.acquiring_images, Phase.rendering, Phase.failed},
        Phase.acquiring_images: {Phase.rendering, Phase.failed},
        Phase.rendering: {Phase.quality_check, Phase.failed},
        Phase.quality_check: {Phase.rendering, Phase.exporting, Phase.failed},
        Phase.exporting: {Phase.done, Phase.failed},
        Phase.done: set(),
        Phase.failed: set(),
    }
    return nxt in allowed[current]


store = WorkflowStore()

