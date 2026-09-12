"""
Tests for historical income/current portfolio reconciliation.

Sprint 19I test coverage includes:
    - Current holdings with historical income.
    - Current holdings without historical income.
    - Historical income from securities no longer held.
    - Zero-share holdings treated as not currently held.
    - Recurring income versus non-recurring income.
    - Symbolless income.
    - Decimal preservation.
    - Input validation.
    - Convenience-function behavior.
"""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from src.holding import Holding
from src.income_portfolio import (
    IncomePortfolio,
    IncomePortfolioResult,
    reconcile_income_with_portfolio,
)
from src.portfolio import Portfolio
from src.transaction import (
    IncomeCharacter,
    IncomeType,
    InvestmentTransaction,
    TransactionType,
)


def make_holding(
    symbol: str,
    shares: str,
) -> Holding:
    """Create a minimal holding for reconciliation tests."""

    return Holding(
        symbol=symbol,
        description=f"Test holding {symbol}",
        asset_type="Equity",
        sector="Test",
        shares=Decimal(shares),
        price=Decimal("10.00"),
        cost_basis=Decimal(shares) * Decimal("10.00"),
        dividend_per_share=Decimal("1.00"),
        dividend_yield=Decimal("10.00"),
    )


def make_portfolio(*holdings: Holding) -> Portfolio:
    """Create a portfolio containing the supplied holdings."""

    return Portfolio(
        name="Test Portfolio",
        holdings=list(holdings),
    )


def make_income(
    symbol: str | None,
    amount: str,
    *,
    recurring: bool = True,
    income_type: IncomeType = IncomeType.DIVIDEND,
) -> InvestmentTransaction:
    """Create a minimal income transaction."""

    character = (
        IncomeCharacter.RECURRING
        if recurring
        else IncomeCharacter.SPECIAL
    )

    return InvestmentTransaction(
        account="Test Account",
        transaction_date=date(2026, 1, 15),
        action="Cash Dividend",
        symbol=symbol,
        description="Test income",
        amount=Decimal(amount),
        transaction_type=TransactionType.INCOME,
        income_type=income_type,
        income_character=character,
    )


