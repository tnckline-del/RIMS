"""
Controlled import service for validated Schwab positions data.

Responsibilities:
    - Accept validated Schwab positions data.
    - Protect against duplicate source-file imports.
    - Preserve the Schwab reporting date as the historical Snapshot date.
    - Persist the historical Snapshot before declaring the import successful.
    - Determine the current portfolio from the latest successful positions
      snapshot by Schwab reporting date.
    - Track the import lifecycle through ImportOperation.
    - Never modify transaction, income, or forward-income data.

This module contains import orchestration only.
Financial calculations remain in the existing RIMS services.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from app.services.import_service import PositionsValidationResult
from src.import_operation import (
    ImportFileType,
    ImportOperation,
    ImportStatus,
    calculate_file_hash,
)
from src.import_operation_store import ImportOperationStore
from src.snapshot import Snapshot
from src.snapshot_store import SnapshotStore


@dataclass(frozen=True, slots=True)
class ControlledPositionsImportResult:
    """Result of one controlled Schwab positions import."""

    operation: ImportOperation
    snapshot: Snapshot
    snapshot_path: Path
    current_portfolio_advanced: bool


class ControlledPositionsImportService:
    """Safely incorporate validated Schwab positions into RIMS."""

    def __init__(
        self,
        import_operation_store: ImportOperationStore,
        snapshot_store: SnapshotStore,
    ) -> None:
        """Create a controlled positions import service."""
        self.import_operation_store = import_operation_store
        self.snapshot_store = snapshot_store

    def import_positions(
        self,
        validation_result: PositionsValidationResult,
        source_file: str | Path,
    ) -> ControlledPositionsImportResult:
        """
        Import a successfully validated Schwab positions file.

        The source file is hashed and checked for prior import before any
        persistent financial data is changed.

        A historical Snapshot is persisted using the Schwab reporting date.
        The import operation is marked IMPORTED only after the Snapshot
        has been successfully saved.

        The current portfolio advances only when the imported reporting
        date is later than the reporting date of the existing current
        positions snapshot.
        """
        if not isinstance(
            validation_result,
            PositionsValidationResult,
        ):
            raise TypeError(
                "Controlled positions import requires a "
                "PositionsValidationResult."
            )

        if not validation_result.is_valid:
            raise ValueError(
                "Cannot import an invalid positions validation result."
            )

        if validation_result.import_result is None:
            raise ValueError(
                "Validated positions result does not contain "
                "an import result."
            )

        path = Path(source_file)

        if not path.is_file():
            raise FileNotFoundError(
                f"Positions source file not found: {path}"
            )

        file_hash = calculate_file_hash(path)

        existing_operation = (
            self.import_operation_store.find_by_file_hash(
                file_hash
            )
        )

        if existing_operation is not None:
            raise FileExistsError(
                "Positions file has already been imported: "
                f"{existing_operation.import_id}"
            )

        import_result = validation_result.import_result
        reporting_date = import_result.reporting_date

        previous_current = self._load_current_snapshot()

        import_id = self._create_import_id(
            file_hash=file_hash,
            reporting_date=reporting_date,
        )

        confirmed_operation = ImportOperation(
            import_id=import_id,
            source_file=path.name,
            file_type=ImportFileType.POSITIONS,
            file_hash=file_hash,
            account=None,
            reporting_start_date=reporting_date,
            reporting_end_date=reporting_date,
            imported_at=datetime.now().astimezone(),
            status=ImportStatus.CONFIRMED,
        )

        self.import_operation_store.save(confirmed_operation)

        snapshot = Snapshot.from_portfolio(
            portfolio=import_result.portfolio,
            snapshot_date=reporting_date,
            cash_market_value=import_result.cash_market_value,
        )

        try:
            snapshot_path = self.snapshot_store.save(snapshot)
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

        current_portfolio_advanced = (
            previous_current is None
            or reporting_date > previous_current.snapshot_date
        )

        return ControlledPositionsImportResult(
            operation=imported_operation,
            snapshot=snapshot,
            snapshot_path=snapshot_path,
            current_portfolio_advanced=current_portfolio_advanced,
        )

    def load_current_portfolio(self) -> Snapshot | None:
        """
        Return the current portfolio snapshot.

        The current portfolio is the successfully imported positions
        snapshot with the latest Schwab reporting date.
        """
        return self._load_current_snapshot()

    def _load_current_snapshot(self) -> Snapshot | None:
        """Return the latest successfully imported positions snapshot."""
        operations = self.import_operation_store.list_operations()

        successful_positions = [
            operation
            for operation in operations
            if (
                operation.file_type is ImportFileType.POSITIONS
                and operation.status
                in {
                    ImportStatus.IMPORTED,
                    ImportStatus.RECONCILED,
                }
                and operation.reporting_end_date is not None
            )
        ]

        if not successful_positions:
            return None

        current_operation = max(
            successful_positions,
            key=lambda operation: operation.reporting_end_date,
        )

        return self.snapshot_store.load(
            current_operation.reporting_end_date
        )

    @staticmethod
    def _create_import_id(
        file_hash: str,
        reporting_date: date,
    ) -> str:
        """Create a deterministic import identifier."""
        return (
            f"positions-"
            f"{reporting_date.isoformat()}-"
            f"{file_hash[:16]}"
        )
