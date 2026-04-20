from enum import Enum


class SessionStatus(str, Enum):
    CREATED = "created"
    AUDIO_UPLOADED = "audio_uploaded"
    TRANSCRIBED = "transcribed"
    DRAFT_CREATED = "draft_created"
    CONFIRMED = "confirmed"
