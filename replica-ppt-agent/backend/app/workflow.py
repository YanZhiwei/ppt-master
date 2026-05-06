from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
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
    prompt: str = ""
    project_id: str = field(default_factory=lambda: f"proj_{uuid4().hex[:10]}")
    project_dir: str = ""
    artifacts: dict[str, Any] = field(default_factory=dict)
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

    def emit(self, session_id: str, event: str, payload: dict[str, Any]) -> None:
        state = self.get(session_id)
        self._emit(state, event, payload)

    def set_project_dir(self, session_id: str, project_dir: Path) -> None:
        state = self.get(session_id)
        state.project_dir = str(project_dir)
        self._emit(state, "project_bound", {"project_dir": state.project_dir})

    def set_step(
        self,
        session_id: str,
        step_name: str,
        status: StepStatus,
        message: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        state = self.get(session_id)
        step = next((x for x in state.steps if x.name == step_name), None)
        if step is None:
            step = StepState(step_name, status, message)
            state.steps.append(step)
        else:
            step.status = status
            step.message = message
            step.updated_at = utc_now()
        payload: dict[str, Any] = {"step": step_name, "status": status.value}
        if message:
            payload["message"] = message
        if extra:
            payload.update(extra)
        self._emit(state, "step_updated", payload)

    def transition(self, session_id: str, nxt: Phase, reason: str = "") -> None:
        state = self.get(session_id)
        if state.phase == nxt:
            return
        if not can_transition(state.phase, nxt):
            message = f"Invalid transition: {state.phase.value} -> {nxt.value}"
            self._emit(state, "error", {"message": message})
            raise ValueError(message)
        state.phase = nxt
        payload: dict[str, Any] = {"phase": nxt.value}
        if reason:
            payload["reason"] = reason
        self._emit(state, "phase_changed", payload)

    def mark_failed(self, session_id: str, message: str) -> None:
        state = self.get(session_id)
        state.phase = Phase.failed
        self._emit(state, "phase_changed", {"phase": state.phase.value})
        self._emit(state, "error", {"message": message})

    def mark_done(self, session_id: str, payload: dict[str, Any]) -> None:
        self.transition(session_id, Phase.done, reason="export_complete")
        self._emit(self.get(session_id), "done", payload)

    def apply_message(self, session_id: str, message_type: str, _message: str) -> str:
        state = self.get(session_id)
        trace_id = f"trace_{uuid4().hex[:12]}"

        if message_type == "prompt":
            state.prompt = _message
            self._emit(state, "prompt_received", {"trace_id": trace_id})
            return trace_id

        if message_type == "confirm" and state.blocked_confirmation:
            state.blocked_confirmation = False
            self.set_step(session_id, "strategist_confirm", StepStatus.completed)
            self.transition(session_id, Phase.rendering, reason="confirmation_passed")
            self.set_step(session_id, "render_pages", StepStatus.running)
            return trace_id

        if state.blocked_confirmation:
            self._emit(state, "warning", {"message": "Workflow blocked by strategist confirmation gate"})
            return trace_id

        self.set_step(session_id, "render_pages", StepStatus.running)
        return trace_id

    def retry(self, session_id: str, scope: RetryScope, target: str) -> str:
        state = self.get(session_id)
        trace_id = f"trace_{uuid4().hex[:12]}"
        if scope == RetryScope.phase:
            if target in Phase.__members__:
                phase = Phase[target]
            elif target in {x.value for x in Phase}:
                phase = next(x for x in Phase if x.value == target)
            else:
                phase = Phase.rendering
            state.phase = phase
            self._emit(
                state,
                "phase_changed",
                {"phase": state.phase.value, "retry_scope": "phase"},
            )
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