class TestIncomePortfolio(unittest.TestCase):
    """Test IncomePortfolio reconciliation behavior."""

    def test_current_holding_with_historical_income(self) -> None:
        portfolio = make_portfolio(
            make_holding("ABC", "100"),
        )
        transactions = (
            make_income("ABC", "125.50"),
        )

        result = IncomePortfolio(portfolio, transactions).reconcile()

        self.assertEqual(
            result.current_holdings_with_history,
            ("ABC",),
        )
        self.assertEqual(
            result.historical_income_by_current_holding["ABC"],
            Decimal("125.50"),
        )
        self.assertEqual(
            result.total_historical_income_from_current_holdings,
            Decimal("125.50"),
        )

    def test_current_holding_without_historical_income(self) -> None:
        portfolio = make_portfolio(
            make_holding("ABC", "100"),
            make_holding("XYZ", "50"),
        )
        transactions = (
            make_income("ABC", "125.50"),
        )

        result = IncomePortfolio(portfolio, transactions).reconcile()

        self.assertEqual(
            result.current_holdings_without_history,
            ("XYZ",),
        )
        self.assertEqual(
            result.current_holdings_with_history,
            ("ABC",),
        )

    def test_historical_security_no_longer_held(self) -> None:
        portfolio = make_portfolio(
            make_holding("ABC", "100"),
        )
        transactions = (
            make_income("ABC", "100.00"),
            make_income("OLD", "250.00"),
        )

        result = IncomePortfolio(portfolio, transactions).reconcile()

        self.assertEqual(
            result.historical_symbols_not_currently_held,
            ("OLD",),
        )
        self.assertEqual(
            result.total_historical_income_from_no_longer_held,
            Decimal("250.00"),
        )

    def test_zero_share_holding_is_not_currently_held(self) -> None:
        portfolio = make_portfolio(
            make_holding("ABC", "0"),
        )
        transactions = (
            make_income("ABC", "100.00"),
        )

        result = IncomePortfolio(portfolio, transactions).reconcile()

        self.assertEqual(
            result.current_holdings_with_history,
            (),
        )
        self.assertEqual(
            result.current_holdings_without_history,
            (),
        )
        self.assertEqual(
            result.historical_symbols_not_currently_held,
            ("ABC",),
        )
        self.assertEqual(
            result.total_historical_income_from_no_longer_held,
            Decimal("100.00"),
        )

    def test_recurring_income_is_separated_from_total_income(self) -> None:
        portfolio = make_portfolio(
            make_holding("ABC", "100"),
        )
        transactions = (
            make_income("ABC", "100.00", recurring=True),
            make_income("ABC", "25.00", recurring=False),
        )

        result = IncomePortfolio(portfolio, transactions).reconcile()

        self.assertEqual(
            result.historical_income_by_current_holding["ABC"],
            Decimal("125.00"),
        )
        self.assertEqual(
            result.recurring_income_by_current_holding["ABC"],
            Decimal("100.00"),
        )
        self.assertEqual(
            result.total_historical_income_from_current_holdings,
            Decimal("125.00"),
        )
        self.assertEqual(
            result.total_recurring_income_from_current_holdings,
            Decimal("100.00"),
        )

    def test_symbolless_income_is_preserved_separately(self) -> None:
        portfolio = make_portfolio(
            make_holding("ABC", "100"),
        )
        transactions = (
            make_income("ABC", "100.00"),
            make_income(None, "12.34", income_type=IncomeType.INTEREST),
        )

        result = IncomePortfolio(portfolio, transactions).reconcile()

        self.assertEqual(
            result.total_historical_income_from_current_holdings,
            Decimal("100.00"),
        )
        self.assertEqual(
            result.total_symbolless_historical_income,
            Decimal("12.34"),
        )
        self.assertNotIn(
            "",
            result.historical_income_by_current_holding,
        )

    def test_multiple_transactions_are_aggregated_by_symbol(self) -> None:
        portfolio = make_portfolio(
            make_holding("ABC", "100"),
        )
        transactions = (
            make_income("ABC", "25.10"),
            make_income("abc", "30.20"),
            make_income("ABC", "44.70"),
        )

        result = IncomePortfolio(portfolio, transactions).reconcile()

        self.assertEqual(
            result.historical_income_by_current_holding["ABC"],
            Decimal("100.00"),
        )
        self.assertEqual(
            result.recurring_income_by_current_holding["ABC"],
            Decimal("100.00"),
        )

    def test_symbols_are_case_insensitive(self) -> None:
        portfolio = make_portfolio(
            make_holding("abc", "100"),
        )
        transactions = (
            make_income("ABC", "75.00"),
        )

        result = IncomePortfolio(portfolio, transactions).reconcile()

        self.assertEqual(
            result.current_holdings_with_history,
            ("ABC",),
        )
        self.assertEqual(
            result.historical_income_by_current_holding["ABC"],
            Decimal("75.00"),
        )

    def test_income_transactions_only_are_included(self) -> None:
        portfolio = make_portfolio(
            make_holding("ABC", "100"),
        )

        income = make_income("ABC", "100.00")
        purchase = InvestmentTransaction(
            account="Test Account",
            transaction_date=date(2026, 1, 20),
            action="Buy",
            symbol="ABC",
            description="Test purchase",
            amount=Decimal("-500.00"),
            transaction_type=TransactionType.PURCHASE,
        )

        transactions = (income, purchase)

        result = IncomePortfolio(portfolio, transactions).reconcile()

        self.assertEqual(
            result.total_historical_income_from_current_holdings,
            Decimal("100.00"),
        )

    def test_no_transactions_returns_empty_reconciliation(self) -> None:
        portfolio = make_portfolio(
            make_holding("ABC", "100"),
        )

        result = IncomePortfolio(portfolio, ()).reconcile()

        self.assertEqual(result.current_holdings_with_history, ())
        self.assertEqual(
            result.current_holdings_without_history,
            ("ABC",),
        )
        self.assertEqual(
            result.historical_symbols_not_currently_held,
            (),
        )
        self.assertEqual(
            result.total_historical_income_from_current_holdings,
            Decimal("0"),
        )
        self.assertEqual(
            result.total_recurring_income_from_current_holdings,
            Decimal("0"),
        )
        self.assertEqual(
            result.total_historical_income_from_no_longer_held,
            Decimal("0"),
        )
        self.assertEqual(
            result.total_symbolless_historical_income,
            Decimal("0"),
        )

    def test_inputs_are_not_modified(self) -> None:
        portfolio = make_portfolio(
            make_holding("ABC", "100"),
        )
        transactions = (
            make_income("ABC", "100.00"),
        )

        original_transactions = transactions
        original_holding_shares = portfolio.holdings[0].shares

        IncomePortfolio(portfolio, transactions).reconcile()

        self.assertIs(transactions, original_transactions)
        self.assertEqual(
            portfolio.holdings[0].shares,
            original_holding_shares,
        )

    def test_decimal_values_are_preserved(self) -> None:
        portfolio = make_portfolio(
            make_holding("ABC", "100"),
        )
        transactions = (
            make_income("ABC", "0.01"),
            make_income("ABC", "0.02"),
            make_income("ABC", "0.03"),
        )

        result = IncomePortfolio(portfolio, transactions).reconcile()

        self.assertIsInstance(
            result.total_historical_income_from_current_holdings,
            Decimal,
        )
        self.assertEqual(
            result.total_historical_income_from_current_holdings,
            Decimal("0.06"),
        )

    def test_invalid_portfolio_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            IncomePortfolio(  # type: ignore[arg-type]
                portfolio="not a portfolio",
                transactions=(),
            )

    def test_invalid_transactions_container_is_rejected(self) -> None:
        portfolio = make_portfolio(
            make_holding("ABC", "100"),
        )

        with self.assertRaises(TypeError):
            IncomePortfolio(  # type: ignore[arg-type]
                portfolio=portfolio,
                transactions=[],
            )

    def test_invalid_transaction_object_is_rejected(self) -> None:
        portfolio = make_portfolio(
            make_holding("ABC", "100"),
        )

        with self.assertRaises(TypeError):
            IncomePortfolio(  # type: ignore[arg-type]
                portfolio=portfolio,
                transactions=("not a transaction",),
            )

    def test_convenience_function_matches_service(self) -> None:
        portfolio = make_portfolio(
            make_holding("ABC", "100"),
            make_holding("XYZ", "50"),
        )
        transactions = (
            make_income("ABC", "100.00"),
            make_income("OLD", "50.00"),
            make_income(None, "10.00"),
        )

        service_result = IncomePortfolio(
            portfolio,
            transactions,
        ).reconcile()

        function_result = reconcile_income_with_portfolio(
            portfolio,
            transactions,
        )

        self.assertEqual(service_result, function_result)

    def test_result_is_income_portfolio_result(self) -> None:
        portfolio = make_portfolio(
            make_holding("ABC", "100"),
        )
        transactions = (
            make_income("ABC", "100.00"),
        )

        result = IncomePortfolio(portfolio, transactions).reconcile()

        self.assertIsInstance(result, IncomePortfolioResult)


if __name__ == "__main__":
    unittest.main()