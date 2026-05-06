from __future__ import annotations

from pathlib import Path
import re

from bs4 import BeautifulSoup


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
    subtitle = paragraphs[0] if paragraphs else ""
    core_title = headings[0] if headings else title

    name = html_path.stem.lower()
    if layout == "cover-hero-b":
        body = _render_cover_dark(core_title, subtitle)
    elif layout == "agenda-roadmap":
        body = _render_agenda_roadmap(core_title, list_items or paragraphs)
    elif layout == "content-steps":
        body = _render_content_steps(core_title, list_items or paragraphs)
    elif layout == "content-compare":
        body = _render_content_compare(core_title, list_items or paragraphs)
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
    elif layout == "summary-grid":
        body = _render_summary_grid(core_title, list_items or paragraphs)
    elif layout == "ending-light":
        body = _render_ending_light(core_title, subtitle or "感谢聆听")
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

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">'
        f"{body}"
        "</svg>"
    )

    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg, encoding="utf-8")
    return svg_path
