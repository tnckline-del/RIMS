from datetime import date
from decimal import Decimal

import pytest

from src.forward_income import (
    ForwardIncomeAssumption,
    analyze_forward_income,
)
from src.forward_income_change import (
    ForwardIncomeChangeReason,
    ForwardIncomePositionState,
)
from src.holding import Holding
from src.portfolio import Portfolio


def make_holding(
    symbol: str,
    shares: str,
    market_value: str,
) -> Holding:
    return Holding(
        symbol=symbol,
        description=f"{symbol} Holding",
        asset_type="Equity",
        sector="Test",
        shares=Decimal(shares),
        price=Decimal("10"),
        cost_basis=Decimal("100"),
        market_value=Decimal(market_value),
    )


def make_portfolio() -> Portfolio:
    return Portfolio(
        name="Test Portfolio",
        holdings=[
            make_holding("AAA", "100", "1000"),
            make_holding("BBB", "200", "2000"),
            make_holding("CCC", "0", "0"),
        ],
    )


def make_assumption(
    symbol: str,
    income_per_share: str,
) -> ForwardIncomeAssumption:
    return ForwardIncomeAssumption(
        symbol=symbol,
        forward_annual_income_per_share=Decimal(income_per_share),
        effective_date=date(2026, 9, 7),
        source="Test",
    )


def test_assumption_normalizes_symbol() -> None:
    assumption = ForwardIncomeAssumption(
        symbol="  arcc ",
        forward_annual_income_per_share=Decimal("1.00"),
        effective_date=date(2026, 9, 7),
        source=" Test ",
    )

    assert assumption.symbol == "ARCC"
    assert assumption.source == "Test"


def test_assumption_rejects_empty_symbol() -> None:
    with pytest.raises(ValueError):
        make_assumption("", "1.00")


def test_assumption_rejects_negative_income() -> None:
    with pytest.raises(ValueError):
        make_assumption("AAA", "-1.00")


def test_assumption_requires_decimal_income() -> None:
    with pytest.raises(TypeError):
        ForwardIncomeAssumption(
            symbol="AAA",
            forward_annual_income_per_share=1.00,
            effective_date=date(2026, 9, 7),
            source="Test",
        )


def test_analysis_uses_only_positive_share_holdings() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "1.00"),
            make_assumption("BBB", "1.00"),
            make_assumption("CCC", "1.00"),
        ],
    )

    assert [item.symbol for item in result.holding_income] == [
        "AAA",
        "BBB",
    ]


def test_total_market_value_uses_current_positive_holdings() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [],
    )

    assert result.total_market_value == Decimal("3000")


def test_forward_income_is_shares_times_income_per_share() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "1.00"),
            make_assumption("BBB", "2.00"),
        ],
    )

    by_symbol = {
        item.symbol: item
        for item in result.holding_income
    }

    assert by_symbol["AAA"].forward_annual_income == Decimal("100")
    assert by_symbol["BBB"].forward_annual_income == Decimal("400")


def test_total_forward_income_is_based_on_current_positions() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "1.00"),
            make_assumption("BBB", "2.00"),
        ],
    )

    assert result.total_forward_annual_income == Decimal("500")


def test_missing_forward_income_is_not_inferred() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "1.00"),
        ],
    )

    holding = next(
        item for item in result.holding_income
        if item.symbol == "BBB"
    )

    assert holding.forward_annual_income == Decimal("0")
    assert holding.has_forward_income is False


def test_holdings_with_and_without_forward_income() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "1.00"),
        ],
    )

    assert result.holdings_with_forward_income == ("AAA",)
    assert result.holdings_without_forward_income == ("BBB",)


def test_forward_income_percentage_is_calculated() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "1.00"),
            make_assumption("BBB", "1.50"),
        ],
    )

    by_symbol = {
        item.symbol: item
        for item in result.holding_income
    }

    assert by_symbol["AAA"].forward_annual_income == Decimal("100")
    assert by_symbol["BBB"].forward_annual_income == Decimal("300")

    assert by_symbol["AAA"].percentage_of_forward_income == Decimal("25")
    assert by_symbol["BBB"].percentage_of_forward_income == Decimal("75")


def test_income_concentration_is_largest_share_of_forward_income() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "1.00"),
            make_assumption("BBB", "1.50"),
        ],
    )

    assert result.income_concentration == Decimal("75")


def test_zero_forward_income_is_not_counted_as_income_producer() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "0"),
            make_assumption("BBB", "1.00"),
        ],
    )

    assert result.holdings_with_forward_income == ("BBB",)
    assert result.holdings_without_forward_income == ()

    aaa = next(
        item for item in result.holding_income
        if item.symbol == "AAA"
    )

    assert aaa.has_forward_income is True
    assert aaa.forward_annual_income == Decimal("0")


