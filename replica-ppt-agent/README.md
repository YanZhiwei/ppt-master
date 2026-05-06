# Replica PPT Agent (Standalone)

This folder contains an isolated replica project.

- `backend/`: FastAPI + workflow orchestration + provider routing + conversion/export wrappers
- `frontend/`: React + TS shell for template explore and generation workspace

## Tooling Policy

- Backend dependency/runtime manager: `uv`
- Frontend package manager: `pnpm`
- Backend and frontend environments MUST stay isolated and MUST NOT share runtime dependencies.

## Design Intent

- Editing model: HTML/CSS + object metadata
- Export model: HTML -> SVG -> PPTX (editable DrawingML)
- Text model: Azure OpenAI
- Image model routing: Gemini or OpenAI `gpt-image-2`
