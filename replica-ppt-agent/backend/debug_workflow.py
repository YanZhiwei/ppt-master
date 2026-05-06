from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.pipeline import convert_html_directory_to_svg, run_export_pipeline
from app.planner import generate_deck_plan
from app.settings import settings
from app.workflow import store


def _build_demo_html_pages(project_dir: Path, plan: dict) -> list[Path]:
    html_dir = project_dir / "html_output"
    html_dir.mkdir(parents=True, exist_ok=True)
    output: list[Path] = []
    pages = plan.get("pages", [])
    layout_cycle = {
        "cover": ["cover-hero-a", "cover-hero-b"],
        "agenda": ["agenda-list", "agenda-roadmap"],
        "content": ["content-cards", "content-steps", "content-compare"],
        "data": ["data-bars", "data-kpi-grid"],
        "summary": ["summary-quote", "summary-grid"],
        "ending": ["ending-dark", "ending-light"],
    }
    layout_index = {k: 0 for k in layout_cycle.keys()}

    for i, page in enumerate(pages, start=1):
        page_id = str(page.get("id") or f"{i:02d}")
        title = str(page.get("title") or f"第{i}页")
        page_type = str(page.get("page_type") or "content")
        bullets = page.get("bullets", [])
        if not isinstance(bullets, list):
            bullets = [str(bullets)]
        options = layout_cycle.get(page_type, ["content-cards"])
        chosen_layout = options[layout_index.get(page_type, 0) % len(options)]
        layout_index[page_type] = layout_index.get(page_type, 0) + 1
        bullet_html = "".join([f"<li>{str(x)}</li>" for x in bullets[:6]])
        # Simple layout variants by page type.
        if page_type == "cover":
            body_html = f"<h1>{title}</h1><p>{' '.join(str(x) for x in bullets[:2])}</p>"
        elif page_type == "agenda":
            body_html = f"<h1>{title}</h1><ul>{bullet_html}</ul>"
        elif page_type == "data":
            row_html = "".join(
                f"<tr><td>指标{i+1}</td><td>{str(x)}</td></tr>" for i, x in enumerate(bullets[:4])
            )
            body_html = f"<h1>{title}</h1><table><tbody>{row_html}</tbody></table>"
        else:
            body_html = f"<h1>{title}</h1><ul>{bullet_html}</ul>"

        content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><title>{title}</title></head>
<body>
  <div data-layout="{chosen_layout}" data-page-type="{page_type}" style="position:relative;width:1280px;height:720px;padding:36px;box-sizing:border-box;">
    {body_html}
  </div>
</body>
</html>
"""
        target = html_dir / f"{page_id}_{page_type}.html"
        target.write_text(content, encoding="utf-8")
        output.append(target)
    return output


def run(theme: str, generate_ppt: bool = True) -> None:
    state = store.create_session("direct-debug-session")
    trace_prompt = store.apply_message(state.session_id, "prompt", theme)
    trace_confirm = store.apply_message(state.session_id, "confirm", "确认八项建议，继续执行")

    project_dir = Path(__file__).resolve().parent / "debug_runs" / state.project_id
    (project_dir / "exports").mkdir(parents=True, exist_ok=True)
    plan = generate_deck_plan(theme)
    (project_dir / "deck_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    html_files = _build_demo_html_pages(project_dir, plan)
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
