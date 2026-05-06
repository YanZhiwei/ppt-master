from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_svg_quality_gate(project_dir: Path) -> tuple[bool, str]:
    """Run reference SVG quality checker before export."""
    repo_root = Path(__file__).resolve().parents[4]
    checker = repo_root / "skills" / "ppt-master" / "scripts" / "svg_quality_checker.py"
    cmd = [sys.executable, str(checker), str(project_dir)]
    result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    return result.returncode == 0, output.strip()

