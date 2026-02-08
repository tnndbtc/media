"""Prompt SQLAlchemy model."""

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PromptLevel(str, enum.Enum):
    """Prompt override level."""

    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"


class Prompt(Base):
    """Prompt model for storing and managing prompts."""

    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    level: Mapped[PromptLevel] = mapped_column(
        Enum(PromptLevel), nullable=False, default=PromptLevel.SYSTEM
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("name", "level", name="uq_prompt_name_level"),
    )

    def __repr__(self) -> str:
        return f"<Prompt(id={self.id}, name='{self.name}', level='{self.level.value}')>"
