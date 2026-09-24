"""
Sprint 22G import reconciliation and lifecycle management.

Responsibilities:
    - Coordinate post-import processing for one successful import.
    - Persist RECONCILED after successful processing.
    - Persist RECONCILIATION_FAILED when post-import processing fails.
    - Preserve the original imported data and import operation.
    - Keep financial calculations inside the existing post-import processing
      coordinator.

This module does not perform financial calculations itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.controlled_positions_import import (
    ControlledPositionsImportResult,
)
from src.controlled_transaction_import import (
    ControlledTransactionImportResult,
)
from src.import_operation import ImportOperation, ImportStatus
from src.import_operation_store import ImportOperationStore
from src.post_import_processing import (
    PostImportProcessingCoordinator,
    PostImportProcessingResult,
)
from src.snapshot_store import SnapshotStore
from src.transaction_repository import TransactionRepository
from src.transaction import IncomeCharacter
from src.transaction_repository import TransactionAppendResult


@dataclass(frozen=True, slots=True)
class ImportReconciliationResult:
    """Represent the outcome of reconciling one imported operation."""

    operation: ImportOperation
    processing_result: PostImportProcessingResult | None
    reconciled: bool
    reconciliation_failed: bool


class ImportReconciliationService:
    """
    Reconcile one successfully imported operation.

    Each CSV import has an independent lifecycle. This service therefore
    reconciles exactly one controlled import result at a time.

    The service owns lifecycle state transitions only. Financial analysis
    remains owned by PostImportProcessingCoordinator and the existing
    analytical services.
    """

    def __init__(
        self,
        import_operation_store: ImportOperationStore,
        snapshot_store: SnapshotStore,
        transaction_repository: TransactionRepository,
        post_import_processing_coordinator: PostImportProcessingCoordinator,
    ) -> None:
        """Initialize the reconciliation service."""
        if not isinstance(
            import_operation_store,
            ImportOperationStore,
        ):
            raise TypeError(
                "import_operation_store must be an ImportOperationStore."
            )

        if not isinstance(snapshot_store, SnapshotStore):
            raise TypeError(
                "snapshot_store must be a SnapshotStore."
            )

        if not isinstance(
            transaction_repository,
            TransactionRepository,
        ):
            raise TypeError(
                "transaction_repository must be a TransactionRepository."
            )

        if not isinstance(
            post_import_processing_coordinator,
            PostImportProcessingCoordinator,
        ):
            raise TypeError(
                "post_import_processing_coordinator must be a "
                "PostImportProcessingCoordinator."
            )

        self._import_operation_store = import_operation_store
        self._snapshot_store = snapshot_store
        self._transaction_repository = transaction_repository
        self._post_import_processing_coordinator = (
            post_import_processing_coordinator
        )

    def reconcile(
        self,
        positions_import: ControlledPositionsImportResult | None = None,
        transactions_import: ControlledTransactionImportResult | None = None,
    ) -> ImportReconciliationResult:
        """
        Reconcile exactly one successfully imported operation.

        The supplied import result must represent an operation currently in
        IMPORTED status. Positions and transaction imports are reconciled
        independently and therefore cannot be supplied together.
        """
        self._validate_import_results(
            positions_import=positions_import,
            transactions_import=transactions_import,
        )

        operation = self._operation(
            positions_import=positions_import,
            transactions_import=transactions_import,
        )

        try:
            processing_result = self._post_import_processing_coordinator.process(
                positions_import=positions_import,
                transactions_import=transactions_import,
            )
        except Exception:
            updated_operation = self._save_status(
                operation,
                ImportStatus.RECONCILIATION_FAILED,
            )

            return ImportReconciliationResult(
                operation=updated_operation,
                processing_result=None,
                reconciled=False,
                reconciliation_failed=True,
            )

        updated_operation = self._save_status(
            operation,
            ImportStatus.RECONCILED,
        )

        return ImportReconciliationResult(
            operation=updated_operation,
            processing_result=processing_result,
            reconciled=True,
            reconciliation_failed=False,
        )
    def recover(
        self,
        import_id: str,
    ) -> ImportReconciliationResult:
        """
        Recover one import whose reconciliation previously failed.

        Recovery uses the authoritative persisted financial data associated
        with the import operation. It never re-imports the source CSV.

        A transaction import is recovered from its persisted transaction
        dataset. A positions import is recovered from its persisted Snapshot.

        The operation must currently be in RECONCILIATION_FAILED status.
        """
        if not isinstance(import_id, str):
            raise TypeError("import_id must be a string.")

        normalized_import_id = import_id.strip()

        if not normalized_import_id:
            raise ValueError("import_id cannot be blank.")

        if import_id != normalized_import_id:
            raise ValueError(
                "import_id cannot have leading or trailing whitespace."
            )

        operation = self._import_operation_store.load(
            normalized_import_id
        )

        if operation.status is not ImportStatus.RECONCILIATION_FAILED:
            raise ValueError(
                "Only RECONCILIATION_FAILED operations can be recovered."
            )

        if operation.file_type.name == "POSITIONS":
            positions_import = self._build_positions_recovery_result(
                operation
            )

            processing_result = (
                self._post_import_processing_coordinator.process(
                    positions_import=positions_import,
                    transactions_import=None,
                )
            )

        elif operation.file_type.name == "TRANSACTIONS":
            transactions_import = self._build_transaction_recovery_result(
                operation
            )

            processing_result = (
                self._post_import_processing_coordinator.process(
                    positions_import=None,
                    transactions_import=transactions_import,
                )
            )

        else:
            raise ValueError(
                f"Unsupported import file type: {operation.file_type}."
            )

        updated_operation = self._save_status(
            operation,
            ImportStatus.RECONCILED,
        )

        return ImportReconciliationResult(
            operation=updated_operation,
            processing_result=processing_result,
            reconciled=True,
            reconciliation_failed=False,
        )    

    def _build_positions_recovery_result(
        self,
        operation: ImportOperation,
    ) -> ControlledPositionsImportResult:
        """Build a processing-only positions result from persisted data."""
        if operation.reporting_end_date is None:
            raise ValueError(
                "Positions import operation has no reporting end date."
            )

        snapshot = self._snapshot_store.load(
            operation.reporting_end_date
        )

        snapshot_path = (
            self._snapshot_store.storage_path
            / f"{operation.reporting_end_date.isoformat()}.json"
        )

        return ControlledPositionsImportResult(
            operation=operation,
            snapshot=snapshot,
            snapshot_path=snapshot_path,
            current_portfolio_advanced=False,
        )

    def _build_transaction_recovery_result(
        self,
        operation: ImportOperation,
    ) -> ControlledTransactionImportResult:
        """Build a processing-only transaction result from persisted data."""
        dataset = self._transaction_repository.find_dataset_by_import_id(
            operation.import_id
        )

        if dataset is None:
            raise FileNotFoundError(
                "No transaction dataset is associated with import "
                f"'{operation.import_id}'."
            )

        transactions = dataset.transactions

        income_transactions = tuple(
            transaction
            for transaction in transactions
            if transaction.income_type is not None
        )

        recurring_income_transactions = tuple(
            transaction
            for transaction in income_transactions
            if transaction.income_character is IncomeCharacter.RECURRING
        )

        start_date = dataset.start_date
        end_date = dataset.end_date

        append_result = TransactionAppendResult(
            transactions_received=len(transactions),
            transactions_added=len(transactions),
            duplicates_skipped=0,
            dataset_path=None,
            added_transactions=transactions,
        )

        return ControlledTransactionImportResult(
            operation=operation,
            source_transaction_count=len(transactions),
            transactions_added=len(transactions),
            duplicates_skipped=0,
            income_transactions_added=len(income_transactions),
            recurring_income_transactions_added=(
                len(recurring_income_transactions)
            ),
            start_date=start_date,
            end_date=end_date,
            append_result=append_result,
        )

    def _validate_import_results(
        self,
        positions_import: ControlledPositionsImportResult | None,
        transactions_import: ControlledTransactionImportResult | None,
    ) -> None:
        """Validate that reconciliation receives exactly one import."""
        if positions_import is None and transactions_import is None:
            raise ValueError(
                "Exactly one successful import result is required."
            )

        if positions_import is not None and transactions_import is not None:
            raise ValueError(
                "Positions and transaction imports must be reconciled "
                "independently."
            )

        if positions_import is not None:
            if not isinstance(
                positions_import,
                ControlledPositionsImportResult,
            ):
                raise TypeError(
                    "positions_import must be a "
                    "ControlledPositionsImportResult."
                )

            self._validate_operation_status(
                positions_import.operation,
            )

        if transactions_import is not None:
            if not isinstance(
                transactions_import,
                ControlledTransactionImportResult,
            ):
                raise TypeError(
                    "transactions_import must be a "
                    "ControlledTransactionImportResult."
                )

            self._validate_operation_status(
                transactions_import.operation,
            )

    @staticmethod
    def _validate_operation_status(
        operation: ImportOperation,
    ) -> None:
        """Require an imported operation before reconciliation."""
        if operation.status is not ImportStatus.IMPORTED:
            raise ValueError(
                "Only IMPORTED operations can be reconciled."
            )

    @staticmethod
    def _operation(
        positions_import: ControlledPositionsImportResult | None,
        transactions_import: ControlledTransactionImportResult | None,
    ) -> ImportOperation:
        """Return the single import operation being reconciled."""
        if positions_import is not None:
            return positions_import.operation

        if transactions_import is not None:
            return transactions_import.operation

        raise ValueError(
            "Exactly one successful import result is required."
        )

    def _save_status(
        self,
        operation: ImportOperation,
        status: ImportStatus,
    ) -> ImportOperation:
        """Persist one lifecycle status transition."""
        updated_operation = ImportOperation(
            import_id=operation.import_id,
            source_file=operation.source_file,
            file_type=operation.file_type,
            file_hash=operation.file_hash,
            account=operation.account,
            reporting_start_date=operation.reporting_start_date,
            reporting_end_date=operation.reporting_end_date,
            imported_at=operation.imported_at,
            status=status,
        )

        self._import_operation_store.save(
            updated_operation,
            overwrite=True,
        )

        return updated_operation
