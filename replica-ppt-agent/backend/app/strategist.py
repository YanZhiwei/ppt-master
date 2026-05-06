from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.providers.llm_provider import build_chat_model


STYLE_PROFILES: dict[str, dict[str, Any]] = {
    "business-blue": {
        "name": "商务专业蓝",
        "colors": {
            "background": "#F8FAFC",
            "background_alt_1": "#F7FAFF",
            "background_alt_2": "#F1F5F9",
            "background_alt_3": "#EEF2FF",
            "background_alt_4": "#EFF6FF",
            "surface": "#FFFFFF",
            "surface_dark": "#0B1220",
            "primary": "#1E3A8A",
            "accent": "#2563EB",
            "accent_alt_1": "#1D4ED8",
            "accent_alt_2": "#0EA5E9",
            "accent_alt_3": "#60A5FA",
            "accent_alt_4": "#93C5FD",
            "accent_alt_5": "#1E40AF",
            "text": "#0F172A",
            "subtext": "#334155",
            "text_alt": "#1E293B",
            "border": "#CBD5E1",
            "border_alt": "#DBEAFE",
            "border_soft": "#E2E8F0",
            "tint": "#BFDBFE",
        },
        "typography": {
            "font_family": '"Microsoft YaHei", Arial, sans-serif',
            "title_family": '"Microsoft YaHei", Arial, sans-serif',
            "body_family": '"Microsoft YaHei", Arial, sans-serif',
            "body": 24,
            "title": 46,
            "subtitle": 30,
            "annotation": 16,
        },
        "visual_style": "商务专业 + 信息优先",
        "color_desc": "深蓝主色 + 浅灰背景 + 蓝色强调",
    },
    "history-ink": {
        "name": "历史文脉墨韵",
        "colors": {
            "background": "#F7F2E9",
            "background_alt_1": "#F5EFE4",
            "background_alt_2": "#EEE5D8",
            "background_alt_3": "#E8DECF",
            "background_alt_4": "#EFE6DA",
            "surface": "#FFFDF8",
            "surface_dark": "#2F241F",
            "primary": "#6B3E26",
            "accent": "#A16207",
            "accent_alt_1": "#854D0E",
            "accent_alt_2": "#B45309",
            "accent_alt_3": "#CA8A04",
            "accent_alt_4": "#D6B56C",
            "accent_alt_5": "#7C2D12",
            "text": "#2E1F18",
            "subtext": "#5B4638",
            "text_alt": "#4A372C",
            "border": "#CDBBA6",
            "border_alt": "#DFCDB6",
            "border_soft": "#E7DCCB",
            "tint": "#E7D8C1",
        },
        "typography": {
            "font_family": '"Microsoft YaHei", Arial, sans-serif',
            "title_family": '"Microsoft YaHei", Arial, sans-serif',
            "body_family": '"Microsoft YaHei", Arial, sans-serif',
            "body": 24,
            "title": 46,
            "subtitle": 30,
            "annotation": 16,
        },
        "visual_style": "历史叙事 + 文化表达",
        "color_desc": "宣纸暖底 + 棕金强调 + 深棕文字",
    },
    "tech-cyan": {
        "name": "科技霓青",
        "colors": {
            "background": "#F4F8FF",
            "background_alt_1": "#EEF4FF",
            "background_alt_2": "#E7EEFB",
            "background_alt_3": "#DFEAFF",
            "background_alt_4": "#EAF4FF",
            "surface": "#FFFFFF",
            "surface_dark": "#0A1022",
            "primary": "#1E1B4B",
            "accent": "#0284C7",
            "accent_alt_1": "#0369A1",
            "accent_alt_2": "#06B6D4",
            "accent_alt_3": "#38BDF8",
            "accent_alt_4": "#7DD3FC",
            "accent_alt_5": "#0F172A",
            "text": "#0B132B",
            "subtext": "#1F3A5F",
            "text_alt": "#1E293B",
            "border": "#BFD6F1",
            "border_alt": "#D6E8FF",
            "border_soft": "#DCEAF8",
            "tint": "#BAE6FD",
        },
        "typography": {
            "font_family": '"Microsoft YaHei", Arial, sans-serif',
            "title_family": '"Microsoft YaHei", Arial, sans-serif',
            "body_family": '"Microsoft YaHei", Arial, sans-serif',
            "body": 24,
            "title": 46,
            "subtitle": 30,
            "annotation": 16,
        },
        "visual_style": "科技现代 + 数据导向",
        "color_desc": "深蓝底色 + 青蓝强调 + 高对比信息层级",
    },
}


