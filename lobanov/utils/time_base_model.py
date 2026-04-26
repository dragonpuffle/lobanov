from datetime import datetime

from pydantic import BaseModel, Field


class TimeBaseModel(BaseModel):
    created_at: datetime = Field()
    updated_at: datetime = Field()
