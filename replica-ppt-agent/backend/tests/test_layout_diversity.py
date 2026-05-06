from pathlib import Path
import re

from app.authoring.demo_pages import build_demo_html_pages


def _extract_layout(html_text: str) -> str:
    m = re.search(r'data-layout="([^"]+)"', html_text)
    return m.group(1) if m else ""


def test_layout_selection_uses_variants_within_deck(tmp_path: Path) -> None:
    plan = {
        "pages": [
            {"id": "01", "page_type": "cover", "title": "封面", "bullets": ["A"], "viz_intent": "hero"},
            {"id": "02", "page_type": "agenda", "title": "目录", "bullets": ["A", "B"], "viz_intent": "roadmap"},
            {"id": "03", "page_type": "content", "title": "流程一", "bullets": ["步骤1", "步骤2"], "viz_intent": "process"},
            {"id": "04", "page_type": "content", "title": "流程二", "bullets": ["步骤1", "步骤2"], "viz_intent": "process"},
            {"id": "05", "page_type": "content", "title": "流程三", "bullets": ["步骤1", "步骤2"], "viz_intent": "process"},
            {"id": "06", "page_type": "summary", "title": "总结", "bullets": ["结论"], "viz_intent": "takeaway"},
        ]
    }
    spec_lock = {
        "style_profile": "business-blue",
        "page_rhythm": {"P01": "anchor", "P02": "anchor", "P03": "dense", "P04": "dense", "P05": "dense", "P06": "breathing"},
    }
    files = build_demo_html_pages(tmp_path, plan, spec_lock)
    layouts = []
    for item in files:
        if item.name.startswith(("03_", "04_", "05_")):
            layouts.append(_extract_layout(item.read_text(encoding="utf-8")))
    assert len(set(layouts)) >= 2
