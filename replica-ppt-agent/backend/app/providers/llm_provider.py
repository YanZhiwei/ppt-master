from __future__ import annotations

from langchain_openai import AzureChatOpenAI

from app.providers.errors import ProviderError, ProviderErrorCode
from app.settings import settings


def build_chat_model() -> AzureChatOpenAI:
    if settings.llm_provider != "azure_openai":
        raise ProviderError(
            ProviderErrorCode.invalid_request,
            f"Unsupported LLM_PROVIDER={settings.llm_provider}",
        )
    if not settings.azure_openai_api_key:
        raise ProviderError(ProviderErrorCode.auth, "AZURE_OPENAI_API_KEY is required")
    if not settings.azure_openai_endpoint:
        raise ProviderError(ProviderErrorCode.invalid_request, "AZURE_OPENAI_ENDPOINT is required")
    if not settings.azure_openai_chat_deployment:
        raise ProviderError(
            ProviderErrorCode.invalid_request,
            "AZURE_OPENAI_CHAT_DEPLOYMENT is required",
        )

    return AzureChatOpenAI(
        api_key=settings.azure_openai_api_key,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_openai_chat_deployment,
        temperature=settings.azure_openai_temperature,
    )

