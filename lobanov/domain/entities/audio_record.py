from uuid import UUID

from lobanov.utils.time_base_model import TimeBaseModel


class AudioRecord(TimeBaseModel):
    id: UUID
    session_id: UUID
    file_path: str
    file_name: str
    file_size: int
    duration: float
    format: str
