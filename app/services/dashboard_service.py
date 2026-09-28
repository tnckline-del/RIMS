"""Application service for current Dashboard portfolio data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from src.controlled_positions_import import (
    ControlledPositionsImportService,
)
from src.import_health import ImportHealth, ImportHealthService
from src.import_operation import ImportFileType, ImportStatus
from src.import_operation_store import ImportOperationStore
from src.portfolio import Portfolio
from src.snapshot_store import SnapshotStore
from src.transaction import IncomeType
from src.transaction_repository import TransactionRepository

@dataclass(frozen=True, slots=True)
class TrailingIncomeComposition:
    """Summarize recurring dividend and interest income for the trailing year."""

    dividends: Decimal
    interest: Decimal

    @property
    def total(self) -> Decimal:
        """Return total recurring dividend and interest income."""
        return self.dividends + self.interest


class DashboardService:
    """Provide authoritative current portfolio data to the Dashboard."""

    def __init__(
        self,
        import_operation_store: ImportOperationStore,
        snapshot_store: SnapshotStore,
        transaction_repository: TransactionRepository,
) -> None:
        """Initialize the Dashboard service."""
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

        self._transaction_repository = transaction_repository
        self._import_operation_store = import_operation_store

        self._import_health_service = ImportHealthService(
           import_operation_store,
        )

        if not isinstance(snapshot_store, SnapshotStore):
            raise TypeError(
                "snapshot_store must be a SnapshotStore."
            )

        self._positions_import_service = ControlledPositionsImportService(
            import_operation_store=import_operation_store,
            snapshot_store=snapshot_store,
        )

    def get_import_health(self) -> ImportHealth:
        """Return authoritative persisted import health."""
        return self._import_health_service.get_health()

    def has_transaction_data(self) -> bool:
        """Return True when persisted transaction data has been imported."""
        operations = self._import_operation_store.list_operations()

        return any(
            operation.file_type is ImportFileType.TRANSACTIONS
            and operation.status in {
                ImportStatus.IMPORTED,
                ImportStatus.RECONCILED,
            }
            for operation in operations
        )

    def load_current_portfolio(self) -> Portfolio | None:
        """
        Load the authoritative current portfolio.

        The latest successful positions Snapshot is the authoritative
        persisted source. The returned Portfolio is an in-memory
        analytical representation of that Snapshot.
        """
        snapshot = (
            self._positions_import_service.load_current_portfolio()
        )

        if snapshot is None:
            return None

        return Portfolio(
            name=snapshot.portfolio_name,
            holdings=list(snapshot.holdings),
        )

    def trailing_12_month_income(self) -> float:
        """Return recurring dividend and interest income for the trailing year."""
        transactions = self._transaction_repository.all_transactions()

        if not transactions:
            return 0.0

        end_date = max(
            transaction.transaction_date
            for transaction in transactions
        )
        start_date = end_date - timedelta(days=365)

        income = [
            transaction
            for transaction in transactions
            if (
                transaction.is_income
                and transaction.is_recurring_income
                and start_date <= transaction.transaction_date <= end_date
            )
        ]

        return sum(
            transaction.amount
            for transaction in income
        )

    def trailing_income_composition(self) -> TrailingIncomeComposition:
        """Return trailing recurring dividend and interest income."""
        transactions = self._transaction_repository.all_transactions()

        if not transactions:
            return TrailingIncomeComposition(
                dividends=Decimal("0"),
                interest=Decimal("0"),
            )

        end_date = max(
            transaction.transaction_date
            for transaction in transactions
        )
        start_date = end_date - timedelta(days=365)

        income = [
            transaction
            for transaction in transactions
            if (
                transaction.is_income
                and transaction.is_recurring_income
                and start_date <= transaction.transaction_date <= end_date
            )
        ]

        dividends = sum(
            (
                transaction.amount
                for transaction in income
                if transaction.income_type == IncomeType.DIVIDEND
            ),
            Decimal("0"),
        )

        interest = sum(
            (
                transaction.amount
                for transaction in income
                if transaction.income_type == IncomeType.INTEREST
            ),
            Decimal("0"),
        )

        return TrailingIncomeComposition(
            dividends=dividends,
            interest=interest,
        )

def create_dashboard_service(
    import_operation_path: str | Path,
    snapshot_path: str | Path,
    transaction_path: str | Path,
) -> DashboardService:
    """Create a DashboardService using RIMS persistence locations."""
    import_operation_store = ImportOperationStore(
        Path(import_operation_path),
    )
    snapshot_store = SnapshotStore(
        Path(snapshot_path),
    )
    transaction_repository = TransactionRepository.from_path(
        Path(transaction_path),
    )

    return DashboardService(
        import_operation_store=import_operation_store,
        snapshot_store=snapshot_store,
        transaction_repository=transaction_repository,
    )
