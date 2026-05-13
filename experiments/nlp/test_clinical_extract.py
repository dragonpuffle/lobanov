# ruff: noqa: T201

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from lobanov.adapters.services.nlp.llm_clinical_extraction_service import LLMClinicalExtractionService
from lobanov.adapters.services.nlp.phi_hf_clinical_extraction_service import PhiHFClinicalExtractionService
from lobanov.adapters.services.nlp.qwen3_hf_clinical_extraction_service import Qwen3HFClinicalExtractionService
from lobanov.domain.entities.template_field import TemplateField
from lobanov.infra.configs import NLPConfig
from lobanov.protocols import ClinicalExtractionProtocol

load_dotenv()

# Supported backends:
#   openrouter      – cloud via OpenRouter (requires OPENROUTER_API_KEY in env)
#   phi_hf          – microsoft/Phi-3-mini-4k-instruct (Phi-4 via model= if needed);
#   qwen3_hf        – Qwen/Qwen3-0.6B (causal LM; chat template enable_thinking=False)

BACKEND = "qwen3_hf"

TRANSCRIPTS_JSON = Path("experiments/dialog_transcripts.json")
DIALOG_ID_COLD = "dialog_01"
DIALOG_ID_WARM = "dialog_10"

CACHE = "models/nlp"
DEVICE = "cuda"


# ---------------------------------------------------------------------------
# Demo template fields — a minimal clinical intake form
# ---------------------------------------------------------------------------

_TEMPLATE_ID = uuid4()
_now = datetime.now(UTC)

DEMO_FIELDS: list[TemplateField] = [
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="full_name",
        label="ФИО пациента",
        is_required=True,
        options=None,
        order=1,
        created_at=_now,
        updated_at=_now,
    ),
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="birth_date",
        label="Дата рождения",
        is_required=True,
        options=None,
        order=2,
        created_at=_now,
        updated_at=_now,
    ),
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="gender",
        label="Пол",
        is_required=True,
        options={"options": ["Мужской", "Женский"]},
        order=3,
        created_at=_now,
        updated_at=_now,
    ),
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="complaints",
        label="Жалобы",
        is_required=True,
        options=None,
        order=4,
        created_at=_now,
        updated_at=_now,
    ),
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="allergies",
        label="Аллергии",
        is_required=False,
        options=None,
        order=5,
        created_at=_now,
        updated_at=_now,
    ),
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="diagnosis",
        label="Диагноз",
        is_required=False,
        options=None,
        order=6,
        created_at=_now,
        updated_at=_now,
    ),
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="treatment_plan",
        label="План лечения",
        is_required=False,
        options=None,
        order=7,
        created_at=_now,
        updated_at=_now,
    ),
]


# ---------------------------------------------------------------------------
# Config builders
# ---------------------------------------------------------------------------


def build_nlp_config() -> NLPConfig:
    common_hf = {
        "use_mock": False,
        "use_structured_output": False,
        "use_response_healing": False,
        "device": DEVICE,
        "compute_type": "float16",
        "revision": "",
        "model_cache_dir": CACHE,
        "trust_remote_code": True,
        "max_tokens": 4096,
        "temperature": 0.0,
    }

    if BACKEND == "openrouter":
        return NLPConfig(
            use_mock=False,
            provider="openrouter",
            model="openai/gpt-4o-mini",
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            max_tokens=4000,
            temperature=0.0,
            use_structured_output=True,
            use_response_healing=True,
        )

    if BACKEND == "phi_hf":
        # microsoft/Phi-4-mini-instruct
        return NLPConfig(
            provider="phi_hf",
            model="microsoft/Phi-4-mini-instruct",
            api_key="",
            **common_hf,
        )

    if BACKEND == "qwen3_hf":
        return NLPConfig(
            provider="qwen3_hf",
            model="Qwen/Qwen3-0.6B",
            api_key="",
            **common_hf,
        )

    msg = f"Unknown BACKEND={BACKEND!r}"
    raise ValueError(msg)


def build_service(cfg: NLPConfig) -> ClinicalExtractionProtocol:
    p = cfg.provider.lower().strip()
    if p == "openrouter":
        return LLMClinicalExtractionService(cfg)
    if p in {"phi_hf", "phi"}:
        return PhiHFClinicalExtractionService(cfg)
    if p in {"qwen3_hf", "qwen3", "qwen3_06b"}:
        return Qwen3HFClinicalExtractionService(cfg)
    msg = f"Unknown provider={cfg.provider!r}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_transcript(dialog_id: str) -> str:
    if not TRANSCRIPTS_JSON.exists():
        print(f"Transcripts file missing: {TRANSCRIPTS_JSON}", file=sys.stderr)
        sys.exit(1)
    dialogs: list[dict] = json.loads(TRANSCRIPTS_JSON.read_text(encoding="utf-8"))
    for d in dialogs:
        if d.get("dialog_id") == dialog_id:
            return str(d.get("expected_transcript", ""))
    print(f"dialog_id={dialog_id!r} not found in transcripts file", file=sys.stderr)
    sys.exit(1)


def _print_facts(facts: list) -> None:
    if not facts:
        print("  (no facts extracted)")
        return
    for fact in facts:
        print(f"  [{fact.confidence:.2f}] {fact.source_text!r:40s} -> {fact.value!r}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def _main() -> None:
    cfg = build_nlp_config()
    svc = build_service(cfg)

    pairs = [
        ("1-cold", DIALOG_ID_COLD),
        ("2-warm", DIALOG_ID_WARM),
    ]

    for label, dialog_id in pairs:
        transcript = _load_transcript(dialog_id)
        t0 = time.perf_counter()
        facts = await svc.extract_clinical_facts(transcript, DEMO_FIELDS)
        dt = time.perf_counter() - t0
        print(f"\n[{label}] dialog={dialog_id}  {dt:.2f}s  facts={len(facts)}")
        _print_facts(facts)


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
