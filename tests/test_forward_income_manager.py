"""Tests for forward income management."""

from datetime import date
from decimal import Decimal

import pytest

from src.forward_income import ForwardIncomeAssumption
from src.forward_income_baseline import ForwardIncomeBaseline
from src.forward_income_manager import ForwardIncomeManager
from src.forward_income_store import ForwardIncomeStore
from src.holding import Holding
from src.portfolio import Portfolio
from src.forward_income_change import ForwardIncomeChangeReason


def make_portfolio(
    symbol: str = "ARCC",
    shares: str = "100",
) -> Portfolio:
    """Create a minimal portfolio for testing."""

    holding = Holding(
        symbol=symbol,
        shares=Decimal(shares),
        market_value=Decimal("2000"),
        cost_basis=Decimal("1800"),
        dividend_per_share=Decimal("0"),
        dividend_yield=Decimal("0"),
        asset_type="Equity",
        sector="Financials",
        price=Decimal("20.00"),
        description="Test holding",
    )

    return Portfolio(
        name="Test Portfolio",
        holdings=[holding],
    )

    return Portfolio(
        name="Test Portfolio",
        holdings=[holding],
    )


def make_assumption(
    symbol: str = "ARCC",
    income_per_share: str = "20.00",
) -> ForwardIncomeAssumption:
    """Create a test forward income assumption."""

    return ForwardIncomeAssumption(
        symbol=symbol,
        forward_annual_income_per_share=Decimal(income_per_share),
        effective_date=date(2026, 9, 15),
        source="Test",
    )


def test_first_run_identifies_new_position(tmp_path):
    """A position with an assumption and no baseline is new."""

    store = ForwardIncomeStore(tmp_path)
    store.save((make_assumption(),))

    result = ForwardIncomeManager(
        make_portfolio(),
        tmp_path,
    ).run()

    assert result.analysis.total_forward_annual_income == Decimal("2000")
    assert result.analysis.holding_income[0].change_reason == (
        ForwardIncomeChangeReason.NEW_POSITION
    )


def test_second_run_identifies_no_change(tmp_path):
    """An unchanged position is identified as no change."""

    store = ForwardIncomeStore(tmp_path)
    store.save((make_assumption(),))

    manager = ForwardIncomeManager(
        make_portfolio(),
        tmp_path,
    )

    first_result = manager.run()

    assert first_result.analysis.total_forward_annual_income == Decimal("2000")

    second_result = manager.run()

    assert second_result.analysis.holding_income[0].change_reason == (
        ForwardIncomeChangeReason.NO_CHANGE
    )


def test_position_change_is_detected(tmp_path):
    """A change in shares is identified as a position change."""

    store = ForwardIncomeStore(tmp_path)
    store.save((make_assumption(),))

    manager = ForwardIncomeManager(
        make_portfolio(shares="100"),
        tmp_path,
    )

    manager.run()

    changed_result = ForwardIncomeManager(
        make_portfolio(shares="125"),
        tmp_path,
    ).run()

    assert changed_result.analysis.holding_income[0].change_reason == (
        ForwardIncomeChangeReason.POSITION_CHANGE
    )
    assert (
        changed_result.analysis.total_forward_annual_income
        == Decimal("2500")
    )


def test_dividend_change_is_detected(tmp_path):
    """A change in the expected income rate is identified."""

    store = ForwardIncomeStore(tmp_path)
    store.save((make_assumption(income_per_share="20.00"),))

    manager = ForwardIncomeManager(
        make_portfolio(),
        tmp_path,
    )

    manager.run()

    store.save((make_assumption(income_per_share="18.00"),))

    changed_result = ForwardIncomeManager(
        make_portfolio(),
        tmp_path,
    ).run()

    assert changed_result.analysis.holding_income[0].change_reason == (
        ForwardIncomeChangeReason.DIVIDEND_CHANGE
    )
    assert (
        changed_result.analysis.total_forward_annual_income
        == Decimal("1800")
    )


def test_position_and_dividend_change_is_detected(tmp_path):
    """Changes in shares and expected income are identified together."""

    store = ForwardIncomeStore(tmp_path)
    store.save((make_assumption(income_per_share="20.00"),))

    manager = ForwardIncomeManager(
        make_portfolio(shares="100"),
        tmp_path,
    )

    manager.run()

    store.save((make_assumption(income_per_share="18.00"),))

    changed_result = ForwardIncomeManager(
        make_portfolio(shares="125"),
        tmp_path,
    ).run()

    assert changed_result.analysis.holding_income[0].change_reason == (
        ForwardIncomeChangeReason.POSITION_AND_DIVIDEND_CHANGE
    )
    assert (
        changed_result.analysis.total_forward_annual_income
        == Decimal("2250")
    )


def test_closed_position_appears_once(tmp_path):
    """A closed position appears on the closing report."""

    store = ForwardIncomeStore(tmp_path)
    store.save((make_assumption(),))

    manager = ForwardIncomeManager(
        make_portfolio(),
        tmp_path,
    )

    manager.run()

    closed_result = ForwardIncomeManager(
        make_portfolio(shares="0"),
        tmp_path,
    ).run()

    closed = [
        item
        for item in closed_result.analysis.holding_income
        if item.symbol == "ARCC"
    ]

    assert len(closed) == 1
    assert closed[0].shares == Decimal("0")
    assert closed[0].forward_annual_income == Decimal("0")
    assert closed[0].change_reason == (
        ForwardIncomeChangeReason.POSITION_CLOSED
    )

    assert closed_result.analysis.total_forward_annual_income == Decimal("0")


