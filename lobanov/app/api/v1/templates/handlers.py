from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from lobanov.app.api.v1.dependencies import get_current_user
from lobanov.app.api.v1.templates.dto import (
    TemplateDetailsResponse,
    TemplateFieldDTO,
    TemplateListResponse,
    TemplateResponse,
)
from lobanov.domain.entities.user import User
from lobanov.protocols.repositories import TemplateRepositoryProtocol

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateHandlerError(Exception):
    pass


class TemplateNotFoundError(TemplateHandlerError):
    pass


@router.get("")
async def list_templates(
    current_user: Annotated[User, Depends(get_current_user)],
    template_repository: TemplateRepositoryProtocol[AsyncSession],
    active_only: bool = Query(True, description="Filter to show only active templates"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> TemplateListResponse:
    try:
        async with template_repository.context() as session:
            if active_only:
                templates = await template_repository.get_active(session, limit=limit, offset=offset)
            else:
                templates = await template_repository.get_all(session, limit=limit, offset=offset)

            return TemplateListResponse(
                templates=[
                    TemplateResponse(
                        id=template.id,
                        name=template.name,
                        description=template.description,
                        version=template.version,
                        is_active=template.is_active,
                        created_at=template.created_at.isoformat(),
                        updated_at=template.updated_at.isoformat(),
                    )
                    for template in templates
                ],
                total=len(templates),
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve templates",
        ) from e


@router.get("/{template_id}")
async def get_template_details(
    template_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    template_repository: TemplateRepositoryProtocol[AsyncSession],
) -> TemplateDetailsResponse:
    try:
        from uuid import UUID

        template_uuid = UUID(template_id)

        async with template_repository.context() as session:
            template = await template_repository.get_by_id(session, template_uuid)

            if template is None:
                raise TemplateNotFoundError(f"Template not found: {template_id}")

            fields = await template_repository.get_fields(session, template_uuid)

            return TemplateDetailsResponse(
                id=template.id,
                name=template.name,
                description=template.description,
                version=template.version,
                is_active=template.is_active,
                created_at=template.created_at.isoformat(),
                updated_at=template.updated_at.isoformat(),
                fields=[
                    TemplateFieldDTO(
                        id=field.id,
                        name=field.name,
                        label=field.label,
                        is_required=field.is_required,
                        default_value=field.default_value,
                        options=field.options,
                        order=field.order,
                    )
                    for field in fields
                ],
            )
    except (ValueError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template ID: {e!s}",
        ) from e
    except TemplateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template details",
        ) from e
