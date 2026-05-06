from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "dev")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8010"))

    llm_provider: str = os.getenv("LLM_PROVIDER", "azure_openai")
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    azure_openai_chat_deployment: str = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "")
    azure_openai_temperature: float = float(os.getenv("AZURE_OPENAI_TEMPERATURE", "0.2"))

    image_provider: str = os.getenv("IMAGE_PROVIDER", "gemini").lower()
    image_model: str = os.getenv("IMAGE_MODEL", "nano-banana-pro")
    image_retry_once: bool = os.getenv("IMAGE_RETRY_ONCE", "true").lower() == "true"
    image_fallback_manual: bool = os.getenv("IMAGE_FALLBACK_MANUAL", "true").lower() == "true"
    default_ppt_theme: str = os.getenv(
        "DEFAULT_PPT_THEME",
        "请生成一份关于AI提效的商务风演示文稿，10页，含封面、目录、3页核心观点、2页数据页、1页总结和结束页。",
    )


settings = Settings()
