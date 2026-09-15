from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.forward_income import (
    ForwardIncomeAssumption,
    analyze_forward_income,
)
from src.importer import import_schwab_csv


PORTFOLIO_FILE = Path(
    "/Users/timothykline/Downloads/"
    "All-Accounts-Positions-2026-09-07-173949.csv"
)


def test_real_portfolio_forward_income_integration() -> None:
    portfolio = import_schwab_csv(PORTFOLIO_FILE).portfolio

    shares_by_symbol = {
        holding.symbol: holding.shares
        for holding in portfolio.holdings
        if holding.shares > Decimal("0")
    }

    assumptions = [
        ForwardIncomeAssumption(
            symbol="PFLT",
            forward_annual_income_per_share=(
                Decimal("2800") / shares_by_symbol["PFLT"]
            ),
            effective_date=date(2026, 9, 7),
            source="Integration Test",
        ),
        ForwardIncomeAssumption(
            symbol="BXSL",
            forward_annual_income_per_share=(
                Decimal("2500") / shares_by_symbol["BXSL"]
            ),
            effective_date=date(2026, 9, 7),
            source="Integration Test",
        ),
        ForwardIncomeAssumption(
            symbol="ARCC",
            forward_annual_income_per_share=(
                Decimal("2000") / shares_by_symbol["ARCC"]
            ),
            effective_date=date(2026, 9, 7),
            source="Integration Test",
        ),
    ]

    result = analyze_forward_income(
        portfolio,
        assumptions,
    )

    positive_share_holdings = [
        holding
        for holding in portfolio.holdings
        if holding.shares > Decimal("0")
    ]

    assert len(positive_share_holdings) == 42

    assert result.total_market_value == Decimal("721964.72")

    assert result.total_forward_annual_income == pytest.approx(
    Decimal("7300"),
    abs=Decimal("0.000000000000001"),
    )

    assert set(result.holdings_with_forward_income) == {
        "PFLT",
        "BXSL",
        "ARCC",
    }

    assert len(result.holdings_without_forward_income) == 39

    by_symbol = {
        item.symbol: item
        for item in result.holding_income
    }

    assert by_symbol["PFLT"].forward_annual_income == pytest.approx(
        Decimal("2800"),
        abs=Decimal("0.000000000000001"),
    )

    assert by_symbol["BXSL"].forward_annual_income == pytest.approx(
        Decimal("2500"),
        abs=Decimal("0.000000000000001"),
    )

    assert by_symbol["ARCC"].forward_annual_income == pytest.approx(
        Decimal("2000"),
        abs=Decimal("0.000000000000001"),
    )