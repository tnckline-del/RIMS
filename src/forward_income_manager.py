"""Forward income management and baseline coordination."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .forward_income import (
    ForwardHoldingIncome,
    ForwardIncome,
    ForwardIncomeAssumption,
    ForwardIncomeResult,
)
from .forward_income_baseline import ForwardIncomeBaseline
from .forward_income_change import (
    ForwardIncomeChangeReason,
    ForwardIncomePositionState,
    compare_forward_income_states,
)
from .forward_income_store import ForwardIncomeStore
from .portfolio import Portfolio


@dataclass(frozen=True, slots=True)
class ForwardIncomeManagementResult:
    """Result of a forward income management operation."""

    analysis: ForwardIncomeResult
    changes: tuple[
        tuple[ForwardIncomePositionState, ForwardIncomeChangeReason],
        ...,
    ]


class ForwardIncomeManager:
    """Coordinate forward income assumptions, comparison, and baseline."""

    def __init__(
        self,
        portfolio: Portfolio,
        storage_path: str,
    ) -> None:
        if not isinstance(portfolio, Portfolio):
            raise TypeError("portfolio must be a Portfolio")

        self._portfolio = portfolio
        self._income_store = ForwardIncomeStore(storage_path)
        self._baseline_store = ForwardIncomeBaseline(storage_path)

    def run(self) -> ForwardIncomeManagementResult:
        """Analyze forward income and update the baseline."""

        assumptions = self._income_store.load()
        previous_baseline = self._baseline_store.load()

        current_states = self._current_states(assumptions)

        changes = compare_forward_income_states(
            previous_baseline,
            current_states,
        )

        analysis = ForwardIncome(
            self._portfolio,
            assumptions,
            previous_baseline,
        ).analyze()

        analysis = self._apply_change_reasons(
            analysis,
            changes,
        )

        analysis = self._add_closed_positions(
            analysis,
            changes,
        )

        self._baseline_store.save(current_states)

        return ForwardIncomeManagementResult(
            analysis=analysis,
            changes=tuple(
                (change.state, change.reason)
                for change in changes
            ),
        )

    def _current_states(
        self,
        assumptions: tuple[ForwardIncomeAssumption, ...],
    ) -> tuple[ForwardIncomePositionState, ...]:
        """Build baseline states for active holdings with assumptions."""

        assumptions_by_symbol = {
            assumption.symbol: assumption
            for assumption in assumptions
        }

        states: list[ForwardIncomePositionState] = []

        for holding in self._portfolio.holdings:
            if holding.shares <= Decimal("0"):
                continue

            assumption = assumptions_by_symbol.get(holding.symbol)

            if assumption is None:
                continue

            states.append(
                ForwardIncomePositionState(
                    symbol=holding.symbol,
                    shares=holding.shares,
                    forward_annual_income_per_share=(
                        assumption.forward_annual_income_per_share
                    ),
                )
            )

        return tuple(states)

    @staticmethod
    def _apply_change_reasons(
        analysis: ForwardIncomeResult,
        changes: tuple,
    ) -> ForwardIncomeResult:
        """Apply detected change reasons to current holdings."""

        reasons_by_symbol = {
            change.state.symbol: change.reason
            for change in changes
            if change.reason != ForwardIncomeChangeReason.POSITION_CLOSED
        }

        updated_items = []

        for item in analysis.holding_income:
            updated_items.append(
                ForwardHoldingIncome(
                    symbol=item.symbol,
                    shares=item.shares,
                    market_value=item.market_value,
                    forward_annual_income=item.forward_annual_income,
                    percentage_of_forward_income=(
                        item.percentage_of_forward_income
                    ),
                    has_forward_income=item.has_forward_income,
                    change_reason=reasons_by_symbol.get(
                        item.symbol,
                        item.change_reason,
                    ),
                )
            )

        return ForwardIncomeResult(
            holding_income=tuple(updated_items),
            total_market_value=analysis.total_market_value,
            total_forward_annual_income=(
                analysis.total_forward_annual_income
            ),
            holdings_with_forward_income=(
                analysis.holdings_with_forward_income
            ),
            holdings_without_forward_income=(
                analysis.holdings_without_forward_income
            ),
            income_concentration=analysis.income_concentration,
        )

    @staticmethod
    def _add_closed_positions(
        analysis: ForwardIncomeResult,
        changes: tuple,
    ) -> ForwardIncomeResult:
        """Add closed positions to the current report once."""

        closed_items = []

        for change in changes:
            if change.reason != ForwardIncomeChangeReason.POSITION_CLOSED:
                continue

            closed_items.append(
                ForwardHoldingIncome(
                    symbol=change.state.symbol,
                    shares=Decimal("0"),
                    market_value=Decimal("0"),
                    forward_annual_income=Decimal("0"),
                    percentage_of_forward_income=Decimal("0"),
                    has_forward_income=False,
                    change_reason=(
                        ForwardIncomeChangeReason.POSITION_CLOSED
                    ),
                )
            )

        if not closed_items:
            return analysis

        return ForwardIncomeResult(
            holding_income=(
                analysis.holding_income
                + tuple(closed_items)
            ),
            total_market_value=analysis.total_market_value,
            total_forward_annual_income=(
                analysis.total_forward_annual_income
            ),
            holdings_with_forward_income=(
                analysis.holdings_with_forward_income
            ),
            holdings_without_forward_income=(
                analysis.holdings_without_forward_income
            ),
            income_concentration=analysis.income_concentration,
        )