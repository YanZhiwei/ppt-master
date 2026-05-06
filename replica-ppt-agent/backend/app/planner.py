from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.providers.llm_provider import build_chat_model


def _fallback_plan(theme: str, target_pages: int = 8) -> dict[str, Any]:
    base = [
        {"id": "01", "page_type": "cover", "title": "封面", "bullets": [theme]},
        {"id": "02", "page_type": "agenda", "title": "目录", "bullets": ["背景与目标", "现状痛点", "核心方案", "实施路线", "总结"]},
        {"id": "03", "page_type": "content", "title": "行业背景", "bullets": ["行业增长持续加速", "竞争格局正在重构", "技术红利仍在释放"]},
        {"id": "04", "page_type": "content", "title": "问题定义", "bullets": ["效率瓶颈突出", "流程割裂影响协同", "决策依赖经验而非数据"]},
        {"id": "05", "page_type": "content", "title": "解决方案", "bullets": ["统一数据底座", "智能自动化流程", "可视化决策支持"]},
        {"id": "06", "page_type": "data", "title": "关键指标", "bullets": ["效率提升 35%", "周期缩短 28%", "成本下降 18%"]},
        {"id": "07", "page_type": "data", "title": "阶段成果", "bullets": ["试点覆盖 3 条业务线", "月活跃用户增长 2.1 倍", "用户满意度 4.7/5"]},
        {"id": "08", "page_type": "summary", "title": "结论与建议", "bullets": ["先试点后推广", "建立统一标准", "持续度量与优化"]},
    ]
    pages = base[:target_pages]
    while len(pages) < target_pages:
        i = len(pages) + 1
        pages.insert(-1, {"id": f"{i:02d}", "page_type": "content", "title": f"核心内容 {i}", "bullets": [f"关键观点{i}-1", f"关键观点{i}-2"]})
    return {
        "language": "zh-CN",
        "theme": theme,
        "pages": pages,
    }


def _extract_json(text: str) -> dict[str, Any] | None:
    raw = text.strip()
    if raw.startswith("{") and raw.endswith("}"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    fenced = re.search(r"```json\s*(\{[\s\S]*\})\s*```", raw, re.IGNORECASE)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            return None
    return None


def generate_deck_plan(theme: str, target_pages: int = 8) -> dict[str, Any]:
    """Generate page-level deck plan via Azure OpenAI; fallback deterministically if unavailable."""
    try:
        model = build_chat_model()
        system = SystemMessage(
            content=(
                "你是专业咨询风PPT策划。请输出严格JSON，不要任何额外文本。"
                "字段：language, theme, pages。"
                "pages为数组，每项字段：id(两位序号), page_type(cover/agenda/content/data/summary/ending), "
                "title, bullets(2-5条字符串)。"
            )
        )
        user = HumanMessage(
            content=(
                f"主题：{theme}\n"
                f"页数目标：{target_pages}\n"
                "要求：商务风、结构完整、可直接用于演示。"
            )
        )
        response = model.invoke([system, user])
        parsed = _extract_json(getattr(response, "content", "") or "")
        if not parsed or "pages" not in parsed or not isinstance(parsed["pages"], list):
            return _fallback_plan(theme, target_pages)
        if len(parsed["pages"]) == 0:
            return _fallback_plan(theme, target_pages)
        return parsed
    except Exception:
        return _fallback_plan(theme, target_pages)
