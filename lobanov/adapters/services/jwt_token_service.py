from datetime import UTC, datetime, timedelta
from typing import override
from uuid import UUID

from jose import JWTError, jwt

from lobanov.protocols.services.jwt_token_protocol import JWTTokenProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class JWTTokenError(Exception):
    pass


class JWTTokenService(JWTTokenProtocol):
    def __init__(self, secret_key: str, algorithm: str, access_token_expire_minutes: int):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes

    @override
    async def create_access_token(self, user_id: UUID, expires_delta: timedelta) -> str:
        try:
            expire = datetime.now(UTC) + expires_delta
            to_encode = {"sub": str(user_id), "exp": expire, "iat": datetime.now(UTC)}
        except Exception as e:
            logger.exception("Failed to create access token")
            err_msg = "Failed to create access token"
            raise JWTTokenError(err_msg) from e
        else:
            return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    @override
    async def decode_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except JWTError as e:
            logger.warning("Failed to decode token: {error}", error=e)
            error_message = f"Failed to decode token: {e!s}"
            raise JWTTokenError(error_message) from e
        else:
            return payload

    @override
    async def verify_token(self, token: str) -> UUID:
        try:
            payload = await self.decode_token(token)
            user_id = payload.get("sub")
            if user_id is None:
                err_msg = "Invalid token: missing user ID"
                raise JWTTokenError(err_msg)
            return UUID(str(user_id))
        except ValueError as e:
            logger.warning("Invalid user ID in token: {error}", error=e)
            error_message = f"Invalid user ID in token: {e!s}"
            raise JWTTokenError(error_message) from e
        except JWTTokenError:
            raise
        except Exception as e:
            logger.exception("Failed to verify token")
            error_message = f"Failed to verify token: {e!s}"
            raise JWTTokenError(error_message) from e
