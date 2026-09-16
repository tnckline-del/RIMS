"""Tests for portfolio-level forward income reporting."""

from decimal import Decimal

import pytest

from src.forward_income import ForwardIncomeAssumption
from src.forward_income_change import ForwardIncomeChangeReason
from src.forward_income_manager import ForwardIncomeManager
from src.forward_income_report import (
    ForwardIncomeReport,
    ForwardIncomeReporter,
    generate_forward_income_report,
)
from src.holding import Holding
from src.portfolio import Portfolio


def make_holding(
    symbol: str,
    shares: str,
    market_value: str,
) -> Holding:
    """Create a test holding."""

    return Holding(
        symbol=symbol,
        description=f"{symbol} test holding",
        shares=Decimal(shares),
        price=Decimal(market_value) / Decimal(shares),
        market_value=Decimal(market_value),
        cost_basis=Decimal(market_value),
        asset_type="Equity",
        sector="Financial",
    )


def make_assumption(
    symbol: str,
    income_per_share: str,
) -> ForwardIncomeAssumption:
    """Create a test forward-income assumption."""

    from datetime import date

    return ForwardIncomeAssumption(
        symbol=symbol,
        forward_annual_income_per_share=Decimal(income_per_share),
        effective_date=date(2026, 9, 16),
        source="Test",
    )


def make_manager(
    tmp_path,
    holdings: list[Holding],
    assumptions: tuple[ForwardIncomeAssumption, ...],
) -> ForwardIncomeManager:
    """Create a manager with persisted test assumptions."""

    from src.forward_income_store import ForwardIncomeStore

    store = ForwardIncomeStore(tmp_path)
    store.save(assumptions)

    portfolio = Portfolio(
        name="Test Portfolio",
        holdings=holdings,
    )

    return ForwardIncomeManager(
        portfolio=portfolio,
        storage_path=str(tmp_path),
    )


def test_reporter_requires_forward_income_manager():
    """Reporter should require the correct manager type."""

    with pytest.raises(TypeError):
        ForwardIncomeReporter(object())


def test_generate_report_returns_report_object(tmp_path):
    """Generate should return a ForwardIncomeReport."""

    manager = make_manager(
        tmp_path,
        [
            make_holding("ARCC", "100", "2000"),
        ],
        (
            make_assumption("ARCC", "10"),
        ),
    )

    report = ForwardIncomeReporter(manager).generate()

    assert isinstance(report, ForwardIncomeReport)


def test_report_contains_holding_information(tmp_path):
    """Report should expose the expected holding information."""

    manager = make_manager(
        tmp_path,
        [
            make_holding("ARCC", "100", "2000"),
        ],
        (
            make_assumption("ARCC", "10"),
        ),
    )

    report = generate_forward_income_report(manager)

    assert len(report.holdings) == 1

    holding = report.holdings[0]

    assert holding.symbol == "ARCC"
    assert holding.shares == Decimal("100")
    assert holding.market_value == Decimal("2000")
    assert holding.forward_annual_income == Decimal("1000")
    assert holding.percentage_of_forward_income == Decimal("100")
    assert holding.change_reason == ForwardIncomeChangeReason.NEW_POSITION


def test_report_contains_portfolio_totals(tmp_path):
    """Report should expose portfolio-level totals."""

    manager = make_manager(
        tmp_path,
        [
            make_holding("ARCC", "100", "2000"),
            make_holding("BXSL", "100", "3000"),
        ],
        (
            make_assumption("ARCC", "10"),
            make_assumption("BXSL", "20"),
        ),
    )

    report = generate_forward_income_report(manager)

    assert report.total_market_value == Decimal("5000")
    assert report.total_forward_annual_income == Decimal("3000")
    assert report.holdings_with_forward_income == 2
    assert report.holdings_without_forward_income == 0


def test_report_identifies_largest_income_holding(tmp_path):
    """Report should identify the holding with the largest income."""

    manager = make_manager(
        tmp_path,
        [
            make_holding("ARCC", "100", "2000"),
            make_holding("BXSL", "100", "3000"),
        ],
        (
            make_assumption("ARCC", "10"),
            make_assumption("BXSL", "20"),
        ),
    )

    report = generate_forward_income_report(manager)

    assert report.largest_income_holding == "BXSL"
    assert report.income_concentration == Decimal("66.66666666666666666666666667")


