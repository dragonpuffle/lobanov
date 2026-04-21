from uuid import UUID

from lobanov.utils.time_base_model import TimeBaseModel


class User(TimeBaseModel):
    id: UUID
    email: str
    hashed_password: str
    full_name: str
    is_active: bool = True
