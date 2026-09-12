from decimal import Decimal
from pathlib import Path

from src.current_income import analyze_current_income
from src.importer import import_schwab_csv
from src.transaction_repository import TransactionRepository


CURRENT_PORTFOLIO_PATH = Path(
    "/Users/timothykline/Downloads/"
    "All-Accounts-Positions-2026-09-07-173949.csv"
)

TRANSACTION_PATH = Path("data/transactions")


def test_current_income_real_data_integration():
    """Validate current income analysis against the real RIMS data."""
    assert CURRENT_PORTFOLIO_PATH.exists()
    assert TRANSACTION_PATH.exists()

    portfolio_result = import_schwab_csv(CURRENT_PORTFOLIO_PATH)
    repository = TransactionRepository.from_path(TRANSACTION_PATH)

    transactions = repository.all_transactions()

    result = analyze_current_income(
        portfolio_result.portfolio,
        transactions,
    )

    assert len(portfolio_result.portfolio.holdings) == 44
    assert len(transactions) == 779

    assert result.total_market_value == Decimal("721964.72")

    assert result.total_historical_income == Decimal("63336.50")
    assert result.total_recurring_income == Decimal("61155.51")

    assert result.symbolless_historical_income == Decimal("87.33")

    assert (
        result.total_historical_income
        + Decimal("5016.21")
        + result.symbolless_historical_income
    ) == Decimal("68440.04")

    assert (
        result.total_recurring_income
        <= Decimal("65533.10")
    )

    assert len(result.holding_income) == 42

    assert len(result.holdings_with_income) > 0
    assert len(result.holdings_without_income) > 0

    assert all(
        item.market_value >= Decimal("0")
        for item in result.holding_income
    )

    assert all(
        item.historical_income >= Decimal("0")
        for item in result.holding_income
    )

    assert all(
        item.recurring_historical_income >= Decimal("0")
        for item in result.holding_income
    )

    assert all(
        item.percentage_of_recurring_income >= Decimal("0")
        for item in result.holding_income
    )

    assert result.income_concentration >= Decimal("0")
    assert result.income_concentration <= Decimal("100")