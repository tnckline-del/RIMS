from datetime import date
from decimal import Decimal

import pytest

from src.forward_income import (
    ForwardIncomeAssumption,
    analyze_forward_income,
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
    income: str,
) -> ForwardIncomeAssumption:
    return ForwardIncomeAssumption(
        symbol=symbol,
        forward_annual_income=Decimal(income),
        effective_date=date(2026, 9, 7),
        source="Test",
    )


def test_assumption_normalizes_symbol() -> None:
    assumption = ForwardIncomeAssumption(
        symbol="  arcc ",
        forward_annual_income=Decimal("100"),
        effective_date=date(2026, 9, 7),
        source=" Test ",
    )

    assert assumption.symbol == "ARCC"
    assert assumption.source == "Test"


def test_assumption_rejects_empty_symbol() -> None:
    with pytest.raises(ValueError):
        make_assumption("", "100")


def test_assumption_rejects_negative_income() -> None:
    with pytest.raises(ValueError):
        make_assumption("AAA", "-1")


def test_assumption_requires_decimal_income() -> None:
    with pytest.raises(TypeError):
        ForwardIncomeAssumption(
            symbol="AAA",
            forward_annual_income=100,
            effective_date=date(2026, 9, 7),
            source="Test",
        )


def test_analysis_uses_only_positive_share_holdings() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "100"),
            make_assumption("BBB", "200"),
            make_assumption("CCC", "300"),
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


def test_total_forward_income_is_explicit_assumptions_only() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "100"),
            make_assumption("BBB", "200"),
        ],
    )

    assert result.total_forward_annual_income == Decimal("300")


def test_missing_forward_income_is_not_inferred() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "100"),
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
            make_assumption("AAA", "100"),
        ],
    )

    assert result.holdings_with_forward_income == ("AAA",)
    assert result.holdings_without_forward_income == ("BBB",)


def test_forward_income_percentage_is_calculated() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "100"),
            make_assumption("BBB", "300"),
        ],
    )

    by_symbol = {
        item.symbol: item
        for item in result.holding_income
    }

    assert by_symbol["AAA"].percentage_of_forward_income == Decimal("25")
    assert by_symbol["BBB"].percentage_of_forward_income == Decimal("75")


def test_income_concentration_is_largest_share_of_forward_income() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "100"),
            make_assumption("BBB", "300"),
        ],
    )

    assert result.income_concentration == Decimal("75")


def test_zero_forward_income_is_not_counted_as_income_producer() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "0"),
            make_assumption("BBB", "200"),
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


def test_duplicate_symbols_use_latest_assumption() -> None:
    result = analyze_forward_income(
        make_portfolio(),
        [
            make_assumption("AAA", "100"),
            make_assumption("AAA", "250"),
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
            make_assumption("AAA", "100"),
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