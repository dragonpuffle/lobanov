from collections.abc import Callable, Sequence
from pathlib import Path
from typing import final
from uuid import UUID

import dishka
from sqlalchemy.ext.asyncio import AsyncSession

import lobanov
from lobanov.adapters.repositories import (
    AudioRecordRepository,
    ClinicalFactRepository,
    DocumentationSessionRepository,
    MedicalDocumentRepository,
    TemplateRepository,
    TranscriptRepository,
    UserRepository,
)
from lobanov.adapters.services import (
    Gemma4E2BHFClinicalExtractionService,
    GigaAMSTTService,
    GraniteSpeechSTTService,
    JWTTokenService,
    LLMClinicalExtractionService,
    LocalFileStorageService,
    OpenRouterAudioSTTService,
    OpenRouterAudioService,
    PasswordManagerService,
    PhiHFClinicalExtractionService,
    Qwen3HFClinicalExtractionService,
    RussianWhisperHFSTTService,
    TextPreprocessingService,
    VibeVoiceHFSTTService,
    WhisperHFSTTService,
)
from lobanov.infra.config import GlobalConfig
from lobanov.infra.configs import (
    JWTConfig,
    NLPConfig,
    STTConfig,
    StorageConfig,
    TextPreprocessingConfig,
)
from lobanov.infra.postgres import provide_async_engine, provide_async_session_factory
from lobanov.protocols.repositories import (
    AudioRecordRepositoryProtocol,
    ClinicalFactRepositoryProtocol,
    DocumentationSessionRepositoryProtocol,
    MedicalDocumentRepositoryProtocol,
    TemplateRepositoryProtocol,
    TranscriptRepositoryProtocol,
    UserRepositoryProtocol,
)
from lobanov.protocols.services import (
    ClinicalExtractionProtocol,
    FileStorageProtocol,
    JWTTokenProtocol,
    PasswordManagerProtocol,
    SpeechRecognitionProtocol,
    TextProcessingProtocol,
)
from lobanov.usecases.audio import TranscribeAudio, UploadAudio
from lobanov.usecases.audio.process_transcription_background_task import (
    ProcessTranscriptionBackgroundTask,
    TranscriptionDependencies,
)
from lobanov.usecases.auth import LoginUser, RegisterUser
from lobanov.usecases.clinical_facts import ExtractClinicalFacts
from lobanov.usecases.document_session import (
    CreateDocumentationSession,
    DeleteSession,
    GetSessionDetails,
    GetUserSessions,
)
from lobanov.usecases.medical_document import (
    ConfirmDocument,
    GenerateMedicalDocument,
    ReviewMedicalDocument,
    SaveDocument,
    UpdateDocumentField,
    ValidateRequiredFields,
)
from lobanov.usecases.medical_document.consultation_protocol_pdf import RenderConsultationProtocolPdf
from lobanov.usecases.medical_document.document_export_types import PdfExportTemplateMap
from lobanov.usecases.transcript import PreprocessTranscript

_LOBANOV_PACKAGE_ROOT = Path(lobanov.__file__).resolve().parent

_NLP_FACTORIES: Sequence[tuple[tuple[str, ...], Callable[[NLPConfig], ClinicalExtractionProtocol]]] = (
    (("openrouter", ""), LLMClinicalExtractionService),
    (("phi_hf", "phi"), PhiHFClinicalExtractionService),
    (
        ("gemma4_e2b_hf", "gemma4_hf", "gemma4", "gemma_4_e2b"),
        Gemma4E2BHFClinicalExtractionService,
    ),
    (("qwen3_hf", "qwen3", "qwen3_06b"), Qwen3HFClinicalExtractionService),
)


def _clinical_extraction_from_config(nlp_config: NLPConfig) -> ClinicalExtractionProtocol:
    provider = nlp_config.provider.lower().strip()
    for names, ctor in _NLP_FACTORIES:
        if provider in names:
            return ctor(nlp_config)
    msg = f"Unknown nlp provider: {provider!r}"
    raise ValueError(msg)


