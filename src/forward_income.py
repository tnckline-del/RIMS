"""Forward annual income assumptions and portfolio aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from .portfolio import Portfolio


@dataclass(frozen=True, slots=True)
class ForwardIncomeAssumption:
    """Explicit forward annual income assumption for one security."""

    symbol: str
    forward_annual_income: Decimal
    effective_date: date
    source: str
    notes: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str):
            raise TypeError("symbol must be a string")

        normalized_symbol = self.symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("symbol must not be empty")

        if not isinstance(self.forward_annual_income, Decimal):
            raise TypeError("forward_annual_income must be a Decimal")

        if self.forward_annual_income < Decimal("0"):
            raise ValueError("forward_annual_income must not be negative")

        if not isinstance(self.effective_date, date):
            raise TypeError("effective_date must be a date")

        if not isinstance(self.source, str):
            raise TypeError("source must be a string")

        if not self.source.strip():
            raise ValueError("source must not be empty")

        if not isinstance(self.notes, str):
            raise TypeError("notes must be a string")

        object.__setattr__(self, "symbol", normalized_symbol)
        object.__setattr__(
            self,
            "source",
            self.source.strip(),
        )


@dataclass(frozen=True, slots=True)
class ForwardHoldingIncome:
    """Forward annual income associated with one current holding."""

    symbol: str
    shares: Decimal
    market_value: Decimal
    forward_annual_income: Decimal
    percentage_of_forward_income: Decimal
    has_forward_income: bool


@dataclass(frozen=True, slots=True)
class ForwardIncomeResult:
    """Portfolio-level forward income analysis."""

    holding_income: tuple[ForwardHoldingIncome, ...]
    total_market_value: Decimal
    total_forward_annual_income: Decimal
    holdings_with_forward_income: tuple[str, ...]
    holdings_without_forward_income: tuple[str, ...]
    income_concentration: Decimal


class ForwardIncome:
    """Analyze explicit forward annual income assumptions for a portfolio."""

    def __init__(
        self,
        portfolio: Portfolio,
        assumptions: Iterable[ForwardIncomeAssumption] = (),
    ) -> None:
        if not isinstance(portfolio, Portfolio):
            raise TypeError("portfolio must be a Portfolio")

        assumption_tuple = tuple(assumptions)

        for assumption in assumption_tuple:
            if not isinstance(assumption, ForwardIncomeAssumption):
                raise TypeError(
                    "assumptions must contain only "
                    "ForwardIncomeAssumption objects"
                )

        self._portfolio = portfolio
        self._assumptions = assumption_tuple

    def analyze(self) -> ForwardIncomeResult:
        """Return forward annual income for current positive-share holdings."""

        current_holdings = self._current_holdings()
        assumptions_by_symbol = {
            assumption.symbol: assumption
            for assumption in self._assumptions
        }

        total_market_value = sum(
            (holding.market_value for holding in current_holdings),
            Decimal("0"),
        )

        total_forward_income = sum(
            (
                assumptions_by_symbol[holding.symbol].forward_annual_income
                for holding in current_holdings
                if holding.symbol in assumptions_by_symbol
            ),
            Decimal("0"),
        )

        holding_income: list[ForwardHoldingIncome] = []

        for holding in current_holdings:
            assumption = assumptions_by_symbol.get(holding.symbol)

            if assumption is None:
                forward_income = Decimal("0")
                has_forward_income = False
            else:
                forward_income = assumption.forward_annual_income
                has_forward_income = True

            if total_forward_income > Decimal("0"):
                percentage = (
                    forward_income
                    / total_forward_income
                    * Decimal("100")
                )
            else:
                percentage = Decimal("0")

            holding_income.append(
                ForwardHoldingIncome(
                    symbol=holding.symbol,
                    shares=holding.shares,
                    market_value=holding.market_value,
                    forward_annual_income=forward_income,
                    percentage_of_forward_income=percentage,
                    has_forward_income=has_forward_income,
                )
            )

        holdings_with_income = tuple(
            item.symbol
            for item in holding_income
            if item.has_forward_income
            and item.forward_annual_income > Decimal("0")
        )

        holdings_without_income = tuple(
            item.symbol
            for item in holding_income
            if not item.has_forward_income
        )

        income_concentration = self._income_concentration(
            holding_income,
            total_forward_income,
        )

        return ForwardIncomeResult(
            holding_income=tuple(holding_income),
            total_market_value=total_market_value,
            total_forward_annual_income=total_forward_income,
            holdings_with_forward_income=holdings_with_income,
            holdings_without_forward_income=holdings_without_income,
            income_concentration=income_concentration,
        )

    def _current_holdings(self):
        """Return holdings with positive share counts."""

        return tuple(
            holding
            for holding in self._portfolio.holdings
            if holding.shares > Decimal("0")
        )

    @staticmethod
    def _income_concentration(
        holding_income: Iterable[ForwardHoldingIncome],
        total_forward_income: Decimal,
    ) -> Decimal:
        """Return the largest holding's percentage of forward income."""

        if total_forward_income <= Decimal("0"):
            return Decimal("0")

        largest_income = max(
            (
                item.forward_annual_income
                for item in holding_income
            ),
            default=Decimal("0"),
        )

        return (
            largest_income
            / total_forward_income
            * Decimal("100")
        )


def analyze_forward_income(
    portfolio: Portfolio,
    assumptions: Iterable[ForwardIncomeAssumption] = (),
) -> ForwardIncomeResult:
    """Analyze explicit forward annual income assumptions."""

    return ForwardIncome(
        portfolio,
        assumptions,
    ).analyze()