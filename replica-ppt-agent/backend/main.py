from __future__ import annotations

import argparse
import json

import uvicorn

from app.settings import settings
from app.workflow import store


def run_demo(theme: str | None = None) -> None:
    prompt = (theme or settings.default_ppt_theme).strip()
    state = store.create_session("debug-main-demo")
    trace_prompt = store.apply_message(state.session_id, "prompt", prompt)
    trace_confirm = store.apply_message(state.session_id, "confirm", "确认八项建议，继续执行")
    print(
        json.dumps(
            {
                "session_id": state.session_id,
                "project_id": state.project_id,
                "theme": prompt,
                "trace_prompt": trace_prompt,
                "trace_confirm": trace_confirm,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def run_server() -> None:
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replica backend debug entry")
    parser.add_argument(
        "--mode",
        choices=["server", "demo"],
        default="server",
        help="server: run FastAPI; demo: trigger one local workflow session",
    )
    parser.add_argument(
        "--theme",
        default=None,
        help="Override default theme for demo mode",
    )
    args = parser.parse_args()
    if args.mode == "demo":
        run_demo(args.theme)
    else:
        run_server()


if __name__ == "__main__":
    main()

