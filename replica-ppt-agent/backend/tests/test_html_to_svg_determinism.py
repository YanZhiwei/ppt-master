from pathlib import Path

from app.conversion.html_to_svg import html_to_svg


def test_html_to_svg_is_deterministic(tmp_path: Path) -> None:
    src = Path(__file__).resolve().parents[1] / "fixtures" / "cover.html"
    out1 = tmp_path / "a.svg"
    out2 = tmp_path / "b.svg"

    html_to_svg(src, out1)
    html_to_svg(src, out2)

    assert out1.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")

