"""Seed system prompts from hardcoded defaults."""

from sqlalchemy import select

from app.db.models.prompt import Prompt, PromptLevel
from app.db.session import AsyncSessionLocal
from app.multilingual.prompts import HARDCODED_PROMPTS
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def seed_system_prompts() -> int:
    """Seed system-level prompts from hardcoded defaults.

    Only creates prompts that don't already exist at the system level.

    Returns:
        Number of prompts created
    """
    async with AsyncSessionLocal() as session:
        created_count = 0

        for name, prompt_data in HARDCODED_PROMPTS.items():
            # Check if system-level prompt already exists
            stmt = (
                select(Prompt.id)
                .where(Prompt.name == name)
                .where(Prompt.level == PromptLevel.SYSTEM)
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing is None:
                # Create system-level prompt
                prompt = Prompt(
                    name=name,
                    level=PromptLevel.SYSTEM,
                    content=prompt_data["content"],
                    description=prompt_data.get("description"),
                    is_active=True,
                )
                session.add(prompt)
                created_count += 1
                logger.debug("prompt_seeded", name=name)

        if created_count > 0:
            await session.commit()
            logger.info("prompts_seeded", count=created_count)

        return created_count


async def reseed_system_prompts() -> int:
    """Re-seed system prompts, updating existing ones.

    Updates content and description for existing system-level prompts.

    Returns:
        Number of prompts updated or created
    """
    async with AsyncSessionLocal() as session:
        updated_count = 0

        for name, prompt_data in HARDCODED_PROMPTS.items():
            # Check if system-level prompt already exists
            stmt = (
                select(Prompt)
                .where(Prompt.name == name)
                .where(Prompt.level == PromptLevel.SYSTEM)
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing is None:
                # Create new system-level prompt
                prompt = Prompt(
                    name=name,
                    level=PromptLevel.SYSTEM,
                    content=prompt_data["content"],
                    description=prompt_data.get("description"),
                    is_active=True,
                )
                session.add(prompt)
            else:
                # Update existing prompt
                existing.content = prompt_data["content"]
                existing.description = prompt_data.get("description")
                existing.version += 1

            updated_count += 1

        await session.commit()
        logger.info("prompts_reseeded", count=updated_count)

        return updated_count
