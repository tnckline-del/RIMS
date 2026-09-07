"""
Purpose:
    Analyze forward annual dividend income across historical portfolio
    snapshots.

Responsibilities:
    - Load a chronological series of historical snapshots.
    - Calculate period-to-period income changes.
    - Calculate beginning-to-ending income changes.
    - Report secondary portfolio yield metrics.
    - Classify the overall income trend.
    - Identify the largest income increase and decrease.

Dependencies:
    - Python standard library.
    - RIMS Snapshot and HistoricalAnalysis components.

Revision History:
    0.2.0 - Initial historical income trend implementation.

Author:
    RIMS Development Team
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .snapshot import Snapshot


@dataclass(frozen=True, slots=True)
class IncomeObservation:
    """Represent the income metrics for one historical snapshot."""

    snapshot_date: date
    forward_annual_dividend_income: Decimal
    total_market_value: Decimal
    portfolio_yield: Decimal
    income_yield_on_cost: Decimal
    holding_count: int


@dataclass(frozen=True, slots=True)
class IncomeChange:
    """Represent the income change between two consecutive snapshots."""

    beginning_date: date
    ending_date: date
    beginning_income: Decimal
    ending_income: Decimal
    income_change: Decimal
    income_change_percent: Decimal
    beginning_yield: Decimal
    ending_yield: Decimal
    yield_change_percentage_points: Decimal
    beginning_income_yield_on_cost: Decimal
    ending_income_yield_on_cost: Decimal
    income_yield_on_cost_change_percentage_points: Decimal
    beginning_market_value: Decimal
    ending_market_value: Decimal
    market_value_change: Decimal


@dataclass(frozen=True, slots=True)
class IncomeTrend:
    """Analyze forward annual dividend income across snapshots."""

    observations: tuple[IncomeObservation, ...]
    changes: tuple[IncomeChange, ...]

    @classmethod
    def from_snapshots(
        cls,
        snapshots: list[Snapshot] | tuple[Snapshot, ...],
    ) -> IncomeTrend:
        """
        Create an income trend from historical snapshots.

        Snapshots are sorted chronologically. At least one snapshot is
        required. No snapshot objects are modified.
        """
        if not isinstance(snapshots, (list, tuple)):
            raise TypeError("snapshots must be a list or tuple of Snapshot objects")

        if not snapshots:
            raise ValueError("At least one snapshot is required")

        if not all(isinstance(snapshot, Snapshot) for snapshot in snapshots):
            raise TypeError("All items must be Snapshot objects")

        ordered_snapshots = sorted(
            snapshots,
            key=lambda snapshot: snapshot.snapshot_date,
        )

        for index in range(1, len(ordered_snapshots)):
            if (
                ordered_snapshots[index].snapshot_date
                == ordered_snapshots[index - 1].snapshot_date
            ):
                raise ValueError(
                    "Snapshots must have unique snapshot dates"
                )

        portfolio_names = {
            snapshot.portfolio_name for snapshot in ordered_snapshots
        }

        if len(portfolio_names) != 1:
            raise ValueError(
                "All snapshots must belong to the same portfolio"
            )

        observations = tuple(
            IncomeObservation(
                snapshot_date=snapshot.snapshot_date,
                forward_annual_dividend_income=(
                    snapshot.forward_annual_dividend_income
                ),
                total_market_value=snapshot.total_market_value,
                portfolio_yield=snapshot.portfolio_yield,
                income_yield_on_cost=snapshot.income_yield_on_cost,
                holding_count=snapshot.holding_count,
            )
            for snapshot in ordered_snapshots
        )

        changes = tuple(
            cls._calculate_change(
                beginning=observations[index - 1],
                ending=observations[index],
            )
            for index in range(1, len(observations))
        )

        return cls(
            observations=observations,
            changes=changes,
        )

    @staticmethod
    def _calculate_change(
        beginning: IncomeObservation,
        ending: IncomeObservation,
    ) -> IncomeChange:
        """Calculate the change between two consecutive observations."""

        income_change = (
            ending.forward_annual_dividend_income
            - beginning.forward_annual_dividend_income
        )

        if beginning.forward_annual_dividend_income == 0:
            income_change_percent = Decimal("0")
        else:
            income_change_percent = (
                income_change
                / beginning.forward_annual_dividend_income
                * Decimal("100")
            )

        yield_change = ending.portfolio_yield - beginning.portfolio_yield

        income_yoc_change = (
            ending.income_yield_on_cost
            - beginning.income_yield_on_cost
        )

        market_value_change = (
            ending.total_market_value - beginning.total_market_value
        )

        return IncomeChange(
            beginning_date=beginning.snapshot_date,
            ending_date=ending.snapshot_date,
            beginning_income=beginning.forward_annual_dividend_income,
            ending_income=ending.forward_annual_dividend_income,
            income_change=income_change,
            income_change_percent=income_change_percent,
            beginning_yield=beginning.portfolio_yield,
            ending_yield=ending.portfolio_yield,
            yield_change_percentage_points=yield_change,
            beginning_income_yield_on_cost=(
                beginning.income_yield_on_cost
            ),
            ending_income_yield_on_cost=(
                ending.income_yield_on_cost
            ),
            income_yield_on_cost_change_percentage_points=(
                income_yoc_change
            ),
            beginning_market_value=beginning.total_market_value,
            ending_market_value=ending.total_market_value,
            market_value_change=market_value_change,
        )

    @property
    def snapshot_count(self) -> int:
        """Return the number of snapshots in the trend."""
        return len(self.observations)

    @property
    def period_count(self) -> int:
        """Return the number of periods between snapshots."""
        return len(self.changes)

    @property
    def beginning(self) -> IncomeObservation:
        """Return the earliest observation."""
        return self.observations[0]

    @property
    def latest(self) -> IncomeObservation:
        """Return the most recent observation."""
        return self.observations[-1]

    @property
    def total_income_change(self) -> Decimal:
        """Return the total change in forward annual dividend income."""
        return (
            self.latest.forward_annual_dividend_income
            - self.beginning.forward_annual_dividend_income
        )

    @property
    def total_income_change_percent(self) -> Decimal:
        """Return the percentage change in forward annual dividend income."""
        if self.beginning.forward_annual_dividend_income == 0:
            return Decimal("0")

        return (
            self.total_income_change
            / self.beginning.forward_annual_dividend_income
            * Decimal("100")
        )

    @property
    def total_yield_change_percentage_points(self) -> Decimal:
        """Return the total portfolio-yield change in percentage points."""
        return (
            self.latest.portfolio_yield
            - self.beginning.portfolio_yield
        )

    @property
    def total_income_yield_on_cost_change_percentage_points(
        self,
    ) -> Decimal:
        """Return the total income-yield-on-cost change in percentage points."""
        return (
            self.latest.income_yield_on_cost
            - self.beginning.income_yield_on_cost
        )

    @property
    def total_market_value_change(self) -> Decimal:
        """Return the total change in portfolio market value."""
        return (
            self.latest.total_market_value
            - self.beginning.total_market_value
        )

    @property
    def trend_direction(self) -> str:
        """Return Increasing, Decreasing, or Stable."""
        if self.total_income_change > 0:
            return "Increasing"

        if self.total_income_change < 0:
            return "Decreasing"

        return "Stable"

    @property
    def largest_income_increase(self) -> IncomeChange | None:
        """Return the period with the largest income increase."""
        increases = [
            change
            for change in self.changes
            if change.income_change > 0
        ]

        if not increases:
            return None

        return max(increases, key=lambda change: change.income_change)

    @property
    def largest_income_decrease(self) -> IncomeChange | None:
        """Return the period with the largest income decrease."""
        decreases = [
            change
            for change in self.changes
            if change.income_change < 0
        ]

        if not decreases:
            return None

        return min(decreases, key=lambda change: change.income_change)

    def to_dict(self) -> dict:
        """Serialize the income trend into a dictionary."""

        return {
            "snapshot_count": self.snapshot_count,
            "period_count": self.period_count,
            "beginning_date": self.beginning.snapshot_date.isoformat(),
            "latest_date": self.latest.snapshot_date.isoformat(),
            "beginning_income": str(
                self.beginning.forward_annual_dividend_income
            ),
            "latest_income": str(
                self.latest.forward_annual_dividend_income
            ),
            "total_income_change": str(self.total_income_change),
            "total_income_change_percent": str(
                self.total_income_change_percent
            ),
            "trend_direction": self.trend_direction,
            "total_yield_change_percentage_points": str(
                self.total_yield_change_percentage_points
            ),
            "total_income_yield_on_cost_change_percentage_points": str(
                self.total_income_yield_on_cost_change_percentage_points
            ),
            "total_market_value_change": str(
                self.total_market_value_change
            ),
            "observations": [
                {
                    "snapshot_date": observation.snapshot_date.isoformat(),
                    "forward_annual_dividend_income": str(
                        observation.forward_annual_dividend_income
                    ),
                    "total_market_value": str(
                        observation.total_market_value
                    ),
                    "portfolio_yield": str(
                        observation.portfolio_yield
                    ),
                    "income_yield_on_cost": str(
                        observation.income_yield_on_cost
                    ),
                    "holding_count": observation.holding_count,
                }
                for observation in self.observations
            ],
            "changes": [
                {
                    "beginning_date": change.beginning_date.isoformat(),
                    "ending_date": change.ending_date.isoformat(),
                    "beginning_income": str(change.beginning_income),
                    "ending_income": str(change.ending_income),
                    "income_change": str(change.income_change),
                    "income_change_percent": str(
                        change.income_change_percent
                    ),
                    "beginning_yield": str(change.beginning_yield),
                    "ending_yield": str(change.ending_yield),
                    "yield_change_percentage_points": str(
                        change.yield_change_percentage_points
                    ),
                    "beginning_income_yield_on_cost": str(
                        change.beginning_income_yield_on_cost
                    ),
                    "ending_income_yield_on_cost": str(
                        change.ending_income_yield_on_cost
                    ),
                    "income_yield_on_cost_change_percentage_points": str(
                        change.income_yield_on_cost_change_percentage_points
                    ),
                    "beginning_market_value": str(
                        change.beginning_market_value
                    ),
                    "ending_market_value": str(
                        change.ending_market_value
                    ),
                    "market_value_change": str(
                        change.market_value_change
                    ),
                }
                for change in self.changes
            ],
        }