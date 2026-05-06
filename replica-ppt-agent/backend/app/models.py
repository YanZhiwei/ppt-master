from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Phase(str, Enum):
    planning = "planning"
    acquiring_images = "acquiring_images"
    rendering = "rendering"
    quality_check = "quality_check"
    exporting = "exporting"
    done = "done"
    failed = "failed"


class StepStatus(str, Enum):
    pending = "pending"
    running = "running"
    blocked = "blocked"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class RetryScope(str, Enum):
    phase = "phase"
    page = "page"


class SessionCreateRequest(BaseModel):
    title: str | None = None


class SessionCreateResponse(BaseModel):
    session_id: str
    project_id: str
    created_at: str


class SessionMessageRequest(BaseModel):
    message_type: Literal["prompt", "confirm", "revise"] = "prompt"
    message: str = Field(min_length=1)


class SessionMessageResponse(BaseModel):
    accepted: bool
    trace_id: str


class RetryRequest(BaseModel):
    scope: RetryScope
    target: str


class ExportRequest(BaseModel):
    format: Literal["pptx"] = "pptx"
    with_narration: bool = False
