from __future__ import annotations

from enum import Enum


class ProviderErrorCode(str, Enum):
    auth = "provider_auth_error"
    rate_limit = "provider_rate_limit"
    unavailable = "provider_unavailable"
    timeout = "provider_timeout"
    invalid_request = "provider_invalid_request"
    unknown = "provider_unknown"


class ProviderError(Exception):
    def __init__(self, code: ProviderErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

