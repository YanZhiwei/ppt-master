from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator


class SlideObject(BaseModel):
    id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    x: int
    y: int
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    text: str | None = None
    style: dict[str, Any] = Field(default_factory=dict)


class SlideAuthoringDocument(BaseModel):
    slide_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    width: int = Field(default=1280, ge=1)
    height: int = Field(default=720, ge=1)
    background: str = "#FFFFFF"
    objects: list[SlideObject] = Field(default_factory=list)

    @field_validator("objects")
    @classmethod
    def require_objects(cls, value: list[SlideObject]) -> list[SlideObject]:
        if len(value) == 0:
            raise ValueError("objects must not be empty")
        return value


def validate_authoring_document(payload: dict[str, Any]) -> tuple[bool, str | None]:
    try:
        SlideAuthoringDocument.model_validate(payload)
        return True, None
    except ValidationError as exc:
        return False, str(exc)

