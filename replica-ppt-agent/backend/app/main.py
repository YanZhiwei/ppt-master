from __future__ import annotations

import asyncio
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app.api.events import stream_session_events
from app.authoring.demo_pages import build_demo_html_pages
from app.models import (
    ExportRequest,
    Phase,
    RetryRequest,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionMessageRequest,
    SessionMessageResponse,
    StepStatus,
)
from app.pipeline import convert_html_directory_to_svg
from app.planner import generate_deck_plan
from app.quality.svg_gate import run_svg_quality_gate
from app.settings import settings
from app.strategist import (
    enrich_semantics_with_llm,
    infer_target_pages,
    normalize_plan,
    write_strategy_files,
)
from app.workflow import store
from app.export.pptx_export import export_pptx, verify_editable_shapes

app = FastAPI(title="Replica PPT Agent API", version="0.1.0")
EXPORT_JOBS: dict[str, dict] = {}
SESSION_TASKS: dict[str, bool] = {}


def _runtime_projects_dir() -> Path:
    backend_root = Path(__file__).resolve().parents[1]
    target = backend_root / "runtime" / "projects"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _session_by_project(project_id: str):
    return next((s for s in store.sessions.values() if s.project_id == project_id), None)


def _spawn_background(coro, *args) -> None:
    def _runner() -> None:
        asyncio.run(coro(*args))

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()


async def _run_generation(session_id: str) -> None:
    state = store.get(session_id)
    theme = state.prompt or settings.default_ppt_theme
    project_dir = _runtime_projects_dir() / state.project_id
    (project_dir / "exports").mkdir(parents=True, exist_ok=True)
    store.set_project_dir(session_id, project_dir)
    state.artifacts["project_dir"] = str(project_dir)
    try:
        target_pages = infer_target_pages(theme)
        plan = await asyncio.to_thread(generate_deck_plan, theme, target_pages)
        plan = normalize_plan(plan, target_pages)
        plan = await asyncio.to_thread(enrich_semantics_with_llm, theme, plan)
        (project_dir / "deck_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        strategy = await asyncio.to_thread(write_strategy_files, project_dir, theme, plan)
        spec_lock = strategy["spec_lock"]
        state.artifacts["design_spec_path"] = strategy["design_spec_path"]
        state.artifacts["spec_lock_path"] = strategy["spec_lock_path"]
        store.emit(session_id, "planning_completed", {"pages": len(plan.get("pages", [])), "target_pages": target_pages})

        html_files = await asyncio.to_thread(build_demo_html_pages, project_dir, plan, spec_lock)
        store.emit(session_id, "html_generated", {"count": len(html_files)})

        svg_files = await asyncio.to_thread(convert_html_directory_to_svg, project_dir)
        state.artifacts["svg_count"] = len(svg_files)
        store.set_step(session_id, "render_pages", StepStatus.completed, extra={"count": len(svg_files)})

        store.transition(session_id, Phase.quality_check, reason="render_completed")
        store.set_step(session_id, "quality_gate", StepStatus.running)
        ok, report = await asyncio.to_thread(run_svg_quality_gate, project_dir)
        (project_dir / "quality_report.txt").write_text(report, encoding="utf-8")
        if not ok:
            store.set_step(session_id, "quality_gate", StepStatus.failed, report)
            store.mark_failed(session_id, f"quality gate failed: {report}")
            return
        store.set_step(session_id, "quality_gate", StepStatus.completed)
        store.emit(session_id, "quality_gate_passed", {"report_path": str(project_dir / "quality_report.txt")})
        store.emit(session_id, "ready_for_export", {"project_id": state.project_id})
    except Exception as exc:
        store.mark_failed(session_id, str(exc))
    finally:
        SESSION_TASKS.pop(session_id, None)


async def _run_export(job_id: str) -> None:
    job = EXPORT_JOBS[job_id]
    session_id = job["session_id"]
    project_id = job["project_id"]
    state = _session_by_project(project_id)
    if state is None:
        job["status"] = "failed"
        job["error"] = "project not found"
        return
    try:
        job["status"] = "running"
        project_dir = Path(state.project_dir) if state.project_dir else (_runtime_projects_dir() / project_id)
        if state.phase != Phase.quality_check:
            store.transition(session_id, Phase.quality_check, reason="export_requested")
        store.transition(session_id, Phase.exporting, reason="export_requested")
        store.set_step(session_id, "export", StepStatus.running)

        ok, report = await asyncio.to_thread(export_pptx, project_dir)
        if not ok:
            job["status"] = "failed"
            job["error"] = report
            store.set_step(session_id, "export", StepStatus.failed, report)
            store.mark_failed(session_id, f"export failed: {report}")
            return

        exports = sorted((project_dir / "exports").glob("*.pptx"), reverse=True)
        if not exports:
            job["status"] = "failed"
            job["error"] = "No exported PPTX found"
            store.mark_failed(session_id, "No exported PPTX found")
            return
        latest = exports[0]
        editable_ok, editable_report = await asyncio.to_thread(verify_editable_shapes, latest)
        if not editable_ok:
            job["status"] = "failed"
            job["error"] = editable_report
            store.set_step(session_id, "export", StepStatus.failed, editable_report)
            store.mark_failed(session_id, f"editability check failed: {editable_report}")
            return

        state.artifacts["pptx_path"] = str(latest)
        job["status"] = "succeeded"
        job["download_url"] = f"/api/v1/exports/{job_id}/download"
        job["report"] = editable_report
        store.set_step(session_id, "export", StepStatus.completed, editable_report)
        store.mark_done(
            session_id,
            {
                "project_id": project_id,
                "job_id": job_id,
                "download_url": job["download_url"],
                "pptx_path": str(latest),
            },
        )
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = str(exc)
        store.mark_failed(session_id, f"export exception: {exc}")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/debug/settings")
def debug_settings() -> dict:
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
async def debug_demo_session() -> dict:
    state = store.create_session("debug-demo-session")
    trace_prompt = store.apply_message(state.session_id, "prompt", settings.default_ppt_theme)
    trace_confirm = store.apply_message(state.session_id, "confirm", "确认八项建议，继续执行")
    SESSION_TASKS[state.session_id] = True  # marker only
    _spawn_background(_run_generation, state.session_id)
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
        session_id=state.session_id,
        project_id=state.project_id,
        created_at=state.created_at,
    )


