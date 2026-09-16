"""Integration test for the forward income portfolio report."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from src.forward_income import ForwardIncomeAssumption
from src.forward_income_manager import ForwardIncomeManager
from src.forward_income_report import generate_forward_income_report
from src.forward_income_store import ForwardIncomeStore
from src.importer import import_schwab_csv


PORTFOLIO_FILE = Path(
    "/Users/timothykline/Downloads/"
    "All-Accounts-Positions-2026-09-07-173949.csv"
)


def test_real_portfolio_forward_income_report(tmp_path):
    """Validate the report against the current Schwab portfolio."""

    result = import_schwab_csv(PORTFOLIO_FILE)

    holdings_by_symbol = {
        holding.symbol: holding
        for holding in result.portfolio.holdings
    }

    assumptions = (
        ForwardIncomeAssumption(
            symbol="PFLT",
            forward_annual_income_per_share=(
                Decimal("2800") / holdings_by_symbol["PFLT"].shares
            ),
            effective_date=date(2026, 9, 7),
            source="Integration Test",
        ),
        ForwardIncomeAssumption(
            symbol="BXSL",
            forward_annual_income_per_share=(
                Decimal("2500") / holdings_by_symbol["BXSL"].shares
            ),
            effective_date=date(2026, 9, 7),
            source="Integration Test",
        ),
        ForwardIncomeAssumption(
            symbol="ARCC",
            forward_annual_income_per_share=(
                Decimal("2000") / holdings_by_symbol["ARCC"].shares
            ),
            effective_date=date(2026, 9, 7),
            source="Integration Test",
        ),
    )

    store = ForwardIncomeStore(tmp_path)
    store.save(assumptions)

    manager = ForwardIncomeManager(
        portfolio=result.portfolio,
        storage_path=str(tmp_path),
    )

    report = generate_forward_income_report(manager)

    positive_share_holdings = tuple(
        holding
        for holding in result.portfolio.holdings
        if holding.shares > Decimal("0")
    )

    assert len(positive_share_holdings) == 42

    assert report.total_market_value == Decimal("721964.72")

    assert report.total_forward_annual_income.quantize(
        Decimal("0.01")
)     == Decimal("7300.00")

    assert report.holdings_with_forward_income == 3

    assert report.holdings_without_forward_income == 39

    assert report.largest_income_holding == "PFLT"

    pflt = next(
        holding
        for holding in report.holdings
        if holding.symbol == "PFLT"
    )

    bxsl = next(
        holding
        for holding in report.holdings
        if holding.symbol == "BXSL"
    )

    arcc = next(
        holding
        for holding in report.holdings
        if holding.symbol == "ARCC"
    )

    assert pflt.forward_annual_income.quantize(
        Decimal("0.01")
    ) == Decimal("2800.00")

    assert bxsl.forward_annual_income.quantize(
        Decimal("0.01")
    ) == Decimal("2500.00")

    assert arcc.forward_annual_income.quantize(
        Decimal("0.01")
    ) == Decimal("2000.00")

    assert pflt.percentage_of_forward_income.quantize(
        Decimal("0.01")
    ) == Decimal("38.36")

    assert bxsl.percentage_of_forward_income.quantize(
        Decimal("0.01")
    ) == Decimal("34.25")

    assert arcc.percentage_of_forward_income.quantize(
        Decimal("0.01")
    ) == Decimal("27.40")