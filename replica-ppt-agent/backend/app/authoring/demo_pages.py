from __future__ import annotations

import hashlib
from pathlib import Path
import re


def _pick_layout(page_type: str, rhythm: str, idx: int) -> str:
    anchor = {
        "cover": ["cover-hero-a", "cover-hero-b"],
        "agenda": ["agenda-cards", "agenda-roadmap", "agenda-list"],
        "content": ["content-steps"],
        "data": ["data-bars"],
        "summary": ["summary-panel", "summary-quote"],
        "ending": ["ending-dark", "ending-light"],
    }
    dense = {
        "cover": ["cover-hero-a", "cover-hero-b"],
        "agenda": ["agenda-cards", "agenda-roadmap", "agenda-list"],
        "content": ["content-cards", "content-steps", "content-compare", "content-zigzag", "content-matrix", "semantic-process-alt", "semantic-compare-alt", "semantic-architecture-alt"],
        "data": ["data-bars", "data-kpi-grid", "data-table-pro", "data-waterfall"],
        "summary": ["summary-panel", "summary-grid", "summary-takeaway"],
        "ending": ["ending-dark"],
    }
    breathing = {
        "cover": ["cover-hero-b"],
        "agenda": ["agenda-cards", "agenda-roadmap"],
        "content": ["content-compare", "content-zigzag", "semantic-compare-alt"],
        "data": ["data-kpi-grid", "data-table-pro"],
        "summary": ["summary-panel", "summary-quote", "summary-grid", "summary-takeaway"],
        "ending": ["ending-light"],
    }
    lib = dense
    if rhythm == "anchor":
        lib = anchor
    elif rhythm == "breathing":
        lib = breathing
    options = lib.get(page_type, ["content-cards"])
    return options[(idx - 1) % len(options)]


LAYOUT_VARIANTS: dict[str, list[str]] = {
    "cover-hero-a": ["cover-hero-a", "cover-hero-b"],
    "cover-hero-b": ["cover-hero-b", "cover-hero-a"],
    "agenda-roadmap": ["agenda-cards", "agenda-roadmap", "agenda-list"],
    "agenda-list": ["agenda-cards", "agenda-list", "agenda-roadmap"],
    "agenda-cards": ["agenda-cards", "agenda-roadmap", "agenda-list"],
    "semantic-process": ["semantic-process-alt", "semantic-process", "content-steps", "content-zigzag"],
    "semantic-process-alt": ["semantic-process-alt", "semantic-process", "content-zigzag"],
    "semantic-compare": ["semantic-compare-alt", "semantic-compare", "content-compare", "data-table-pro"],
    "semantic-compare-alt": ["semantic-compare-alt", "semantic-compare", "content-compare"],
    "semantic-risk": ["semantic-risk-alt", "semantic-risk", "content-matrix"],
    "semantic-risk-alt": ["semantic-risk-alt", "semantic-risk", "content-matrix"],
    "semantic-architecture": ["semantic-architecture-alt", "semantic-architecture", "content-matrix"],
    "semantic-architecture-alt": ["semantic-architecture-alt", "semantic-architecture", "content-matrix"],
    "timeline-modern": ["timeline-strip", "timeline-modern", "content-steps", "content-zigzag"],
    "timeline-strip": ["timeline-strip", "timeline-modern", "content-zigzag"],
    "history-timeline": ["history-timeline", "content-zigzag"],
    "data-funnel": ["data-funnel", "data-table-pro"],
    "data-line-trend": ["data-line-trend", "data-table-pro", "data-kpi-grid"],
    "data-waterfall": ["data-waterfall", "data-table-pro", "data-kpi-grid"],
    "data-table-pro": ["data-table-pro", "data-kpi-grid"],
    "data-bars": ["data-bars", "data-kpi-grid"],
    "summary-takeaway": ["summary-panel", "summary-takeaway", "summary-grid", "summary-quote"],
    "summary-panel": ["summary-panel", "summary-grid", "summary-quote", "summary-takeaway"],
    "ending-light": ["ending-light", "ending-dark"],
    "ending-dark": ["ending-dark", "ending-light"],
    "content-cards": ["content-cards", "content-zigzag", "content-matrix"],
    "content-zigzag": ["content-zigzag", "content-cards", "content-matrix"],
    "content-matrix": ["content-matrix", "content-cards", "content-zigzag"],
}