_STT_FACTORIES: Sequence[tuple[tuple[str, ...], Callable[[STTConfig], SpeechRecognitionProtocol]]] = (
    (("whisper_hf", "openai_whisper_hf"), WhisperHFSTTService),
    (("russian_whisper_hf", "russian_whisper"), RussianWhisperHFSTTService),
    (("granite_speech_hf", "granite_speech"), GraniteSpeechSTTService),
    (("gigaam_hf", "gigaam"), GigaAMSTTService),
    (("vibevoice_hf", "vibevoice"), VibeVoiceHFSTTService),
    (("openrouter_audio",), OpenRouterAudioService),
    (("openrouter_audio_stt", "openrouter_stt"), OpenRouterAudioSTTService),
)


def _speech_recognition_from_config(stt_config: STTConfig) -> SpeechRecognitionProtocol:
    provider = stt_config.provider.lower().strip()
    for names, ctor in _STT_FACTORIES:
        if provider in names:
            return ctor(stt_config)
    msg = f"Unknown stt provider: {provider!r}"
    raise ValueError(msg)


@final
class InfraProvider(dishka.Provider):
    scope = dishka.Scope.APP

    global_config = dishka.provide(staticmethod(GlobalConfig.load))
    """глобальный конфиг приложения, загружаемый из файла"""

    subconfigs = dishka.provide_all(*GlobalConfig.subconfigs())
    """загружает все вложенные конфиги из глобального конфига"""

    async_engine = dishka.provide(staticmethod(provide_async_engine))
    """sqlalchemy engine для подключения к базе данных"""

    async_session_factory = dishka.provide(staticmethod(provide_async_session_factory))
    """фабрика сессий для подключения к базе данных"""


@final
class RepositoryProvider(dishka.Provider):
    scope = dishka.Scope.APP

    user_repository = dishka.provide(
        source=UserRepository,
        provides=UserRepositoryProtocol[AsyncSession],
    )
    """репозиторий пользователей на Postgres"""

    documentation_session_repository = dishka.provide(
        source=DocumentationSessionRepository,
        provides=DocumentationSessionRepositoryProtocol[AsyncSession],
    )
    """репозиторий сессий документации на Postgres"""

    audio_record_repository = dishka.provide(
        source=AudioRecordRepository,
        provides=AudioRecordRepositoryProtocol[AsyncSession],
    )
    """репозиторий аудиозаписей на Postgres"""

    transcript_repository = dishka.provide(
        source=TranscriptRepository,
        provides=TranscriptRepositoryProtocol[AsyncSession],
    )
    """репозиторий транскрипций на Postgres"""

    clinical_fact_repository = dishka.provide(
        source=ClinicalFactRepository,
        provides=ClinicalFactRepositoryProtocol[AsyncSession],
    )
    """репозиторий клинических фактов на Postgres"""

    template_repository = dishka.provide(
        source=TemplateRepository,
        provides=TemplateRepositoryProtocol[AsyncSession],
    )
    """репозиторий шаблонов на Postgres"""

    medical_document_repository = dishka.provide(
        source=MedicalDocumentRepository,
        provides=MedicalDocumentRepositoryProtocol[AsyncSession],
    )
    """репозиторий медицинских документов на Postgres"""


@final
class ServiceProvider(dishka.Provider):
    scope = dishka.Scope.APP

    @dishka.provide
    def provide_file_storage_service(self, storage_config: StorageConfig) -> FileStorageProtocol:
        """сервис локального хранения файлов"""
        return LocalFileStorageService(storage_config)

    @dishka.provide
    def provide_speech_recognition_service(self, stt_config: STTConfig) -> SpeechRecognitionProtocol:
        """сервис распознавания речи"""
        return _speech_recognition_from_config(stt_config)

    @dishka.provide
    def provide_text_preprocessing_service(self, text_cfg: TextPreprocessingConfig) -> TextProcessingProtocol:
        """сервис предобработки текста"""
        return TextPreprocessingService(text_cfg)

    @dishka.provide
    def provide_clinical_extraction_service(self, nlp_config: NLPConfig) -> ClinicalExtractionProtocol:
        """сервис извлечения клинической информации (openrouter или локальная HF-модель)"""
        return _clinical_extraction_from_config(nlp_config)

    @dishka.provide
    def provide_jwt_token_service(self, jwt_config: JWTConfig) -> JWTTokenProtocol:
        """сервис управления JWT токенами"""
        return JWTTokenService(jwt_config)

    password_manager_service = dishka.provide(
        source=PasswordManagerService,
        provides=PasswordManagerProtocol,
    )
    """сервис управления паролями"""