def infer_target_pages(theme: str, default: int = 8) -> int:
    m = re.search(r"(\d+)\s*页", theme)
    if not m:
        return default
    pages = int(m.group(1))
    return max(6, min(20, pages))


def _fallback_page(page_idx: int) -> dict[str, Any]:
    return {
        "id": f"{page_idx:02d}",
        "page_type": "content",
        "title": f"核心内容 {page_idx}",
        "bullets": [f"关键观点 {page_idx}-1", f"关键观点 {page_idx}-2", f"关键观点 {page_idx}-3"],
    }


def _is_placeholder_title(text: str) -> bool:
    t = text.strip().lower()
    if re.match(r"^第\s*\d+\s*页$", t):
        return True
    return t.startswith("核心内容") or t.startswith("page ")


def _is_placeholder_bullet(text: str) -> bool:
    t = text.strip().lower()
    return t.startswith("关键观点") or t.startswith("要点")


def _detect_domain(theme: str) -> str:
    t = theme.lower()
    if any(k in t for k in ["历史", "文脉", "文化", "古", "heritage", "history"]):
        return "history"
    if any(k in t for k in ["教育", "课堂", "学校", "教学", "教育集团", "education"]):
        return "education"
    if any(k in t for k in ["科技", "ai", "数字化", "效率", "企业", "运营", "business", "tech"]):
        return "business-tech"
    return "general"


