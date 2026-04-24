from typing import Annotated
from uuid import UUID, uuid4

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from lobanov.app.api.v1.dependencies import get_current_user
from lobanov.app.api.v1.transcription.dto import TranscribeRequest, TranscribeResponse, TranscriptResponse
from lobanov.domain.entities.user import User
from lobanov.infra.configs import STTConfig
from lobanov.protocols.repositories import TranscriptRepositoryProtocol
from lobanov.usecases.audio import ProcessTranscriptionBackgroundTask

router = APIRouter(prefix="/sessions/{session_id}", tags=["transcription"], route_class=DishkaRoute)


class TranscriptionHandlerError(Exception):
    pass


class SessionNotFoundError(TranscriptionHandlerError):
    pass


class InvalidSessionStateError(TranscriptionHandlerError):
    pass


class AudioRecordNotFoundError(TranscriptionHandlerError):
    pass


class TranscriptionFailedError(TranscriptionHandlerError):
    pass


class TranscriptNotFoundError(TranscriptionHandlerError):
    pass


@router.post(
    "/transcribe",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start audio transcription",
    description="Starts the transcription process for the audio file associated with a session."
    " The transcription runs in the background. The session must have an uploaded audio file.",
)
async def transcribe_audio(
    session_id: str,
    request: TranscribeRequest,
    background_tasks: BackgroundTasks,
    stt_config: FromDishka[STTConfig],
    process_transcription_bg_task: FromDishka[ProcessTranscriptionBackgroundTask[AsyncSession]],
) -> TranscribeResponse:
    try:
        session_uuid = UUID(session_id)
        task_id = uuid4()
        language = request.language.value if request.language is not None else stt_config.language

        background_tasks.add_task(
            process_transcription_bg_task.execute,
            session_id=session_uuid,
            language=language,
        )

        return TranscribeResponse(
            task_id=str(task_id),
            message="Transcription task started",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session ID: {e!s}",
        ) from e
    except Exception as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            if "session" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e),
                ) from e
            if "audio" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e),
                ) from e
        if "state" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        if "transcribe" in error_msg or "transcription" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to transcribe audio",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.get(
    "/transcript",
    summary="Get transcript for a session",
    description="Retrieves the transcript text and metadata for a session."
    " The transcript must exist (transcription must be completed).",
)
async def get_transcript(
    session_id: str,
    _: Annotated[User, Depends(get_current_user)],
    transcript_repository: FromDishka[TranscriptRepositoryProtocol[AsyncSession]],
) -> TranscriptResponse:
    try:
        session_uuid = UUID(session_id)

        async with transcript_repository.context() as session:
            transcript = await transcript_repository.get_by_session_id(session, session_uuid)

            if transcript is None:
                error_message = f"Transcript not found for session {session_id}"
                raise TranscriptNotFoundError(error_message)

            return TranscriptResponse(
                id=transcript.id,
                session_id=transcript.session_id,
                audio_record_id=transcript.audio_record_id,
                text=transcript.text,
                language=transcript.language,
                confidence_score=transcript.confidence_score,
                created_at=transcript.created_at.isoformat(),
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session ID: {e!s}",
        ) from e
    except TranscriptNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transcript",
        ) from e
