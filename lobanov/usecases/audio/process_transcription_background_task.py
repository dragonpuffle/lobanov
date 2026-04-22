from uuid import UUID

from lobanov.protocols.repositories import (
    AudioRecordRepositoryProtocol,
    ClinicalFactRepositoryProtocol,
    DocumentationSessionRepositoryProtocol,
    TemplateRepositoryProtocol,
    TranscriptRepositoryProtocol,
)
from lobanov.usecases.audio import TranscribeAudio
from lobanov.usecases.clinical_facts import ExtractClinicalFacts
from lobanov.usecases.transcript import PreprocessTranscript


class BackgroundTaskError(Exception):
    pass


class ProcessTranscriptionBackgroundTask[SessionT]:
    def __init__(
        self,
        session_repository: DocumentationSessionRepositoryProtocol[SessionT],
        transcript_repository: TranscriptRepositoryProtocol[SessionT],
        audio_record_repository: AudioRecordRepositoryProtocol[SessionT],
        clinical_fact_repository: ClinicalFactRepositoryProtocol[SessionT],
        template_repository: TemplateRepositoryProtocol[SessionT],
        transcribe_audio: TranscribeAudio[SessionT],
        preprocess_transcript: PreprocessTranscript[SessionT],
        extract_clinical_facts: ExtractClinicalFacts[SessionT],
    ):
        self.session_repository = session_repository
        self.transcript_repository = transcript_repository
        self.audio_record_repository = audio_record_repository
        self.clinical_fact_repository = clinical_fact_repository
        self.template_repository = template_repository
        self.transcribe_audio = transcribe_audio
        self.preprocess_transcript = preprocess_transcript
        self.extract_clinical_facts = extract_clinical_facts

    async def execute(self, session_id: UUID, language: str = "ru") -> None:
        try:
            transcript = await self.transcribe_audio.execute(session_id, language)

            async with self.session_repository.context() as session:
                updated_transcript = await self.preprocess_transcript.execute(session, transcript.id)

            async with self.session_repository.context() as session:
                await self.extract_clinical_facts.execute(session, updated_transcript.id)

        except Exception as e:
            error_message = f"Background task failed for session {session_id}: {e}"
            raise BackgroundTaskError(error_message) from e