def test_no_assumptions_produces_zero_forward_income() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [],
    )

    assert result.total_forward_annual_income == Decimal("0")
    assert result.income_concentration == Decimal("0")


def test_position_change_is_reflected_automatically() -> None:
    portfolio = Portfolio(
        name="Test Portfolio",
        holdings=[
            make_holding("AAA", "100", "1000"),
        ],
    )

    assumption = make_assumption("AAA", "1.00")

    first_result = analyze_forward_income(
        portfolio,
        [assumption],
    )

    portfolio.holdings[0].shares = Decimal("150")

    second_result = analyze_forward_income(
        portfolio,
        [assumption],
    )

    assert (
        first_result.holding_income[0].forward_annual_income
        == Decimal("100")
    )
    assert (
        second_result.holding_income[0].forward_annual_income
        == Decimal("150")
    )


def test_income_per_share_change_is_reflected_automatically() -> None:
    portfolio = make_portfolio()

    first_result = analyze_forward_income(
        portfolio,
        [make_assumption("AAA", "1.00")],
    )

    second_result = analyze_forward_income(
        portfolio,
        [make_assumption("AAA", "1.25")],
    )

    assert (
        first_result.holding_income[0].forward_annual_income
        == Decimal("100")
    )
    assert (
        second_result.holding_income[0].forward_annual_income
        == Decimal("125")
    )


def test_duplicate_symbols_use_latest_assumption() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "1.00"),
            make_assumption("AAA", "2.50"),
        ],
    )

    holding = next(
        item for item in result.holding_income
        if item.symbol == "AAA"
    )

    assert holding.forward_annual_income == Decimal("250")


def test_analysis_does_not_mutate_portfolio() -> None:
    portfolio = make_portfolio()
    original_holdings = tuple(portfolio.holdings)

    analyze_forward_income(
        portfolio,
        [
            make_assumption("AAA", "1.00"),
        ],
    )

    assert tuple(portfolio.holdings) == original_holdings


def test_analysis_rejects_invalid_portfolio() -> None:
    with pytest.raises(TypeError):
        analyze_forward_income(
            "not a portfolio",
            [],
        )


def test_analysis_rejects_invalid_assumption() -> None:
    with pytest.raises(TypeError):
        analyze_forward_income(
            make_portfolio(),
            [object()],
        )
def test_change_reason_is_none_without_baseline() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "1.00"),
        ],
    )

    aaa = next(
        item for item in result.holding_income
        if item.symbol == "AAA"
    )

    assert aaa.change_reason is None


def test_change_reason_detects_position_change() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "1.00"),
        ],
        [
            ForwardIncomePositionState(
                symbol="AAA",
                shares=Decimal("100"),
                forward_annual_income_per_share=Decimal("1.00"),
            ),
        ],
    )

    portfolio = make_portfolio()
    portfolio.holdings[0].shares = Decimal("150")

    result = analyze_forward_income(
        portfolio,
        [
            make_assumption("AAA", "1.00"),
        ],
        [
            ForwardIncomePositionState(
                symbol="AAA",
                shares=Decimal("100"),
                forward_annual_income_per_share=Decimal("1.00"),
            ),
        ],
    )

    aaa = next(
        item for item in result.holding_income
        if item.symbol == "AAA"
    )

    assert aaa.change_reason == ForwardIncomeChangeReason.POSITION_CHANGE


def test_change_reason_detects_dividend_change() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "1.25"),
        ],
        [
            ForwardIncomePositionState(
                symbol="AAA",
                shares=Decimal("100"),
                forward_annual_income_per_share=Decimal("1.00"),
            ),
        ],
    )

    aaa = next(
        item for item in result.holding_income
        if item.symbol == "AAA"
    )

    assert aaa.change_reason == ForwardIncomeChangeReason.DIVIDEND_CHANGE


def test_change_reason_detects_position_and_dividend_change() -> None:
    portfolio = make_portfolio()
    portfolio.holdings[0].shares = Decimal("150")

    result = analyze_forward_income(
        portfolio,
        [
            make_assumption("AAA", "1.25"),
        ],
        [
            ForwardIncomePositionState(
                symbol="AAA",
                shares=Decimal("100"),
                forward_annual_income_per_share=Decimal("1.00"),
            ),
        ],
    )

    aaa = next(
        item for item in result.holding_income
        if item.symbol == "AAA"
    )

    assert aaa.change_reason == (
        ForwardIncomeChangeReason.POSITION_AND_DIVIDEND_CHANGE
    )


def test_change_reason_detects_new_position() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "1.00"),
        ],
        [
            ForwardIncomePositionState(
                symbol="BBB",
                shares=Decimal("200"),
                forward_annual_income_per_share=Decimal("2.00"),
            ),
        ],
    )

    aaa = next(
        item for item in result.holding_income
        if item.symbol == "AAA"
    )

    assert aaa.change_reason == ForwardIncomeChangeReason.NEW_POSITION