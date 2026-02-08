"""Pydantic schemas for prompt management."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PromptLevel(str, Enum):
    """Prompt override level."""

    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"


class PromptBase(BaseModel):
    """Base prompt schema."""

    name: str = Field(..., min_length=1, max_length=100, description="Prompt identifier")
    level: PromptLevel = Field(default=PromptLevel.SYSTEM, description="Override level")
    content: str = Field(..., min_length=1, description="Prompt text content")
    description: str | None = Field(
        default=None, max_length=500, description="Optional description"
    )
    is_active: bool = Field(default=True, description="Whether prompt is active")


class PromptCreate(PromptBase):
    """Schema for creating a prompt."""

    pass


class PromptUpdate(BaseModel):
    """Schema for updating a prompt."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    level: PromptLevel | None = None
    content: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class PromptResponse(PromptBase):
    """Schema for prompt response."""

    id: int
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PromptListResponse(BaseModel):
    """Schema for paginated prompt list response."""

    items: list[PromptResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
