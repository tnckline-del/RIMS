"""
Reconcile historical investment income with the current portfolio.

Sprint 19I provides a RIMS-level analysis that connects two distinct
sets of information:

    - Current portfolio holdings.
    - Historical investment-income transactions.

The reconciliation is performed by security symbol.

Responsibilities:
    - Identify current holdings that have historical income.
    - Identify current holdings with no historical income.
    - Identify historical income from securities no longer currently held.
    - Summarize historical and recurring income attributable to current holdings.
    - Preserve symbolless historical income separately.

This module does not import source files, modify portfolio or transaction
objects, forecast future income, or annualize historical results.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .portfolio import Portfolio
from .transaction import InvestmentTransaction


@dataclass(frozen=True, slots=True)
class IncomePortfolioResult:
    """Results of reconciling historical income with current holdings."""

    current_holdings_with_history: tuple[str, ...]
    current_holdings_without_history: tuple[str, ...]
    historical_symbols_not_currently_held: tuple[str, ...]
    historical_income_by_current_holding: dict[str, Decimal]
    recurring_income_by_current_holding: dict[str, Decimal]
    total_historical_income_from_current_holdings: Decimal
    total_recurring_income_from_current_holdings: Decimal
    total_historical_income_from_no_longer_held: Decimal
    total_symbolless_historical_income: Decimal


class IncomePortfolio:
    """
    Reconcile historical income transactions with the current portfolio.

    Matching is based exclusively on security symbol. Historical income
    without a symbol remains separate and is never assigned to a holding.
    """

    def __init__(
        self,
        portfolio: Portfolio,
        transactions: tuple[InvestmentTransaction, ...],
    ) -> None:
        if not isinstance(portfolio, Portfolio):
            raise TypeError("portfolio must be a Portfolio.")

        if not isinstance(transactions, tuple):
            raise TypeError("transactions must be a tuple.")

        for transaction in transactions:
            if not isinstance(transaction, InvestmentTransaction):
                raise TypeError(
                    "transactions must contain InvestmentTransaction objects."
                )

        self._portfolio = portfolio
        self._transactions = transactions

    def reconcile(self) -> IncomePortfolioResult:
        """Return the historical-income/current-portfolio reconciliation."""

        current_symbols = self._current_holding_symbols()

        historical_income_by_symbol: dict[str, Decimal] = {}
        recurring_income_by_symbol: dict[str, Decimal] = {}
        symbolless_income = Decimal("0")

        for transaction in self._income_transactions():
            amount = transaction.amount

            if transaction.symbol is None:
                symbolless_income += amount
                continue

            symbol = transaction.symbol.strip().upper()

            if not symbol:
                symbolless_income += amount
                continue

            historical_income_by_symbol[symbol] = (
                historical_income_by_symbol.get(symbol, Decimal("0")) + amount
            )

            if transaction.is_recurring_income:
                recurring_income_by_symbol[symbol] = (
                    recurring_income_by_symbol.get(symbol, Decimal("0"))
                    + amount
                )

        current_with_history = tuple(
            sorted(
                symbol
                for symbol in current_symbols
                if symbol in historical_income_by_symbol
            )
        )

        current_without_history = tuple(
            sorted(
                symbol
                for symbol in current_symbols
                if symbol not in historical_income_by_symbol
            )
        )

        historical_not_currently_held = tuple(
            sorted(
                symbol
                for symbol in historical_income_by_symbol
                if symbol not in current_symbols
            )
        )

        historical_income_current = {
            symbol: historical_income_by_symbol[symbol]
            for symbol in current_with_history
        }

        recurring_income_current = {
            symbol: recurring_income_by_symbol.get(symbol, Decimal("0"))
            for symbol in current_with_history
        }

        total_current_income = sum(
            historical_income_current.values(),
            Decimal("0"),
        )

        total_current_recurring_income = sum(
            recurring_income_current.values(),
            Decimal("0"),
        )

        total_no_longer_held_income = sum(
            (
                historical_income_by_symbol[symbol]
                for symbol in historical_not_currently_held
            ),
            Decimal("0"),
        )

        return IncomePortfolioResult(
            current_holdings_with_history=current_with_history,
            current_holdings_without_history=current_without_history,
            historical_symbols_not_currently_held=historical_not_currently_held,
            historical_income_by_current_holding=historical_income_current,
            recurring_income_by_current_holding=recurring_income_current,
            total_historical_income_from_current_holdings=total_current_income,
            total_recurring_income_from_current_holdings=(
                total_current_recurring_income
            ),
            total_historical_income_from_no_longer_held=(
                total_no_longer_held_income
            ),
            total_symbolless_historical_income=symbolless_income,
        )

    def _current_holding_symbols(self) -> set[str]:
        """Return symbols for holdings with a positive share balance."""

        symbols: set[str] = set()

        for holding in self._portfolio.holdings:
            symbol = holding.symbol.strip().upper()

            if holding.shares > 0:
                symbols.add(symbol)

        return symbols

    def _income_transactions(
        self,
    ) -> tuple[InvestmentTransaction, ...]:
        """Return income transactions without modifying source data."""

        return tuple(
            transaction
            for transaction in self._transactions
            if transaction.is_income
        )


def reconcile_income_with_portfolio(
    portfolio: Portfolio,
    transactions: tuple[InvestmentTransaction, ...],
) -> IncomePortfolioResult:
    """
    Convenience function for current-portfolio/historical-income
    reconciliation.
    """

    return IncomePortfolio(
        portfolio=portfolio,
        transactions=transactions,
    ).reconcile()