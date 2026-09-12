from datetime import date
from decimal import Decimal

import pytest

from src.current_income import (
    CurrentIncome,
    CurrentIncomeResult,
    analyze_current_income,
)
from src.holding import Holding
from src.portfolio import Portfolio
from src.transaction import (
    IncomeCharacter,
    IncomeType,
    InvestmentTransaction,
    TaxCharacter,
    TransactionType,
)


def make_holding(
    symbol: str,
    shares: str,
    market_value: str,
) -> Holding:
    """Create a minimal Holding for tests."""
    shares_decimal = Decimal(shares)
    market_value_decimal = Decimal(market_value)

    price = (
        market_value_decimal / shares_decimal
        if shares_decimal != Decimal("0")
        else Decimal("0")
    )

    return Holding(
        symbol=symbol,
        description=f"{symbol} Test Holding",
        asset_type="Stock",
        sector="Test",
        shares=shares_decimal,
        price=price,
        cost_basis=market_value_decimal,
        market_value=market_value_decimal,
    )


def make_income_transaction(
    symbol: str,
    amount: str,
    *,
    recurring: bool = True,
    transaction_date: date = date(2026, 1, 15),
) -> InvestmentTransaction:
    """Create a minimal income transaction for tests."""
    income_character = (
        IncomeCharacter.RECURRING
        if recurring
        else IncomeCharacter.SPECIAL
    )

    return InvestmentTransaction(
        account="TEST",
        transaction_date=transaction_date,
        action="Cash Dividend",
        symbol=symbol or None,
        description="Test income",
        amount=Decimal(amount),
        transaction_type=TransactionType.INCOME,
        income_type=IncomeType.DIVIDEND,
        income_character=income_character,
        tax_character=TaxCharacter.ORDINARY,
    )


def make_portfolio(*holdings: Holding) -> Portfolio:
    """Create a test portfolio."""
    return Portfolio(
        name="Test Portfolio",
        holdings=list(holdings),
    )


def test_current_income_returns_result_for_current_holdings():
    portfolio = make_portfolio(
        make_holding("AAA", "100", "10000"),
        make_holding("BBB", "200", "20000"),
    )
    transactions = (
        make_income_transaction("AAA", "1000"),
        make_income_transaction("BBB", "500"),
    )

    result = analyze_current_income(portfolio, transactions)

    assert isinstance(result, CurrentIncomeResult)
    assert len(result.holding_income) == 2


def test_historical_income_is_assigned_to_correct_holding():
    portfolio = make_portfolio(
        make_holding("AAA", "100", "10000"),
        make_holding("BBB", "200", "20000"),
    )
    transactions = (
        make_income_transaction("AAA", "1000"),
        make_income_transaction("BBB", "500"),
    )

    result = analyze_current_income(portfolio, transactions)

    income = {item.symbol: item for item in result.holding_income}

    assert income["AAA"].historical_income == Decimal("1000")
    assert income["BBB"].historical_income == Decimal("500")


def test_recurring_income_is_assigned_separately():
    portfolio = make_portfolio(
        make_holding("AAA", "100", "10000"),
    )
    transactions = (
        make_income_transaction("AAA", "1000", recurring=True),
        make_income_transaction("AAA", "250", recurring=False),
    )

    result = analyze_current_income(portfolio, transactions)

    item = result.holding_income[0]

    assert item.historical_income == Decimal("1250")
    assert item.recurring_historical_income == Decimal("1000")


def test_percentage_of_recurring_income_is_calculated():
    portfolio = make_portfolio(
        make_holding("AAA", "100", "10000"),
        make_holding("BBB", "200", "20000"),
    )
    transactions = (
        make_income_transaction("AAA", "1000"),
        make_income_transaction("BBB", "500"),
    )

    result = analyze_current_income(portfolio, transactions)

    income = {item.symbol: item for item in result.holding_income}

    assert income["AAA"].percentage_of_recurring_income == (
        Decimal("100") * Decimal("1000") / Decimal("1500")
    )
    assert income["BBB"].percentage_of_recurring_income == (
        Decimal("100") * Decimal("500") / Decimal("1500")
    )


def test_holdings_with_and_without_income_are_identified():
    portfolio = make_portfolio(
        make_holding("AAA", "100", "10000"),
        make_holding("BBB", "200", "20000"),
    )
    transactions = (
        make_income_transaction("AAA", "1000"),
    )

    result = analyze_current_income(portfolio, transactions)

    assert result.holdings_with_income == ("AAA",)
    assert result.holdings_without_income == ("BBB",)


def test_total_market_value_is_reported():
    portfolio = make_portfolio(
        make_holding("AAA", "100", "10000"),
        make_holding("BBB", "200", "20000"),
    )

    result = analyze_current_income(
        portfolio,
        (
            make_income_transaction("AAA", "1000"),
            make_income_transaction("BBB", "500"),
        ),
    )

    assert result.total_market_value == Decimal("30000")


