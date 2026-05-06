from __future__ import annotations

from pathlib import Path
import re

from bs4 import BeautifulSoup

STYLE_COLOR_REPLACEMENTS: dict[str, dict[str, str]] = {
    "business-blue": {},
    "history-ink": {
        "#F8FAFC": "#F7F2E9",
        "#F7FAFF": "#F5EFE4",
        "#F1F5F9": "#EEE5D8",
        "#EEF2FF": "#E8DECF",
        "#EFF6FF": "#EFE6DA",
        "#FFFFFF": "#FFFDF8",
        "#0B1220": "#2F241F",
        "#1E3A8A": "#6B3E26",
        "#2563EB": "#A16207",
        "#1D4ED8": "#854D0E",
        "#0EA5E9": "#B45309",
        "#60A5FA": "#CA8A04",
        "#93C5FD": "#D6B56C",
        "#1E40AF": "#7C2D12",
        "#0F172A": "#2E1F18",
        "#334155": "#5B4638",
        "#1E293B": "#4A372C",
        "#CBD5E1": "#CDBBA6",
        "#DBEAFE": "#DFCDB6",
        "#E2E8F0": "#E7DCCB",
        "#BFDBFE": "#E7D8C1",
    },
    "tech-cyan": {
        "#F8FAFC": "#F4F8FF",
        "#F7FAFF": "#EEF4FF",
        "#F1F5F9": "#E7EEFB",
        "#EEF2FF": "#DFEAFF",
        "#EFF6FF": "#EAF4FF",
        "#FFFFFF": "#FFFFFF",
        "#0B1220": "#0A1022",
        "#1E3A8A": "#1E1B4B",
        "#2563EB": "#0284C7",
        "#1D4ED8": "#0369A1",
        "#0EA5E9": "#06B6D4",
        "#60A5FA": "#38BDF8",
        "#93C5FD": "#7DD3FC",
        "#1E40AF": "#0F172A",
        "#0F172A": "#0B132B",
        "#334155": "#1F3A5F",
        "#1E293B": "#1E293B",
        "#CBD5E1": "#BFD6F1",
        "#DBEAFE": "#D6E8FF",
        "#E2E8F0": "#DCEAF8",
        "#BFDBFE": "#BAE6FD",
    },
}


def _escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _char_width(ch: str, font_size: int) -> float:
    # Approximate glyph width for deterministic server-side wrapping.
    if ch == " ":
        return font_size * 0.33
    if ord(ch) < 128:
        return font_size * 0.56
    return font_size * 0.95


def _truncate_to_width(text: str, max_width: float, font_size: int) -> str:
    width = 0.0
    out = []
    for ch in text:
        cw = _char_width(ch, font_size)
        if width + cw > max_width:
            break
        out.append(ch)
        width += cw
    result = "".join(out).rstrip()
    if result != text.strip():
        # Add ellipsis if truncated.
        while result and sum(_char_width(c, font_size) for c in (result + "…")) > max_width:
            result = result[:-1]
        result = (result.rstrip() + "…") if result else "…"
    return result


def _wrap_text(text: str, max_width: float, font_size: int, max_lines: int) -> list[str]:
    raw_lines = [segment.strip() for segment in text.split("\n") if segment.strip()]
    if not raw_lines:
        return []
    wrapped: list[str] = []
    for raw in raw_lines:
        current = ""
        width = 0.0
        for ch in raw:
            cw = _char_width(ch, font_size)
            if width + cw > max_width and current:
                wrapped.append(current.rstrip())
                current = ch
                width = cw
                if len(wrapped) >= max_lines:
                    break
            else:
                current += ch
                width += cw
        if len(wrapped) >= max_lines:
            break
        if current.strip():
            wrapped.append(current.rstrip())
        if len(wrapped) >= max_lines:
            break

    if len(wrapped) > max_lines:
        wrapped = wrapped[:max_lines]
    if wrapped and len(wrapped) == max_lines:
        # Detect possible truncation and force final-line ellipsis when needed.
        original_flat = " ".join(raw_lines)
        wrapped_flat = " ".join(wrapped).replace("…", "")
        if len(original_flat) > len(wrapped_flat):
            wrapped[-1] = _truncate_to_width(wrapped[-1], max_width, font_size)
    return wrapped


def _render_text_block(
    x: int,
    y: int,
    text: str,
    *,
    max_width: int,
    font_size: int,
    line_height: int,
    max_lines: int,
    fill: str,
    font_weight: str = "400",
) -> str:
    lines = _wrap_text(text, max_width=max_width, font_size=font_size, max_lines=max_lines)
    if not lines:
        return ""
    parts = []
    for i, line in enumerate(lines):
        parts.append(
            f'<text x="{x}" y="{y + i * line_height}" font-size="{font_size}" '
            f'fill="{fill}" font-weight="{font_weight}" font-family="Arial, Microsoft YaHei">'
            f"{_escape_xml(line)}</text>"
        )
    return "".join(parts)


def _replace_hex_color(content: str, old_hex: str, new_hex: str) -> str:
    pattern = re.compile(re.escape(old_hex), re.IGNORECASE)
    return pattern.sub(new_hex, content)


def _apply_style_profile(body: str, style_profile: str) -> str:
    replacements = STYLE_COLOR_REPLACEMENTS.get(style_profile, {})
    if not replacements:
        return body
    out = body
    for old_hex, new_hex in replacements.items():
        out = _replace_hex_color(out, old_hex, new_hex)
    return out


def _render_cover(title: str, subtitle: str) -> str:
    title_block = _render_text_block(
        130,
        250,
        title,
        max_width=920,
        font_size=58,
        line_height=72,
        max_lines=2,
        fill="#0F172A",
        font_weight="700",
    )
    subtitle_block = _render_text_block(
        130,
        360,
        subtitle,
        max_width=900,
        font_size=28,
        line_height=38,
        max_lines=3,
        fill="#334155",
    )
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F7FAFF"/>
<rect x="0" y="0" width="1280" height="16" fill="#1D4ED8"/>
<rect x="0" y="690" width="1280" height="30" fill="#0F172A"/>
<rect x="70" y="110" width="1140" height="500" rx="24" fill="#FFFFFF" stroke="#DBEAFE" stroke-width="2"/>
<circle cx="1110" cy="180" r="110" fill="#DBEAFE" fill-opacity="0.7"/>
<circle cx="980" cy="560" r="140" fill="#BFDBFE" fill-opacity="0.55"/>
{title_block}
{subtitle_block}
<text x="130" y="640" font-size="20" fill="#E2E8F0" font-family="Arial, Microsoft YaHei">Replica PPT Agent · AI Generated</text>
"""


def _render_cover_dark(title: str, subtitle: str) -> str:
    title_block = _render_text_block(
        120, 280, title, max_width=980, font_size=62, line_height=76, max_lines=2, fill="#F8FAFC", font_weight="700"
    )
    subtitle_block = _render_text_block(
        120, 410, subtitle, max_width=900, font_size=30, line_height=40, max_lines=2, fill="#CBD5E1"
    )
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#0F172A"/>
<rect x="0" y="0" width="1280" height="720" fill="url(#bggrad)"/>
<defs>
  <linearGradient id="bggrad" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#1E3A8A" stop-opacity="0.6"/>
    <stop offset="100%" stop-color="#0F172A" stop-opacity="0.2"/>
  </linearGradient>
</defs>
<circle cx="1080" cy="160" r="150" fill="#60A5FA" fill-opacity="0.20"/>
<circle cx="180" cy="650" r="220" fill="#2563EB" fill-opacity="0.24"/>
<rect x="80" y="120" width="1120" height="500" rx="28" fill="#0B1220" fill-opacity="0.45" stroke="#334155"/>
{title_block}
{subtitle_block}
"""


