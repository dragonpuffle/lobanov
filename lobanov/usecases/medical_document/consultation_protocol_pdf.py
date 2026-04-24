from collections.abc import Mapping
from datetime import UTC
from pathlib import Path
from uuid import UUID

from fpdf import FPDF
from fpdf.fonts import TextStyle
from jinja2 import Environment, FileSystemLoader, select_autoescape

from lobanov.domain.entities.medical_document import MedicalDocument
from lobanov.utils.pdf_font import resolve_cyrillic_font_ttf


class PdfExportTemplateNotSupportedError(ValueError):
    """Для `template_id` не задан jinja-файл в карте PDF-шаблонов."""

    def __init__(self, template_id: UUID) -> None:
        self.template_id = template_id
        super().__init__(f"No PDF Jinja template registered for template_id={template_id}")


def _dash(values: dict[str, str], key: str) -> str:
    raw = values.get(key)
    if raw is None:
        return "—"
    s = str(raw).strip()
    return s or "—"


class RenderConsultationProtocolPdf:
    """PDF-экспорт по Jinja → HTML → fpdf2. Набор шаблонов задаётся словарём `template_id → .j2`."""

    def __init__(self, template_id_to_jinja_file: Mapping[UUID, Path]) -> None:
        self._template_id_to_jinja: dict[UUID, Path] = {k: Path(v) for k, v in template_id_to_jinja_file.items()}
        self._jinja_env_cache: dict[UUID, tuple[Environment, str]] = {}

    def _env_for_template(self, template_id: UUID) -> tuple[Environment, str]:
        if template_id in self._jinja_env_cache:
            return self._jinja_env_cache[template_id]

        jinja_path = self._template_id_to_jinja.get(template_id)
        if jinja_path is None:
            raise PdfExportTemplateNotSupportedError(template_id)
        jinja_path = jinja_path.resolve()
        env = Environment(
            loader=FileSystemLoader(str(jinja_path.parent)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        pair = (env, jinja_path.name)
        self._jinja_env_cache[template_id] = pair
        return pair

    def execute(self, values: dict[str, str], document: MedicalDocument) -> bytes:
        tid = document.template_id
        env, jinja_name = self._env_for_template(tid)

        doc_ts = document.updated_at
        if doc_ts.tzinfo is None:
            doc_ts = doc_ts.replace(tzinfo=UTC)
        document_date = doc_ts.astimezone(UTC).strftime("%d.%m.%Y")

        tpl = env.get_template(jinja_name)
        html = tpl.render(
            template_id=str(tid),
            document_id=str(document.id),
            document_date=document_date,
            patient_name=_dash(values, "patient_name"),
            birth_date=_dash(values, "birth_date"),
            gender=_dash(values, "gender"),
            visit_date=_dash(values, "visit_date"),
            chief_complaint=_dash(values, "chief_complaint"),
            medical_history=_dash(values, "medical_history"),
            allergies=_dash(values, "allergies"),
            examination=_dash(values, "examination"),
            diagnosis=_dash(values, "diagnosis"),
            treatment_plan=_dash(values, "treatment_plan"),
            doctor_name=_dash(values, "doctor_name"),
        )

        font_path = resolve_cyrillic_font_ttf()
        family = "ProtocolExport"
        fp = str(font_path)

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.add_font(family, "", fp)
        pdf.add_font(family, "B", fp)
        pdf.add_font(family, "I", fp)
        pdf.add_font(family, "BI", fp)

        title_color = (13 / 255, 79 / 255, 74 / 255)
        h2 = TextStyle(font_family=family, font_size_pt=11, color=title_color, t_margin=3, b_margin=1)
        h1 = TextStyle(font_family=family, font_size_pt=16, color=title_color, t_margin=2, b_margin=2)
        body = TextStyle(font_family=family, font_size_pt=10, t_margin=1, b_margin=1)

        pdf.write_html(
            html,
            tag_styles={
                "h1": h1,
                "h2": h2,
                "p": body,
                "b": TextStyle(font_family=family, font_size_pt=10, font_style="B"),
            },
        )

        return bytes(pdf.output())