@app.post("/api/v1/sessions/{session_id}/messages", response_model=SessionMessageResponse)
async def send_message(session_id: str, payload: SessionMessageRequest) -> SessionMessageResponse:
    if session_id not in store.sessions:
        raise HTTPException(status_code=404, detail="session not found")
    trace_id = store.apply_message(session_id, payload.message_type, payload.message)
    state = store.get(session_id)
    if payload.message_type == "confirm" and not state.blocked_confirmation:
        existing = SESSION_TASKS.get(session_id)
        if existing:
            raise HTTPException(status_code=409, detail="generation already running")
        SESSION_TASKS[session_id] = True  # marker only
        _spawn_background(_run_generation, session_id)
    return SessionMessageResponse(accepted=True, trace_id=trace_id)


@app.get("/api/v1/sessions/{session_id}/events")
async def session_events(session_id: str) -> StreamingResponse:
    if session_id not in store.sessions:
        raise HTTPException(status_code=404, detail="session not found")
    return StreamingResponse(stream_session_events(session_id), media_type="text/event-stream")


@app.get("/api/v1/projects/{project_id}")
def get_project(project_id: str) -> dict:
    session = _session_by_project(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="project not found")
    return {
        "project_id": project_id,
        "phase": session.phase.value,
        "progress": {
            "total": len(session.steps),
            "complete": len([x for x in session.steps if x.status.value == "completed"]),
        },
        "artifacts": session.artifacts,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/projects/{project_id}/slides")
def get_slides(project_id: str) -> dict:
    session = _session_by_project(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="project not found")
    project_dir = Path(session.project_dir) if session.project_dir else (_runtime_projects_dir() / project_id)
    svg_files = sorted((project_dir / "svg_output").glob("*.svg"))
    slides = [
        {
            "index": idx + 1,
            "title": item.stem,
            "preview_url": f"/api/v1/projects/{project_id}/slides/{item.name}/preview",
            "status": "ready",
        }
        for idx, item in enumerate(svg_files)
    ]
    return {"project_id": project_id, "slides": slides}


@app.get("/api/v1/projects/{project_id}/slides/{slide_name}/preview")
def slide_preview(project_id: str, slide_name: str):
    session = _session_by_project(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="project not found")
    project_dir = Path(session.project_dir) if session.project_dir else (_runtime_projects_dir() / project_id)
    target = project_dir / "svg_output" / slide_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="slide preview not found")
    return FileResponse(target, media_type="image/svg+xml")


@app.post("/api/v1/projects/{project_id}/retry")
def retry_project(project_id: str, payload: RetryRequest) -> dict:
    session = _session_by_project(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="project not found")
    trace_id = store.retry(session.session_id, payload.scope, payload.target)
    return {"accepted": True, "new_trace_id": trace_id}


@app.post("/api/v1/projects/{project_id}/export")
async def export_project(project_id: str, payload: ExportRequest) -> dict:
    session = _session_by_project(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="project not found")
    job_id = f"job_{uuid4().hex[:10]}"
    EXPORT_JOBS[job_id] = {
        "job_id": job_id,
        "project_id": project_id,
        "session_id": session.session_id,
        "format": payload.format,
        "status": "queued",
        "download_url": None,
    }
    _spawn_background(_run_export, job_id)
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/v1/exports/{job_id}")
def export_status(job_id: str) -> dict:
    job = EXPORT_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.get("/api/v1/exports/{job_id}/download")
def export_download(job_id: str):
    job = EXPORT_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "succeeded":
        raise HTTPException(status_code=409, detail="export not ready")
    session = _session_by_project(job["project_id"])
    if not session:
        raise HTTPException(status_code=404, detail="project not found")
    pptx_path = session.artifacts.get("pptx_path", "")
    if not pptx_path or not Path(pptx_path).exists():
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(Path(pptx_path), media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")
