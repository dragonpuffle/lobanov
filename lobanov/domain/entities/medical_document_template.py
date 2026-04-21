from uuid import UUID

from lobanov.utils.time_base_model import TimeBaseModel


class MedicalDocumentTemplate(TimeBaseModel):
    id: UUID
    name: str
    description: str
    version: str
    is_active: bool = True
