import re
from typing import Final


class Email:
    EMAIL_PATTERN: Final[re.Pattern[str]] = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    def __init__(self, value: str) -> None:
        if not self._is_valid_email(value):
            raise ValueError(f"Invalid email address: {value}")
        self._value = value.lower()

    @property
    def value(self) -> str:
        return self._value

    def _is_valid_email(self, email: str) -> bool:
        if not email or len(email) > 254:
            return False
        return bool(self.EMAIL_PATTERN.match(email))

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"Email(value={self._value!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Email):
            return NotImplemented
        return self._value.lower() == other._value.lower()

    def __hash__(self) -> int:
        return hash(self._value.lower())
