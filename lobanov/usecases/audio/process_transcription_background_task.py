from dataclasses import dataclass
from uuid import UUID

from lobanov.protocols.repositories import (
    AudioRecordRepositoryProtocol,
    ClinicalFactRepositoryProtocol,
    DocumentationSessionRepositoryProtocol,
    TemplateRepositoryProtocol,
    TranscriptRepositoryProtocol,
)
from lobanov.usecases.audio.transcribe_audio import TranscribeAudio
from lobanov.usecases.clinical_facts.extract_clinical_facts import ExtractClinicalFacts
from lobanov.usecases.transcript.preprocess_transcript import PreprocessTranscript
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class BackgroundTaskError(Exception):
    pass


@dataclass
class TranscriptionDependencies[SessionT]:
    session_repository: DocumentationSessionRepositoryProtocol[SessionT]
    transcript_repository: TranscriptRepositoryProtocol[SessionT]
    audio_record_repository: AudioRecordRepositoryProtocol[SessionT]
    clinical_fact_repository: ClinicalFactRepositoryProtocol[SessionT]
    template_repository: TemplateRepositoryProtocol[SessionT]
    transcribe_audio: TranscribeAudio[SessionT]
    preprocess_transcript: PreprocessTranscript[SessionT]
    extract_clinical_facts: ExtractClinicalFacts[SessionT]


class ProcessTranscriptionBackgroundTask[SessionT]:
    def __init__(self, dependencies: TranscriptionDependencies[SessionT]):
        self.dependencies = dependencies

    async def execute(self, session_id: UUID, language: str = "ru") -> None:
        try:
            transcript = await self.dependencies.transcribe_audio.execute(session_id, language)

            async with self.dependencies.session_repository.context() as session:
                updated_transcript = await self.dependencies.preprocess_transcript.execute(session, transcript.id)

            async with self.dependencies.session_repository.context() as session:
                await self.dependencies.extract_clinical_facts.execute(session, updated_transcript.id)

        except Exception as e:
            logger.exception("Background transcription task failed for session {sid}", sid=session_id)
            error_message = f"Background task failed for session {session_id}: {e}"
            raise BackgroundTaskError(error_message) from e
