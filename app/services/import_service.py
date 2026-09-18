"""Application service for validating Schwab import files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.importer import SchwabImportResult, import_schwab_csv
from src.schwab_income_importer import (
    SchwabIncomeImportResult,
    import_schwab_income_csv,
)


@dataclass(frozen=True, slots=True)
class PositionsValidationResult:
    """Validation result for a Schwab positions file."""

    is_valid: bool
    source_file: str
    holding_count: int
    market_value_difference: Decimal
    cost_basis_difference: Decimal
    is_reconciled: bool
    error: str | None = None
    import_result: SchwabImportResult | None = None


@dataclass(frozen=True, slots=True)
class TransactionsValidationResult:
    """Validation result for a Schwab transaction file."""

    is_valid: bool
    source_file: str
    account: str
    transaction_count: int
    income_transaction_count: int
    recurring_income_amount: Decimal
    start_date: date | None
    end_date: date | None
    error: str | None = None
    import_result: SchwabIncomeImportResult | None = None


class ImportService:
    """Application-layer interface to the existing Schwab importers."""

    def validate_positions(
        self,
        file_path: str | Path,
        portfolio_name: str = "Schwab Portfolio",
    ) -> PositionsValidationResult:
        """Validate a Schwab positions file without persisting it."""
        path = Path(file_path)

        if not path.is_file():
            return PositionsValidationResult(
                is_valid=False,
                source_file=path.name,
                holding_count=0,
                market_value_difference=Decimal("0"),
                cost_basis_difference=Decimal("0"),
                is_reconciled=False,
                error=f"File not found: {path}",
            )

        try:
            result = import_schwab_csv(
                path,
                portfolio_name=portfolio_name,
            )
        except (OSError, ValueError, TypeError) as exc:
            return PositionsValidationResult(
                is_valid=False,
                source_file=path.name,
                holding_count=0,
                market_value_difference=Decimal("0"),
                cost_basis_difference=Decimal("0"),
                is_reconciled=False,
                error=str(exc),
            )

        return self._positions_result(path, result)

    def validate_transactions(
        self,
        file_path: str | Path,
        account: str,
    ) -> TransactionsValidationResult:
        """Validate a Schwab transaction file without persisting it."""
        path = Path(file_path)
        normalized_account = account.strip()

        if not path.is_file():
            return TransactionsValidationResult(
                is_valid=False,
                source_file=path.name,
                account=normalized_account,
                transaction_count=0,
                income_transaction_count=0,
                recurring_income_amount=Decimal("0"),
                start_date=None,
                end_date=None,
                error=f"File not found: {path}",
            )

        if not normalized_account:
            return TransactionsValidationResult(
                is_valid=False,
                source_file=path.name,
                account="",
                transaction_count=0,
                income_transaction_count=0,
                recurring_income_amount=Decimal("0"),
                start_date=None,
                end_date=None,
                error="Account is required for Schwab transaction imports.",
            )

        try:
            result = import_schwab_income_csv(
                path,
                account=normalized_account,
            )
        except (OSError, ValueError, TypeError) as exc:
            return TransactionsValidationResult(
                is_valid=False,
                source_file=path.name,
                account=normalized_account,
                transaction_count=0,
                income_transaction_count=0,
                recurring_income_amount=Decimal("0"),
                start_date=None,
                end_date=None,
                error=str(exc),
            )

        return self._transactions_result(path, normalized_account, result)

    @staticmethod
    def _positions_result(
        path: Path,
        result: SchwabImportResult,
    ) -> PositionsValidationResult:
        """Build a structured positions validation result."""
        return PositionsValidationResult(
            is_valid=True,
            source_file=path.name,
            holding_count=result.portfolio.holding_count,
            market_value_difference=result.market_value_difference,
            cost_basis_difference=result.cost_basis_difference,
            is_reconciled=result.is_reconciled,
            import_result=result,
        )

    @staticmethod
    def _transactions_result(
        path: Path,
        account: str,
        result: SchwabIncomeImportResult,
    ) -> TransactionsValidationResult:
        """Build a structured transaction validation result."""
        dates = [
            transaction.transaction_date
            for transaction in result.transactions
        ]

        return TransactionsValidationResult(
            is_valid=True,
            source_file=path.name,
            account=account,
            transaction_count=result.transaction_count,
            income_transaction_count=result.income_transaction_count,
            recurring_income_amount=result.recurring_income_amount,
            start_date=min(dates) if dates else None,
            end_date=max(dates) if dates else None,
            import_result=result,
        )


def validate_positions_file(
    file_path: str | Path,
    portfolio_name: str = "Schwab Portfolio",
) -> PositionsValidationResult:
    """Validate a Schwab positions file."""
    return ImportService().validate_positions(
        file_path,
        portfolio_name=portfolio_name,
    )


def validate_transactions_file(
    file_path: str | Path,
    account: str,
) -> TransactionsValidationResult:
    """Validate a Schwab transaction file."""
    return ImportService().validate_transactions(
        file_path,
        account=account,
    )