def _render_agenda(title: str, items: list[str]) -> str:
    item_svg = []
    top = 190
    for idx, item in enumerate(items[:6], start=1):
        y = top + (idx - 1) * 78
        item_svg.append(
            f"""
<rect x="140" y="{y}" width="1000" height="58" rx="12" fill="#FFFFFF" stroke="#E2E8F0"/>
<circle cx="180" cy="{y + 29}" r="18" fill="#1D4ED8"/>
<text x="173" y="{y + 36}" font-size="18" fill="#FFFFFF" font-weight="700" font-family="Arial, Microsoft YaHei">{idx}</text>
{_render_text_block(220, y + 38, item, max_width=880, font_size=28, line_height=34, max_lines=1, fill="#0F172A")}
"""
        )
    title_block = _render_text_block(
        90,
        62,
        title,
        max_width=1080,
        font_size=44,
        line_height=52,
        max_lines=1,
        fill="#FFFFFF",
        font_weight="700",
    )
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
<rect x="0" y="0" width="1280" height="96" fill="#0F172A"/>
{title_block}
{''.join(item_svg)}
"""


def _render_agenda_roadmap(title: str, items: list[str]) -> str:
    cards = []
    for idx, item in enumerate(items[:5], start=1):
        x = 110 + (idx - 1) * 220
        y = 260 + (idx % 2) * 60
        cards.append(
            f"""
<rect x="{x}" y="{y}" width="190" height="160" rx="16" fill="#FFFFFF" stroke="#CBD5E1"/>
<circle cx="{x + 30}" cy="{y + 30}" r="16" fill="#1D4ED8"/>
<text x="{x + 23}" y="{y + 36}" font-size="18" fill="#FFFFFF" font-weight="700" font-family="Arial, Microsoft YaHei">{idx}</text>
{_render_text_block(x + 24, y + 84, item, max_width=150, font_size=22, line_height=30, max_lines=3, fill="#0F172A")}
"""
        )
        if idx < min(5, len(items)):
            nx = x + 196
            ny = y + 80
            cards.append(f'<line x1="{nx}" y1="{ny}" x2="{nx + 20}" y2="{ny}" stroke="#60A5FA" stroke-width="3"/>')
            cards.append(f'<polygon points="{nx + 20},{ny} {nx + 12},{ny - 5} {nx + 12},{ny + 5}" fill="#60A5FA"/>')
    title_block = _render_text_block(
        90, 70, title, max_width=1080, font_size=44, line_height=52, max_lines=1, fill="#FFFFFF", font_weight="700"
    )
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#EEF2FF"/>
<rect x="0" y="0" width="1280" height="110" fill="#1E3A8A"/>
{title_block}
{''.join(cards)}
"""