def test_closed_position_disappears_on_next_report(tmp_path):
    """A closed position disappears after the closing report."""

    store = ForwardIncomeStore(tmp_path)
    store.save((make_assumption(),))

    manager = ForwardIncomeManager(
        make_portfolio(),
        tmp_path,
    )

    manager.run()

    ForwardIncomeManager(
        make_portfolio(shares="0"),
        tmp_path,
    ).run()

    next_result = ForwardIncomeManager(
        Portfolio(
            name="Test Portfolio",
            holdings=[],
        ),
        tmp_path,
    ).run()

    assert not next_result.analysis.holding_income


def test_missing_assumption_has_no_change_reason(tmp_path):
    """A holding without a forward income assumption is not misclassified."""

    result = ForwardIncomeManager(
        make_portfolio(),
        tmp_path,
    ).run()

    assert result.analysis.holding_income[0].has_forward_income is False
    assert result.analysis.holding_income[0].change_reason is None
    assert result.analysis.total_forward_annual_income == Decimal("0")


def test_baseline_is_updated_after_successful_run(tmp_path):
    """The active current states become the new baseline."""

    store = ForwardIncomeStore(tmp_path)
    store.save((make_assumption(),))

    ForwardIncomeManager(
        make_portfolio(shares="125"),
        tmp_path,
    ).run()

    baseline = ForwardIncomeBaseline(tmp_path).load()

    assert len(baseline) == 1
    assert baseline[0].symbol == "ARCC"
    assert baseline[0].shares == Decimal("125")
    assert (
        baseline[0].forward_annual_income_per_share
        == Decimal("20.00")
    )


def test_closed_position_is_removed_from_baseline(tmp_path):
    """A closed position is not carried into the next baseline."""

    store = ForwardIncomeStore(tmp_path)
    store.save((make_assumption(),))

    ForwardIncomeManager(
        make_portfolio(),
        tmp_path,
    ).run()

    ForwardIncomeManager(
        make_portfolio(shares="0"),
        tmp_path,
    ).run()

    baseline = ForwardIncomeBaseline(tmp_path).load()

    assert baseline == ()


def test_new_position_after_previous_run_is_detected(tmp_path):
    """A newly added holding is identified as a new position."""

    store = ForwardIncomeStore(tmp_path)
    store.save((make_assumption("ARCC"),))

    ForwardIncomeManager(
        make_portfolio("ARCC"),
        tmp_path,
    ).run()

    new_portfolio = Portfolio(
        name="Test Portfolio",
        holdings=[
            Holding(
                symbol="ARCC",
                shares=Decimal("100"),
                market_value=Decimal("2000"),
                cost_basis=Decimal("1800"),
                dividend_per_share=Decimal("0"),
                dividend_yield=Decimal("0"),
                asset_type="Equity",
                sector="Financials",
                price=Decimal("20.00"),
                description="Test holding",
            ),
            Holding(
                symbol="BXSL",
                shares=Decimal("50"),
                market_value=Decimal("1000"),
                cost_basis=Decimal("900"),
                dividend_per_share=Decimal("0"),
                dividend_yield=Decimal("0"),
                asset_type="Equity",
                sector="Financials",
                price=Decimal("20.00"),
                description="Test holding",
            ),
        ],
    )

    store.save(
        (
            make_assumption("ARCC"),
            make_assumption("BXSL", "15.00"),
        )
    )

    result = ForwardIncomeManager(
        new_portfolio,
        tmp_path,
    ).run()

    reasons = {
        item.symbol: item.change_reason
        for item in result.analysis.holding_income
    }

    assert reasons["ARCC"] == ForwardIncomeChangeReason.NO_CHANGE
    assert reasons["BXSL"] == ForwardIncomeChangeReason.NEW_POSITION


def test_manager_rejects_invalid_portfolio(tmp_path):
    """The manager requires a Portfolio."""

    with pytest.raises(TypeError, match="portfolio"):
        ForwardIncomeManager("not a portfolio", tmp_path)


def test_manager_creates_storage_directory(tmp_path):
    """The manager can operate with a new storage directory."""

    storage_path = tmp_path / "new_directory"

    result = ForwardIncomeManager(
        make_portfolio(),
        storage_path,
    ).run()

    assert result.analysis.total_forward_annual_income == Decimal("0")
    assert storage_path.exists()


def test_manager_returns_change_summary(tmp_path):
    """The management result exposes the detected changes."""

    store = ForwardIncomeStore(tmp_path)
    store.save((make_assumption(),))

    result = ForwardIncomeManager(
        make_portfolio(),
        tmp_path,
    ).run()

    assert len(result.changes) == 1
    state, reason = result.changes[0]

    assert state.symbol == "ARCC"
    assert state.shares == Decimal("100")
    assert reason == ForwardIncomeChangeReason.NEW_POSITION


def test_closed_position_is_not_counted_in_income(tmp_path):
    """A closed position contributes nothing to forward income totals."""

    store = ForwardIncomeStore(tmp_path)
    store.save((make_assumption(),))

    ForwardIncomeManager(
        make_portfolio(),
        tmp_path,
    ).run()

    result = ForwardIncomeManager(
        make_portfolio(shares="0"),
        tmp_path,
    ).run()

    assert result.analysis.total_forward_annual_income == Decimal("0")
    assert result.analysis.income_concentration == Decimal("0")