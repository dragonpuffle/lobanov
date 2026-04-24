import json
from uuid import UUID

from lobanov.domain.entities.clinical_fact import ClinicalFact
from lobanov.domain.entities.medical_document import MedicalDocument, MedicalDocumentStatus
from lobanov.domain.entities.template_field import TemplateField
from lobanov.domain.entities.transcript import Transcript
from lobanov.protocols.repositories import (
    ClinicalFactRepositoryProtocol,
    MedicalDocumentRepositoryProtocol,
    TemplateRepositoryProtocol,
    TranscriptRepositoryProtocol,
)
from lobanov.protocols.services import FileStorageProtocol
from lobanov.usecases.medical_document.consultation_protocol_pdf import (
    RenderConsultationProtocolPdf,
)
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class MedicalDocumentNotFoundError(Exception):
    pass


class InvalidDocumentStateError(Exception):
    pass


class TranscriptNotFoundError(Exception):
    pass


class SaveDocument[SessionT]:
    def __init__(  # noqa: PLR0913
        self,
        medical_document_repository: MedicalDocumentRepositoryProtocol[SessionT],
        transcript_repository: TranscriptRepositoryProtocol[SessionT],
        clinical_fact_repository: ClinicalFactRepositoryProtocol[SessionT],
        template_repository: TemplateRepositoryProtocol[SessionT],
        file_storage: FileStorageProtocol,
        render_consultation_protocol_pdf: RenderConsultationProtocolPdf,
    ):
        self.medical_document_repository = medical_document_repository
        self.transcript_repository = transcript_repository
        self.clinical_fact_repository = clinical_fact_repository
        self.template_repository = template_repository
        self.file_storage = file_storage
        self._render_consultation_protocol_pdf = render_consultation_protocol_pdf

    async def execute(
        self,
        document_id: UUID,
        output_format: str = "json",
    ) -> str:
        try:
            return await self._execute(document_id, output_format)
        except (MedicalDocumentNotFoundError, InvalidDocumentStateError, TranscriptNotFoundError, ValueError):
            raise
        except Exception:
            logger.exception("SaveDocument.execute failed")
            raise

    async def _execute(
        self,
        document_id: UUID,
        output_format: str = "json",
    ) -> str:
        async with self.medical_document_repository.context() as session:
            document = await self.medical_document_repository.get_by_id(session, document_id)
            if document is None:
                error_message = f"Medical document with id {document_id} not found"
                raise MedicalDocumentNotFoundError(error_message)

            if document.status != MedicalDocumentStatus.CONFIRMED:
                error_message = (
                    f"Cannot save document with status {document.status}. Only confirmed documents can be saved."
                )
                raise InvalidDocumentStateError(error_message)

            transcript = await self.transcript_repository.get_by_id(session, document.transcript_id)
            if transcript is None:
                error_message = f"Transcript with id {document.transcript_id} not found"
                raise TranscriptNotFoundError(error_message)

            clinical_facts = await self.clinical_fact_repository.get_by_session_id(session, document.session_id)
            template_fields = await self.template_repository.get_fields(session, document.template_id)

            fmt = output_format.lower()
            content: str | bytes
            if fmt == "json":
                content = self._export_to_json(document, transcript, clinical_facts, template_fields)
                filename = f"document_{document_id}.json"
            elif fmt == "pdf":
                field_by_name = self._field_values_by_name(clinical_facts, template_fields)
                content = self._render_consultation_protocol_pdf.execute(field_by_name, document)
                filename = f"document_{document_id}.pdf"
            else:
                error_message = f"Unsupported format: {output_format}. Supported: json, pdf."
                raise ValueError(error_message)

            return await self.file_storage.save_document(content, filename, document.session_id)

    def _field_values_by_name(
        self,
        clinical_facts: list[ClinicalFact],
        template_fields: list[TemplateField],
    ) -> dict[str, str]:
        facts_by_template_field_id: dict = {}
        for fact in clinical_facts:
            if fact.template_field_id not in facts_by_template_field_id:
                facts_by_template_field_id[fact.template_field_id] = []
            facts_by_template_field_id[fact.template_field_id].append({
                "value": fact.value,
                "confidence": fact.confidence,
            })

        out: dict[str, str] = {}
        for field in template_fields:
            matching_facts = facts_by_template_field_id.get(field.id, [])
            if matching_facts:
                best_fact = max(matching_facts, key=lambda f: f["confidence"])
                if best_fact["value"] is not None:
                    out[field.name] = str(best_fact["value"])
            elif field.default_value:
                out[field.name] = str(field.default_value)
        return out

    def _export_to_json(
        self,
        document: MedicalDocument,
        transcript: Transcript,
        clinical_facts: list[ClinicalFact],
        template_fields: list[TemplateField],
    ) -> str:
        facts_by_template_field_id = {}
        for fact in clinical_facts:
            if fact.template_field_id not in facts_by_template_field_id:
                facts_by_template_field_id[fact.template_field_id] = []
            facts_by_template_field_id[fact.template_field_id].append({
                "value": fact.value,
                "confidence": fact.confidence,
                "source_text": fact.source_text,
                "is_updated_by_user": fact.is_updated_by_user,
            })

        field_values = []
        for field in template_fields:
            matching_facts = facts_by_template_field_id.get(field.id, [])
            if matching_facts:
                best_fact = max(matching_facts, key=lambda f: f["confidence"])
                field_values.append({
                    "field_name": field.name,
                    "field_label": field.label,
                    "value": best_fact["value"],
                    "confidence": best_fact["confidence"],
                    "is_updated_by_user": best_fact["is_updated_by_user"],
                })
            elif field.default_value:
                field_values.append({
                    "field_name": field.name,
                    "field_label": field.label,
                    "value": field.default_value,
                    "confidence": 1.0,
                    "is_updated_by_user": False,
                })

        document_data = {
            "document_id": str(document.id),
            "user_id": str(document.user_id),
            "session_id": str(document.session_id),
            "template_id": str(document.template_id),
            "status": document.status.value,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat(),
            "transcript": {
                "id": str(transcript.id),
                "text": transcript.text,
                "language": transcript.language.value,
                "confidence_score": transcript.confidence_score,
            },
            "field_values": field_values,
            "clinical_facts_count": len(clinical_facts),
        }

        return json.dumps(document_data, indent=2, ensure_ascii=False)
