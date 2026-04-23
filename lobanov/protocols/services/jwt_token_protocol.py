from datetime import timedelta
from typing import Protocol
from uuid import UUID


class JWTTokenProtocol(Protocol):
    async def create_access_token(self, user_id: UUID, expires_delta: timedelta) -> str:
        """Create a JWT access token for the given user.

        Args:
            user_id: The UUID of the user to create the token for.
            expires_delta: The time delta after which the token expires.

        Returns:
            The encoded JWT access token as a string.

        Raises:
            JWTTokenError: If token creation fails.
        """
        ...

    async def decode_token(self, token: str) -> dict:
        """Decode a JWT token and return its payload.

        Args:
            token: The JWT token to decode.

        Returns:
            The decoded token payload as a dictionary.

        Raises:
            JWTTokenError: If token decoding fails.
        """
        ...

    async def verify_token(self, token: str) -> UUID:
        """Verify a JWT token and extract the user ID.

        Args:
            token: The JWT token to verify.

        Returns:
            The UUID of the user from the token.

        Raises:
            JWTTokenError: If token verification fails.
        """
        ...
