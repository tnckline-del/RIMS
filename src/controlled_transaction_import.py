"""
Controlled import service for validated Schwab transaction data.

Responsibilities:
    - Accept validated Schwab transaction data.
    - Protect against duplicate source-file imports.
    - Append only previously unseen transactions.
    - Preserve transaction account and date-range provenance.
    - Track the import lifecycle through ImportOperation.
    - Report only transactions actually added to RIMS.
    - Never independently calculate or modify income history.

This module contains import orchestration only.
Transaction persistence remains in TransactionRepository.
Financial analysis remains in the existing RIMS services.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from app.services.import_service import TransactionsValidationResult
from src.import_operation import (
    ImportFileType,
    ImportOperation,
    ImportStatus,
    calculate_file_hash,
)
from src.import_operation_store import ImportOperationStore
from src.transaction_repository import (
    TransactionAppendResult,
    TransactionRepository,
)


@dataclass(frozen=True, slots=True)
class ControlledTransactionImportResult:
    """Result of one controlled Schwab transaction import."""

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
    """Safely incorporate validated Schwab transactions into RIMS."""

    def __init__(
        self,
        import_operation_store: ImportOperationStore,
        transaction_repository: TransactionRepository,
    ) -> None:
        """Create a controlled transaction import service."""
        self.import_operation_store = import_operation_store
        self.transaction_repository = transaction_repository

    def import_transactions(
        self,
        validation_result: TransactionsValidationResult,
        source_file: str | Path,
    ) -> ControlledTransactionImportResult:
        """
        Import a successfully validated Schwab transaction file.

        The source file is hashed and checked for prior import before any
        persistent transaction data is changed.

        Transactions are appended through TransactionRepository, which
        suppresses transaction-level duplicates.

        The import operation is marked IMPORTED only after the transaction
        append succeeds.

        If transaction persistence fails, the operation is marked
        IMPORT_FAILED and the original exception is re-raised.
        """
        self._validate_input(validation_result, source_file)

        path = Path(source_file)

        if not path.is_file():
            raise FileNotFoundError(
                f"Transactions source file not found: {path}"
            )

        file_hash = calculate_file_hash(path)

        existing_operation = (
            self.import_operation_store.find_by_file_hash(
                file_hash
            )
        )

        if existing_operation is not None:
            raise FileExistsError(
                "Transactions file has already been imported: "
                f"{existing_operation.import_id}"
            )

        import_result = validation_result.import_result

        if import_result is None:
            raise ValueError(
                "Validated transactions result does not contain "
                "an import result."
            )

        import_id = self._create_import_id(file_hash)

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

        if not validation_result.account.strip():
            raise ValueError(
                "Validated transaction account cannot be blank."
            )

    @staticmethod
    def _create_import_id(file_hash: str) -> str:
        """Create a deterministic transaction import identifier."""
        return f"transactions-{file_hash[:16]}"
    