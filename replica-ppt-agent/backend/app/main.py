from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from app.api.events import stream_session_events
from app.models import (
    ExportRequest,
    RetryRequest,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionMessageRequest,
    SessionMessageResponse,
)
from app.settings import settings
from app.workflow import store

app = FastAPI(title="Replica PPT Agent API", version="0.1.0")
EXPORT_JOBS: dict[str, dict] = {}


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/debug/settings")
def debug_settings() -> dict:
    """Non-secret runtime view to verify .env loading.

    Keys are masked/truncated for safety.
    """
    return {
        "llm_provider": settings.llm_provider,
        "azure_openai_endpoint": settings.azure_openai_endpoint,
        "azure_openai_api_version": settings.azure_openai_api_version,
        "azure_openai_chat_deployment": settings.azure_openai_chat_deployment,
        "azure_openai_api_key_set": bool(settings.azure_openai_api_key),
        "image_provider": settings.image_provider,
        "image_model": settings.image_model,
        "gemini_api_key_set": bool(os.getenv("GEMINI_API_KEY")),
        "openai_api_key_set": bool(os.getenv("OPENAI_API_KEY")),
        "default_ppt_theme": settings.default_ppt_theme,
    }


@app.post("/debug/demo-session")
def debug_demo_session() -> dict:
    """Create and trigger a demo session with DEFAULT_PPT_THEME.

    This is for local smoke testing without frontend wiring.
    """
    state = store.create_session("debug-demo-session")
    trace_prompt = store.apply_message(
        state.session_id, "prompt", settings.default_ppt_theme
    )
    trace_confirm = store.apply_message(
        state.session_id, "confirm", "确认八项建议，继续执行"
    )
    return {
        "session_id": state.session_id,
        "project_id": state.project_id,
        "theme": settings.default_ppt_theme,
        "trace_prompt": trace_prompt,
        "trace_confirm": trace_confirm,
    }


@app.post("/api/v1/sessions", response_model=SessionCreateResponse)
def create_session(payload: SessionCreateRequest) -> SessionCreateResponse:
    state = store.create_session(payload.title)
    return SessionCreateResponse(
        session_id=state.session_id, created_at=state.created_at
    )


@app.post(
    "/api/v1/sessions/{session_id}/messages", response_model=SessionMessageResponse
)
def send_message(
    session_id: str, payload: SessionMessageRequest
) -> SessionMessageResponse:
    if session_id not in store.sessions:
        raise HTTPException(status_code=404, detail="session not found")
    trace_id = store.apply_message(session_id, payload.message_type, payload.message)
    return SessionMessageResponse(accepted=True, trace_id=trace_id)


@app.get("/api/v1/sessions/{session_id}/events")
async def session_events(session_id: str) -> StreamingResponse:
    if session_id not in store.sessions:
        raise HTTPException(status_code=404, detail="session not found")
    return StreamingResponse(
        stream_session_events(session_id), media_type="text/event-stream"
    )


@app.get("/api/v1/projects/{project_id}")
def get_project(project_id: str) -> dict:
    session = next(
        (s for s in store.sessions.values() if s.project_id == project_id), None
    )
    if not session:
        raise HTTPException(status_code=404, detail="project not found")
    return {
        "project_id": project_id,
        "phase": session.phase.value,
        "progress": {
            "total": len(session.steps),
            "complete": len(
                [x for x in session.steps if x.status.value == "completed"]
            ),
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/projects/{project_id}/slides")
def get_slides(project_id: str) -> dict:
    # Placeholder data contract for frontend integration.
    return {
        "project_id": project_id,
        "slides": [
            {
                "index": 1,
                "title": "Cover",
                "preview_url": "/static/previews/01.svg",
                "status": "ready",
            },
            {
                "index": 2,
                "title": "Agenda",
                "preview_url": "/static/previews/02.svg",
                "status": "ready",
            },
        ],
    }


@app.post("/api/v1/projects/{project_id}/retry")
def retry_project(project_id: str, payload: RetryRequest) -> dict:
    session = next(
        (s for s in store.sessions.values() if s.project_id == project_id), None
    )
    if not session:
        raise HTTPException(status_code=404, detail="project not found")
    trace_id = store.retry(session.session_id, payload.scope, payload.target)
    return {"accepted": True, "new_trace_id": trace_id}


@app.post("/api/v1/projects/{project_id}/export")
def export_project(project_id: str, payload: ExportRequest) -> dict:
    job_id = f"job_{uuid4().hex[:10]}"
    EXPORT_JOBS[job_id] = {
        "job_id": job_id,
        "project_id": project_id,
        "format": payload.format,
        "status": "queued",
        "download_url": None,
    }
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/v1/exports/{job_id}")
def export_status(job_id: str) -> dict:
    job = EXPORT_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job
