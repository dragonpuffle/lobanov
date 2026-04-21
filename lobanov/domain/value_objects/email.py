from pydantic import BaseModel


class Email(BaseModel):
    value: str

    def __str__(self) -> str:
        return self.value