def _render_agenda_cards(title: str, items: list[str]) -> str:
    cards = []
    data = items[:6] if items else ["背景", "目标", "路径", "指标", "风险", "结论"]
    for i, item in enumerate(data):
        x = 110 + (i % 3) * 360
        y = 190 + (i // 3) * 220
        cards.append(f'<rect x="{x}" y="{y}" width="320" height="170" rx="16" fill="#FFFFFF" stroke="#DBEAFE"/>')
        cards.append(f'<rect x="{x}" y="{y}" width="320" height="46" rx="16" fill="#1E3A8A"/>')
        cards.append(_render_text_block(x + 20, y + 30, f"0{i+1}", max_width=40, font_size=18, line_height=20, max_lines=1, fill="#FFFFFF", font_weight="700"))
        cards.append(_render_text_block(x + 20, y + 102, item, max_width=280, font_size=24, line_height=30, max_lines=3, fill="#1E293B"))
    title_block = _render_text_block(90, 74, title, max_width=1080, font_size=44, line_height=52, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
{title_block}
{''.join(cards)}
"""


def _render_content(title: str, bullets: list[str]) -> str:
    left = bullets[::2][:3]
    right = bullets[1::2][:3]

    def _col_block(x: int, entries: list[str], accent: str) -> str:
        blocks = []
        for i, b in enumerate(entries):
            y = 180 + i * 150
            blocks.append(
                f"""
<rect x="{x}" y="{y}" width="500" height="120" rx="16" fill="#FFFFFF" stroke="#E2E8F0" />
<rect x="{x}" y="{y}" width="10" height="120" rx="6" fill="{accent}" />
{_render_text_block(x + 30, y + 52, b, max_width=450, font_size=24, line_height=34, max_lines=2, fill="#1E293B")}
"""
            )
        return "".join(blocks)
    title_block = _render_text_block(
        80,
        90,
        title,
        max_width=1120,
        font_size=48,
        line_height=56,
        max_lines=1,
        fill="#0F172A",
        font_weight="700",
    )

    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
{title_block}
<line x1="80" y1="118" x2="1200" y2="118" stroke="#CBD5E1" />
{_col_block(80, left, "#2563EB")}
{_col_block(700, right, "#0EA5E9")}
"""


def _render_content_steps(title: str, bullets: list[str]) -> str:
    steps = []
    for i, b in enumerate((bullets or ["步骤一", "步骤二", "步骤三"])[:5], start=1):
        y = 170 + (i - 1) * 102
        steps.append(
            f"""
<circle cx="140" cy="{y}" r="24" fill="#1D4ED8"/>
<text x="132" y="{y + 8}" font-size="22" fill="#FFFFFF" font-weight="700" font-family="Arial, Microsoft YaHei">{i}</text>
<line x1="140" y1="{y + 24}" x2="140" y2="{y + 78}" stroke="#93C5FD" stroke-width="3"/>
<rect x="190" y="{y - 36}" width="980" height="72" rx="12" fill="#FFFFFF" stroke="#DBEAFE"/>
{_render_text_block(220, y + 8, b, max_width=930, font_size=26, line_height=32, max_lines=2, fill="#1E293B")}
"""
        )
    title_block = _render_text_block(
        80, 92, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700"
    )
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
{title_block}
<line x1="80" y1="120" x2="1200" y2="120" stroke="#CBD5E1" />
{''.join(steps)}
"""


def _render_content_compare(title: str, bullets: list[str]) -> str:
    left = bullets[:3] if bullets else ["现状问题", "流程割裂", "效率瓶颈"]
    right = bullets[3:6] if len(bullets) > 3 else ["优化方向", "流程标准化", "自动化提效"]
    left_items = "".join(
        _render_text_block(130, 245 + i * 90, f"• {t}", max_width=430, font_size=24, line_height=30, max_lines=2, fill="#1E293B")
        for i, t in enumerate(left)
    )
    right_items = "".join(
        _render_text_block(720, 245 + i * 90, f"• {t}", max_width=430, font_size=24, line_height=30, max_lines=2, fill="#1E293B")
        for i, t in enumerate(right)
    )
    title_block = _render_text_block(
        80, 92, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700"
    )
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#FFFFFF"/>
{title_block}
<rect x="90" y="170" width="500" height="470" rx="18" fill="#F8FAFC" stroke="#E2E8F0"/>
<rect x="690" y="170" width="500" height="470" rx="18" fill="#EFF6FF" stroke="#BFDBFE"/>
<text x="130" y="220" font-size="32" fill="#0F172A" font-weight="700" font-family="Arial, Microsoft YaHei">现状</text>
<text x="720" y="220" font-size="32" fill="#1D4ED8" font-weight="700" font-family="Arial, Microsoft YaHei">目标</text>
{left_items}
{right_items}
"""


def _render_content_zigzag(title: str, bullets: list[str]) -> str:
    items = bullets[:5] if bullets else ["关键主题一", "关键主题二", "关键主题三", "关键主题四"]
    blocks = []
    for i, item in enumerate(items):
        y = 180 + i * 95
        left = i % 2 == 0
        x = 110 if left else 620
        accent = "#2563EB" if left else "#0EA5E9"
        blocks.append(f'<rect x="{x}" y="{y}" width="550" height="74" rx="14" fill="#FFFFFF" stroke="#DBEAFE"/>')
        blocks.append(f'<rect x="{x}" y="{y}" width="10" height="74" rx="6" fill="{accent}"/>')
        blocks.append(
            _render_text_block(x + 30, y + 46, item, max_width=500, font_size=24, line_height=30, max_lines=2, fill="#1E293B")
        )
        if i < len(items) - 1:
            nx = x + (550 if left else 0)
            tx = 620 if left else 660
            blocks.append(f'<line x1="{nx}" y1="{y + 74}" x2="{tx}" y2="{y + 95}" stroke="#93C5FD" stroke-width="3"/>')
    title_block = _render_text_block(
        80, 92, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700"
    )
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
{title_block}
{''.join(blocks)}
"""


def _render_content_matrix(title: str, bullets: list[str]) -> str:
    items = bullets[:4] if bullets else ["象限一", "象限二", "象限三", "象限四"]
    cards = []
    for i, item in enumerate(items):
        x = 140 + (i % 2) * 520
        y = 210 + (i // 2) * 210
        cards.append(f'<rect x="{x}" y="{y}" width="480" height="170" rx="16" fill="#FFFFFF" stroke="#CBD5E1"/>')
        cards.append(f'<circle cx="{x + 30}" cy="{y + 30}" r="10" fill="#1D4ED8"/>')
        cards.append(
            _render_text_block(x + 56, y + 38, f"维度{i + 1}", max_width=390, font_size=22, line_height=28, max_lines=1, fill="#1E3A8A", font_weight="700")
        )
        cards.append(_render_text_block(x + 28, y + 104, item, max_width=420, font_size=24, line_height=32, max_lines=2, fill="#1E293B"))
    title_block = _render_text_block(
        80, 92, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700"
    )
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F1F5F9"/>
{title_block}
<line x1="640" y1="190" x2="640" y2="630" stroke="#BFDBFE" stroke-width="2"/>
<line x1="120" y1="410" x2="1160" y2="410" stroke="#BFDBFE" stroke-width="2"/>
{''.join(cards)}
"""


def _render_data(title: str, rows: list[tuple[str, str]]) -> str:
    bars = []
    max_value = 1
    parsed_rows: list[tuple[str, str, int]] = []
    for k, v in rows[:5]:
        digits = re.findall(r"\d+", v)
        num = int(digits[0]) if digits else 10
        parsed_rows.append((k, v, num))
        max_value = max(max_value, num)

    for i, (k, v, n) in enumerate(parsed_rows):
        y = 200 + i * 90
        width = int(520 * n / max_value)
        bars.append(
            f"""
{_render_text_block(100, y + 28, k, max_width=160, font_size=24, line_height=30, max_lines=1, fill="#0F172A")}
<rect x="280" y="{y}" width="540" height="34" rx="8" fill="#E2E8F0"/>
<rect x="280" y="{y}" width="{width}" height="34" rx="8" fill="#2563EB"/>
{_render_text_block(840, y + 24, v, max_width=340, font_size=20, line_height=26, max_lines=2, fill="#1E293B", font_weight="700")}
"""
        )
    title_block = _render_text_block(
        90,
        76,
        title,
        max_width=1080,
        font_size=46,
        line_height=54,
        max_lines=1,
        fill="#FFFFFF",
        font_weight="700",
    )

    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#FFFFFF"/>
<rect x="0" y="0" width="1280" height="120" fill="#1E3A8A"/>
{title_block}
<rect x="70" y="150" width="1140" height="520" rx="18" fill="#F8FAFC" stroke="#DBEAFE"/>
{''.join(bars)}
"""


def _render_data_table_pro(title: str, rows: list[tuple[str, str]]) -> str:
    entries = rows[:6] if rows else [("指标", "说明"), ("效率", "提升 35%"), ("成本", "下降 18%"), ("周期", "缩短 28%")]
    table = []
    start_y = 220
    row_h = 68
    table.append('<rect x="90" y="190" width="1100" height="460" rx="16" fill="#FFFFFF" stroke="#CBD5E1"/>')
    table.append('<rect x="90" y="190" width="1100" height="72" rx="16" fill="#1E3A8A"/>')
    table.append(_render_text_block(130, 236, "维度", max_width=260, font_size=24, line_height=30, max_lines=1, fill="#FFFFFF", font_weight="700"))
    table.append(_render_text_block(430, 236, "核心结论", max_width=720, font_size=24, line_height=30, max_lines=1, fill="#FFFFFF", font_weight="700"))
    for i, (k, v) in enumerate(entries):
        y = start_y + i * row_h
        if i % 2 == 0:
            table.append(f'<rect x="90" y="{y}" width="1100" height="{row_h}" fill="#F8FAFC"/>')
        table.append(f'<line x1="390" y1="{y}" x2="390" y2="{y + row_h}" stroke="#E2E8F0"/>')
        table.append(_render_text_block(130, y + 44, k, max_width=240, font_size=22, line_height=28, max_lines=1, fill="#0F172A", font_weight="700"))
        table.append(_render_text_block(430, y + 44, v, max_width=710, font_size=22, line_height=28, max_lines=2, fill="#1E293B"))
        table.append(f'<line x1="90" y1="{y + row_h}" x2="1190" y2="{y + row_h}" stroke="#E2E8F0"/>')
    title_block = _render_text_block(
        90, 90, title, max_width=1080, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700"
    )
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
{title_block}
{''.join(table)}
"""


def _render_data_waterfall(title: str, rows: list[tuple[str, str]]) -> str:
    entries = rows[:5] if rows else [("投入", "20"), ("节省", "8"), ("增收", "14"), ("新增成本", "6"), ("净收益", "36")]
    parsed: list[tuple[str, int]] = []
    for k, v in entries:
        digits = re.findall(r"-?\d+", v)
        parsed.append((k, int(digits[0]) if digits else 10))
    max_abs = max(10, max(abs(v) for _, v in parsed))
    x = 150
    bars = []
    cum = 0
    for i, (k, v) in enumerate(parsed):
        is_last = i == len(parsed) - 1
        val = (cum + v) if is_last else v
        if not is_last:
            cum += v
        h = int(220 * abs(val) / max_abs)
        y = 470 - h
        color = "#2563EB" if val >= 0 else "#DC2626"
        bars.append(f'<rect x="{x}" y="{y}" width="160" height="{h}" rx="8" fill="{color}"/>')
        bars.append(_render_text_block(x + 20, 505, k, max_width=120, font_size=20, line_height=24, max_lines=2, fill="#1E293B"))
        bars.append(_render_text_block(x + 26, y - 12, str(val), max_width=110, font_size=20, line_height=24, max_lines=1, fill="#0F172A", font_weight="700"))
        if i < len(parsed) - 1:
            bars.append(f'<line x1="{x + 160}" y1="{y}" x2="{x + 190}" y2="{y}" stroke="#93C5FD" stroke-width="2"/>')
        x += 200
    title_block = _render_text_block(
        90, 90, title, max_width=1080, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700"
    )
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#FFFFFF"/>
{title_block}
<line x1="120" y1="470" x2="1160" y2="470" stroke="#CBD5E1" stroke-width="2"/>
{''.join(bars)}
"""


def _render_data_line_trend(title: str, rows: list[tuple[str, str]]) -> str:
    entries = rows[:6] if rows else [("Q1", "12"), ("Q2", "18"), ("Q3", "26"), ("Q4", "34"), ("Q5", "41")]
    parsed: list[tuple[str, int]] = []
    has_real_numbers = False
    for k, v in entries:
        digits = re.findall(r"-?\d+", v)
        if digits:
            parsed.append((k, int(digits[0])))
            has_real_numbers = True
        else:
            parsed.append((k, 0))
    if len(parsed) < 2:
        parsed = [("阶段1", 10), ("阶段2", 20), ("阶段3", 30)]
        has_real_numbers = True
    if not has_real_numbers:
        # No numeric signal from input: synthesize a smooth upward trend
        # so the slide still reads as a trend chart instead of a flat line.
        parsed = [(k, 18 + i * 8) for i, (k, _) in enumerate(parsed)]
    max_v = max(v for _, v in parsed)
    min_v = min(v for _, v in parsed)
    span = max(1, max_v - min_v)
    points: list[tuple[int, int, str, int]] = []
    for i, (k, v) in enumerate(parsed):
        x = 180 + int(i * (880 / (len(parsed) - 1)))
        y = 520 - int(((v - min_v) / span) * 240)
        points.append((x, y, k, v))
    poly = " ".join(f"{x},{y}" for x, y, _, _ in points)
    labels = []
    for x, y, k, v in points:
        labels.append(f'<circle cx="{x}" cy="{y}" r="8" fill="#2563EB"/>')
        labels.append(_render_text_block(x - 22, y - 16, str(v), max_width=44, font_size=18, line_height=20, max_lines=1, fill="#0F172A", font_weight="700"))
        labels.append(_render_text_block(x - 40, 560, k, max_width=80, font_size=18, line_height=20, max_lines=1, fill="#334155"))
    title_block = _render_text_block(90, 90, title, max_width=1080, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
{title_block}
<rect x="90" y="170" width="1100" height="460" rx="18" fill="#FFFFFF" stroke="#DBEAFE"/>
<line x1="150" y1="520" x2="1110" y2="520" stroke="#CBD5E1" stroke-width="2"/>
<line x1="150" y1="250" x2="150" y2="520" stroke="#CBD5E1" stroke-width="2"/>
<polyline points="{poly}" fill="none" stroke="#2563EB" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
{''.join(labels)}
"""


def _render_data_funnel(title: str, rows: list[tuple[str, str]]) -> str:
    entries = rows[:5] if rows else [("线索", "1000"), ("MQL", "640"), ("SQL", "360"), ("商机", "170"), ("成交", "82")]
    parsed: list[tuple[str, int]] = []
    for k, v in entries:
        digits = re.findall(r"-?\d+", v)
        parsed.append((k, max(1, int(digits[0]) if digits else 10)))
    top = max(v for _, v in parsed)
    blocks = []
    for i, (k, v) in enumerate(parsed):
        y = 210 + i * 80
        w = int(820 * (v / top))
        x = 640 - w // 2
        blocks.append(f'<rect x="{x}" y="{y}" width="{w}" height="62" rx="10" fill="#EFF6FF" stroke="#BFDBFE"/>')
        blocks.append(_render_text_block(x + 18, y + 38, k, max_width=260, font_size=22, line_height=28, max_lines=1, fill="#1E293B", font_weight="700"))
        blocks.append(_render_text_block(x + w - 120, y + 38, str(v), max_width=100, font_size=22, line_height=28, max_lines=1, fill="#1D4ED8", font_weight="700"))
        if i < len(parsed) - 1:
            nx = 640
            blocks.append(f'<line x1="{nx}" y1="{y + 62}" x2="{nx}" y2="{y + 80}" stroke="#93C5FD" stroke-width="3"/>')
    title_block = _render_text_block(90, 90, title, max_width=1080, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#FFFFFF"/>
{title_block}
<rect x="90" y="170" width="1100" height="470" rx="18" fill="#F8FAFC" stroke="#DBEAFE"/>
{''.join(blocks)}
"""


def _render_data_kpi_grid(title: str, rows: list[tuple[str, str]]) -> str:
    cards = []
    data = rows[:6] if rows else [("指标1", "35%"), ("指标2", "28%"), ("指标3", "18%"), ("指标4", "2.1x")]
    for i, (k, v) in enumerate(data):
        col = i % 3
        row = i // 3
        x = 100 + col * 360
        y = 190 + row * 210
        cards.append(
            f"""
<rect x="{x}" y="{y}" width="320" height="170" rx="16" fill="#FFFFFF" stroke="#DBEAFE"/>
{_render_text_block(x + 24, y + 48, k, max_width=270, font_size=24, line_height=30, max_lines=1, fill="#334155")}
{_render_text_block(x + 24, y + 118, v, max_width=270, font_size=46, line_height=52, max_lines=1, fill="#1D4ED8", font_weight="700")}
"""
        )
    title_block = _render_text_block(
        90, 80, title, max_width=1080, font_size=44, line_height=52, max_lines=1, fill="#0F172A", font_weight="700"
    )
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
{title_block}
<rect x="70" y="130" width="1140" height="530" rx="20" fill="#EFF6FF" stroke="#BFDBFE"/>
{''.join(cards)}
"""


def _render_summary(title: str, bullets: list[str]) -> str:
    quote = bullets[0] if bullets else "总结：聚焦高价值场景，分阶段推进，持续迭代。"
    points = bullets[1:4] if len(bullets) > 1 else ["聚焦价值", "规模复制", "持续优化"]
    points_svg = []
    for i, p in enumerate(points):
        y = 420 + i * 70
        points_svg.append(
            f"""
<circle cx="170" cy="{y - 14}" r="8" fill="#2563EB"/>
{_render_text_block(195, y - 6, p, max_width=920, font_size=28, line_height=34, max_lines=1, fill="#1E293B")}
"""
        )
    title_block = _render_text_block(
        90,
        100,
        title,
        max_width=1060,
        font_size=48,
        line_height=56,
        max_lines=1,
        fill="#0F172A",
        font_weight="700",
    )
    quote_block = _render_text_block(
        130,
        240,
        f"“{quote}”",
        max_width=1010,
        font_size=36,
        line_height=48,
        max_lines=2,
        fill="#0F172A",
    )
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F1F5F9"/>
{title_block}
<rect x="90" y="150" width="1100" height="220" rx="20" fill="#FFFFFF" stroke="#CBD5E1"/>
{quote_block}
{''.join(points_svg)}
"""


def _render_summary_grid(title: str, bullets: list[str]) -> str:
    items = bullets[:4] if bullets else ["聚焦高价值场景", "试点先行", "建立标准", "持续优化"]
    blocks = []
    for i, t in enumerate(items):
        x = 100 + (i % 2) * 560
        y = 190 + (i // 2) * 190
        blocks.append(
            f"""
<rect x="{x}" y="{y}" width="520" height="150" rx="16" fill="#FFFFFF" stroke="#CBD5E1"/>
{_render_text_block(x + 26, y + 88, t, max_width=470, font_size=30, line_height=38, max_lines=2, fill="#0F172A")}
"""
        )
    title_block = _render_text_block(
        90, 96, title, max_width=1080, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700"
    )
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F1F5F9"/>
{title_block}
{''.join(blocks)}
"""


def _render_summary_takeaway(title: str, bullets: list[str]) -> str:
    takeaway = bullets[0] if bullets else "以结果为导向，优先推进高价值场景。"
    actions = bullets[1:4] if len(bullets) > 1 else ["建立统一标准", "试点验证ROI", "形成规模复制机制"]
    action_svg = []
    for i, item in enumerate(actions, start=1):
        x = 130 + (i - 1) * 340
        action_svg.append(f'<rect x="{x}" y="430" width="300" height="170" rx="16" fill="#FFFFFF" stroke="#CBD5E1"/>')
        action_svg.append(f'<circle cx="{x + 34}" cy="462" r="12" fill="#1D4ED8"/>')
        action_svg.append(_render_text_block(x + 28, 468, str(i), max_width=12, font_size=16, line_height=18, max_lines=1, fill="#FFFFFF", font_weight="700"))
        action_svg.append(_render_text_block(x + 26, 530, item, max_width=250, font_size=24, line_height=30, max_lines=3, fill="#1E293B"))
    title_block = _render_text_block(
        90, 96, title, max_width=1080, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700"
    )
    takeaway_block = _render_text_block(
        130, 260, takeaway, max_width=1010, font_size=34, line_height=42, max_lines=3, fill="#0F172A", font_weight="700"
    )
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F1F5F9"/>
{title_block}
<rect x="100" y="180" width="1080" height="200" rx="20" fill="#FFFFFF" stroke="#DBEAFE"/>
{takeaway_block}
{''.join(action_svg)}
"""


def _render_ending(title: str, subtitle: str) -> str:
    title_block = _render_text_block(
        140,
        300,
        title,
        max_width=980,
        font_size=68,
        line_height=80,
        max_lines=2,
        fill="#FFFFFF",
        font_weight="700",
    )
    subtitle_block = _render_text_block(
        140,
        410,
        subtitle,
        max_width=960,
        font_size=30,
        line_height=40,
        max_lines=2,
        fill="#CBD5E1",
    )
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#0F172A"/>
<rect x="0" y="0" width="1280" height="720" fill="#1E293B" fill-opacity="0.4"/>
<circle cx="240" cy="140" r="180" fill="#334155" fill-opacity="0.35"/>
<circle cx="1080" cy="620" r="260" fill="#1E40AF" fill-opacity="0.25"/>
{title_block}
{subtitle_block}
"""


def _render_ending_light(title: str, subtitle: str) -> str:
    title_block = _render_text_block(
        120, 320, title, max_width=980, font_size=64, line_height=76, max_lines=2, fill="#0F172A", font_weight="700"
    )
    subtitle_block = _render_text_block(
        120, 430, subtitle, max_width=900, font_size=30, line_height=40, max_lines=2, fill="#334155"
    )
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
<rect x="0" y="0" width="1280" height="720" fill="url(#eg)"/>
<defs>
  <linearGradient id="eg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#DBEAFE" stop-opacity="0.55"/>
    <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0.8"/>
  </linearGradient>
</defs>
<circle cx="1120" cy="120" r="170" fill="#93C5FD" fill-opacity="0.25"/>
<circle cx="180" cy="650" r="220" fill="#BFDBFE" fill-opacity="0.35"/>
<rect x="80" y="130" width="1120" height="470" rx="26" fill="#FFFFFF" stroke="#BFDBFE"/>
{title_block}
{subtitle_block}
"""


def _render_history_timeline(title: str, bullets: list[str]) -> str:
    items = bullets[:5] if bullets else ["1292 设县", "1843 开埠", "1949 重构", "1990 浦东开发", "2010+ 全球化升级"]
    nodes = []
    for i, item in enumerate(items):
        x = 170 + i * 230
        y = 390 if i % 2 == 0 else 470
        nodes.append(f'<line x1="{x}" y1="360" x2="{x}" y2="{y-24}" stroke="#93C5FD" stroke-width="3"/>')
        nodes.append(f'<circle cx="{x}" cy="360" r="12" fill="#1D4ED8"/>')
        nodes.append(f'<rect x="{x - 96}" y="{y - 24}" width="192" height="92" rx="12" fill="#FFFFFF" stroke="#DBEAFE"/>')
        nodes.append(_render_text_block(x - 82, y + 18, item, max_width=164, font_size=20, line_height=26, max_lines=3, fill="#1E293B"))
    title_block = _render_text_block(80, 90, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
{title_block}
<line x1="120" y1="360" x2="1160" y2="360" stroke="#60A5FA" stroke-width="6"/>
{''.join(nodes)}
"""


def _render_timeline_modern(title: str, bullets: list[str]) -> str:
    items = bullets[:5] if bullets else ["阶段1", "阶段2", "阶段3", "阶段4", "阶段5"]
    nodes = []
    for i, item in enumerate(items):
        x = 130 + i * 245
        y = 360
        nodes.append(f'<circle cx="{x}" cy="{y}" r="14" fill="#1D4ED8"/>')
        nodes.append(f'<rect x="{x - 92}" y="{y + 36}" width="184" height="96" rx="12" fill="#FFFFFF" stroke="#DBEAFE"/>')
        nodes.append(_render_text_block(x - 78, y + 78, item, max_width=156, font_size=20, line_height=26, max_lines=3, fill="#1E293B"))
        nodes.append(f'<text x="{x - 10}" y="{y - 26}" font-size="18" fill="#1D4ED8" font-weight="700" font-family="Arial, Microsoft YaHei">P{i + 1}</text>')
        if i < len(items) - 1:
            nx = x + 14
            nodes.append(f'<line x1="{nx}" y1="{y}" x2="{nx + 217}" y2="{y}" stroke="#60A5FA" stroke-width="4"/>')
            nodes.append(f'<polygon points="{nx + 217},{y} {nx + 209},{y - 5} {nx + 209},{y + 5}" fill="#60A5FA"/>')
    title_block = _render_text_block(80, 92, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
{title_block}
<rect x="70" y="160" width="1140" height="460" rx="18" fill="#FFFFFF" stroke="#DBEAFE"/>
{''.join(nodes)}
"""


def _render_history_figures(title: str, bullets: list[str]) -> str:
    cards = []
    items = bullets[:3] if bullets else ["实业家群体推动近代工业", "思想文化人物塑造城市精神", "多元社会角色构建海派气质"]
    for i, item in enumerate(items):
        x = 90 + i * 390
        cards.append(f'<rect x="{x}" y="190" width="350" height="420" rx="20" fill="#FFFFFF" stroke="#DBEAFE"/>')
        cards.append(f'<circle cx="{x+175}" cy="275" r="58" fill="#BFDBFE"/>')
        cards.append(f'<rect x="{x+120}" y="340" width="110" height="8" rx="4" fill="#93C5FD"/>')
        cards.append(_render_text_block(x + 32, 395, item, max_width=286, font_size=23, line_height=31, max_lines=5, fill="#1E293B"))
    title_block = _render_text_block(80, 92, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#EEF2FF"/>
{title_block}
{''.join(cards)}
"""


def _render_history_landmarks(title: str, bullets: list[str]) -> str:
    left = bullets[:2] if bullets else ["外滩：近代金融与建筑风貌", "豫园：传统城市空间记忆"]
    right = bullets[2:4] if len(bullets) > 2 else ["南京路：商业活力与消费文化", "浦东：现代天际线与全球门户"]
    left_block = "".join(
        _render_text_block(110, 280 + i * 120, f"• {t}", max_width=460, font_size=24, line_height=30, max_lines=3, fill="#1E293B")
        for i, t in enumerate(left)
    )
    right_block = "".join(
        _render_text_block(710, 280 + i * 120, f"• {t}", max_width=460, font_size=24, line_height=30, max_lines=3, fill="#1E293B")
        for i, t in enumerate(right)
    )
    title_block = _render_text_block(80, 92, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
{title_block}
<rect x="80" y="160" width="520" height="470" rx="18" fill="#FFFFFF" stroke="#CBD5E1"/>
<rect x="680" y="160" width="520" height="470" rx="18" fill="#FFFFFF" stroke="#CBD5E1"/>
<rect x="100" y="190" width="480" height="70" rx="12" fill="#EFF6FF"/>
<rect x="700" y="190" width="480" height="70" rx="12" fill="#EFF6FF"/>
<text x="120" y="235" font-size="28" fill="#1D4ED8" font-weight="700" font-family="Arial, Microsoft YaHei">历史地标群 A</text>
<text x="720" y="235" font-size="28" fill="#1D4ED8" font-weight="700" font-family="Arial, Microsoft YaHei">历史地标群 B</text>
{left_block}
{right_block}
"""


def _render_history_modern(title: str, bullets: list[str]) -> str:
    items = bullets[:4] if bullets else ["金融中心建设", "航运枢纽提升", "科创产业集聚", "城市治理升级"]
    bars = []
    for i, item in enumerate(items):
        y = 220 + i * 110
        bars.append(_render_text_block(110, y + 28, item, max_width=260, font_size=24, line_height=30, max_lines=1, fill="#1E293B"))
        bars.append(f'<rect x="390" y="{y}" width="640" height="34" rx="8" fill="#E2E8F0"/>')
        bars.append(f'<rect x="390" y="{y}" width="{240 + i * 110}" height="34" rx="8" fill="#2563EB"/>')
    title_block = _render_text_block(80, 92, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#FFFFFF"/>
{title_block}
<rect x="80" y="160" width="1120" height="500" rx="20" fill="#F8FAFC" stroke="#DBEAFE"/>
{''.join(bars)}
"""


def _render_history_culture(title: str, bullets: list[str]) -> str:
    quote = bullets[0] if bullets else "海派文化是传统与现代、东方与西方交汇形成的城市文化表达。"
    points = bullets[1:4] if len(bullets) > 1 else ["中西交融", "商业活力", "公共精神"]
    chips = []
    for i, p in enumerate(points):
        x = 130 + i * 340
        chips.append(f'<rect x="{x}" y="460" width="300" height="86" rx="20" fill="#FFFFFF" stroke="#CBD5E1"/>')
        chips.append(_render_text_block(x + 30, 512, p, max_width=240, font_size=28, line_height=34, max_lines=1, fill="#1D4ED8", font_weight="700"))
    title_block = _render_text_block(80, 92, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    quote_block = _render_text_block(130, 250, f"“{quote}”", max_width=1010, font_size=34, line_height=46, max_lines=3, fill="#0F172A")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F1F5F9"/>
{title_block}
<rect x="100" y="180" width="1080" height="240" rx="24" fill="#FFFFFF" stroke="#DBEAFE"/>
{quote_block}
{''.join(chips)}
"""


def _render_semantic_process(title: str, bullets: list[str]) -> str:
    steps = bullets[:5] if bullets else ["明确目标", "拆解任务", "执行推进", "复盘优化"]
    nodes = []
    for i, step in enumerate(steps, start=1):
        x = 100 + (i - 1) * 230
        y = 340
        nodes.append(f'<rect x="{x}" y="{y}" width="190" height="140" rx="16" fill="#FFFFFF" stroke="#DBEAFE"/>')
        nodes.append(f'<circle cx="{x + 30}" cy="{y + 30}" r="16" fill="#1D4ED8"/>')
        nodes.append(f'<text x="{x + 23}" y="{y + 36}" font-size="18" fill="#FFFFFF" font-weight="700" font-family="Arial, Microsoft YaHei">{i}</text>')
        nodes.append(_render_text_block(x + 24, y + 92, step, max_width=150, font_size=22, line_height=30, max_lines=2, fill="#1E293B"))
        if i < len(steps):
            nx = x + 196
            ny = y + 70
            nodes.append(f'<line x1="{nx}" y1="{ny}" x2="{nx + 24}" y2="{ny}" stroke="#60A5FA" stroke-width="3"/>')
            nodes.append(f'<polygon points="{nx + 24},{ny} {nx + 16},{ny - 5} {nx + 16},{ny + 5}" fill="#60A5FA"/>')
    title_block = _render_text_block(80, 96, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
{title_block}
{''.join(nodes)}
"""


def _render_semantic_process_alt(title: str, bullets: list[str]) -> str:
    steps = bullets[:4] if bullets else ["定义范围", "能力建设", "试点验证", "规模推广"]
    cols = []
    for i, step in enumerate(steps):
        x = 120 + i * 260
        cols.append(f'<rect x="{x}" y="250" width="220" height="300" rx="14" fill="#FFFFFF" stroke="#DBEAFE"/>')
        cols.append(f'<rect x="{x+20}" y="280" width="180" height="8" rx="4" fill="#1D4ED8"/>')
        cols.append(_render_text_block(x + 24, 336, f"阶段 {i+1}", max_width=170, font_size=22, line_height=28, max_lines=1, fill="#1E3A8A", font_weight="700"))
        cols.append(_render_text_block(x + 24, 392, step, max_width=170, font_size=22, line_height=30, max_lines=4, fill="#1E293B"))
        if i < len(steps) - 1:
            cols.append(f'<line x1="{x+220}" y1="400" x2="{x+260}" y2="400" stroke="#93C5FD" stroke-width="3"/>')
    title_block = _render_text_block(80, 96, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
{title_block}
{''.join(cols)}
"""


def _render_semantic_compare(title: str, bullets: list[str]) -> str:
    left = bullets[:3] if bullets else ["现状流程复杂", "成本偏高", "响应较慢"]
    right = bullets[3:6] if len(bullets) > 3 else ["流程标准化", "成本优化", "响应提速"]
    left_items = "".join(
        _render_text_block(130, 255 + i * 95, f"• {t}", max_width=430, font_size=24, line_height=30, max_lines=2, fill="#1E293B")
        for i, t in enumerate(left)
    )
    right_items = "".join(
        _render_text_block(720, 255 + i * 95, f"• {t}", max_width=430, font_size=24, line_height=30, max_lines=2, fill="#1E293B")
        for i, t in enumerate(right)
    )
    title_block = _render_text_block(80, 92, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#FFFFFF"/>
{title_block}
<rect x="90" y="180" width="500" height="440" rx="18" fill="#F8FAFC" stroke="#E2E8F0"/>
<rect x="690" y="180" width="500" height="440" rx="18" fill="#EFF6FF" stroke="#BFDBFE"/>
<text x="130" y="235" font-size="30" fill="#0F172A" font-weight="700" font-family="Arial, Microsoft YaHei">现状</text>
<text x="720" y="235" font-size="30" fill="#1D4ED8" font-weight="700" font-family="Arial, Microsoft YaHei">目标</text>
{left_items}
{right_items}
"""


def _render_semantic_compare_alt(title: str, bullets: list[str]) -> str:
    items = bullets[:4] if bullets else ["维度A：现状与目标差距", "维度B：流程效率差距", "维度C：成本结构差距", "维度D：能力成熟度差距"]
    rows = []
    for i, item in enumerate(items):
        y = 210 + i * 100
        rows.append(f'<rect x="100" y="{y}" width="1080" height="80" rx="12" fill="#FFFFFF" stroke="#E2E8F0"/>')
        rows.append(f'<rect x="100" y="{y}" width="140" height="80" rx="12" fill="#EFF6FF" stroke="#DBEAFE"/>')
        rows.append(_render_text_block(124, y + 50, f"D{i+1}", max_width=90, font_size=24, line_height=28, max_lines=1, fill="#1D4ED8", font_weight="700"))
        rows.append(_render_text_block(270, y + 50, item, max_width=880, font_size=23, line_height=28, max_lines=2, fill="#1E293B"))
    title_block = _render_text_block(80, 92, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#FFFFFF"/>
{title_block}
{''.join(rows)}
"""


def _render_semantic_risk(title: str, bullets: list[str]) -> str:
    risks = bullets[:4] if bullets else ["数据质量风险", "项目推进延迟", "跨部门协同不足", "投入产出不及预期"]
    blocks = []
    for i, item in enumerate(risks):
        x = 110 + (i % 2) * 540
        y = 210 + (i // 2) * 190
        blocks.append(f'<rect x="{x}" y="{y}" width="500" height="150" rx="16" fill="#FFFFFF" stroke="#FCA5A5"/>')
        blocks.append(f'<circle cx="{x + 30}" cy="{y + 30}" r="12" fill="#DC2626"/>')
        blocks.append(_render_text_block(x + 56, y + 38, item, max_width=420, font_size=24, line_height=30, max_lines=2, fill="#7F1D1D", font_weight="700"))
        blocks.append(_render_text_block(x + 30, y + 94, "缓释策略：建立预警阈值与周度复盘", max_width=440, font_size=20, line_height=26, max_lines=2, fill="#1E293B"))
    title_block = _render_text_block(80, 92, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#FFF7F7"/>
{title_block}
{''.join(blocks)}
"""


def _render_semantic_risk_alt(title: str, bullets: list[str]) -> str:
    items = bullets[:5] if bullets else ["数据口径不一致", "流程执行偏差", "资源投入不足", "跨部门协同低效", "收益兑现滞后"]
    rows = []
    for i, item in enumerate(items):
        y = 200 + i * 92
        rows.append(f'<rect x="100" y="{y}" width="1080" height="70" rx="10" fill="#FFFFFF" stroke="#FECACA"/>')
        rows.append(f'<circle cx="132" cy="{y+35}" r="10" fill="#DC2626"/>')
        rows.append(_render_text_block(158, y + 44, item, max_width=700, font_size=22, line_height=28, max_lines=2, fill="#7F1D1D"))
        rows.append(_render_text_block(900, y + 44, "中风险", max_width=120, font_size=20, line_height=24, max_lines=1, fill="#B45309", font_weight="700"))
        rows.append(_render_text_block(1010, y + 44, "缓释中", max_width=120, font_size=20, line_height=24, max_lines=1, fill="#2563EB", font_weight="700"))
    title_block = _render_text_block(80, 92, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#FFF7F7"/>
{title_block}
{''.join(rows)}
"""


def _render_semantic_architecture(title: str, bullets: list[str]) -> str:
    layers = bullets[:4] if bullets else ["应用层", "服务层", "数据层", "基础设施层"]
    blocks = []
    for i, layer in enumerate(layers):
        y = 180 + i * 120
        w = 940 - i * 80
        x = 170 + i * 40
        blocks.append(f'<rect x="{x}" y="{y}" width="{w}" height="90" rx="14" fill="#FFFFFF" stroke="#BFDBFE"/>')
        blocks.append(_render_text_block(x + 30, y + 56, layer, max_width=w - 60, font_size=28, line_height=34, max_lines=1, fill="#1E3A8A", font_weight="700"))
    title_block = _render_text_block(80, 92, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
{title_block}
{''.join(blocks)}
"""


def _render_semantic_architecture_alt(title: str, bullets: list[str]) -> str:
    layers = bullets[:4] if bullets else ["应用编排层", "领域服务层", "数据能力层", "基础设施层"]
    blocks = []
    for i, layer in enumerate(layers):
        y = 210 + i * 110
        blocks.append(f'<rect x="150" y="{y}" width="980" height="78" rx="12" fill="#FFFFFF" stroke="#CBD5E1"/>')
        blocks.append(f'<rect x="150" y="{y}" width="180" height="78" rx="12" fill="#EFF6FF" stroke="#DBEAFE"/>')
        blocks.append(_render_text_block(178, y + 48, f"L{i+1}", max_width=120, font_size=22, line_height=24, max_lines=1, fill="#1D4ED8", font_weight="700"))
        blocks.append(_render_text_block(360, y + 48, layer, max_width=730, font_size=24, line_height=30, max_lines=1, fill="#1E293B", font_weight="700"))
    title_block = _render_text_block(80, 92, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
{title_block}
{''.join(blocks)}
"""


def _render_timeline_strip(title: str, bullets: list[str]) -> str:
    items = bullets[:6] if bullets else ["阶段1", "阶段2", "阶段3", "阶段4", "阶段5"]
    blocks = []
    x = 120
    for i, item in enumerate(items):
        w = 160
        y = 320 + (i % 2) * 80
        blocks.append(f'<rect x="{x}" y="{y}" width="{w}" height="70" rx="10" fill="#FFFFFF" stroke="#DBEAFE"/>')
        blocks.append(_render_text_block(x + 12, y + 44, item, max_width=136, font_size=20, line_height=24, max_lines=2, fill="#1E293B"))
        blocks.append(f'<circle cx="{x + 80}" cy="300" r="10" fill="#1D4ED8"/>')
        blocks.append(f'<line x1="{x+80}" y1="310" x2="{x+80}" y2="{y}" stroke="#93C5FD" stroke-width="3"/>')
        if i < len(items)-1:
            blocks.append(f'<line x1="{x+160}" y1="300" x2="{x+200}" y2="300" stroke="#60A5FA" stroke-width="3"/>')
        x += 180
    title_block = _render_text_block(80, 92, title, max_width=1120, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F8FAFC"/>
{title_block}
<line x1="120" y1="300" x2="1160" y2="300" stroke="#BFDBFE" stroke-width="6"/>
{''.join(blocks)}
"""


def _render_summary_panel(title: str, bullets: list[str]) -> str:
    core = bullets[0] if bullets else "核心结论：聚焦高价值场景，按阶段推进。"
    actions = bullets[1:4] if len(bullets) > 1 else ["统一目标", "强化执行", "持续复盘"]
    cards = []
    for i, a in enumerate(actions):
        x = 120 + i * 350
        cards.append(f'<rect x="{x}" y="430" width="300" height="150" rx="14" fill="#FFFFFF" stroke="#CBD5E1"/>')
        cards.append(_render_text_block(x + 20, 482, f"行动 {i+1}", max_width=130, font_size=20, line_height=24, max_lines=1, fill="#1D4ED8", font_weight="700"))
        cards.append(_render_text_block(x + 20, 536, a, max_width=260, font_size=24, line_height=30, max_lines=2, fill="#1E293B"))
    title_block = _render_text_block(90, 96, title, max_width=1080, font_size=46, line_height=54, max_lines=1, fill="#0F172A", font_weight="700")
    core_block = _render_text_block(130, 265, core, max_width=1010, font_size=32, line_height=40, max_lines=3, fill="#0F172A", font_weight="700")
    return f"""
<rect x="0" y="0" width="1280" height="720" fill="#F1F5F9"/>
{title_block}
<rect x="100" y="180" width="1080" height="220" rx="20" fill="#FFFFFF" stroke="#DBEAFE"/>
{core_block}
{''.join(cards)}
"""


def html_to_svg(html_path: Path, svg_path: Path) -> Path:
    """Deterministic converter for constrained slide HTML.

    V1 behavior:
    - Parse title + body text blocks.
    - Emit fixed 1280x720 canvas.
    - Output deterministic order (background, title, paragraphs).
    """
    content = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")
    title = (soup.title.string or "").strip() if soup.title else "Untitled Slide"
    headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])]
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
    list_items = [li.get_text(strip=True) for li in soup.find_all("li")]
    table_cells = [td.get_text(strip=True) for td in soup.find_all("td")]
    root = soup.find(attrs={"data-layout": True})
    layout = (root.get("data-layout") if root else "") or ""
    style_profile = (root.get("data-style") if root else "") or "business-blue"
    subtitle = paragraphs[0] if paragraphs else ""
    core_title = headings[0] if headings else title

    name = html_path.stem.lower()
    if layout == "cover-hero-b":
        body = _render_cover_dark(core_title, subtitle)
    elif layout == "agenda-roadmap":
        body = _render_agenda_roadmap(core_title, list_items or paragraphs)
    elif layout == "agenda-cards":
        body = _render_agenda_cards(core_title, list_items or paragraphs)
    elif layout == "content-steps":
        body = _render_content_steps(core_title, list_items or paragraphs)
    elif layout == "content-compare":
        body = _render_content_compare(core_title, list_items or paragraphs)
    elif layout == "content-zigzag":
        body = _render_content_zigzag(core_title, list_items or paragraphs)
    elif layout == "content-matrix":
        body = _render_content_matrix(core_title, list_items or paragraphs)
    elif layout == "data-kpi-grid":
        rows = []
        for i in range(0, len(table_cells), 2):
            left = table_cells[i]
            right = table_cells[i + 1] if i + 1 < len(table_cells) else ""
            rows.append((left, right))
        if not rows:
            for idx, item in enumerate(list_items or paragraphs[:6], start=1):
                rows.append((f"指标{idx}", item))
        body = _render_data_kpi_grid(core_title, rows)
    elif layout == "data-table-pro":
        rows = []
        for i in range(0, len(table_cells), 2):
            left = table_cells[i]
            right = table_cells[i + 1] if i + 1 < len(table_cells) else ""
            rows.append((left, right))
        if not rows:
            for idx, item in enumerate(list_items or paragraphs[:6], start=1):
                rows.append((f"维度{idx}", item))
        body = _render_data_table_pro(core_title, rows)
    elif layout == "data-waterfall":
        rows = []
        for i in range(0, len(table_cells), 2):
            left = table_cells[i]
            right = table_cells[i + 1] if i + 1 < len(table_cells) else ""
            rows.append((left, right))
        if not rows:
            for idx, item in enumerate(list_items or paragraphs[:5], start=1):
                rows.append((f"项目{idx}", item))
        body = _render_data_waterfall(core_title, rows)
    elif layout == "data-line-trend":
        rows = []
        for i in range(0, len(table_cells), 2):
            left = table_cells[i]
            right = table_cells[i + 1] if i + 1 < len(table_cells) else ""
            rows.append((left, right))
        if not rows:
            for idx, item in enumerate(list_items or paragraphs[:6], start=1):
                rows.append((f"阶段{idx}", item))
        body = _render_data_line_trend(core_title, rows)
    elif layout == "data-funnel":
        rows = []
        for i in range(0, len(table_cells), 2):
            left = table_cells[i]
            right = table_cells[i + 1] if i + 1 < len(table_cells) else ""
            rows.append((left, right))
        if not rows:
            for idx, item in enumerate(list_items or paragraphs[:5], start=1):
                rows.append((f"阶段{idx}", item))
        body = _render_data_funnel(core_title, rows)
    elif layout == "summary-grid":
        body = _render_summary_grid(core_title, list_items or paragraphs)
    elif layout == "summary-panel":
        body = _render_summary_panel(core_title, list_items or paragraphs)
    elif layout == "summary-takeaway":
        body = _render_summary_takeaway(core_title, list_items or paragraphs)
    elif layout == "ending-light":
        body = _render_ending_light(core_title, subtitle or "感谢聆听")
    elif layout == "history-timeline":
        body = _render_history_timeline(core_title, list_items or paragraphs)
    elif layout == "timeline-strip":
        body = _render_timeline_strip(core_title, list_items or paragraphs)
    elif layout == "timeline-modern":
        body = _render_timeline_modern(core_title, list_items or paragraphs)
    elif layout == "history-figures":
        body = _render_history_figures(core_title, list_items or paragraphs)
    elif layout == "history-landmarks":
        body = _render_history_landmarks(core_title, list_items or paragraphs)
    elif layout == "history-modern":
        body = _render_history_modern(core_title, list_items or paragraphs)
    elif layout == "history-culture":
        body = _render_history_culture(core_title, list_items or paragraphs)
    elif layout == "semantic-process":
        body = _render_semantic_process(core_title, list_items or paragraphs)
    elif layout == "semantic-process-alt":
        body = _render_semantic_process_alt(core_title, list_items or paragraphs)
    elif layout == "semantic-compare":
        body = _render_semantic_compare(core_title, list_items or paragraphs)
    elif layout == "semantic-compare-alt":
        body = _render_semantic_compare_alt(core_title, list_items or paragraphs)
    elif layout == "semantic-risk":
        body = _render_semantic_risk(core_title, list_items or paragraphs)
    elif layout == "semantic-risk-alt":
        body = _render_semantic_risk_alt(core_title, list_items or paragraphs)
    elif layout == "semantic-architecture":
        body = _render_semantic_architecture(core_title, list_items or paragraphs)
    elif layout == "semantic-architecture-alt":
        body = _render_semantic_architecture_alt(core_title, list_items or paragraphs)
    elif "cover" in name:
        body = _render_cover(core_title, subtitle)
    elif "agenda" in name:
        body = _render_agenda(core_title, list_items or paragraphs)
    elif "data" in name:
        rows: list[tuple[str, str]] = []
        for i in range(0, len(table_cells), 2):
            left = table_cells[i]
            right = table_cells[i + 1] if i + 1 < len(table_cells) else ""
            rows.append((left, right))
        if not rows:
            for idx, item in enumerate(list_items or paragraphs[:4], start=1):
                rows.append((f"指标{idx}", item))
        body = _render_data(core_title, rows)
    elif "summary" in name:
        body = _render_summary(core_title, list_items or paragraphs)
    elif "ending" in name:
        body = _render_ending(core_title, subtitle or "感谢聆听")
    else:
        bullets = list_items or paragraphs
        body = _render_content(core_title, bullets)

    body = _apply_style_profile(body, style_profile)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">'
        f"{body}"
        "</svg>"
    )

    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg, encoding="utf-8")
    return svg_path