@final
class UseCaseProvider(dishka.Provider):
    scope = dishka.Scope.REQUEST

    @dishka.provide
    def provide_register_user_usecase(
        self,
        user_repository: UserRepositoryProtocol[AsyncSession],
        password_manager: PasswordManagerProtocol,
    ) -> RegisterUser[AsyncSession]:
        """юзкейс регистрации пользователя"""
        return RegisterUser[AsyncSession](
            user_repository=user_repository,
            password_manager=password_manager,
        )

    @dishka.provide
    def provide_login_user_usecase(
        self,
        user_repository: UserRepositoryProtocol[AsyncSession],
        password_manager: PasswordManagerProtocol,
        jwt_token_service: JWTTokenProtocol,
        jwt_config: JWTConfig,
    ) -> LoginUser[AsyncSession]:
        """юзкейс входа пользователя"""
        return LoginUser[AsyncSession](
            user_repository=user_repository,
            password_manager=password_manager,
            jwt_token_service=jwt_token_service,
            jwt_config=jwt_config,
        )

    @dishka.provide
    def provide_create_documentation_session_usecase(
        self,
        user_repository: UserRepositoryProtocol[AsyncSession],
        session_repository: DocumentationSessionRepositoryProtocol[AsyncSession],
    ) -> CreateDocumentationSession[AsyncSession]:
        """юзкейс создания сессии документации"""
        return CreateDocumentationSession[AsyncSession](
            user_repository=user_repository,
            session_repository=session_repository,
        )

    @dishka.provide
    def provide_upload_audio_usecase(
        self,
        session_repository: DocumentationSessionRepositoryProtocol[AsyncSession],
        audio_record_repository: AudioRecordRepositoryProtocol[AsyncSession],
        file_storage_service: FileStorageProtocol,
    ) -> UploadAudio[AsyncSession]:
        """юзкейс загрузки аудиофайла"""
        return UploadAudio[AsyncSession](
            session_repository=session_repository,
            audio_record_repository=audio_record_repository,
            file_storage=file_storage_service,
        )

    @dishka.provide
    def provide_transcribe_audio_usecase(
        self,
        session_repository: DocumentationSessionRepositoryProtocol[AsyncSession],
        audio_record_repository: AudioRecordRepositoryProtocol[AsyncSession],
        transcript_repository: TranscriptRepositoryProtocol[AsyncSession],
        speech_recognition_service: SpeechRecognitionProtocol,
    ) -> TranscribeAudio[AsyncSession]:
        """юзкейс транскрибации аудио"""
        return TranscribeAudio[AsyncSession](
            session_repository=session_repository,
            audio_record_repository=audio_record_repository,
            transcript_repository=transcript_repository,
            stt_service=speech_recognition_service,
        )

    @dishka.provide
    def provide_process_transcription_background_task(  # noqa: PLR0913
        self,
        session_repository: DocumentationSessionRepositoryProtocol[AsyncSession],
        transcript_repository: TranscriptRepositoryProtocol[AsyncSession],
        audio_record_repository: AudioRecordRepositoryProtocol[AsyncSession],
        clinical_fact_repository: ClinicalFactRepositoryProtocol[AsyncSession],
        template_repository: TemplateRepositoryProtocol[AsyncSession],
        transcribe_audio: TranscribeAudio[AsyncSession],
        preprocess_transcript: PreprocessTranscript[AsyncSession],
        extract_clinical_facts: ExtractClinicalFacts[AsyncSession],
    ) -> ProcessTranscriptionBackgroundTask[AsyncSession]:
        """фоновая цепочка: транскрипция → препроцессинг → извлечение фактов"""
        deps = TranscriptionDependencies(
            session_repository=session_repository,
            transcript_repository=transcript_repository,
            audio_record_repository=audio_record_repository,
            clinical_fact_repository=clinical_fact_repository,
            template_repository=template_repository,
            transcribe_audio=transcribe_audio,
            preprocess_transcript=preprocess_transcript,
            extract_clinical_facts=extract_clinical_facts,
        )
        return ProcessTranscriptionBackgroundTask(deps)

    @dishka.provide
    def provide_preprocess_transcript_usecase(
        self,
        transcript_repository: TranscriptRepositoryProtocol[AsyncSession],
        text_preprocessing_service: TextProcessingProtocol,
    ) -> PreprocessTranscript[AsyncSession]:
        """юзкейс предобработки транскрипции"""
        return PreprocessTranscript[AsyncSession](
            transcript_repository=transcript_repository,
            text_processing_service=text_preprocessing_service,
        )

    @dishka.provide
    def provide_extract_clinical_facts_usecase(
        self,
        transcript_repository: TranscriptRepositoryProtocol[AsyncSession],
        clinical_fact_repository: ClinicalFactRepositoryProtocol[AsyncSession],
        template_repository: TemplateRepositoryProtocol[AsyncSession],
        session_repository: DocumentationSessionRepositoryProtocol[AsyncSession],
        clinical_extraction_service: ClinicalExtractionProtocol,
    ) -> ExtractClinicalFacts[AsyncSession]:
        """юзкейс извлечения клинических фактов"""
        return ExtractClinicalFacts[AsyncSession](
            transcript_repository=transcript_repository,
            clinical_fact_repository=clinical_fact_repository,
            template_repository=template_repository,
            session_repository=session_repository,
            clinical_extraction_service=clinical_extraction_service,
        )

    @dishka.provide
    def provide_generate_medical_document_usecase(
        self,
        session_repository: DocumentationSessionRepositoryProtocol[AsyncSession],
        transcript_repository: TranscriptRepositoryProtocol[AsyncSession],
        clinical_fact_repository: ClinicalFactRepositoryProtocol[AsyncSession],
        medical_document_repository: MedicalDocumentRepositoryProtocol[AsyncSession],
    ) -> GenerateMedicalDocument[AsyncSession]:
        """юзкейс генерации медицинского документа"""
        return GenerateMedicalDocument[AsyncSession](
            session_repository=session_repository,
            transcript_repository=transcript_repository,
            clinical_fact_repository=clinical_fact_repository,
            medical_document_repository=medical_document_repository,
        )

    @dishka.provide
    def provide_validate_required_fields_usecase(
        self,
        template_repository: TemplateRepositoryProtocol[AsyncSession],
        clinical_fact_repository: ClinicalFactRepositoryProtocol[AsyncSession],
    ) -> ValidateRequiredFields[AsyncSession]:
        """юзкейс валидации обязательных полей"""
        return ValidateRequiredFields[AsyncSession](
            template_repository=template_repository,
            clinical_fact_repository=clinical_fact_repository,
        )

    @dishka.provide
    def provide_review_medical_document_usecase(
        self,
        medical_document_repository: MedicalDocumentRepositoryProtocol[AsyncSession],
        transcript_repository: TranscriptRepositoryProtocol[AsyncSession],
        clinical_fact_repository: ClinicalFactRepositoryProtocol[AsyncSession],
        template_repository: TemplateRepositoryProtocol[AsyncSession],
        validate_required_fields: ValidateRequiredFields[AsyncSession],
    ) -> ReviewMedicalDocument[AsyncSession]:
        """юзкейс просмотра медицинского документа"""
        return ReviewMedicalDocument[AsyncSession](
            medical_document_repository=medical_document_repository,
            transcript_repository=transcript_repository,
            clinical_fact_repository=clinical_fact_repository,
            template_repository=template_repository,
            validate_required_fields=validate_required_fields,
        )

    @dishka.provide
    def provide_update_document_field_usecase(
        self,
        medical_document_repository: MedicalDocumentRepositoryProtocol[AsyncSession],
        clinical_fact_repository: ClinicalFactRepositoryProtocol[AsyncSession],
        template_repository: TemplateRepositoryProtocol[AsyncSession],
        validate_required_fields: ValidateRequiredFields[AsyncSession],
    ) -> UpdateDocumentField[AsyncSession]:
        """юзкейс обновления поля документа"""
        return UpdateDocumentField[AsyncSession](
            medical_document_repository=medical_document_repository,
            clinical_fact_repository=clinical_fact_repository,
            template_repository=template_repository,
            validate_required_fields=validate_required_fields,
        )

    @dishka.provide
    def provide_confirm_document_usecase(
        self,
        session_repository: DocumentationSessionRepositoryProtocol[AsyncSession],
        medical_document_repository: MedicalDocumentRepositoryProtocol[AsyncSession],
        validate_required_fields: ValidateRequiredFields[AsyncSession],
    ) -> ConfirmDocument[AsyncSession]:
        """юзкейс подтверждения документа"""
        return ConfirmDocument[AsyncSession](
            medical_document_repository=medical_document_repository,
            session_repository=session_repository,
            validate_required_fields=validate_required_fields,
        )

    @dishka.provide
    def provide_pdf_export_template_map(self) -> PdfExportTemplateMap:
        """template_id (шаблон МД) → jinja-файл PDF; сюда же добавлять новые шаблоны."""
        consultation = UUID("550e8400-e29b-41d4-a716-446655440010")
        jinja = _LOBANOV_PACKAGE_ROOT / "templates" / "document_export" / "550e8400-e29b-41d4-a716-446655440010.html.j2"
        return PdfExportTemplateMap({consultation: jinja})

    @dishka.provide
    def provide_render_consultation_protocol_pdf(
        self,
        template_map: PdfExportTemplateMap,
    ) -> RenderConsultationProtocolPdf:
        """юзкейс PDF по карте jinja-шаблонов"""
        return RenderConsultationProtocolPdf(template_id_to_jinja_file=template_map)

    @dishka.provide
    def provide_save_document_usecase(  # noqa: PLR0913
        self,
        medical_document_repository: MedicalDocumentRepositoryProtocol[AsyncSession],
        transcript_repository: TranscriptRepositoryProtocol[AsyncSession],
        clinical_fact_repository: ClinicalFactRepositoryProtocol[AsyncSession],
        template_repository: TemplateRepositoryProtocol[AsyncSession],
        file_storage_service: FileStorageProtocol,
        render_consultation_protocol_pdf: RenderConsultationProtocolPdf,
    ) -> SaveDocument[AsyncSession]:
        """юзкейс сохранения документа"""
        return SaveDocument[AsyncSession](
            medical_document_repository=medical_document_repository,
            transcript_repository=transcript_repository,
            clinical_fact_repository=clinical_fact_repository,
            template_repository=template_repository,
            file_storage=file_storage_service,
            render_consultation_protocol_pdf=render_consultation_protocol_pdf,
        )

    @dishka.provide
    def provide_get_user_sessions_usecase(
        self,
        user_repository: UserRepositoryProtocol[AsyncSession],
        session_repository: DocumentationSessionRepositoryProtocol[AsyncSession],
    ) -> GetUserSessions[AsyncSession]:
        """юзкейс получения сессий пользователя"""
        return GetUserSessions[AsyncSession](
            user_repository=user_repository,
            session_repository=session_repository,
        )

    @dishka.provide
    def provide_get_session_details_usecase(
        self,
        user_repository: UserRepositoryProtocol[AsyncSession],
        session_repository: DocumentationSessionRepositoryProtocol[AsyncSession],
        audio_record_repository: AudioRecordRepositoryProtocol[AsyncSession],
        transcript_repository: TranscriptRepositoryProtocol[AsyncSession],
        medical_document_repository: MedicalDocumentRepositoryProtocol[AsyncSession],
    ) -> GetSessionDetails[AsyncSession]:
        """юзкейс получения деталей сессии"""
        return GetSessionDetails[AsyncSession](
            user_repository=user_repository,
            session_repository=session_repository,
            audio_record_repository=audio_record_repository,
            transcript_repository=transcript_repository,
            medical_document_repository=medical_document_repository,
        )

    @dishka.provide
    def provide_delete_session_usecase(  # noqa: PLR0913
        self,
        user_repository: UserRepositoryProtocol[AsyncSession],
        session_repository: DocumentationSessionRepositoryProtocol[AsyncSession],
        audio_record_repository: AudioRecordRepositoryProtocol[AsyncSession],
        transcript_repository: TranscriptRepositoryProtocol[AsyncSession],
        clinical_fact_repository: ClinicalFactRepositoryProtocol[AsyncSession],
        medical_document_repository: MedicalDocumentRepositoryProtocol[AsyncSession],
    ) -> DeleteSession[AsyncSession]:
        """юзкейс удаления сессии"""
        return DeleteSession[AsyncSession](
            user_repository=user_repository,
            session_repository=session_repository,
            audio_record_repository=audio_record_repository,
            transcript_repository=transcript_repository,
            clinical_fact_repository=clinical_fact_repository,
            medical_document_repository=medical_document_repository,
        )


container = dishka.make_async_container(InfraProvider(), RepositoryProvider(), ServiceProvider(), UseCaseProvider())
