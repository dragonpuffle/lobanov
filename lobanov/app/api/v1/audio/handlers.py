from io import BytesIO
from typing import Annotated
from uuid import UUID

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from lobanov.app.api.v1.audio.dto import AudioUploadResponse
from lobanov.app.api.v1.dependencies import get_current_user
from lobanov.domain.entities.user import User
from lobanov.protocols.repositories import AudioRecordRepositoryProtocol
from lobanov.usecases.audio import UploadAudio

router = APIRouter(prefix="/sessions/{session_id}/audio", tags=["audio"])


class AudioHandlerError(Exception):
    pass


class AudioNotFoundError(AudioHandlerError):
    pass


class InvalidSessionStateError(AudioHandlerError):
    pass


class AudioUploadFailedError(AudioHandlerError):
    pass


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_audio(
    session_id: str,
    file: UploadFile,
    current_user: Annotated[User, Depends(get_current_user)],
    upload_audio_use_case: UploadAudio[AsyncSession],
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


@router.get("")
async def get_audio(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    audio_record_repository: AudioRecordRepositoryProtocol[AsyncSession],
) -> FileResponse:
    try:
        session_uuid = UUID(session_id)

        async with audio_record_repository.context() as session:
            audio_record = await audio_record_repository.get_by_session_id(session, session_uuid)

            if audio_record is None:
                raise AudioNotFoundError(f"Audio not found for session {session_id}")

            file_path = audio_record.file_path

            if not await aiofiles.os.path.exists(file_path):
                raise AudioNotFoundError(f"Audio file not found at {file_path}")

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
