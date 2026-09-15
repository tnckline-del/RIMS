"""Forward annual income assumptions and portfolio aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from .forward_income_change import (
    ForwardIncomeChangeReason,
    ForwardIncomePositionState,
    classify_forward_income_change,
)
from .portfolio import Portfolio


@dataclass(frozen=True, slots=True)
class ForwardIncomeAssumption:
    """Explicit forward annual income rate for one security."""

    symbol: str
    forward_annual_income_per_share: Decimal
    effective_date: date
    source: str
    notes: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str):
            raise TypeError("symbol must be a string")

        normalized_symbol = self.symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("symbol must not be empty")

        if not isinstance(
            self.forward_annual_income_per_share,
            Decimal,
        ):
            raise TypeError(
                "forward_annual_income_per_share must be a Decimal"
            )

        if self.forward_annual_income_per_share < Decimal("0"):
            raise ValueError(
                "forward_annual_income_per_share must not be negative"
            )

        if not isinstance(self.effective_date, date):
            raise TypeError("effective_date must be a date")

        if not isinstance(self.source, str):
            raise TypeError("source must be a string")

        if not self.source.strip():
            raise ValueError("source must not be empty")

        if not isinstance(self.notes, str):
            raise TypeError("notes must be a string")

        object.__setattr__(self, "symbol", normalized_symbol)
        object.__setattr__(self, "source", self.source.strip())


@dataclass(frozen=True, slots=True)
class ForwardHoldingIncome:
    """Forward annual income associated with one current holding."""

    symbol: str
    shares: Decimal
    market_value: Decimal
    forward_annual_income: Decimal
    percentage_of_forward_income: Decimal
    has_forward_income: bool
    change_reason: ForwardIncomeChangeReason | None = None


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
    """Analyze explicit forward annual income assumptions."""

    def __init__(
        self,
        portfolio: Portfolio,
        assumptions: Iterable[ForwardIncomeAssumption] = (),
        previous_baseline: Iterable[ForwardIncomePositionState] = (),
    ) -> None:
        if not isinstance(portfolio, Portfolio):
            raise TypeError("portfolio must be a Portfolio")

        assumption_tuple = tuple(assumptions)
        baseline_tuple = tuple(previous_baseline)

        for assumption in assumption_tuple:
            if not isinstance(assumption, ForwardIncomeAssumption):
                raise TypeError(
                    "assumptions must contain only "
                    "ForwardIncomeAssumption objects"
                )

        for state in baseline_tuple:
            if not isinstance(state, ForwardIncomePositionState):
                raise TypeError(
                    "previous_baseline must contain only "
                    "ForwardIncomePositionState objects"
                )

        self._portfolio = portfolio
        self._assumptions = assumption_tuple
        self._previous_baseline = baseline_tuple

    def analyze(self) -> ForwardIncomeResult:
        """Return forward annual income for current holdings."""

        current_holdings = self._current_holdings()
        assumptions_by_symbol = {
            assumption.symbol: assumption
            for assumption in self._assumptions
        }

        total_market_value = sum(
            (holding.market_value for holding in current_holdings),
            Decimal("0"),
        )

        holding_income: list[ForwardHoldingIncome] = []

        for holding in current_holdings:
            assumption = assumptions_by_symbol.get(holding.symbol)

            if assumption is None:
                forward_income = Decimal("0")
                has_forward_income = False
                current_rate = Decimal("0")
            else:
                current_rate = (
                    assumption.forward_annual_income_per_share
                )
                forward_income = holding.shares * current_rate
                has_forward_income = True

            change_reason = self._change_reason(
                symbol=holding.symbol,
                shares=holding.shares,
                income_per_share=current_rate,
            )

            holding_income.append(
                ForwardHoldingIncome(
                    symbol=holding.symbol,
                    shares=holding.shares,
                    market_value=holding.market_value,
                    forward_annual_income=forward_income,
                    percentage_of_forward_income=Decimal("0"),
                    has_forward_income=has_forward_income,
                    change_reason=change_reason,
                )
            )

        total_forward_income = sum(
            (
                item.forward_annual_income
                for item in holding_income
                if item.has_forward_income
            ),
            Decimal("0"),
        )

        finalized_holding_income: list[ForwardHoldingIncome] = []

        for item in holding_income:
            if total_forward_income > Decimal("0"):
                percentage = (
                    item.forward_annual_income
                    / total_forward_income
                    * Decimal("100")
                )
            else:
                percentage = Decimal("0")

            finalized_holding_income.append(
                ForwardHoldingIncome(
                    symbol=item.symbol,
                    shares=item.shares,
                    market_value=item.market_value,
                    forward_annual_income=item.forward_annual_income,
                    percentage_of_forward_income=percentage,
                    has_forward_income=item.has_forward_income,
                    change_reason=item.change_reason,
                )
            )

        holdings_with_income = tuple(
            item.symbol
            for item in finalized_holding_income
            if item.has_forward_income
            and item.forward_annual_income > Decimal("0")
        )

        holdings_without_income = tuple(
            item.symbol
            for item in finalized_holding_income
            if not item.has_forward_income
        )

        income_concentration = self._income_concentration(
            finalized_holding_income,
            total_forward_income,
        )

        return ForwardIncomeResult(
            holding_income=tuple(finalized_holding_income),
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

    def _change_reason(
        self,
        symbol: str,
        shares: Decimal,
        income_per_share: Decimal,
    ) -> ForwardIncomeChangeReason | None:
        """Return the change reason when a baseline is available."""

        if not self._previous_baseline:
            return None

        current_state = ForwardIncomePositionState(
            symbol=symbol,
            shares=shares,
            forward_annual_income_per_share=income_per_share,
        )

        previous = next(
            (
                state
                for state in self._previous_baseline
                if state.symbol == symbol
            ),
            None,
        )

        return classify_forward_income_change(
            previous,
            current_state,
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
    previous_baseline: Iterable[ForwardIncomePositionState] = (),
) -> ForwardIncomeResult:
    """Analyze explicit forward annual income assumptions."""

    return ForwardIncome(
        portfolio,
        assumptions,
        previous_baseline,
    ).analyze()