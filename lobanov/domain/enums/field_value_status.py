from enum import Enum


class FieldValueStatus(str, Enum):
    AUTO_FILLED = "auto_filled"
    USER_EDITED = "user_edited"
    MISSING = "missing"
    DOUBTFUL = "doubtful"
    CONFIRMED = "confirmed"
