from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
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

router = APIRouter(prefix="/templates", tags=["templates"], route_class=DishkaRoute)


class TemplateHandlerError(Exception):
    pass


class TemplateNotFoundError(TemplateHandlerError):
    pass


@router.get(
    "",
    summary="List medical document templates",
    description="Retrieves a paginated list of medical document templates. Can filter to show only active templates.",
)
async def list_templates(
    _: Annotated[User, Depends(get_current_user)],
    template_repository: FromDishka[TemplateRepositoryProtocol[AsyncSession]],
    active_only: Annotated[bool, Query(description="Filter to show only active templates")] = True,
    limit: Annotated[
        int, Query(ge=1, le=1000, description="Maximum number of templates to return (1-1000)")
    ] = 100,
    offset: Annotated[int, Query(ge=0, description="Number of templates to skip for pagination")] = 0,
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


@router.get(
    "/{template_id}",
    summary="Get template details",
    description="Retrieves detailed information about a specific medical document template, including all its fields.",
)
async def get_template_details(
    template_id: str,
    _: Annotated[User, Depends(get_current_user)],
    template_repository: FromDishka[TemplateRepositoryProtocol[AsyncSession]],
) -> TemplateDetailsResponse:
    try:
        template_uuid = UUID(template_id)

        async with template_repository.context() as session:
            template = await template_repository.get_by_id(session, template_uuid)

            if template is None:
                error_message = f"Template not found: {template_id}"
                raise TemplateNotFoundError(error_message)

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