def _split_data_cell_text(text: str, idx: int) -> tuple[str, str]:
    raw = str(text).strip()
    if not raw:
        return (f"维度{idx}", f"要点{idx}")
    for sep in ["：", ":", "-", "|", "—"]:
        if sep in raw:
            left, right = raw.split(sep, 1)
            l = left.strip()
            r = right.strip()
            if l and r:
                return (l[:18], r)
    compact = raw.replace(" ", "")
    if len(compact) >= 8:
        return (compact[:6], raw)
    return (f"维度{idx}", raw)


def _stable_hash_int(text: str) -> int:
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _pick_layout_variant(
    base_layout: str,
    *,
    usage: dict[str, int],
    page_id: str,
    title: str,
    seed: str,
) -> str:
    candidates = LAYOUT_VARIANTS.get(base_layout, [base_layout])
    min_use = min(usage.get(x, 0) for x in candidates)
    least_used = [x for x in candidates if usage.get(x, 0) == min_use]
    idx = _stable_hash_int(f"{seed}:{page_id}:{title}:{base_layout}") % len(least_used)
    chosen = least_used[idx]
    usage[chosen] = usage.get(chosen, 0) + 1
    return chosen


def _pick_semantic_layout(page: dict, rhythm: str, idx: int, style_profile: str) -> str:
    page_type = str(page.get("page_type", "content"))
    semantic = str(page.get("semantic", "generic"))
    viz_intent = str(page.get("viz_intent", ""))
    intent_mapping = {
        "hero": "cover-hero-b" if rhythm == "breathing" else "cover-hero-a",
        "ending": "ending-light" if rhythm == "anchor" else "ending-dark",
        "roadmap": "agenda-cards",
        "takeaway": "summary-panel",
        "timeline": "history-timeline" if style_profile == "history-ink" else "timeline-modern",
        "process": "semantic-process-alt",
        "compare": "semantic-compare-alt",
        "risk-matrix": "semantic-risk-alt",
        "architecture": "semantic-architecture-alt",
        "matrix": "content-matrix",
        "trend": "data-line-trend",
        "funnel": "data-funnel",
        "waterfall": "data-waterfall",
        "table": "data-table-pro",
        "bar": "data-bars",
        "cards": "",
    }
    if viz_intent in intent_mapping and intent_mapping[viz_intent]:
        return intent_mapping[viz_intent]
    mapping = {
        ("content", "timeline"): "history-timeline" if style_profile == "history-ink" else "timeline-modern",
        ("data", "timeline"): "history-timeline" if style_profile == "history-ink" else "timeline-modern",
        ("content", "process"): "semantic-process",
        ("data", "process"): "semantic-process",
        ("content", "compare"): "semantic-compare",
        ("data", "compare"): "semantic-compare",
        ("content", "risk"): "semantic-risk",
        ("data", "risk"): "semantic-risk",
        ("content", "architecture"): "semantic-architecture",
        ("data", "architecture"): "semantic-architecture",
        ("content", "figures"): "history-figures",
        ("content", "landmarks"): "history-landmarks",
        ("content", "culture"): "history-culture",
        ("content", "modern"): "history-modern" if style_profile == "history-ink" else "content-steps",
        ("data", "modern"): "history-modern" if style_profile == "history-ink" else "data-kpi-grid",
    }
    if (page_type, semantic) in mapping:
        return mapping[(page_type, semantic)]
    if page_type == "data":
        return _pick_data_layout(page, rhythm, idx)
    return _pick_layout(page_type, rhythm, idx)


