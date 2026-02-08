"""Prompt service for resolving prompts with hierarchical overrides."""

from functools import lru_cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.prompt import Prompt, PromptLevel
from app.multilingual.prompts import HARDCODED_PROMPTS, get_hardcoded_prompt
from app.utils.logging import get_logger

logger = get_logger(__name__)


class PromptCache:
    """Simple in-memory cache for prompts."""

    def __init__(self, max_size: int = 100):
        self._cache: dict[str, str] = {}
        self._max_size = max_size

    def get(self, key: str) -> str | None:
        """Get cached prompt."""
        return self._cache.get(key)

    def set(self, key: str, value: str) -> None:
        """Set cached prompt."""
        if len(self._cache) >= self._max_size:
            # Simple eviction: remove first item
            first_key = next(iter(self._cache))
            del self._cache[first_key]
        self._cache[key] = value

    def invalidate(self, name: str | None = None) -> None:
        """Invalidate cache entries.

        Args:
            name: Prompt name to invalidate, or None to clear all
        """
        if name is None:
            self._cache.clear()
        else:
            # Remove all entries for this prompt name (all levels)
            keys_to_remove = [k for k in self._cache if k.startswith(f"{name}:")]
            for key in keys_to_remove:
                del self._cache[key]


class PromptService:
    """Service for resolving prompts with hierarchical overrides.

    Resolution order (first found wins):
    1. User level (if exists and is_active)
    2. Developer level (if exists and is_active)
    3. System level (if exists and is_active)
    4. Hardcoded fallback from app/multilingual/prompts.py
    """

    def __init__(self, session: AsyncSession, cache: PromptCache | None = None):
        """Initialize prompt service.

        Args:
            session: Async database session
            cache: Optional prompt cache
        """
        self.session = session
        self.cache = cache or PromptCache()

    async def get_prompt(
        self,
        name: str,
        user_id: str | None = None,
    ) -> str:
        """Get prompt content by name with hierarchical resolution.

        Args:
            name: Prompt identifier
            user_id: Optional user ID for user-level prompts (future multi-tenant)

        Returns:
            Prompt content string

        Raises:
            ValueError: If prompt not found at any level
        """
        # Build cache key
        cache_key = f"{name}:{user_id or 'default'}"

        # Check cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug("prompt_cache_hit", name=name)
            return cached

        # Try resolution hierarchy
        levels = [PromptLevel.USER, PromptLevel.DEVELOPER, PromptLevel.SYSTEM]

        for level in levels:
            # Skip user level if no user_id provided
            if level == PromptLevel.USER and user_id is None:
                continue

            prompt = await self._get_prompt_at_level(name, level)
            if prompt is not None:
                logger.debug(
                    "prompt_resolved",
                    name=name,
                    level=level.value,
                    source="database",
                )
                self.cache.set(cache_key, prompt)
                return prompt

        # Fall back to hardcoded
        fallback = get_hardcoded_prompt(name)
        if fallback is not None:
            logger.debug(
                "prompt_resolved",
                name=name,
                level="hardcoded",
                source="fallback",
            )
            self.cache.set(cache_key, fallback)
            return fallback

        raise ValueError(f"Prompt not found: {name}")

    async def _get_prompt_at_level(
        self,
        name: str,
        level: PromptLevel,
    ) -> str | None:
        """Get prompt at specific level.

        Args:
            name: Prompt name
            level: Prompt level

        Returns:
            Prompt content or None
        """
        stmt = (
            select(Prompt.content)
            .where(Prompt.name == name)
            .where(Prompt.level == level)
            .where(Prompt.is_active == True)  # noqa: E712
        )

        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return row

    async def get_all_prompts(
        self,
        name: str | None = None,
        level: PromptLevel | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Prompt], int]:
        """Get all prompts with optional filtering.

        Args:
            name: Filter by name (partial match)
            level: Filter by level
            is_active: Filter by active status
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Tuple of (prompts list, total count)
        """
        # Build base query
        stmt = select(Prompt)

        if name is not None:
            stmt = stmt.where(Prompt.name.ilike(f"%{name}%"))
        if level is not None:
            stmt = stmt.where(Prompt.level == level)
        if is_active is not None:
            stmt = stmt.where(Prompt.is_active == is_active)

        # Get total count
        count_stmt = select(Prompt.id)
        if name is not None:
            count_stmt = count_stmt.where(Prompt.name.ilike(f"%{name}%"))
        if level is not None:
            count_stmt = count_stmt.where(Prompt.level == level)
        if is_active is not None:
            count_stmt = count_stmt.where(Prompt.is_active == is_active)

        count_result = await self.session.execute(count_stmt)
        total = len(count_result.all())

        # Apply pagination and ordering
        stmt = stmt.order_by(Prompt.name, Prompt.level).offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        prompts = list(result.scalars().all())

        return prompts, total

    async def get_prompt_by_id(self, prompt_id: int) -> Prompt | None:
        """Get prompt by ID.

        Args:
            prompt_id: Prompt ID

        Returns:
            Prompt or None
        """
        stmt = select(Prompt).where(Prompt.id == prompt_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_prompt(
        self,
        name: str,
        content: str,
        level: PromptLevel = PromptLevel.SYSTEM,
        description: str | None = None,
        is_active: bool = True,
    ) -> Prompt:
        """Create a new prompt.

        Args:
            name: Prompt identifier
            content: Prompt text
            level: Override level
            description: Optional description
            is_active: Whether prompt is active

        Returns:
            Created prompt
        """
        prompt = Prompt(
            name=name,
            level=level,
            content=content,
            description=description,
            is_active=is_active,
        )
        self.session.add(prompt)
        await self.session.commit()
        await self.session.refresh(prompt)

        # Invalidate cache for this prompt
        self.cache.invalidate(name)

        logger.info(
            "prompt_created",
            id=prompt.id,
            name=name,
            level=level.value,
        )

        return prompt

    async def update_prompt(
        self,
        prompt_id: int,
        updates: dict[str, Any],
    ) -> Prompt | None:
        """Update a prompt.

        Args:
            prompt_id: Prompt ID
            updates: Dictionary of fields to update

        Returns:
            Updated prompt or None if not found
        """
        prompt = await self.get_prompt_by_id(prompt_id)
        if prompt is None:
            return None

        old_name = prompt.name

        # Apply updates
        for key, value in updates.items():
            if value is not None and hasattr(prompt, key):
                setattr(prompt, key, value)

        # Increment version
        prompt.version += 1

        await self.session.commit()
        await self.session.refresh(prompt)

        # Invalidate cache for old and new name
        self.cache.invalidate(old_name)
        if "name" in updates and updates["name"] != old_name:
            self.cache.invalidate(updates["name"])

        logger.info(
            "prompt_updated",
            id=prompt_id,
            version=prompt.version,
        )

        return prompt

    async def delete_prompt(self, prompt_id: int) -> bool:
        """Delete a prompt.

        Args:
            prompt_id: Prompt ID

        Returns:
            True if deleted, False if not found
        """
        prompt = await self.get_prompt_by_id(prompt_id)
        if prompt is None:
            return False

        name = prompt.name
        await self.session.delete(prompt)
        await self.session.commit()

        # Invalidate cache
        self.cache.invalidate(name)

        logger.info("prompt_deleted", id=prompt_id, name=name)

        return True

    async def toggle_active(self, prompt_id: int) -> Prompt | None:
        """Toggle prompt active status.

        Args:
            prompt_id: Prompt ID

        Returns:
            Updated prompt or None if not found
        """
        prompt = await self.get_prompt_by_id(prompt_id)
        if prompt is None:
            return None

        prompt.is_active = not prompt.is_active
        await self.session.commit()
        await self.session.refresh(prompt)

        # Invalidate cache
        self.cache.invalidate(prompt.name)

        logger.info(
            "prompt_toggled",
            id=prompt_id,
            is_active=prompt.is_active,
        )

        return prompt

    def invalidate_cache(self, name: str | None = None) -> None:
        """Invalidate prompt cache.

        Args:
            name: Prompt name to invalidate, or None for all
        """
        self.cache.invalidate(name)


# Global cache instance
_prompt_cache = PromptCache()


def get_prompt_cache() -> PromptCache:
    """Get global prompt cache instance."""
    return _prompt_cache
