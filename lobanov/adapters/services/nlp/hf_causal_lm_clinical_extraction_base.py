from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, override
from uuid import uuid4

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from lobanov.domain.entities.clinical_fact import ClinicalFact
from lobanov.infra.configs import NLPConfig
from lobanov.protocols import ClinicalExtractionProtocol
from lobanov.protocols.services.clinical_extraction_protocol import TemplateField
from lobanov.utils.clinical_normalization import normalize_fact_value, safe_normalize_transcript
from lobanov.utils.llm import pick_device_string, pick_torch_dtype, resolve_pretrained_source, safe_hf_dirname
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

_SYSTEM_PROMPT = (
    "You are a medical information extraction assistant for Russian clinical dialogs. "
    "Reply with a single JSON object only: top-level keys are field identifiers, "
    "each value is an object with keys field_name, value, confidence, source_text. "
    "No markdown, no extra prose."
)

# Matches ```json … ``` or ``` … ``` fences
_FENCE_RE = re.compile(r"^```[a-zA-Z]*\n?(.*?)```$", re.DOTALL)
# Matches <think>…</think> reasoning blocks (used by DeepSeek-R1-Distill)
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

_TOKENIZER_MAX_LEN_SANE_UPPER = 1_000_000
_TRANSCRIPT_TRIM_FLOOR_CHARS = 160


class ClinicalExtractionError(Exception):
    pass


def _strip_fences(text: str) -> str:
    stripped = text.strip()
    m = _FENCE_RE.match(stripped)
    return m.group(1).strip() if m else stripped


def _parse_llm_json_object(content: str) -> dict[str, Any]:
    if isinstance(content, dict):
        return content  # type: ignore[return-value]
    text = _strip_fences(str(content)).strip()
    brace = text.find("{")
    if brace != -1:
        text = text[brace:]
    decoder = json.JSONDecoder()
    try:
        data, _end = decoder.raw_decode(text)
    except json.JSONDecodeError:
        data = json.loads(text)
    if not isinstance(data, dict):
        msg = "LLM response must be a JSON object, not a list or other type"
        raise ClinicalExtractionError(msg)
    return data


def _ensure_transformers_loss_kwargs_compat() -> None:
    """Hub ``modeling_phi3.py`` imports ``LossKwargs``; some transformers 5.x releases only expose ``TransformersKwargs``."""
    import transformers.utils as tu  # noqa: PLC0415

    if hasattr(tu, "LossKwargs"):
        return
    from transformers.utils.generic import TransformersKwargs  # noqa: PLC0415

    tu.LossKwargs = TransformersKwargs  # type: ignore[attr-defined]


