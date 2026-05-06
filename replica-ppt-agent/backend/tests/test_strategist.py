from app.strategist import _apply_semantic_labels, build_spec_lock, infer_target_pages, normalize_plan


def test_infer_target_pages_from_prompt() -> None:
    assert infer_target_pages("介绍上海历史，10页") == 10
    assert infer_target_pages("做一份报告") == 8
    assert infer_target_pages("做25页", default=8) == 20


def test_normalize_plan_respects_target_pages() -> None:
    plan = {
        "pages": [
            {"id": "01", "page_type": "cover", "title": "封面", "bullets": ["A"]},
            {"id": "02", "page_type": "content", "title": "正文", "bullets": ["B"]},
        ]
    }
    normalized = normalize_plan(plan, 6)
    assert len(normalized["pages"]) == 6
    assert normalized["pages"][0]["page_type"] == "cover"
    assert normalized["pages"][-1]["page_type"] in {"summary", "ending"}


def test_spec_lock_contains_page_rhythm() -> None:
    pages = [
        {"id": "01", "page_type": "cover"},
        {"id": "02", "page_type": "content"},
        {"id": "03", "page_type": "summary"},
    ]
    lock = build_spec_lock("theme", pages)
    assert lock["page_rhythm"]["P01"] == "anchor"
    assert lock["page_rhythm"]["P02"] == "dense"
    assert lock["page_rhythm"]["P03"] == "breathing"


def test_spec_lock_style_profile_detects_history() -> None:
    pages = [
        {"id": "01", "page_type": "cover", "semantic": "generic"},
        {"id": "02", "page_type": "content", "semantic": "timeline"},
        {"id": "03", "page_type": "content", "semantic": "culture"},
    ]
    lock = build_spec_lock("上海历史介绍", pages)
    assert lock["style_profile"] == "history-ink"
    assert lock["colors"]["primary"] == "#6B3E26"


def test_semantic_tagging_is_generic() -> None:
    plan = {
        "theme": "介绍某城市发展，10页",
        "pages": [
            {"id": "01", "page_type": "cover", "title": "封面", "bullets": ["主题"]},
            {"id": "02", "page_type": "content", "title": "关键时间线", "bullets": ["1990", "2000"]},
            {"id": "03", "page_type": "content", "title": "核心人物", "bullets": ["人物A", "人物B"]},
            {"id": "04", "page_type": "content", "title": "城市地标", "bullets": ["地标A"]},
            {"id": "05", "page_type": "content", "title": "文化传承", "bullets": ["文化点"]},
            {"id": "06", "page_type": "data", "title": "发展指标", "bullets": ["增长 20%"]},
            {"id": "07", "page_type": "content", "title": "实施流程", "bullets": ["步骤A"]},
            {"id": "08", "page_type": "content", "title": "方案对比", "bullets": ["A优于B"]},
            {"id": "09", "page_type": "content", "title": "系统架构与风险", "bullets": ["风险控制"]},
            {"id": "10", "page_type": "summary", "title": "总结", "bullets": ["结论"]},
        ],
    }
    normalized = normalize_plan(plan, 10)["pages"]
    assert normalized[1]["semantic"] == "timeline"
    assert normalized[2]["semantic"] == "figures"
    assert normalized[3]["semantic"] == "landmarks"
    assert normalized[4]["semantic"] == "culture"
    assert normalized[5]["semantic"] == "modern"
    assert normalized[6]["semantic"] == "process"
    assert normalized[7]["semantic"] == "compare"
    assert normalized[8]["semantic"] in {"architecture", "risk"}
    assert normalized[6]["viz_intent"] == "process"
    assert normalized[7]["viz_intent"] == "compare"
    assert normalized[9]["viz_intent"] in {"takeaway", "ending"}


def test_viz_intent_detects_trend_and_funnel() -> None:
    plan = {
        "theme": "运营分析，8页",
        "pages": [
            {"id": "01", "page_type": "cover", "title": "封面", "bullets": ["主题"]},
            {"id": "02", "page_type": "agenda", "title": "目录", "bullets": ["A", "B"]},
            {"id": "03", "page_type": "data", "title": "季度趋势分析", "bullets": ["Q1 12", "Q2 18", "Q3 26", "Q4 35"]},
            {"id": "04", "page_type": "data", "title": "转化漏斗", "bullets": ["线索 1000", "MQL 620", "SQL 360", "成交 88"]},
            {"id": "05", "page_type": "content", "title": "实施路径", "bullets": ["步骤A", "步骤B"]},
            {"id": "06", "page_type": "content", "title": "方案对比", "bullets": ["A vs B"]},
            {"id": "07", "page_type": "content", "title": "架构设计", "bullets": ["模块一"]},
            {"id": "08", "page_type": "summary", "title": "总结", "bullets": ["结论"]},
        ],
    }
    normalized = normalize_plan(plan, 8)["pages"]
    assert normalized[2]["viz_intent"] == "trend"
    assert normalized[3]["viz_intent"] == "funnel"


def test_theme_required_intents_are_rebalanced() -> None:
    plan = {
        "theme": "企业转型汇报，10页，包含趋势、漏斗、架构、对比",
        "pages": [{"id": f"{i:02d}", "page_type": "content", "title": f"第{i}页", "bullets": ["关键观点"]} for i in range(1, 11)],
    }
    normalized = normalize_plan(plan, 10)["pages"]
    intents = {str(p.get("viz_intent", "")) for p in normalized}
    assert "trend" in intents
    assert "funnel" in intents
    assert "architecture" in intents
    assert "compare" in intents


def test_apply_semantic_labels_overrides_when_valid() -> None:
    pages = [
        {"id": "01", "semantic": "generic"},
        {"id": "02", "semantic": "generic"},
    ]
    labels = [{"id": "01", "semantic": "timeline"}, {"id": "02", "semantic": "invalid"}]
    out = _apply_semantic_labels(pages, labels)
    assert out[0]["semantic"] == "timeline"
    assert out[1]["semantic"] == "generic"


def test_outline_auto_augmentation_for_weak_history_plan() -> None:
    plan = {
        "theme": "介绍上海历史，10页",
        "pages": [{"id": f"{i:02d}", "page_type": "content", "title": f"第{i}页", "bullets": [f"关键观点{i}-1"]} for i in range(1, 11)],
    }
    normalized = normalize_plan(plan, 10)["pages"]
    middle = normalized[2:-1]
    assert any(p.get("semantic") in {"timeline", "figures", "landmarks", "culture"} for p in middle)
    assert any(p.get("semantic") in {"compare", "architecture", "risk"} for p in middle)
    assert all(not str(p.get("title", "")).startswith("第") for p in middle[:3])
    assert all("viz_intent" in p for p in normalized)