def _blueprint_for_domain(domain: str) -> list[dict[str, Any]]:
    if domain == "history":
        return [
            {"page_type": "content", "semantic": "timeline", "title": "历史演进总览", "bullets": ["起源阶段：形成早期聚落与文脉基础", "扩展阶段：交通与商贸推动城市连接", "转型阶段：制度与产业结构重塑城市功能", "现代阶段：创新驱动与全球链接能力增强"]},
            {"page_type": "content", "semantic": "figures", "title": "关键人物与时代推动力", "bullets": ["思想文化人物：塑造城市价值表达", "产业先行者：推动经济结构升级", "治理改革者：提升制度与组织效能", "公众群体：共同构建城市认同"]},
            {"page_type": "content", "semantic": "landmarks", "title": "地标与空间记忆", "bullets": ["历史地标：承载城市起源与早期记忆", "商业地标：体现产业变迁与消费结构", "文化地标：连接传统与现代生活方式", "现代地标：展示全球化城市形象"]},
            {"page_type": "data", "semantic": "compare", "title": "阶段对比：功能与结构变化", "bullets": ["早期：区域型功能，服务半径有限", "近代：商贸金融跃升，外向连接增强", "工业化：制造与基建主导，规模扩张", "当代：创新与服务驱动，复合竞争优势"]},
            {"page_type": "content", "semantic": "risk", "title": "保护与发展中的挑战", "bullets": ["文化遗产保护与城市更新之间的平衡", "人口与资源约束带来的治理压力", "产业转型过程中的结构性风险", "跨部门协同不足导致推进效率波动"]},
            {"page_type": "content", "semantic": "architecture", "title": "城市治理架构与协同机制", "bullets": ["决策层：明确战略方向与治理目标", "执行层：分领域推进重点任务落实", "基层层：社区与街镇形成服务闭环", "支撑层：数字化平台提供数据与监测能力"]},
            {"page_type": "content", "semantic": "modern", "title": "当代发展重点与未来方向", "bullets": ["创新经济：强化产业链核心环节", "公共服务：提升教育医疗与生活品质", "空间治理：优化交通与生态承载能力", "全球链接：增强国际资源配置能力"]},
        ]
    if domain == "education":
        return [
            {"page_type": "content", "semantic": "process", "title": "教学改革实施路径", "bullets": ["目标定义：明确核心素养与结果导向", "课程重构：建立模块化内容与任务链", "课堂执行：推进分层教学与项目实践", "评估优化：数据反馈驱动持续改进"]},
            {"page_type": "content", "semantic": "architecture", "title": "教学治理架构", "bullets": ["校级层：顶层设计与资源统筹", "年级层：学段目标分解与执行跟踪", "学科层：教研协同与课程共建", "班级层：个体支持与学习闭环"]},
            {"page_type": "data", "semantic": "compare", "title": "改革前后教学效果对比", "bullets": ["课堂参与度：由被动听讲转向主动探究", "作业质量：由重复训练转向高阶任务", "学习表现：由单点分数转向综合能力", "教师协同：由孤立备课转向团队共创"]},
            {"page_type": "content", "semantic": "risk", "title": "推进风险与应对策略", "bullets": ["教师负荷上升：分阶段导入与工具支持", "资源不均衡：共享课程包与示范课机制", "评价口径不统一：建立标准与校准流程", "家校认知差异：强化沟通与结果可视化"]},
            {"page_type": "content", "semantic": "modern", "title": "数字化教学能力建设", "bullets": ["数据平台：沉淀学习过程与行为数据", "资源平台：统一素材、题库与活动模板", "教研平台：沉淀最佳实践与共性问题", "运营平台：跟踪质量指标与改进进度"]},
            {"page_type": "content", "semantic": "culture", "title": "校园文化与价值导向", "bullets": ["共同愿景：形成一致的育人价值", "行为规范：将价值观落地为日常行动", "教师文化：强化专业成长与协作精神", "学生文化：提升责任感与自主学习能力"]},
        ]
    return [
        {"page_type": "content", "semantic": "process", "title": "实施路径与阶段目标", "bullets": ["阶段一：明确目标与业务边界", "阶段二：搭建能力与治理机制", "阶段三：试点验证并沉淀标准", "阶段四：规模化推广与持续优化"]},
        {"page_type": "data", "semantic": "modern", "title": "关键指标趋势分析", "bullets": ["Q1：12", "Q2：18", "Q3：27", "Q4：35"]},
        {"page_type": "data", "semantic": "modern", "title": "业务转化漏斗", "bullets": ["线索：1000", "商机：420", "报价：230", "成交：96"]},
        {"page_type": "data", "semantic": "compare", "title": "现状与目标对比", "bullets": ["效率：流程时长与吞吐能力对比", "质量：错误率与稳定性对比", "成本：人力投入与运营成本对比", "价值：客户体验与业务产出对比"]},
        {"page_type": "content", "semantic": "architecture", "title": "能力架构与模块设计", "bullets": ["应用层：场景化能力封装与复用", "服务层：流程编排与规则执行引擎", "数据层：统一数据模型与指标口径", "底座层：安全、权限、监控与运维"]},
        {"page_type": "content", "semantic": "risk", "title": "风险识别与缓释机制", "bullets": ["组织风险：跨部门协同不足", "数据风险：口径不一致与质量波动", "技术风险：系统集成复杂度上升", "经营风险：投入产出周期不匹配"]},
        {"page_type": "content", "semantic": "culture", "title": "组织能力与文化保障", "bullets": ["机制保障：明确职责与协作接口", "人才保障：建立培训与激励体系", "流程保障：规范关键流程与SOP", "文化保障：数据驱动与持续改进共识"]},
    ]


