from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.authoring.demo_pages import build_demo_html_pages
from app.pipeline import convert_html_directory_to_svg, run_export_pipeline
from app.planner import generate_deck_plan
from app.settings import settings
from app.strategist import enrich_semantics_with_llm, infer_target_pages, normalize_plan, write_strategy_files
from app.workflow import store


def run(theme: str, generate_ppt: bool = True) -> None:
    state = store.create_session("direct-debug-session")
    trace_prompt = store.apply_message(state.session_id, "prompt", theme)
    trace_confirm = store.apply_message(state.session_id, "confirm", "确认八项建议，继续执行")

    project_dir = Path(__file__).resolve().parent / "debug_runs" / state.project_id
    (project_dir / "exports").mkdir(parents=True, exist_ok=True)
    target_pages = infer_target_pages(theme)
    plan = generate_deck_plan(theme, target_pages)
    plan = normalize_plan(plan, target_pages)
    plan = enrich_semantics_with_llm(theme, plan)
    (project_dir / "deck_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    strategy = write_strategy_files(project_dir, theme, plan)
    html_files = build_demo_html_pages(project_dir, plan, strategy["spec_lock"])
    svg_files = convert_html_directory_to_svg(project_dir)

    print("=== Direct Workflow Debug (No REST) ===")
    print(
        json.dumps(
            {
                "session_id": state.session_id,
                "project_id": state.project_id,
                "phase": state.phase.value,
                "trace_prompt": trace_prompt,
                "trace_confirm": trace_confirm,
                "event_count": len(state.events),
                "project_dir": str(project_dir),
                "html_count": len(html_files),
                "svg_count": len(svg_files),
                "target_pages": target_pages,
                "design_spec": strategy["design_spec_path"],
                "spec_lock": strategy["spec_lock_path"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print("\n=== Events ===")
    for evt in state.events:
        print(json.dumps(evt, ensure_ascii=False))

    if generate_ppt:
        print("\n=== Export Pipeline ===")
        ok, report = run_export_pipeline(project_dir)
        exports = sorted((project_dir / "exports").glob("*.pptx"), reverse=True)
        print(json.dumps({"ok": ok, "report": report, "exports": [str(x) for x in exports]}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Direct workflow debug without REST")
    parser.add_argument("--theme", default=settings.default_ppt_theme)
    parser.add_argument("--no-export", action="store_true")
    args = parser.parse_args()
    run(args.theme, generate_ppt=not args.no_export)


if __name__ == "__main__":
    main()
