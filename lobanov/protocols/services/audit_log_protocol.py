from datetime import datetime
from uuid import UUID
from typing import Protocol, List, Dict, Any, runtime_checkable


class AuditLog:
    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        action: str,
        entity_type: str,
        entity_id: UUID,
        details: Dict[str, Any],
        timestamp: datetime | None = None,
    ) -> None:
        self.id = id
        self.user_id = user_id
        self.action = action
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.details = details
        self.timestamp = timestamp or datetime.utcnow()


@runtime_checkable
class AuditLogProtocol(Protocol):
    async def log_action(
        self,
        user_id: UUID,
        action: str,
        entity_type: str,
        entity_id: UUID,
        details: Dict[str, Any],
    ) -> AuditLog:
        """Log a user action for audit purposes.

        Args:
            user_id: The UUID of the user performing the action.
            action: The action performed (e.g., 'create', 'update', 'delete').
            entity_type: The type of entity affected (e.g., 'session', 'document').
            entity_id: The UUID of the affected entity.
            details: Additional details about the action as key-value pairs.

        Returns:
            The created AuditLog entry.

        Raises:
            AuditLogError: If the action cannot be logged due to storage errors.
        """
        ...

    async def get_logs(self, entity_id: UUID) -> List[AuditLog]:
        """Retrieve all audit logs for a specific entity.

        Args:
            entity_id: The UUID of the entity to retrieve logs for.

        Returns:
            List of AuditLog entries associated with the entity, ordered by timestamp.

        Raises:
            AuditLogError: If logs cannot be retrieved due to storage errors.
        """
        ...
