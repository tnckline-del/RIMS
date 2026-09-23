"""
Purpose:
    Coordinate post-import financial analysis after successful controlled
    positions and/or transaction imports.

Responsibilities:
    - Process successful controlled import results.
    - Load authoritative persisted portfolio and transaction data.
    - Trigger the appropriate existing financial analysis services.
    - Return a structured immutable processing result.
    - Avoid duplicating financial calculations or persistence ownership.

Design:
    This module is an orchestration layer only. Financial calculations remain
    owned by the existing CurrentIncome, ForwardIncomeManager,
    IncomeAggregator, and HistoricalIncomeAnalyzer services.

Revision History:
    0.1.0 - Initial Sprint 22F implementation.

Author:
    RIMS Development Team
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.controlled_positions_import import (
    ControlledPositionsImportResult,
    ControlledPositionsImportService,
)
from src.controlled_transaction_import import (
    ControlledTransactionImportResult,
)
from src.current_income import CurrentIncome, CurrentIncomeResult
from src.forward_income_manager import (
    ForwardIncomeManagementResult,
    ForwardIncomeManager,
)
from src.historical_income import (
    HistoricalIncomeAnalyzer,
    HistoricalIncomeResult,
)
from src.income_aggregation import (
    IncomeAggregationResult,
    IncomeAggregator,
)
from src.portfolio import Portfolio
from src.snapshot import Snapshot
from src.transaction import InvestmentTransaction
from src.transaction_repository import TransactionRepository

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class PostImportProcessingResult:
    """
    Represent the results of post-import processing.

    The result records which import types triggered processing, which
    financial analyses actually ran, the resulting analysis objects, the
    import identifiers that triggered processing, and the authoritative
    transaction counts observed after processing.
    """

    positions_processed: bool
    transactions_processed: bool

    current_income_processed: bool
    forward_income_processed: bool
    historical_income_processed: bool

    current_income: CurrentIncomeResult | None
    forward_income: ForwardIncomeManagementResult | None
    historical_income: HistoricalIncomeResult | None

    positions_import_id: str | None
    transactions_import_id: str | None

    transactions_available: int
    income_transactions_available: int
    recurring_income_transactions_available: int

    @property
    def analyses_run(self) -> tuple[str, ...]:
        """Return the names of analyses that actually ran."""
        analyses: list[str] = []

        if self.current_income_processed:
            analyses.append("current_income")

        if self.forward_income_processed:
            analyses.append("forward_income")

        if self.historical_income_processed:
            analyses.append("historical_income")

        return tuple(analyses)


class PostImportProcessingCoordinator:
    """
    Coordinate financial analysis after successful controlled imports.

    Positions imports trigger current-income and forward-income processing.

    Transaction imports that add at least one new transaction trigger
    historical-income and current-income processing.

    A transaction import that adds only duplicates does not trigger
    transaction-driven analysis. A combined positions/transaction import
    still processes the positions-driven analyses even when the transaction
    portion adds no new transactions.
    """

    def __init__(
        self,
        positions_import_service: ControlledPositionsImportService,
        transaction_repository: TransactionRepository,
        forward_income_storage_path: str,
    ) -> None:
        """Initialize the coordinator with its required dependencies."""
        if not isinstance(
            positions_import_service,
            ControlledPositionsImportService,
        ):
            raise TypeError(
                "positions_import_service must be a "
                "ControlledPositionsImportService."
            )

        if not isinstance(
            transaction_repository,
            TransactionRepository,
        ):
            raise TypeError(
                "transaction_repository must be a TransactionRepository."
            )

        if not forward_income_storage_path.strip():
            raise ValueError(
                "forward_income_storage_path cannot be blank."
            )

        self._positions_import_service = positions_import_service
        self._transaction_repository = transaction_repository
        self._forward_income_storage_path = forward_income_storage_path

    def process(
        self,
        positions_import: ControlledPositionsImportResult | None = None,
        transactions_import: ControlledTransactionImportResult | None = None,
    ) -> PostImportProcessingResult:
        """
        Process the analyses applicable to the supplied successful imports.

        At least one import result must be supplied.

        The transaction repository is always treated as authoritative for
        transaction analysis. The current portfolio is always reconstructed
        from the latest authoritative persisted positions Snapshot.
        """
        if positions_import is None and transactions_import is None:
            raise ValueError(
                "At least one successful import result is required."
            )

        if positions_import is not None and not isinstance(
            positions_import,
            ControlledPositionsImportResult,
        ):
            raise TypeError(
                "positions_import must be a "
                "ControlledPositionsImportResult."
            )

        if transactions_import is not None and not isinstance(
            transactions_import,
            ControlledTransactionImportResult,
        ):
            raise TypeError(
                "transactions_import must be a "
                "ControlledTransactionImportResult."
            )

        positions_processed = positions_import is not None
        transactions_processed = transactions_import is not None

        new_transactions_added = (
            transactions_import.transactions_added
            if transactions_import is not None
            else 0
        )

        transaction_analysis_required = (
            transactions_processed
            and new_transactions_added > 0
        )

        portfolio_processing_required = (
            positions_processed
            or transaction_analysis_required
        )

        portfolio = (
            self._load_required_portfolio()
            if portfolio_processing_required
            else None
        )

        transactions = self._load_transactions()

        current_income_result: CurrentIncomeResult | None = None
        forward_income_result: ForwardIncomeManagementResult | None = None
        historical_income_result: HistoricalIncomeResult | None = None

        if transaction_analysis_required:
            historical_income_result = self._run_historical_income(
                transactions
            )

        if portfolio_processing_required:
            if portfolio is None:
                raise RuntimeError(
                    "Portfolio processing was required but no portfolio "
                    "was loaded."
                )

            current_income_result = self._run_current_income(
                portfolio,
                transactions,
            )

        if positions_processed:
            if portfolio is None:
                raise RuntimeError(
                    "Positions processing was required but no portfolio "
                    "was loaded."
                )

            forward_income_result = self._run_forward_income(portfolio)

        return PostImportProcessingResult(
            positions_processed=positions_processed,
            transactions_processed=transactions_processed,
            current_income_processed=current_income_result is not None,
            forward_income_processed=forward_income_result is not None,
            historical_income_processed=(
                historical_income_result is not None
            ),
            current_income=current_income_result,
            forward_income=forward_income_result,
            historical_income=historical_income_result,
            positions_import_id=(
                positions_import.operation.import_id
                if positions_import is not None
                else None
            ),
            transactions_import_id=(
                transactions_import.operation.import_id
                if transactions_import is not None
                else None
            ),
            transactions_available=len(transactions),
            income_transactions_available=sum(
                1
                for transaction in transactions
                if transaction.is_income
            ),
            recurring_income_transactions_available=sum(
                1
                for transaction in transactions
                if transaction.is_recurring_income
            ),
        )

    def _load_required_portfolio(self) -> Portfolio:
        """
        Load the authoritative current Snapshot and reconstruct a Portfolio.

        ControlledPositionsImportService.load_current_portfolio() returns
        the latest authoritative persisted Snapshot. The analytical services
        require a Portfolio, so the Snapshot's portfolio name and holdings
        are used to reconstruct the analytical Portfolio representation.

        The Snapshot remains the authoritative persisted source; this
        Portfolio is an in-memory analysis object only.
        """
        snapshot = self._positions_import_service.load_current_portfolio()

        if snapshot is None:
            raise RuntimeError(
                "No current portfolio is available."
            )

        if not isinstance(snapshot, Snapshot):
            raise TypeError(
                "load_current_portfolio() must return a Snapshot."
            )

        return Portfolio(
            name=snapshot.portfolio_name,
            holdings=list(snapshot.holdings),
        )

    def _load_transactions(self) -> tuple[InvestmentTransaction, ...]:
        """
        Load the complete authoritative transaction dataset.
        """
        transactions = self._transaction_repository.all_transactions()

        if not isinstance(transactions, tuple):
            transactions = tuple(transactions)

        for transaction in transactions:
            if not isinstance(transaction, InvestmentTransaction):
                raise TypeError(
                    "TransactionRepository returned a non-"
                    "InvestmentTransaction value."
                )

        return transactions

    @staticmethod
    def _run_historical_income(
        transactions: tuple[InvestmentTransaction, ...],
    ) -> HistoricalIncomeResult:
        """Run historical-income analysis from authoritative transactions."""
        aggregation: IncomeAggregationResult = (
            IncomeAggregator.from_transactions(transactions)
        )

        return HistoricalIncomeAnalyzer().analyze(aggregation)

    @staticmethod
    def _run_current_income(
        portfolio: Portfolio,
        transactions: tuple[InvestmentTransaction, ...],
    ) -> CurrentIncomeResult:
        """Run current-income analysis."""
        return CurrentIncome(
            portfolio,
            transactions,
        ).analyze()

    def _run_forward_income(
        self,
        portfolio: Portfolio,
    ) -> ForwardIncomeManagementResult:
        """
        Run forward-income management.

        ForwardIncomeManager remains responsible for its own assumptions,
        baseline persistence, change detection, and forward-income analysis.
        """
        return ForwardIncomeManager(
            portfolio,
            self._forward_income_storage_path,
        ).run()