def _augment_outline_if_needed(theme: str, pages: list[dict[str, Any]]) -> None:
    if len(pages) < 6:
        return
    middle = pages[2:-1]
    if not middle:
        return
    weak_count = 0
    for page in middle:
        title = str(page.get("title") or "")
        bullets = [str(x) for x in page.get("bullets", []) if str(x).strip()]
        semantic = str(page.get("semantic") or "generic")
        weak_title = _is_placeholder_title(title)
        weak_bullets = (len(bullets) < 3) or all(_is_placeholder_bullet(x) for x in bullets)
        if semantic == "generic" and (weak_title or weak_bullets):
            weak_count += 1
    if weak_count < max(2, len(middle) // 2):
        return

    blueprint = _blueprint_for_domain(_detect_domain(theme))
    if not blueprint:
        return

    for idx, page in enumerate(middle):
        block = blueprint[idx % len(blueprint)]
        title = str(page.get("title") or "")
        bullets = [str(x) for x in page.get("bullets", []) if str(x).strip()]
        semantic = str(page.get("semantic") or "generic")
        if _is_placeholder_title(title) or semantic == "generic":
            page["title"] = block["title"]
        if (len(bullets) < 3) or all(_is_placeholder_bullet(x) for x in bullets):
            page["bullets"] = list(block["bullets"])
        if semantic == "generic":
            page["semantic"] = block["semantic"]
        if page.get("page_type") not in {"cover", "agenda", "summary", "ending"}:
            page["page_type"] = block["page_type"]


def _specialize_page_semantics(page: dict[str, Any]) -> dict[str, Any]:
    title = str(page.get("title") or "")
    bullets = [str(x) for x in page.get("bullets", []) if str(x).strip()]
    text = f"{title} {' '.join(bullets)}".lower()

    # Semantic tags are generic building blocks, not topic hard-codes.
    semantic = "generic"
    if any(k in text for k in ["对比", "比较", "差异", "现状vs", "versus", "comparison", "before after"]):
        semantic = "compare"
    elif any(k in text for k in ["流程", "路径", "步骤", "阶段推进", "process", "workflow", "roadmap"]):
        semantic = "process"
    elif any(k in text for k in ["风险", "挑战", "问题", "瓶颈", "risk", "issue", "challenge"]):
        semantic = "risk"
    elif any(k in text for k in ["架构", "系统", "模块", "平台", "architecture", "module", "system"]):
        semantic = "architecture"
    elif any(k in text for k in ["时间线", "timeline", "历程", "里程碑"]):
        semantic = "timeline"
    elif bool(re.search(r"\b(19|20)\d{2}\b", text)):
        semantic = "timeline"
    elif any(k in text for k in ["人物", "团队", "角色", "person", "people"]):
        semantic = "figures"
    elif any(k in text for k in ["地标", "地图", "区域", "landmark", "map"]):
        semantic = "landmarks"
    elif any(k in text for k in ["文化", "价值观", "文脉", "culture", "values"]):
        semantic = "culture"
    elif any(k in text for k in ["现代", "发展", "增长", "指标", "modern", "growth", "kpi"]):
        semantic = "modern"

    page["semantic"] = semantic
    return page


def _infer_viz_intent(page: dict[str, Any]) -> str:
    page_type = str(page.get("page_type", "content"))
    semantic = str(page.get("semantic", "generic"))
    title = str(page.get("title", "")).lower()
    bullets = [str(x).lower() for x in page.get("bullets", []) if str(x).strip()]
    text = f"{title} {' '.join(bullets)}"
    number_hits = sum(len(re.findall(r"\d+", b)) for b in bullets)

    if page_type == "cover":
        return "hero"
    if page_type == "ending":
        return "ending"
    if page_type == "agenda":
        return "roadmap"
    if page_type == "summary":
        return "takeaway"
    if semantic == "timeline":
        return "timeline"
    if semantic == "process":
        return "process"
    if semantic == "compare":
        return "compare"
    if semantic == "risk":
        return "risk-matrix"
    if semantic == "architecture":
        return "architecture"
    if any(k in text for k in ["矩阵", "象限", "matrix", "quadrant"]):
        return "matrix"
    if any(k in text for k in ["漏斗", "转化", "转化率", "funnel", "conversion"]):
        return "funnel"
    if any(k in text for k in ["趋势", "变化", "同比", "环比", "trend", "growth"]):
        return "trend"
    if any(k in text for k in ["投入", "产出", "净收益", "roi", "增量", "减量"]) and number_hits >= 2:
        return "waterfall"
    if any(k in text for k in ["表格", "清单", "对照"]) and page_type == "data":
        return "table"
    if page_type == "data" and number_hits >= 2:
        return "bar"
    return "cards"


def _required_intents_from_theme(theme: str) -> list[str]:
    t = theme.lower()
    required: list[str] = []
    mapping = [
        (["时间线", "timeline", "里程碑", "历程"], "timeline"),
        (["流程", "路径", "roadmap", "workflow"], "process"),
        (["对比", "比较", "差异", "vs", "versus"], "compare"),
        (["架构", "系统", "architecture"], "architecture"),
        (["趋势", "同比", "环比", "trend", "growth"], "trend"),
        (["漏斗", "转化", "conversion", "funnel"], "funnel"),
        (["风险", "挑战", "risk"], "risk-matrix"),
        (["投入产出", "roi", "净收益"], "waterfall"),
    ]
    for keys, intent in mapping:
        if any(k in t for k in keys):
            required.append(intent)
    return required


def _intent_default_semantic(intent: str) -> str:
    return {
        "timeline": "timeline",
        "process": "process",
        "compare": "compare",
        "architecture": "architecture",
        "trend": "modern",
        "funnel": "modern",
        "risk-matrix": "risk",
        "waterfall": "modern",
    }.get(intent, "generic")


def _rebalance_viz_intents(theme: str, pages: list[dict[str, Any]]) -> None:
    if len(pages) < 6:
        return
    required = _required_intents_from_theme(theme)
    if not required:
        return
    existing = {str(p.get("viz_intent", "")) for p in pages}
    missing = [x for x in required if x not in existing]
    if not missing:
        return

    candidates = pages[2:-1]
    if not candidates:
        return

    for intent in missing:
        target = next(
            (
                p
                for p in candidates
                if str(p.get("viz_intent", "")) in {"cards", "bar", "table"}
                and str(p.get("page_type", "content")) in {"content", "data"}
            ),
            None,
        )
        if target is None:
            target = next((p for p in candidates if str(p.get("page_type", "content")) in {"content", "data"}), None)
        if target is None:
            break
        target["viz_intent"] = intent
        if str(target.get("semantic", "generic")) == "generic":
            target["semantic"] = _intent_default_semantic(intent)
        if intent in {"trend", "funnel", "waterfall"}:
            target["page_type"] = "data"


def _apply_semantic_labels(pages: list[dict[str, Any]], labels: list[dict[str, str]]) -> list[dict[str, Any]]:
    allowed = {
        "timeline",
        "process",
        "compare",
        "risk",
        "architecture",
        "figures",
        "landmarks",
        "culture",
        "modern",
        "generic",
    }
    lookup = {}
    for item in labels:
        pid = str(item.get("id", "")).strip()
        sem = str(item.get("semantic", "")).strip()
        if pid and sem in allowed:
            lookup[pid] = sem
    for page in pages:
        pid = str(page.get("id", ""))
        if pid in lookup:
            page["semantic"] = lookup[pid]
    return pages


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


def enrich_semantics_with_llm(theme: str, plan: dict[str, Any]) -> dict[str, Any]:
    """Best-effort semantic labeling via LLM. Falls back silently to rule labels."""
    pages = plan.get("pages", [])
    if not isinstance(pages, list) or not pages:
        return plan
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        model = build_chat_model()
        compact_pages = [
            {
                "id": p.get("id"),
                "page_type": p.get("page_type"),
                "title": p.get("title"),
                "bullets": p.get("bullets", [])[:4],
            }
            for p in pages
        ]
        system = SystemMessage(
            content=(
                "你是演示文稿语义标签器。输出严格JSON，不要额外文本。"
                "可选semantic仅限: timeline, process, compare, risk, architecture, figures, landmarks, culture, modern, generic。"
                "返回结构: {\"labels\":[{\"id\":\"01\",\"semantic\":\"timeline\"}, ...]}"
            )
        )
        user = HumanMessage(content=json.dumps({"theme": theme, "pages": compact_pages}, ensure_ascii=False))
        response = model.invoke([system, user])
        parsed = _extract_json(getattr(response, "content", "") or "")
        labels = parsed.get("labels", []) if isinstance(parsed, dict) else []
        if isinstance(labels, list):
            _apply_semantic_labels(pages, labels)
            for page in pages:
                page["viz_intent"] = _infer_viz_intent(page)
            _rebalance_viz_intents(theme, pages)
    except Exception:
        # Keep existing rule-based semantic tags.
        pass
    return plan


def normalize_plan(plan: dict[str, Any], target_pages: int) -> dict[str, Any]:
    pages = plan.get("pages", [])
    if not isinstance(pages, list):
        pages = []
    normalized = [p for p in pages if isinstance(p, dict)]
    if not normalized:
        normalized = [_fallback_page(i) for i in range(1, target_pages + 1)]

    if len(normalized) > target_pages:
        normalized = normalized[:target_pages]
    elif len(normalized) < target_pages:
        for i in range(len(normalized) + 1, target_pages + 1):
            normalized.append(_fallback_page(i))

    normalized[0]["page_type"] = "cover"
    normalized[0]["id"] = "01"
    if len(normalized) >= 2 and normalized[1].get("page_type") != "agenda":
        normalized[1]["page_type"] = "agenda"
    if normalized[-1].get("page_type") not in {"summary", "ending"}:
        normalized[-1]["page_type"] = "summary"

    for i, raw in enumerate(normalized, start=1):
        page = raw
        page["id"] = f"{i:02d}"
        page["title"] = str(page.get("title") or f"第{i}页")
        page_type = str(page.get("page_type") or "content")
        if page_type not in {"cover", "agenda", "content", "data", "summary", "ending"}:
            page_type = "content"
        page["page_type"] = page_type
        bullets = page.get("bullets", [])
        if not isinstance(bullets, list):
            bullets = [str(bullets)]
        page["bullets"] = [str(x) for x in bullets[:6]] or [page["title"]]
        _specialize_page_semantics(page)

    _augment_outline_if_needed(str(plan.get("theme") or ""), normalized)
    for page in normalized:
        _specialize_page_semantics(page)
        page["viz_intent"] = _infer_viz_intent(page)
    _rebalance_viz_intents(str(plan.get("theme") or ""), normalized)

    plan["pages"] = normalized
    return plan


def build_page_rhythm(pages: list[dict[str, Any]]) -> dict[str, str]:
    rhythm: dict[str, str] = {}
    for idx, page in enumerate(pages, start=1):
        key = f"P{idx:02d}"
        page_type = page.get("page_type", "content")
        semantic = page.get("semantic", "generic")
        if page_type in {"cover", "agenda", "ending"}:
            rhythm[key] = "anchor"
        elif page_type == "summary":
            rhythm[key] = "breathing"
        elif semantic in {"timeline", "culture"}:
            rhythm[key] = "breathing"
        elif semantic in {"modern", "landmarks", "figures", "architecture", "process", "compare", "risk"}:
            rhythm[key] = "dense"
        elif idx % 4 == 0 and page_type == "content":
            rhythm[key] = "breathing"
        else:
            rhythm[key] = "dense"
    return rhythm


def detect_style_profile(theme: str, pages: list[dict[str, Any]]) -> str:
    t = theme.lower()
    has_history_kw = any(k in t for k in ["历史", "文脉", "文化", "古", "heritage", "history"])
    has_tech_kw = any(k in t for k in ["科技", "数字化", "ai", "智能", "tech", "digital"])
    history_semantics = {str(p.get("semantic", "")) for p in pages}
    history_hits = sum(1 for p in pages if str(p.get("semantic", "")) in {"timeline", "culture", "figures", "landmarks"})
    tech_hits = sum(
        1
        for p in pages
        if str(p.get("semantic", "")) in {"process", "compare", "architecture", "modern", "risk"}
    )
    if has_tech_kw:
        return "tech-cyan"
    if has_history_kw:
        return "history-ink"
    has_history_combo = "timeline" in history_semantics and bool(
        history_semantics.intersection({"culture", "figures", "landmarks"})
    )
    if has_history_combo and history_hits >= 3 and tech_hits <= 2:
        return "history-ink"
    if tech_hits >= 4:
        return "tech-cyan"
    return "business-blue"


def build_spec_lock(theme: str, pages: list[dict[str, Any]]) -> dict[str, Any]:
    profile_id = detect_style_profile(theme, pages)
    profile = STYLE_PROFILES.get(profile_id, STYLE_PROFILES["business-blue"])
    return {
        "theme": theme,
        "style_profile": profile_id,
        "style_profile_name": profile["name"],
        "canvas": {"width": 1280, "height": 720, "viewBox": "0 0 1280 720"},
        "colors": dict(profile["colors"]),
        "typography": dict(profile["typography"]),
        "icons": {"library": "chunk-filled", "inventory": []},
        "images": [],
        "page_rhythm": build_page_rhythm(pages),
    }


def render_spec_lock_markdown(spec_lock: dict[str, Any]) -> str:
    return (
        "# spec_lock\n\n"
        "```json\n"
        f"{json.dumps(spec_lock, ensure_ascii=False, indent=2)}\n"
        "```\n"
    )


def render_design_spec_markdown(theme: str, plan: dict[str, Any], spec_lock: dict[str, Any]) -> str:
    pages = plan.get("pages", [])
    lines = [
        "# Design Spec",
        "",
        f"- Theme: {theme}",
        f"- Canvas: 1280x720",
        f"- Page Count: {len(pages)}",
        "",
        "## Visual Theme",
        "",
        f"- Style Profile: {spec_lock.get('style_profile', 'business-blue')} ({spec_lock.get('style_profile_name', '商务专业蓝')})",
        f"- Style: {STYLE_PROFILES.get(spec_lock.get('style_profile', 'business-blue'), STYLE_PROFILES['business-blue'])['visual_style']}",
        f"- Color System: {STYLE_PROFILES.get(spec_lock.get('style_profile', 'business-blue'), STYLE_PROFILES['business-blue'])['color_desc']}",
        "",
        "## Typography",
        "",
        f"- Font: {spec_lock['typography']['font_family']}",
        f"- Title: {spec_lock['typography']['title']}px",
        f"- Body: {spec_lock['typography']['body']}px",
        "",
        "## Content Outline",
        "",
    ]
    rhythm = spec_lock.get("page_rhythm", {})
    for idx, page in enumerate(pages, start=1):
        key = f"P{idx:02d}"
        lines.append(
            f"- P{idx:02d} | {page.get('page_type')} | {page.get('semantic', 'generic')} | {rhythm.get(key, 'dense')} | {page.get('title')}"
        )
    lines.append("")
    return "\n".join(lines)


def write_strategy_files(project_dir: Path, theme: str, plan: dict[str, Any]) -> dict[str, Any]:
    pages = plan.get("pages", [])
    spec_lock = build_spec_lock(theme, pages)
    design_spec_text = render_design_spec_markdown(theme, plan, spec_lock)
    spec_lock_text = render_spec_lock_markdown(spec_lock)
    design_spec_path = project_dir / "design_spec.md"
    spec_lock_path = project_dir / "spec_lock.md"
    design_spec_path.write_text(design_spec_text, encoding="utf-8")
    spec_lock_path.write_text(spec_lock_text, encoding="utf-8")
    return {
        "spec_lock": spec_lock,
        "design_spec_path": str(design_spec_path),
        "spec_lock_path": str(spec_lock_path),
    }