class HFCausalLMClinicalExtractionService(ClinicalExtractionProtocol):
    """Lazy-loading base adapter: downloads once, caches on disk, serves locally."""

    # Subclasses set this to the default HF repo-id for the family.
    model_id_default: str = ""

    @staticmethod
    def effective_context_length(model: Any, tokenizer: Any) -> int:
        """Usable sequence length for positions (prompt + generation)."""
        cfg_max = getattr(getattr(model, "config", None), "max_position_embeddings", None)
        tok_max = getattr(tokenizer, "model_max_length", None)
        candidates: list[int] = []
        if isinstance(cfg_max, int) and cfg_max > 0:
            candidates.append(cfg_max)
        if isinstance(tok_max, int) and 0 < tok_max < _TOKENIZER_MAX_LEN_SANE_UPPER:
            candidates.append(tok_max)
        if not candidates:
            return 2048
        return min(candidates)

    @staticmethod
    def _effective_context_length(model: Any, tokenizer: Any) -> int:
        return HFCausalLMClinicalExtractionService.effective_context_length(model, tokenizer)

    def _shrink_user_prompt_once(self, user_content: str) -> tuple[str, bool]:
        """One step of shortening the clinical extraction user blob; returns (new_text, changed)."""
        user_content = user_content.replace("\r\n", "\n")
        rules_sep = "\n\nOutput rules (strict):"
        if rules_sep not in user_content:
            return user_content, False

        head_norm, tail_rules = user_content.split(rules_sep, 1)
        tail_rules = rules_sep + tail_rules

        norm_marker = "\n\nNormalized transcript:\n"
        if norm_marker in head_norm:
            before, _ = head_norm.split(norm_marker, 1)
            return before + tail_rules, True

        raw_marker = "\n\nRaw transcript:\n"
        if raw_marker not in head_norm:
            return user_content, False
        prefix, raw_and_rest = head_norm.split(raw_marker, 1)
        raw_body = raw_and_rest
        if norm_marker in raw_body:
            raw_body, _ = raw_body.split(norm_marker, 1)
        if raw_body.endswith("\n"):
            raw_body = raw_body.rstrip("\n")

        if len(raw_body) <= _TRANSCRIPT_TRIM_FLOOR_CHARS:
            return user_content, False
        keep = max(_TRANSCRIPT_TRIM_FLOOR_CHARS, int(len(raw_body) * 0.72))
        trimmed = "[... earlier transcript omitted ...]\n\n" + raw_body[-keep:]
        new_content = prefix + raw_marker + trimmed + tail_rules
        return new_content, True

    def _coerce_messages_within_context(
        self,
        messages: list[dict[str, str]],
        tokenizer: Any,
        model: Any,
    ) -> list[dict[str, str]]:
        """Ensure encoded prompt leaves room for generation (small-context models e.g. phi-2)."""
        out: list[dict[str, str]] = []
        for m in messages:
            mm = dict(m)
            mm["content"] = str(mm.get("content", "")).replace("\r\n", "\n")
            out.append(mm)
        max_ctx = self._effective_context_length(model, tokenizer)
        gen_reserve = min(int(self._nlp.max_tokens) + 48, max_ctx // 2)
        target_len = max(64, max_ctx - gen_reserve - 8)

        for _ in range(48):
            enc = self._encode_messages_for_generation(tokenizer, out)
            cur = int(enc["input_ids"].shape[-1])
            if cur <= target_len:
                return out
            uidx = next(i for i, m in enumerate(out) if m["role"] == "user")
            new_uc, changed = self._shrink_user_prompt_once(out[uidx]["content"])
            if not changed:
                logger.warning(
                    "clinical HF prompt still long ({cur} tokens > budget {target}); continuing anyway",
                    cur=cur,
                    target=target_len,
                )
                return out
            out[uidx]["content"] = new_uc

        return out

    def __init__(self, nlp_config: NLPConfig) -> None:
        self._nlp = nlp_config
        # If provider left model blank, fall back to the subclass default
        if not self._nlp.model.strip():
            object.__setattr__(self, "_nlp", nlp_config.model_copy(update={"model": self.model_id_default}))
        self._bundle: tuple[Any, Any] | None = None  # (tokenizer, model)
        self._model_lock = asyncio.Lock()

    def _extra_load_kwargs(self) -> dict[str, Any]:
        """Extra kwargs to pass to ``AutoModelForCausalLM.from_pretrained``."""
        return {}

    def _strip_reasoning(self, text: str) -> str:
        """Remove model-specific reasoning wrappers before JSON parsing."""
        return text

    def _after_model_loaded(self, tokenizer: Any, model: Any, source: str, hub_kw: dict[str, Any]) -> None:
        """Optional hook after weights are loaded (e.g. attach a hub ``GenerationConfig``)."""

    def _load_sync(self) -> tuple[Any, Any]:
        _ensure_transformers_loss_kwargs_compat()
        source, hub_kw = resolve_pretrained_source(self._nlp)
        device_str = pick_device_string(self._nlp.device)
        dtype = pick_torch_dtype(self._nlp.compute_type, device_str)

        trust = self._nlp.trust_remote_code

        tokenizer = AutoTokenizer.from_pretrained(
            source,
            trust_remote_code=trust,
            **hub_kw,
        )

        extra = self._extra_load_kwargs()
        load_kw: dict[str, Any] = {
            "trust_remote_code": trust,
            **hub_kw,
            **extra,
        }
        # Only set torch_dtype when not letting accelerate choose via device_map
        if "dtype" not in load_kw:
            load_kw["dtype"] = dtype

        # When device_map is set we don't call .to() manually
        uses_device_map = "device_map" in load_kw
        # MoE / non-sharded layouts (e.g. openai/gpt-oss-20b) may need a disk staging dir when
        # Accelerate materialises weights that do not map 1:1 to checkpoint tensors.
        if uses_device_map and "offload_folder" not in load_kw:
            cache_root = Path(hub_kw.get("cache_dir") or self._nlp.model_cache_dir).expanduser().resolve()
            offload = cache_root / "accelerate-offload" / safe_hf_dirname(self._nlp.model)
            offload.mkdir(parents=True, exist_ok=True)
            load_kw["offload_folder"] = str(offload)

        model: Any = AutoModelForCausalLM.from_pretrained(source, **load_kw)

        if not uses_device_map and device_str not in {"auto", "cpu"}:
            model = model.to(device_str)

        self._after_model_loaded(tokenizer, model, str(source), hub_kw)

        logger.info(
            "Loaded HF causal-LM {src!r} device={dev!r} dtype={dt}",
            src=str(source),
            dev=device_str,
            dt=str(dtype),
        )
        return tokenizer, model

    async def _get_bundle(self) -> tuple[Any, Any]:
        if self._bundle is not None:
            return self._bundle
        async with self._model_lock:
            if self._bundle is None:
                self._bundle = await asyncio.to_thread(self._load_sync)
        return self._bundle

    def _build_user_prompt(self, transcript: str, template_fields: list[TemplateField]) -> str:
        field_descriptions = "\n".join(
            f"- {f.name} ({f.label}) | required={f.is_required} | options={self._extract_options(f) or 'n/a'}"
            for f in template_fields
        )
        field_names_quoted = ", ".join(f'"{f.name}"' for f in template_fields)
        normalized_transcript = safe_normalize_transcript(transcript)
        transcript = transcript.replace("\r\n", "\n")
        normalized_transcript = normalized_transcript.replace("\r\n", "\n")

        return f"""You extract structured clinical data from a medical dialog transcript.

Template fields (use field_name exactly as listed):
{field_descriptions}

Raw transcript:
{transcript}

Normalized transcript:
{normalized_transcript}

Output rules (strict):
- Return ONE JSON object only. No markdown fences, no comments, no text before or after the JSON.
- Top-level keys: one key per extracted fact. Each key should identify the field and must come from: {field_names_quoted}.
- Each value MUST be an object with exactly these string/number fields:
  - "field_name": same as in the template list (field `name`, string)
  - "value": extracted value (string; use "" if nothing reliable)
  - "confidence": number from 0.0 to 1.0
  - "source_text": a verbatim or minimal quote from Raw transcript that supports the value (string)
- Include only fields where you have a meaningful value and supporting source_text from this transcript.
- Do NOT put character position indices in the response.
- Never invent medications or diagnoses that are absent from transcript.

Example shape (keys and `field_name` must match your template):
{_JSON_EXAMPLE}"""

    def _encode_messages_for_generation(
        self,
        tokenizer: Any,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Turn chat ``messages`` into model inputs (IDs + mask).

        Prefer the tokenizer Jinja ``chat_template`` when present. Older checkpoints
        (e.g. ``microsoft/phi-2``) ship without one; use Phi instruct markup instead.
        """
        if getattr(tokenizer, "chat_template", None):
            enc: Any = tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
            )
            return dict(enc)
        system_blocks = [m["content"] for m in messages if m["role"] == "system"]
        user_blocks = [m["content"] for m in messages if m["role"] == "user"]
        combined = "\n\n".join([*system_blocks, *user_blocks]).strip()
        prompt = f"Instruct: {combined}\nOutput:"
        return dict(tokenizer(prompt, return_tensors="pt", add_special_tokens=True))

    def _generate_sync(
        self,
        tokenizer: Any,
        model: Any,
        messages: list[dict[str, str]],
    ) -> str:
        device_param = next(iter(model.parameters())).device

        fitted = self._coerce_messages_within_context(messages, tokenizer, model)
        inputs: Any = self._encode_messages_for_generation(tokenizer, fitted)
        inputs = {k: v.to(device_param) for k, v in inputs.items()}

        max_ctx = self._effective_context_length(model, tokenizer)
        planned_gen = min(int(self._nlp.max_tokens) + 8, max_ctx // 2)
        max_prompt_len = max(128, max_ctx - planned_gen - 8)
        seq_len = int(inputs["input_ids"].shape[-1])
        if seq_len > max_prompt_len:
            chop = seq_len - max_prompt_len
            logger.warning(
                "truncating HF prompt from the left ({seq} tokens -> {keep}); small-context model",
                seq=seq_len,
                keep=max_prompt_len,
            )
            inputs["input_ids"] = inputs["input_ids"][:, chop:]
            if "attention_mask" in inputs:
                inputs["attention_mask"] = inputs["attention_mask"][:, chop:]

        input_len = int(inputs["input_ids"].shape[-1])
        allowed_new = max_ctx - input_len - 8
        if allowed_new < 1:
            logger.warning(
                "prompt fills context ({inp}/{ctx}); generation capped to 1 token",
                inp=input_len,
                ctx=max_ctx,
            )
            allowed_new = 1
        max_new_tokens = min(int(self._nlp.max_tokens), allowed_new)

        gen_kwargs: dict[str, Any] = {
            **inputs,
            "max_new_tokens": max_new_tokens,
            "do_sample": self._nlp.temperature > 0,
            "pad_token_id": self._pad_token_id_for_generate(tokenizer),
        }
        if self._nlp.temperature > 0:
            gen_kwargs["temperature"] = self._nlp.temperature

        with torch.no_grad():
            output_ids: torch.Tensor = model.generate(**gen_kwargs)

        continuation = output_ids[0, input_len:].cpu()
        return self._decode_continuation_ids(tokenizer, continuation)

    def _pad_token_id_for_generate(self, tokenizer: Any) -> int | None:
        return getattr(tokenizer, "eos_token_id", None)

    def _decode_continuation_ids(self, tokenizer: Any, token_ids: torch.Tensor) -> str:
        return tokenizer.decode(token_ids, skip_special_tokens=True)

    @override
    async def extract_clinical_facts(
        self,
        transcript: str,
        template_fields: list[TemplateField],
    ) -> list[ClinicalFact]:
        if not transcript or not template_fields:
            return []

        if self._nlp.use_mock:
            return await self._mock_extract_facts(transcript, template_fields)

        try:
            return await self._hf_extract_facts(transcript, template_fields)
        except Exception as e:
            logger.exception("HF clinical extraction failed")
            err_msg = f"HF clinical extraction failed: {e}"
            raise ClinicalExtractionError(err_msg) from e

    @override
    async def get_confidence(self, fact: ClinicalFact) -> float:
        return fact.confidence

    async def _hf_extract_facts(
        self,
        transcript: str,
        template_fields: list[TemplateField],
    ) -> list[ClinicalFact]:
        tokenizer, model = await self._get_bundle()

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": self._build_user_prompt(transcript, template_fields)},
        ]

        raw_output = await asyncio.to_thread(self._generate_sync, tokenizer, model, messages)

        # Strip reasoning tags injected by some models (e.g. DeepSeek-R1-Distill)
        raw_output = self._strip_reasoning(raw_output)

        extracted_data = _parse_llm_json_object(raw_output)
        return self._map_to_facts(extracted_data, template_fields)

    def _map_to_facts(
        self,
        extracted_data: dict[str, Any],
        template_fields: list[TemplateField],
    ) -> list[ClinicalFact]:
        facts: list[ClinicalFact] = []
        field_name_to_id = {f.name: f.id for f in template_fields}
        field_by_name = {f.name: f for f in template_fields}

        for top_key, item in extracted_data.items():
            if isinstance(item, dict):
                field_name = str(item.get("field_name", "") or top_key).strip()
                template_field_id = field_name_to_id.get(field_name)
                if not template_field_id:
                    continue
                value = item.get("value", "")
                if not isinstance(value, str):
                    value = str(value) if value is not None else ""
                value = normalize_fact_value(
                    field_name,
                    value,
                    allowed_options=self._extract_options(field_by_name[field_name]),
                )
                try:
                    confidence = float(item.get("confidence", 0.7))
                except (TypeError, ValueError):
                    confidence = 0.7
                confidence = max(0.0, min(confidence, 1.0))
                source_st = item.get("source_text", "")
                if not isinstance(source_st, str):
                    source_st = str(source_st) if source_st is not None else ""

                facts.append(
                    ClinicalFact(
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
                )
            elif isinstance(item, (str, int, float, bool)) or item is None:
                # Flat JSON {"full_name": "..."} from weaker instruct checkpoints (e.g. phi-2).
                field_name = str(top_key).strip()
                template_field_id = field_name_to_id.get(field_name)
                if not template_field_id:
                    continue
                value = "" if item is None else str(item)
                value = normalize_fact_value(
                    field_name,
                    value,
                    allowed_options=self._extract_options(field_by_name[field_name]),
                )
                facts.append(
                    ClinicalFact(
                        id=uuid4(),
                        session_id=uuid4(),
                        transcript_id=uuid4(),
                        template_field_id=template_field_id,
                        is_updated_by_user=False,
                        value=value,
                        confidence=0.65,
                        source_text="",
                        source_start_index=0,
                        source_end_index=0,
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                    )
                )
        return facts

    async def _mock_extract_facts(
        self,
        transcript: str,
        template_fields: list[TemplateField],
    ) -> list[ClinicalFact]:
        facts: list[ClinicalFact] = []
        transcript_lower = transcript.lower()
        for field in template_fields:
            if field.name.lower() in transcript_lower or field.label.lower() in transcript_lower:
                value = self._extract_value_for_field(transcript, field)
                if value:
                    source_text, start_idx, end_idx = self._find_source_in_transcript(transcript, value)
                    facts.append(
                        ClinicalFact(
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
                    )
        return facts

    @staticmethod
    def _extract_options(field: TemplateField) -> list[str]:
        options_raw = field.options or {}
        if isinstance(options_raw, dict):
            values = options_raw.get("options", [])
            if isinstance(values, list):
                return [str(v) for v in values]
        return []

    @staticmethod
    def _extract_value_for_field(transcript: str, field: TemplateField) -> str:
        field_name = field.name.lower()
        field_label = field.label.lower()
        for sentence in transcript.split("."):
            s_low = sentence.lower().strip()
            if field_name in s_low or field_label in s_low:
                words = sentence.split()
                for i, word in enumerate(words):
                    if (field_name in word.lower() or field_label in word.lower()) and i + 1 < len(words):
                        return " ".join(words[i + 1 : i + 6]).strip()
        return ""

    @staticmethod
    def _find_source_in_transcript(transcript: str, value: str) -> tuple[str, int, int]:
        start_idx = transcript.lower().find(value.lower())
        if start_idx == -1:
            return "", 0, 0
        end_idx = start_idx + len(value)
        return transcript[start_idx:end_idx], start_idx, end_idx
