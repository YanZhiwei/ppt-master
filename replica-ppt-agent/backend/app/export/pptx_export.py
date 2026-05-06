from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path


def export_pptx(project_dir: Path) -> tuple[bool, str]:
    repo_root = Path(__file__).resolve().parents[4]
    script = repo_root / "skills" / "ppt-master" / "scripts" / "svg_to_pptx.py"
    # Debug/pipeline default uses native editable output only.
    cmd = [sys.executable, str(script), str(project_dir), "--only", "native"]
    result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    return result.returncode == 0, output.strip()


def verify_editable_shapes(pptx_path: Path) -> tuple[bool, str]:
    """Basic editability sanity check.

    We assert at least one slide XML contains shape/text tags.
    """
    if not pptx_path.exists():
        return False, f"PPTX not found: {pptx_path}"

    with zipfile.ZipFile(pptx_path, "r") as zf:
        slide_xmls = [n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
        if not slide_xmls:
            return False, "No slide XML entries found"
        for name in slide_xmls:
            data = zf.read(name).decode("utf-8", errors="ignore")
            if "<p:sp" in data or "<a:t>" in data:
                return True, "Editable shape/text markers detected"
    return False, "No editable shape/text markers found"
