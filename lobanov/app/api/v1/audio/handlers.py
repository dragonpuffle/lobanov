from io import BytesIO
from uuid import UUID

import aiofiles
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from lobanov.app.api.v1.audio.dto import AudioUploadResponse
from lobanov.protocols.repositories import AudioRecordRepositoryProtocol
from lobanov.usecases.audio import UploadAudio

router = APIRouter(prefix="/sessions/{session_id}/audio", tags=["audio"], route_class=DishkaRoute)


class AudioHandlerError(Exception):
    pass


class AudioNotFoundError(AudioHandlerError):
    pass


class InvalidSessionStateError(AudioHandlerError):
    pass


class AudioUploadFailedError(AudioHandlerError):
    pass


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Upload audio file for a session",
    description="Uploads an audio file to a documentation session. The session must be in 'created' state."
    " Supports common audio formats (MP3, WAV, M4A, etc.).",
)
async def upload_audio(
    session_id: str,
    file: UploadFile,
    upload_audio_use_case: FromDishka[UploadAudio[AsyncSession]],
) -> AudioUploadResponse:
    try:
        session_uuid = UUID(session_id)
        file_content = BytesIO(await file.read())

        audio_record = await upload_audio_use_case.execute(
            session_id=session_uuid,
            file=file_content,
            filename=file.filename or "audio.mp3",
        )

        return AudioUploadResponse(
            id=audio_record.id,
            session_id=audio_record.session_id,
            file_name=audio_record.file_name,
            file_size=audio_record.file_size,
            duration=audio_record.duration,
            format=audio_record.format,
            uploaded_at=audio_record.created_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session ID: {e!s}",
        ) from e
    except Exception as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        if "state" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload audio",
        ) from e


@router.get(
    "",
    summary="Download audio file for a session",
    description="Retrieves and downloads the audio file associated with a documentation session.",
)
async def get_audio(
    session_id: str,
    audio_record_repository: FromDishka[AudioRecordRepositoryProtocol[AsyncSession]],
) -> FileResponse:
    try:
        session_uuid = UUID(session_id)

        async with audio_record_repository.context() as session:
            audio_record = await audio_record_repository.get_by_session_id(session, session_uuid)

            if audio_record is None:
                error_message = f"Audio not found for session {session_id}"
                raise AudioNotFoundError(error_message)

            file_path = audio_record.file_path

            if not await aiofiles.os.path.exists(file_path):
                error_message = f"Audio file not found at {file_path}"
                raise AudioNotFoundError(error_message)

            return FileResponse(
                path=file_path,
                media_type=f"audio/{audio_record.format}",
                filename=audio_record.file_name,
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session ID: {e!s}",
        ) from e
    except AudioNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audio",
        ) from e