def test_report_identifies_holdings_without_forward_income(tmp_path):
    """Report should identify holdings without assumptions."""

    manager = make_manager(
        tmp_path,
        [
            make_holding("ARCC", "100", "2000"),
            make_holding("XYZ", "100", "3000"),
        ],
        (
            make_assumption("ARCC", "10"),
        ),
    )

    report = generate_forward_income_report(manager)

    assert report.holdings_with_forward_income == 1
    assert report.holdings_without_forward_income == 1

    xyz = next(
        holding
        for holding in report.holdings
        if holding.symbol == "XYZ"
    )

    assert xyz.forward_annual_income == Decimal("0")
    assert xyz.change_reason is None


def test_report_preserves_change_reason(tmp_path):
    """Report should expose changes detected by the manager."""

    manager = make_manager(
        tmp_path,
        [
            make_holding("ARCC", "100", "2000"),
        ],
        (
            make_assumption("ARCC", "10"),
        ),
    )

    first_report = generate_forward_income_report(manager)

    assert (
        first_report.holdings[0].change_reason
        == ForwardIncomeChangeReason.NEW_POSITION
    )

    manager = make_manager(
        tmp_path,
        [
            make_holding("ARCC", "150", "3000"),
        ],
        (
            make_assumption("ARCC", "10"),
        ),
    )

    second_report = generate_forward_income_report(manager)

    assert (
        second_report.holdings[0].change_reason
        == ForwardIncomeChangeReason.POSITION_CHANGE
    )


def test_report_preserves_dividend_change_reason(tmp_path):
    """Report should expose an expected income-rate change."""

    manager = make_manager(
        tmp_path,
        [
            make_holding("ARCC", "100", "2000"),
        ],
        (
            make_assumption("ARCC", "10"),
        ),
    )

    generate_forward_income_report(manager)

    manager = make_manager(
        tmp_path,
        [
            make_holding("ARCC", "100", "2000"),
        ],
        (
            make_assumption("ARCC", "12"),
        ),
    )

    report = generate_forward_income_report(manager)

    assert (
        report.holdings[0].change_reason
        == ForwardIncomeChangeReason.DIVIDEND_CHANGE
    )


def test_closed_position_appears_once(tmp_path):
    """A closed position should appear on the closing report."""

    assumptions = (
        make_assumption("ARCC", "10"),
    )

    manager = make_manager(
        tmp_path,
        [
            make_holding("ARCC", "100", "2000"),
        ],
        assumptions,
    )

    generate_forward_income_report(manager)

    manager = make_manager(
        tmp_path,
        [],
        assumptions,
    )

    closing_report = generate_forward_income_report(manager)

    assert len(closing_report.holdings) == 1
    assert closing_report.holdings[0].symbol == "ARCC"
    assert closing_report.holdings[0].shares == Decimal("0")
    assert (
        closing_report.holdings[0].change_reason
        == ForwardIncomeChangeReason.POSITION_CLOSED
    )

    manager = make_manager(
        tmp_path,
        [],
        assumptions,
    )

    later_report = generate_forward_income_report(manager)

    assert len(later_report.holdings) == 0


def test_report_does_not_mutate_manager_portfolio(tmp_path):
    """Generating a report should not mutate the portfolio."""

    holdings = [
        make_holding("ARCC", "100", "2000"),
        make_holding("BXSL", "100", "3000"),
    ]

    manager = make_manager(
        tmp_path,
        holdings,
        (
            make_assumption("ARCC", "10"),
            make_assumption("BXSL", "20"),
        ),
    )

    before = tuple(manager._portfolio.holdings)

    generate_forward_income_report(manager)

    after = tuple(manager._portfolio.holdings)

    assert after == before


def test_report_with_no_forward_income_is_safe(tmp_path):
    """Report should safely handle a portfolio with no assumptions."""

    manager = make_manager(
        tmp_path,
        [
            make_holding("ARCC", "100", "2000"),
        ],
        (),
    )

    report = generate_forward_income_report(manager)

    assert report.total_forward_annual_income == Decimal("0")
    assert report.holdings_with_forward_income == 0
    assert report.holdings_without_forward_income == 1
    assert report.income_concentration == Decimal("0")
    assert report.largest_income_holding is None
