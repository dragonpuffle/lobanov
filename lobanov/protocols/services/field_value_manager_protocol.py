from uuid import UUID
from typing import Protocol, runtime_checkable

from lobanov.domain.entities.medical_document_draft import MedicalDocumentDraft
from lobanov.domain.entities.medical_document_template import MedicalDocumentTemplate
from lobanov.domain.entities.draft_field_value import DraftFieldValue
from lobanov.domain.entities.template_field import TemplateField


class ValidationResult:
    def __init__(
        self,
        is_valid: bool,
        missing_fields: list[TemplateField],
        invalid_fields: list[TemplateField],
    ) -> None:
        self.is_valid = is_valid
        self.missing_fields = missing_fields
        self.invalid_fields = invalid_fields


@runtime_checkable
class FieldValueManagerProtocol(Protocol):
    async def get_field_value(
        self, draft: MedicalDocumentDraft, field_id: UUID
    ) -> DraftFieldValue | None:
        """Retrieve the value of a specific field from a draft.

        Args:
            draft: The MedicalDocumentDraft entity containing the field.
            field_id: The UUID of the field to retrieve.

        Returns:
            The DraftFieldValue entity if found, None otherwise.

        Raises:
            FieldValueManagerError: If the field value cannot be retrieved due to processing errors.
        """
        ...

    async def update_field_value(
        self,
        draft: MedicalDocumentDraft,
        field_id: UUID,
        value: str,
        status: str,
    ) -> None:
        """Update the value and status of a specific field in a draft.

        Args:
            draft: The MedicalDocumentDraft entity containing the field.
            field_id: The UUID of the field to update.
            value: The new value to set for the field.
            status: The new status for the field (e.g., 'pending', 'verified', 'rejected').

        Returns:
            None

        Raises:
            FieldValueManagerError: If the field value cannot be updated due to processing errors.
        """
        ...

    async def validate_required_fields(
        self, draft: MedicalDocumentDraft, template: MedicalDocumentTemplate
    ) -> ValidationResult:
        """Validate that all required fields in a draft have valid values.

        Args:
            draft: The MedicalDocumentDraft entity to validate.
            template: The MedicalDocumentTemplate defining required fields.

        Returns:
            ValidationResult containing validation status, missing fields, and invalid fields.

        Raises:
            FieldValueManagerError: If validation cannot be performed due to processing errors.
        """
        ...
