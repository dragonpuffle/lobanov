from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from lobanov.app.api.v1.dependencies import get_current_user
from lobanov.app.api.v1.documentation_session.dto import (
    CreateSessionRequest,
    SessionDetailsResponse,
    SessionListResponse,
    SessionResponse,
)
from lobanov.domain import DocumentationSessionStatus, User
from lobanov.usecases.document_session import (
    CreateDocumentationSession,
    GetSessionDetails,
    GetUserSessions,
)

router = APIRouter(prefix="/sessions", tags=["sessions"], route_class=DishkaRoute)


class SessionHandlerError(Exception):
    pass


class UserNotFoundError(SessionHandlerError):
    pass


class SessionNotFoundError(SessionHandlerError):
    pass


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new documentation session",
    description="Creates a new documentation session for the authenticated user."
    " A session represents a complete workflow from audio upload to document confirmation.",
)
async def create_session(
    request: CreateSessionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    create_session_use_case: FromDishka[CreateDocumentationSession[AsyncSession]],
) -> SessionResponse:
    try:
        session = await create_session_use_case.execute(current_user.id, request.template_id)
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            template_id=session.template_id,
            status=session.status,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session",
        ) from e


@router.get(
    "",
    summary="List user's documentation sessions",
    description="Retrieves a paginated list of documentation sessions for the authenticated user."
    " Supports filtering by session status.",
)
async def get_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    get_user_sessions_use_case: FromDishka[GetUserSessions[AsyncSession]],
    limit: Annotated[int, Query(ge=1, le=1000, description="Maximum number of sessions to return (1-1000)")] = 100,
    offset: Annotated[int, Query(ge=0, description="Number of sessions to skip for pagination")] = 0,
    status_filter: Annotated[
        DocumentationSessionStatus | None,
        Query(
            alias="status",
            description="Filter sessions by status (created, audio_uploaded, transcribed, draft_created, confirmed)",
        ),
    ] = None,
) -> SessionListResponse:
    try:
        sessions = await get_user_sessions_use_case.execute(
            user_id=current_user.id,
            limit=limit,
            offset=offset,
            status=status_filter,
        )
        return SessionListResponse(
            sessions=[
                SessionResponse(
                    id=session.id,
                    user_id=session.user_id,
                    template_id=session.template_id,
                    status=session.status,
                    created_at=session.created_at.isoformat(),
                    updated_at=session.updated_at.isoformat(),
                )
                for session in sessions
            ],
            total=len(sessions),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions",
        ) from e


@router.get(
    "/{session_id}",
    summary="Get session details",
    description="Retrieves detailed information about a specific documentation session,"
    " including the presence of audio, transcript, and medical document.",
)
async def get_session_details(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    get_session_details_use_case: FromDishka[GetSessionDetails[AsyncSession]],
) -> SessionDetailsResponse:
    try:
        session_uuid = UUID(session_id)
        details = await get_session_details_use_case.execute(
            session_id=session_uuid,
            user_id=current_user.id,
        )
        return SessionDetailsResponse(
            id=details.session.id,
            user_id=details.session.user_id,
            template_id=details.session.template_id,
            status=details.session.status,
            created_at=details.session.created_at.isoformat(),
            updated_at=details.session.updated_at.isoformat(),
            has_audio=details.audio_record is not None,
            has_transcript=details.transcript is not None,
            has_document=details.medical_document is not None,
        )
    except (ValueError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session ID: {e!s}",
        ) from e
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session details",
        ) from e
