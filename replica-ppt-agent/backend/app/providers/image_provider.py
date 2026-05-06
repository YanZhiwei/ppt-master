from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from app.providers.errors import ProviderError, ProviderErrorCode
from app.settings import settings


class ImageProviderRouter:
    def __init__(self) -> None:
        self.provider = settings.image_provider
        self.model = settings.image_model
        self.retry_once = settings.image_retry_once
        self.fallback_manual = settings.image_fallback_manual
        self.repo_root = Path(__file__).resolve().parents[4]
        self.image_script = self.repo_root / "skills" / "ppt-master" / "scripts" / "image_gen.py"

    def generate(self, prompt: str, output_dir: Path, aspect_ratio: str = "16:9") -> str:
        if self.provider not in {"gemini", "openai"}:
            raise ProviderError(
                ProviderErrorCode.invalid_request,
                f"Unsupported IMAGE_PROVIDER={self.provider}",
            )
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            str(self.image_script),
            prompt,
            "--backend",
            self.provider,
            "--aspect_ratio",
            aspect_ratio,
            "--image_size",
            "1K",
            "-o",
            str(output_dir),
        ]

        env = os.environ.copy()
        env["IMAGE_BACKEND"] = self.provider
        # Pass-through model names. For OpenAI image this supports gpt-image-2.
        env.setdefault("OPENAI_MODEL", self.model)
        env.setdefault("GEMINI_MODEL", self.model)

        attempts = 2 if self.retry_once else 1
        last_error = None
        for _ in range(attempts):
            result = subprocess.run(
                cmd,
                cwd=self.repo_root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return self._parse_output_path(result.stdout, output_dir)
            last_error = result.stderr or result.stdout

        if self.fallback_manual:
            return "Needs-Manual"

        raise self._normalize_error(last_error or "Unknown provider failure")

    def _normalize_error(self, raw: str) -> ProviderError:
        text = raw.lower()
        if "401" in text or "unauthorized" in text or "api key" in text:
            return ProviderError(ProviderErrorCode.auth, raw)
        if "429" in text or "rate" in text or "quota" in text:
            return ProviderError(ProviderErrorCode.rate_limit, raw)
        if "timeout" in text:
            return ProviderError(ProviderErrorCode.timeout, raw)
        if "invalid" in text or "bad request" in text:
            return ProviderError(ProviderErrorCode.invalid_request, raw)
        if "503" in text or "unavailable" in text:
            return ProviderError(ProviderErrorCode.unavailable, raw)
        return ProviderError(ProviderErrorCode.unknown, raw)

    @staticmethod
    def _parse_output_path(stdout: str, fallback_dir: Path) -> str:
        for line in stdout.splitlines():
            line = line.strip()
            if line.endswith((".png", ".jpg", ".jpeg", ".webp")):
                return line
            if "Saved:" in line:
                return line.split("Saved:", 1)[-1].strip()
        return str(fallback_dir)

