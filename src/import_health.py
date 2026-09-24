"""Factual lifecycle health reporting for RIMS import operations."""

from __future__ import annotations

from dataclasses import dataclass

from src.import_operation import ImportOperation, ImportStatus
from src.import_operation_store import ImportOperationStore


@dataclass(frozen=True, slots=True)
class ImportHealth:
    """Describe the persisted lifecycle state of RIMS import operations."""

    total_operations: int
    reconciled_operations: int
    reconciliation_failed_operations: int
    reconciliation_failed_import_ids: tuple[str, ...]

    @property
    def all_reconciled(self) -> bool:
        """Return True when every recorded operation is reconciled."""
        return (
            self.total_operations > 0
            and self.reconciliation_failed_operations == 0
            and self.total_operations == self.reconciled_operations
        )

    @property
    def unresolved_reconciliation_count(self) -> int:
        """Return the number of operations requiring reconciliation."""
        return self.reconciliation_failed_operations

    @property
    def summary(self) -> str:
        """Return a concise factual summary of import lifecycle state."""
        if self.total_operations == 0:
            return "No import operations recorded."

        if self.reconciliation_failed_operations == 0:
            if self.all_reconciled:
                return "All imports reconciled."

            return (
                f"{self.total_operations - self.reconciled_operations} "
                "import(s) not yet reconciled."
            )

        count = self.reconciliation_failed_operations
        suffix = "" if count == 1 else "s"

        return f"{count} import{suffix} require reconciliation."


class ImportHealthService:
    """Derive factual import health from persisted ImportOperation records."""

    def __init__(
        self,
        import_operation_store: ImportOperationStore,
    ) -> None:
        """Create an import health service."""
        if not isinstance(
            import_operation_store,
            ImportOperationStore,
        ):
            raise TypeError(
                "ImportHealthService requires an ImportOperationStore."
            )

        self._import_operation_store = import_operation_store

    def get_health(self) -> ImportHealth:
        """Return current lifecycle health from persisted operations."""
        operations = self._import_operation_store.list_operations()

        return self._build_health(operations)

    @staticmethod
    def _build_health(
        operations: list[ImportOperation],
    ) -> ImportHealth:
        """Build an ImportHealth result from persisted operations."""
        reconciled_operations = sum(
            operation.status is ImportStatus.RECONCILED
            for operation in operations
        )

        failed_operations = [
            operation
            for operation in operations
            if operation.status is ImportStatus.RECONCILIATION_FAILED
        ]

        failed_import_ids = tuple(
            operation.import_id
            for operation in failed_operations
        )

        return ImportHealth(
            total_operations=len(operations),
            reconciled_operations=reconciled_operations,
            reconciliation_failed_operations=len(failed_operations),
            reconciliation_failed_import_ids=failed_import_ids,
        )
