from typing import Protocol, List, runtime_checkable

from lobanov.domain.entities.medical_document_template import MedicalDocumentTemplate
from lobanov.domain.entities.clinical_fact import ClinicalFact
from lobanov.domain.entities.medical_document_draft import MedicalDocumentDraft


class ValidationResult:
    def __init__(
        self, is_valid: bool, missing_fields: List[str], invalid_fields: List[str]
    ) -> None:
        self.is_valid = is_valid
        self.missing_fields = missing_fields
        self.invalid_fields = invalid_fields


@runtime_checkable
class DraftGenerationProtocol(Protocol):
    async def generate_draft(
        self, template: MedicalDocumentTemplate, facts: List[ClinicalFact]
    ) -> MedicalDocumentDraft:
        """Generate a medical document draft from a template and clinical facts.

        Args:
            template: The MedicalDocumentTemplate defining the document structure.
            facts: List of ClinicalFact entities containing extracted clinical information.

        Returns:
            The generated MedicalDocumentDraft entity with populated field values.

        Raises:
            DraftGenerationError: If draft generation fails due to invalid template or insufficient facts.
        """
        ...

    async def validate_draft(self, draft: MedicalDocumentDraft) -> ValidationResult:
        """Validate a medical document draft for completeness and correctness.

        Args:
            draft: The MedicalDocumentDraft entity to validate.

        Returns:
            ValidationResult containing validation status, missing fields, and invalid fields.

        Raises:
            DraftGenerationError: If validation cannot be performed due to processing errors.
        """
        ...
