from typing import Protocol, runtime_checkable

from lobanov.domain.entities.final_medical_document import FinalMedicalDocument


@runtime_checkable
class DocumentExporterProtocol(Protocol):
    async def export_to_pdf(self, document: FinalMedicalDocument) -> bytes:
        """Export a final medical document to PDF format.

        Args:
            document: The FinalMedicalDocument entity to export.

        Returns:
            The document content as bytes in PDF format.

        Raises:
            DocumentExportError: If the document cannot be exported to PDF due to processing errors.
        """
        ...

    async def export_to_json(self, document: FinalMedicalDocument) -> str:
        """Export a final medical document to JSON format.

        Args:
            document: The FinalMedicalDocument entity to export.

        Returns:
            The document content as a JSON string.

        Raises:
            DocumentExportError: If the document cannot be exported to JSON due to processing errors.
        """
        ...
