from pathlib import Path
from typing import NewType
from uuid import UUID

PdfExportTemplateMap = NewType("PdfExportTemplateMap", dict[UUID, Path])
"""Соответствие template_id (medical document template) → путь к Jinja-файлу для PDF."""