def _pick_data_layout(page: dict, rhythm: str, idx: int) -> str:
    title = str(page.get("title", "")).lower()
    bullets = [str(x).strip() for x in page.get("bullets", []) if str(x).strip()]
    joined = f"{title} {' '.join(bullets)}".lower()
    number_hits = sum(len(re.findall(r"\d+", x)) for x in bullets)
    compare_hits = sum(1 for k in ["对比", "比较", "差异", "vs", "versus"] if k in joined)
    flow_hits = sum(1 for k in ["投入", "产出", "增量", "减量", "净收益", "roi", "成本", "收益"] if k in joined)
    trend_hits = sum(1 for k in ["趋势", "同比", "环比", "增长率", "走势", "trend", "growth"] if k in joined)
    funnel_hits = sum(1 for k in ["漏斗", "转化", "留存", "conversion", "funnel"] if k in joined)
    if funnel_hits >= 1 and len(bullets) >= 3:
        return "data-funnel"
    if trend_hits >= 1:
        return "data-line-trend"
    if flow_hits >= 2 and number_hits >= 2:
        return "data-waterfall"
    if compare_hits >= 1 and len(bullets) >= 3:
        return "data-table-pro"
    if number_hits >= max(2, len(bullets)):
        return "data-bars"
    if rhythm == "breathing":
        return "data-kpi-grid"
    return _pick_layout("data", rhythm, idx)


def build_demo_html_pages(project_dir: Path, plan: dict, spec_lock: dict | None = None) -> list[Path]:
    html_dir = project_dir / "html_output"
    html_dir.mkdir(parents=True, exist_ok=True)
    output: list[Path] = []
    pages = plan.get("pages", [])
    rhythm_map = (spec_lock or {}).get("page_rhythm", {})
    style_profile = str((spec_lock or {}).get("style_profile", "business-blue"))
    usage: dict[str, int] = {}
    seed = f"{project_dir.name}:{style_profile}:{len(pages)}"

    for i, page in enumerate(pages, start=1):
        page_id = str(page.get("id") or f"{i:02d}")
        title = str(page.get("title") or f"第{i}页")
        page_type = str(page.get("page_type") or "content")
        bullets = page.get("bullets", [])
        if not isinstance(bullets, list):
            bullets = [str(bullets)]
        rhythm = rhythm_map.get(f"P{i:02d}", "dense")
        base_layout = _pick_semantic_layout(page, rhythm, i, style_profile)
        chosen_layout = _pick_layout_variant(
            base_layout,
            usage=usage,
            page_id=page_id,
            title=title,
            seed=seed,
        )
        bullet_html = "".join([f"<li>{str(x)}</li>" for x in bullets[:6]])

        if page_type == "cover":
            body_html = f"<h1>{title}</h1><p>{' '.join(str(x) for x in bullets[:2])}</p>"
        elif page_type == "agenda":
            body_html = f"<h1>{title}</h1><ul>{bullet_html}</ul>"
        elif page_type == "data":
            pairs = [_split_data_cell_text(x, j + 1) for j, x in enumerate(bullets[:4])]
            row_html = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in pairs)
            body_html = f"<h1>{title}</h1><table><tbody>{row_html}</tbody></table>"
        else:
            body_html = f"<h1>{title}</h1><ul>{bullet_html}</ul>"

        content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><title>{title}</title></head>
<body>
  <div data-layout="{chosen_layout}" data-page-type="{page_type}" data-semantic="{page.get('semantic', 'generic')}" data-viz-intent="{page.get('viz_intent', 'cards')}" data-page-rhythm="{rhythm}" data-style="{style_profile}" style="position:relative;width:1280px;height:720px;padding:36px;box-sizing:border-box;">
    {body_html}
  </div>
</body>
</html>
"""
        target = html_dir / f"{page_id}_{page_type}.html"
        target.write_text(content, encoding="utf-8")
        output.append(target)
    return output
