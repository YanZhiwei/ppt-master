# Replica PPT Agent Backend

Standalone backend for the replica project.

## Stack
- FastAPI
- LangGraph / LangChain
- Azure OpenAI for text generation
- Configurable image routing (Gemini / OpenAI gpt-image-2)

## Quick Start

```bash
uv sync --dev
cp .env.example .env
uv run python main.py --mode server
```

## Environment Isolation

- Use `uv` virtual environment scoped to `replica-ppt-agent/backend`.
- Do not install backend deps into repository-level Python environments.
- Run backend commands with `uv run ...`.

## Testing

```bash
uv run pytest -q
```

## Debug Helpers

```bash
# Print one demo session with DEFAULT_PPT_THEME
uv run python main.py --mode demo

# Override theme in demo mode
uv run python main.py --mode demo --theme "生成一份新能源行业路演PPT，8页"

# Direct workflow debug without REST/API server
uv run python debug_workflow.py

# Only run workflow state/events (skip export pipeline)
uv run python debug_workflow.py --no-export
```

Runtime debug endpoints:
- `GET /debug/settings` 查看 `.env` 是否生效（敏感值仅显示是否已设置）
- `POST /debug/demo-session` 直接创建并触发默认主题会话

## VS Code Breakpoint Debug

已提供根目录调试配置：
- `.vscode/launch.json`
- `.vscode/tasks.json`

使用方式：
1. 先执行 `uv sync --dev`（确保 `backend/.venv` 存在）
2. VS Code 打开 Run and Debug
3. 选择：
   - `Replica Backend (Python, breakpoints)` 仅后端断点
   - `Replica Full Stack Debug` 前后端联调

## Notes

- This backend is isolated from `skills/ppt-master` runtime code.
- It may call reference scripts as external tools through subprocess wrappers.
