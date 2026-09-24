"""
Controlled import of validated Schwab transaction data.

Sprint 22B establishes the import-operation lifecycle.

Sprint 22D establishes controlled transaction persistence with
transaction-level duplicate detection.

Sprint 22G records the originating ImportOperation identifier on any
transaction dataset created by the controlled import.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
from pathlib import Path

from app.services.import_service import TransactionsValidationResult

from .import_operation import (
    ImportFileType,
    ImportOperation,
    ImportStatus,
)
from .import_operation_store import ImportOperationStore
from .transaction import InvestmentTransaction
from .transaction_repository import (
    TransactionAppendResult,
    TransactionRepository,
)


@dataclass(frozen=True, slots=True)
class ControlledTransactionImportResult:
    """
    Result of one controlled transaction import.

    The result reports what the repository actually persisted rather than
    merely what appeared in the source file.
    """

    operation: ImportOperation
    source_transaction_count: int
    transactions_added: int
    duplicates_skipped: int
    income_transactions_added: int
    recurring_income_transactions_added: int
    start_date: date | None
    end_date: date | None
    append_result: TransactionAppendResult


class ControlledTransactionImportService:
    """
    Execute the controlled import boundary for validated transactions.

    The service owns import-operation lifecycle tracking and delegates
    transaction persistence and duplicate detection to the repository.
    """

    def __init__(
        self,
        import_operation_store: ImportOperationStore,
        transaction_repository: TransactionRepository,
    ) -> None:
        """
        Initialize the controlled transaction import service.
        """
        if not isinstance(
            import_operation_store,
            ImportOperationStore,
        ):
            raise TypeError(
                "import_operation_store must be an ImportOperationStore."
            )

        if not isinstance(
            transaction_repository,
            TransactionRepository,
        ):
            raise TypeError(
                "transaction_repository must be a TransactionRepository."
            )

        self.import_operation_store = import_operation_store
        self.transaction_repository = transaction_repository

    def import_transactions(
        self,
        validation_result: TransactionsValidationResult,
        source_file: str | Path,
    ) -> ControlledTransactionImportResult:
        """
        Import one validated Schwab transaction export.

        The source file is identified by SHA-256 hash. A previously
        imported source file is rejected before any transaction persistence
        occurs.

        A confirmed ImportOperation is persisted before transaction
        persistence begins. If transaction persistence fails, the operation
        is replaced with IMPORT_FAILED. If persistence succeeds, the
        operation is replaced with IMPORTED.
        """
        self._validate_input(
            validation_result,
            source_file,
        )

        path = Path(source_file)
        file_hash = self._file_hash(path)

        existing_operation = (
            self.import_operation_store.find_by_file_hash(
                file_hash
            )
        )

        if existing_operation is not None:
            raise FileExistsError(
                "Source file has already been imported: "
                f"{existing_operation.import_id}"
            )

        import_id = f"transactions-{file_hash[:16]}"

        import_result = validation_result.import_result
        assert import_result is not None

        confirmed_operation = ImportOperation(
            import_id=import_id,
            source_file=path.name,
            file_type=ImportFileType.TRANSACTIONS,
            file_hash=file_hash,
            account=validation_result.account,
            reporting_start_date=validation_result.start_date,
            reporting_end_date=validation_result.end_date,
            imported_at=datetime.now().astimezone(),
            status=ImportStatus.CONFIRMED,
        )

        self.import_operation_store.save(confirmed_operation)

        try:
            append_result = (
                self.transaction_repository.append_unique_transactions(
                    dataset_id=import_id,
                    account=validation_result.account,
                    source_file=path.name,
                    transactions=import_result.transactions,
                    import_id=import_id,
                )
            )
        except Exception:
            failed_operation = ImportOperation(
                import_id=confirmed_operation.import_id,
                source_file=confirmed_operation.source_file,
                file_type=confirmed_operation.file_type,
                file_hash=confirmed_operation.file_hash,
                account=confirmed_operation.account,
                reporting_start_date=(
                    confirmed_operation.reporting_start_date
                ),
                reporting_end_date=(
                    confirmed_operation.reporting_end_date
                ),
                imported_at=confirmed_operation.imported_at,
                status=ImportStatus.IMPORT_FAILED,
            )

            self.import_operation_store.save(
                failed_operation,
                overwrite=True,
            )

            raise

        imported_operation = ImportOperation(
            import_id=confirmed_operation.import_id,
            source_file=confirmed_operation.source_file,
            file_type=confirmed_operation.file_type,
            file_hash=confirmed_operation.file_hash,
            account=confirmed_operation.account,
            reporting_start_date=(
                confirmed_operation.reporting_start_date
            ),
            reporting_end_date=(
                confirmed_operation.reporting_end_date
            ),
            imported_at=confirmed_operation.imported_at,
            status=ImportStatus.IMPORTED,
        )

        self.import_operation_store.save(
            imported_operation,
            overwrite=True,
        )

        income_transactions_added = sum(
            transaction.is_income
            for transaction in append_result.added_transactions
        )

        recurring_income_transactions_added = sum(
            transaction.is_recurring_income
            for transaction in append_result.added_transactions
        )

        return ControlledTransactionImportResult(
            operation=imported_operation,
            source_transaction_count=(
                validation_result.transaction_count
            ),
            transactions_added=append_result.transactions_added,
            duplicates_skipped=append_result.duplicates_skipped,
            income_transactions_added=income_transactions_added,
            recurring_income_transactions_added=(
                recurring_income_transactions_added
            ),
            start_date=validation_result.start_date,
            end_date=validation_result.end_date,
            append_result=append_result,
        )

    @staticmethod
    def _validate_input(
        validation_result: TransactionsValidationResult,
        source_file: str | Path,
    ) -> None:
        """Validate the controlled-import inputs."""
        if not isinstance(
            validation_result,
            TransactionsValidationResult,
        ):
            raise TypeError(
                "Controlled transaction import requires a "
                "TransactionsValidationResult."
            )

        if not validation_result.is_valid:
            raise ValueError(
                "Cannot import an invalid transaction validation result."
            )

        if validation_result.import_result is None:
            raise ValueError(
                "Validated transactions result does not contain "
                "an import result."
            )

        path = Path(source_file)

        if not path.name:
            raise ValueError("source_file cannot be blank.")

        if validation_result.source_file != path.name:
            raise ValueError(
                "Source file name does not match the validated "
                "transaction file."
            )

    @staticmethod
    def _file_hash(path: Path) -> str:
        """Return the SHA-256 hash of a physical source file."""
        digest = hashlib.sha256()

        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)

        return digest.hexdigest()
