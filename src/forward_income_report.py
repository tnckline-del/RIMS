"""Portfolio-level forward income reporting."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .forward_income import ForwardHoldingIncome
from .forward_income_change import ForwardIncomeChangeReason
from .forward_income_manager import ForwardIncomeManager


@dataclass(frozen=True, slots=True)
class ForwardIncomeReportHolding:
    """User-facing forward income information for one holding."""

    symbol: str
    shares: Decimal
    market_value: Decimal
    forward_annual_income: Decimal
    percentage_of_forward_income: Decimal
    change_reason: ForwardIncomeChangeReason | None


@dataclass(frozen=True, slots=True)
class ForwardIncomeReport:
    """User-facing portfolio-level forward income report."""

    holdings: tuple[ForwardIncomeReportHolding, ...]
    total_market_value: Decimal
    total_forward_annual_income: Decimal
    holdings_with_forward_income: int
    holdings_without_forward_income: int
    income_concentration: Decimal
    largest_income_holding: str | None


class ForwardIncomeReporter:
    """Create a simple portfolio-level forward income report."""

    def __init__(self, manager: ForwardIncomeManager) -> None:
        if not isinstance(manager, ForwardIncomeManager):
            raise TypeError(
                "manager must be a ForwardIncomeManager"
            )

        self._manager = manager

    def generate(self) -> ForwardIncomeReport:
        """Generate a forward income report."""

        management_result = self._manager.run()
        analysis = management_result.analysis

        holdings = tuple(
            self._to_report_holding(item)
            for item in analysis.holding_income
        )

        largest_income_holding = self._largest_income_holding(
            analysis.holding_income
        )

        return ForwardIncomeReport(
            holdings=holdings,
            total_market_value=analysis.total_market_value,
            total_forward_annual_income=(
                analysis.total_forward_annual_income
            ),
            holdings_with_forward_income=len(
                analysis.holdings_with_forward_income
            ),
            holdings_without_forward_income=len(
                analysis.holdings_without_forward_income
            ),
            income_concentration=analysis.income_concentration,
            largest_income_holding=largest_income_holding,
        )

    @staticmethod
    def _to_report_holding(
        holding: ForwardHoldingIncome,
    ) -> ForwardIncomeReportHolding:
        """Convert an analysis holding to a report holding."""

        return ForwardIncomeReportHolding(
            symbol=holding.symbol,
            shares=holding.shares,
            market_value=holding.market_value,
            forward_annual_income=holding.forward_annual_income,
            percentage_of_forward_income=(
                holding.percentage_of_forward_income
            ),
            change_reason=holding.change_reason,
        )

    @staticmethod
    def _largest_income_holding(
        holdings: Iterable[ForwardHoldingIncome],
    ) -> str | None:
        """Return the symbol with the largest forward income."""

        income_holding = max(
            (
                holding
                for holding in holdings
                if holding.has_forward_income
                and holding.forward_annual_income > Decimal("0")
            ),
            key=lambda holding: holding.forward_annual_income,
            default=None,
        )

        if income_holding is None:
            return None

        return income_holding.symbol


def generate_forward_income_report(
    manager: ForwardIncomeManager,
) -> ForwardIncomeReport:
    """Generate a portfolio-level forward income report."""

    return ForwardIncomeReporter(manager).generate()
