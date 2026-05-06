from __future__ import annotations

from pathlib import Path

from app.conversion.html_to_svg import html_to_svg
from app.export.pptx_export import export_pptx, verify_editable_shapes
from app.quality.svg_gate import run_svg_quality_gate


def convert_html_directory_to_svg(project_dir: Path) -> list[Path]:
    html_dir = project_dir / "html_output"
    svg_dir = project_dir / "svg_output"
    svg_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for html_file in sorted(html_dir.glob("*.html")):
        svg_file = svg_dir / f"{html_file.stem}.svg"
        outputs.append(html_to_svg(html_file, svg_file))
    return outputs


def run_export_pipeline(project_dir: Path) -> tuple[bool, str]:
    ok, report = run_svg_quality_gate(project_dir)
    if not ok:
        return False, f"Quality gate failed:\n{report}"

    ok, report = export_pptx(project_dir)
    if not ok:
        return False, f"PPTX export failed:\n{report}"

    exports = sorted((project_dir / "exports").glob("*.pptx"), reverse=True)
    if not exports:
        return False, "No exported PPTX found under exports/"
    editable_ok, editable_report = verify_editable_shapes(exports[0])
    if not editable_ok:
        return False, f"Editable verification failed: {editable_report}"
    return True, editable_report

