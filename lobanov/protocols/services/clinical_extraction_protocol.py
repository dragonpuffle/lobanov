from typing import Protocol, List, runtime_checkable

from lobanov.domain.entities.clinical_fact import ClinicalFact
from lobanov.domain.entities.template_field import TemplateField


@runtime_checkable
class ClinicalExtractionProtocol(Protocol):
    async def extract_clinical_facts(
        self, transcript: str, template_fields: List[TemplateField]
    ) -> List[ClinicalFact]:
        """Extract clinical facts from a transcript based on template field definitions.

        Args:
            transcript: The text transcript to analyze for clinical information.
            template_fields: List of template field definitions specifying what to extract.

        Returns:
            List of ClinicalFact entities extracted from the transcript.

        Raises:
            ClinicalExtractionError: If extraction fails due to processing errors or invalid input.
        """
        ...

    async def get_confidence(self, fact: ClinicalFact) -> float:
        """Get the confidence score for a specific clinical fact.

        Args:
            fact: The ClinicalFact entity to evaluate.

        Returns:
            Confidence score as a float between 0.0 and 1.0, where 1.0 indicates highest confidence.

        Raises:
            ClinicalExtractionError: If confidence cannot be calculated due to invalid fact data.
        """
        ...