def test_portfolio_income_totals_are_reported():
    portfolio = make_portfolio(
        make_holding("AAA", "100", "10000"),
        make_holding("BBB", "200", "20000"),
    )
    transactions = (
        make_income_transaction("AAA", "1000"),
        make_income_transaction("BBB", "500"),
    )

    result = analyze_current_income(portfolio, transactions)

    assert result.total_historical_income == Decimal("1500")
    assert result.total_recurring_income == Decimal("1500")


def test_income_concentration_is_largest_recurring_income_percentage():
    portfolio = make_portfolio(
        make_holding("AAA", "100", "10000"),
        make_holding("BBB", "200", "20000"),
    )
    transactions = (
        make_income_transaction("AAA", "3000"),
        make_income_transaction("BBB", "1000"),
    )

    result = analyze_current_income(portfolio, transactions)

    assert result.income_concentration == Decimal("75")


def test_no_recurring_income_produces_zero_percentages():
    portfolio = make_portfolio(
        make_holding("AAA", "100", "10000"),
    )
    transactions = (
        make_income_transaction(
            "AAA",
            "1000",
            recurring=False,
        ),
    )

    result = analyze_current_income(portfolio, transactions)

    assert result.total_historical_income == Decimal("1000")
    assert result.total_recurring_income == Decimal("0")
    assert result.holding_income[0].percentage_of_recurring_income == Decimal("0")
    assert result.income_concentration == Decimal("0")


def test_zero_share_holding_is_not_current():
    portfolio = make_portfolio(
        make_holding("AAA", "100", "10000"),
        make_holding("BBB", "0", "0"),
    )
    transactions = (
        make_income_transaction("AAA", "1000"),
        make_income_transaction("BBB", "500"),
    )

    result = analyze_current_income(portfolio, transactions)

    symbols = tuple(item.symbol for item in result.holding_income)

    assert symbols == ("AAA",)
    assert result.total_historical_income == Decimal("1000")


def test_symbolless_income_remains_separate():
    portfolio = make_portfolio(
        make_holding("AAA", "100", "10000"),
    )
    transactions = (
        make_income_transaction("AAA", "1000"),
        make_income_transaction("", "250"),
    )

    result = analyze_current_income(portfolio, transactions)

    assert result.total_historical_income == Decimal("1000")
    assert result.symbolless_historical_income == Decimal("250")


def test_current_holding_without_historical_income_has_zero_income():
    portfolio = make_portfolio(
        make_holding("AAA", "100", "10000"),
    )

    result = analyze_current_income(portfolio, ())

    item = result.holding_income[0]

    assert item.symbol == "AAA"
    assert item.historical_income == Decimal("0")
    assert item.recurring_historical_income == Decimal("0")
    assert item.has_historical_income is False


def test_result_uses_decimal_values():
    portfolio = make_portfolio(
        make_holding("AAA", "100", "10000"),
    )
    transactions = (
        make_income_transaction("AAA", "123.45"),
    )

    result = analyze_current_income(portfolio, transactions)

    item = result.holding_income[0]

    assert isinstance(item.shares, Decimal)
    assert isinstance(item.market_value, Decimal)
    assert isinstance(item.historical_income, Decimal)
    assert isinstance(item.recurring_historical_income, Decimal)
    assert isinstance(item.percentage_of_recurring_income, Decimal)
    assert isinstance(result.total_market_value, Decimal)
    assert isinstance(result.total_historical_income, Decimal)
    assert isinstance(result.total_recurring_income, Decimal)


def test_analysis_does_not_mutate_portfolio():
    holding = make_holding("AAA", "100", "10000")
    portfolio = make_portfolio(holding)
    original_holdings = list(portfolio.holdings)

    analyze_current_income(
        portfolio,
        (make_income_transaction("AAA", "1000"),),
    )

    assert portfolio.holdings == original_holdings
    assert portfolio.holdings[0] is holding


def test_analysis_does_not_mutate_transactions():
    portfolio = make_portfolio(
        make_holding("AAA", "100", "10000"),
    )
    transactions = (
        make_income_transaction("AAA", "1000"),
    )
    original_transactions = transactions

    analyze_current_income(portfolio, transactions)

    assert transactions == original_transactions
    assert transactions is original_transactions


def test_invalid_portfolio_type_is_rejected():
    with pytest.raises(TypeError, match="portfolio must be a Portfolio"):
        CurrentIncome("not a portfolio", ())


def test_invalid_transactions_type_is_rejected():
    portfolio = make_portfolio(
        make_holding("AAA", "100", "10000"),
    )

    with pytest.raises(TypeError, match="transactions must be a tuple"):
        CurrentIncome(portfolio, [])


def test_invalid_transaction_contents_are_rejected():
    portfolio = make_portfolio(
        make_holding("AAA", "100", "10000"),
    )

    with pytest.raises(
        TypeError,
        match="transactions must contain only InvestmentTransaction objects",
    ):
        CurrentIncome(portfolio, ("not a transaction",))