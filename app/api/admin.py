"""Admin API endpoints for prompt management."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.api.dependencies import DbSessionDep, PromptServiceDep
from app.db.models.prompt import PromptLevel
from app.db.seed import reseed_system_prompts
from app.models.prompt import (
    PromptCreate,
    PromptListResponse,
    PromptResponse,
    PromptUpdate,
)
from app.services.prompt_service import PromptService, get_prompt_cache
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("", response_class=HTMLResponse)
async def admin_ui() -> HTMLResponse:
    """Serve admin UI."""
    static_dir = Path(__file__).parent.parent / "static" / "admin"
    index_path = static_dir / "index.html"

    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Admin UI not found")

    return HTMLResponse(content=index_path.read_text())


@router.get("/api/prompts", response_model=PromptListResponse)
async def list_prompts(
    prompt_service: PromptServiceDep,
    name: Annotated[str | None, Query(description="Filter by name (partial match)")] = None,
    level: Annotated[PromptLevel | None, Query(description="Filter by level")] = None,
    is_active: Annotated[bool | None, Query(description="Filter by active status")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> PromptListResponse:
    """List prompts with optional filtering."""
    prompts, total = await prompt_service.get_all_prompts(
        name=name,
        level=level,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size

    return PromptListResponse(
        items=[PromptResponse.model_validate(p) for p in prompts],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/api/prompts", response_model=PromptResponse, status_code=201)
async def create_prompt(
    prompt_data: PromptCreate,
    prompt_service: PromptServiceDep,
) -> PromptResponse:
    """Create a new prompt."""
    try:
        prompt = await prompt_service.create_prompt(
            name=prompt_data.name,
            content=prompt_data.content,
            level=PromptLevel(prompt_data.level.value),
            description=prompt_data.description,
            is_active=prompt_data.is_active,
        )
        return PromptResponse.model_validate(prompt)
    except Exception as e:
        logger.error("create_prompt_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/prompts/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: int,
    prompt_service: PromptServiceDep,
) -> PromptResponse:
    """Get a prompt by ID."""
    prompt = await prompt_service.get_prompt_by_id(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return PromptResponse.model_validate(prompt)


@router.put("/api/prompts/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: int,
    prompt_data: PromptUpdate,
    prompt_service: PromptServiceDep,
) -> PromptResponse:
    """Update a prompt."""
    updates = prompt_data.model_dump(exclude_unset=True)

    # Convert level enum if present
    if "level" in updates and updates["level"] is not None:
        updates["level"] = PromptLevel(updates["level"].value)

    prompt = await prompt_service.update_prompt(prompt_id, updates)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    return PromptResponse.model_validate(prompt)


@router.delete("/api/prompts/{prompt_id}", status_code=204)
async def delete_prompt(
    prompt_id: int,
    prompt_service: PromptServiceDep,
) -> None:
    """Delete a prompt."""
    deleted = await prompt_service.delete_prompt(prompt_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Prompt not found")


@router.post("/api/prompts/{prompt_id}/toggle", response_model=PromptResponse)
async def toggle_prompt_active(
    prompt_id: int,
    prompt_service: PromptServiceDep,
) -> PromptResponse:
    """Toggle prompt active status."""
    prompt = await prompt_service.toggle_active(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return PromptResponse.model_validate(prompt)


@router.post("/api/prompts/seed", response_model=dict)
async def seed_prompts() -> dict:
    """Re-seed system prompts from hardcoded defaults."""
    count = await reseed_system_prompts()

    # Invalidate cache
    cache = get_prompt_cache()
    cache.invalidate()

    return {"message": f"Re-seeded {count} system prompts", "count": count}
