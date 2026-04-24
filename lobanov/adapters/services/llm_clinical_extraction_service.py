# ruff: noqa: E501

import json
from datetime import UTC, datetime
from typing import override
from uuid import uuid4

import httpx

from lobanov.domain.entities.clinical_fact import ClinicalFact
from lobanov.protocols import ClinicalExtractionProtocol
from lobanov.protocols.services.clinical_extraction_protocol import TemplateField
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)

_JSON_EXAMPLE = """{
  "complaints": {
    "field_name": "complaints",
    "value": "боль в груди",
    "confidence": 0.9,
    "source_text": "жалуется на боль в груди"
  }
}"""


class ClinicalExtractionError(Exception):
    pass


def _parse_llm_json_object(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    data = json.loads(text)
    if not isinstance(data, dict):
        msg = "LLM response must be a JSON object, not a list or other type"
        raise ClinicalExtractionError(msg)
    return data


class LLMClinicalExtractionService(ClinicalExtractionProtocol):
    def __init__(self, use_mock: bool = True, api_key: str | None = None, model: str = "gpt-4"):  # noqa: FBT001, FBT002
        self.use_mock = use_mock
        self.api_key = api_key
        self.model = model

    @override
    async def extract_clinical_facts(self, transcript: str, template_fields: list[TemplateField]) -> list[ClinicalFact]:
        try:
            if not transcript:
                return []

            if not template_fields:
                return []

            facts: list[ClinicalFact] = []

            if self.use_mock:
                facts = await self._mock_extract_facts(transcript, template_fields)
            else:
                facts = await self._llm_extract_facts(transcript, template_fields)

            return facts  # noqa: TRY300
        except Exception as e:
            logger.exception("Failed to extract clinical facts")
            err_msg = f"Failed to extract clinical facts: {e}"
            raise ClinicalExtractionError(err_msg) from e

    @override
    async def get_confidence(self, fact: ClinicalFact) -> float:
        try:
            if not fact:
                return 0.0

            return fact.confidence  # noqa: TRY300
        except Exception as e:
            logger.exception("Failed to get confidence for fact")
            err_msg = f"Failed to get confidence for fact: {e}"
            raise ClinicalExtractionError(err_msg) from e

    async def _mock_extract_facts(self, transcript: str, template_fields: list[TemplateField]) -> list[ClinicalFact]:
        facts: list[ClinicalFact] = []

        transcript_lower = transcript.lower()

        for field in template_fields:
            field_name = field.name.lower()
            field_label = field.label.lower()

            if field_name in transcript_lower or field_label in transcript_lower:
                value = self._extract_value_for_field(transcript, field)

                if value:
                    source_text, start_idx, end_idx = self._find_source_in_transcript(transcript, value)

                    fact = ClinicalFact(
                        id=uuid4(),
                        session_id=uuid4(),
                        transcript_id=uuid4(),
                        template_field_id=field.id,
                        is_updated_by_user=False,
                        value=value,
                        confidence=0.8,
                        source_text=source_text,
                        source_start_index=start_idx,
                        source_end_index=end_idx,
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                    )
                    facts.append(fact)

        return facts

    async def _llm_extract_facts(self, transcript: str, template_fields: list[TemplateField]) -> list[ClinicalFact]:
        facts: list[ClinicalFact] = []

        field_descriptions = "\n".join([f"- {field.name} ({field.label})" for field in template_fields])
        field_names_quoted = ", ".join(f'"{f.name}"' for f in template_fields)

        prompt = f"""You extract structured clinical data from a medical dialog transcript.

Template fields (use field_name exactly as listed):
{field_descriptions}

Transcript:
{transcript}

Output rules (strict):
- Return ONE JSON object only. No markdown fences, no comments, no text before or after the JSON.
- Top-level keys: one key per extracted fact. Each key should identify the field (preferably the field `name` from the list: {field_names_quoted}).
- Each value MUST be an object with exactly these string/number fields:
  - "field_name": same as in the template list (field `name`, string)
  - "value": extracted value (string; use "" if nothing reliable)
  - "confidence": number from 0.0 to 1.0
  - "source_text": a verbatim or minimal quote from the transcript that supports the value (string; the exact substring that will be searched in the full transcript)
- Include only fields where you have a meaningful value and supporting source_text from this transcript.
- Do NOT put character position indices in the response.

Example shape (keys and `field_name` must match your template):
{_JSON_EXAMPLE}"""

        try:
            if not self.api_key:
                raise ClinicalExtractionError("API key is required for LLM extraction")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/lobanov/lobanov",
                "X-Title": "Lobanov Clinical Documentation",
            }

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a medical information extraction assistant. "
                            "Reply with a single JSON object only: top-level keys are field identifiers, "
                            "each value is an object with keys field_name, value, confidence, source_text. "
                            "No markdown, no extra prose."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()

                content = result["choices"][0]["message"]["content"]

                extracted_data = _parse_llm_json_object(content)

                field_name_to_id = {field.name: field.id for field in template_fields}

                for _top_key, item in extracted_data.items():
                    if not isinstance(item, dict):
                        continue
                    field_name = str(item.get("field_name", "") or _top_key).strip()
                    template_field_id = field_name_to_id.get(field_name)
                    if not template_field_id:
                        continue
                    value = item.get("value", "")
                    if not isinstance(value, str):
                        value = str(value) if value is not None else ""
                    try:
                        confidence = float(item.get("confidence", 0.7))
                    except (TypeError, ValueError):
                        confidence = 0.7
                    source_st = item.get("source_text", "")
                    if not isinstance(source_st, str):
                        source_st = str(source_st) if source_st is not None else ""

                    fact = ClinicalFact(
                        id=uuid4(),
                        session_id=uuid4(),
                        transcript_id=uuid4(),
                        template_field_id=template_field_id,
                        is_updated_by_user=False,
                        value=value,
                        confidence=confidence,
                        source_text=source_st,
                        source_start_index=0,
                        source_end_index=0,
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                    )
                    facts.append(fact)

        except Exception as e:
            logger.exception("LLM extraction failed")
            err_msg = f"LLM extraction failed, falling back to mock extraction: {e}"
            raise ClinicalExtractionError(err_msg) from e

        return facts

    def _extract_value_for_field(self, transcript: str, field: TemplateField) -> str:
        field_name = field.name.lower()
        field_label = field.label.lower()

        sentences = transcript.split(".")

        for sentence in sentences:
            sentence_lower = sentence.lower().strip()

            if field_name in sentence_lower or field_label in sentence_lower:
                words = sentence.split()
                for i, word in enumerate(words):
                    if (field_name in word.lower() or field_label in word.lower()) and i + 1 < len(words):
                        return " ".join(words[i + 1 : i + 6]).strip()

        return ""

    def _find_source_in_transcript(self, transcript: str, value: str) -> tuple[str, int, int]:
        value_lower = value.lower()

        start_idx = transcript.lower().find(value_lower)

        if start_idx == -1:
            return "", 0, 0

        end_idx = start_idx + len(value)

        source_text = transcript[start_idx:end_idx]

        return source_text, start_idx, end_idx
