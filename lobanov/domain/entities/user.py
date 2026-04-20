from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field


class User:
    def __init__(
        self,
        id: UUID,
        email: EmailStr,
        hashed_password: str,
        full_name: str,
        is_active: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.email = email
        self.hashed_password = hashed_password
        self.full_name = full_name
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email}, full_name={self.full_name}, is_active={self.is_active})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, User):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
