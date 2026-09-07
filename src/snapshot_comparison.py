"""
Purpose:
    Compare two historical RIMS portfolio snapshots and quantify changes
    in portfolio value, income, and individual holdings.

Responsibilities:
    - Compare two Snapshot objects.
    - Calculate portfolio-level changes.
    - Identify common, added, and removed holdings.
    - Calculate holding-level changes.
    - Report forward annual dividend income changes.
    - Preserve Decimal precision for financial calculations.
    - Serialize comparison results to a dictionary.

Dependencies:
    Python standard library.
    RIMS Snapshot and Holding classes.

Revision History:
    0.2.0 - Initial historical snapshot comparison capability.

Author:
    RIMS Development Team
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from .holding import Holding
from .snapshot import Snapshot


HoldingStatus = Literal["common", "added", "removed"]


def _to_decimal(value: Decimal | float | int) -> Decimal:
    """Convert a numeric value to Decimal without introducing float artifacts."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class HoldingChange:
    """
    Represent the change in one security between two snapshots.

    A holding can be:
        - common: present in both snapshots
        - added: present only in the ending snapshot
        - removed: present only in the beginning snapshot
    """

    symbol: str
    status: HoldingStatus

    beginning_shares: Decimal
    ending_shares: Decimal
    shares_change: Decimal

    beginning_market_value: Decimal
    ending_market_value: Decimal
    market_value_change: Decimal

    beginning_cost_basis: Decimal
    ending_cost_basis: Decimal
    cost_basis_change: Decimal

    beginning_gain_loss: Decimal
    ending_gain_loss: Decimal
    gain_loss_change: Decimal

    beginning_annual_dividend_income: Decimal
    ending_annual_dividend_income: Decimal
    annual_dividend_income_change: Decimal

    @classmethod
    def from_holdings(
        cls,
        beginning: Holding | None,
        ending: Holding | None,
    ) -> HoldingChange:
        """Create a holding comparison from beginning and ending holdings."""
        if beginning is None and ending is None:
            raise ValueError(
                "At least one holding must be provided for comparison."
            )

        if beginning is not None and ending is not None:
            status: HoldingStatus = "common"
        elif ending is not None:
            status = "added"
        else:
            status = "removed"

        symbol = (
            ending.symbol.strip().upper()
            if ending is not None
            else beginning.symbol.strip().upper()
        )

        beginning_shares = (
            _to_decimal(beginning.shares)
            if beginning is not None
            else Decimal("0")
        )
        ending_shares = (
            _to_decimal(ending.shares)
            if ending is not None
            else Decimal("0")
        )

        beginning_market_value = (
            _to_decimal(beginning.market_value)
            if beginning is not None and beginning.market_value is not None
            else (
                _to_decimal(beginning.shares * beginning.price)
                if beginning is not None
                else Decimal("0")
            )
        )
        ending_market_value = (
            _to_decimal(ending.market_value)
            if ending is not None and ending.market_value is not None
            else (
                _to_decimal(ending.shares * ending.price)
                if ending is not None
                else Decimal("0")
            )
        )

        beginning_cost_basis = (
            _to_decimal(beginning.cost_basis)
            if beginning is not None
            else Decimal("0")
        )
        ending_cost_basis = (
            _to_decimal(ending.cost_basis)
            if ending is not None
            else Decimal("0")
        )

        beginning_gain_loss = (
            beginning_market_value - beginning_cost_basis
        )
        ending_gain_loss = ending_market_value - ending_cost_basis

        beginning_dividend_income = (
            _to_decimal(beginning.annual_dividend_income)
            if beginning is not None
            else Decimal("0")
        )
        ending_dividend_income = (
            _to_decimal(ending.annual_dividend_income)
            if ending is not None
            else Decimal("0")
        )

        return cls(
            symbol=symbol,
            status=status,
            beginning_shares=beginning_shares,
            ending_shares=ending_shares,
            shares_change=ending_shares - beginning_shares,
            beginning_market_value=beginning_market_value,
            ending_market_value=ending_market_value,
            market_value_change=ending_market_value - beginning_market_value,
            beginning_cost_basis=beginning_cost_basis,
            ending_cost_basis=ending_cost_basis,
            cost_basis_change=ending_cost_basis - beginning_cost_basis,
            beginning_gain_loss=beginning_gain_loss,
            ending_gain_loss=ending_gain_loss,
            gain_loss_change=ending_gain_loss - beginning_gain_loss,
            beginning_annual_dividend_income=beginning_dividend_income,
            ending_annual_dividend_income=ending_dividend_income,
            annual_dividend_income_change=(
                ending_dividend_income - beginning_dividend_income
            ),
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize the holding comparison to a dictionary."""
        return {
            "symbol": self.symbol,
            "status": self.status,
            "beginning_shares": str(self.beginning_shares),
            "ending_shares": str(self.ending_shares),
            "shares_change": str(self.shares_change),
            "beginning_market_value": str(self.beginning_market_value),
            "ending_market_value": str(self.ending_market_value),
            "market_value_change": str(self.market_value_change),
            "beginning_cost_basis": str(self.beginning_cost_basis),
            "ending_cost_basis": str(self.ending_cost_basis),
            "cost_basis_change": str(self.cost_basis_change),
            "beginning_gain_loss": str(self.beginning_gain_loss),
            "ending_gain_loss": str(self.ending_gain_loss),
            "gain_loss_change": str(self.gain_loss_change),
            "beginning_annual_dividend_income": str(
                self.beginning_annual_dividend_income
            ),
            "ending_annual_dividend_income": str(
                self.ending_annual_dividend_income
            ),
            "annual_dividend_income_change": str(
                self.annual_dividend_income_change
            ),
        }


@dataclass(frozen=True, slots=True)
class SnapshotComparison:
    """
    Compare two historical portfolio snapshots.

    This class reports changes in portfolio values and income. It does not
    calculate investment performance or total return because transaction
    history is not yet part of the RIMS data model.
    """

    beginning_date: object
    ending_date: object
    portfolio_name: str

    beginning_total_market_value: Decimal
    ending_total_market_value: Decimal
    total_market_value_change: Decimal

    beginning_securities_market_value: Decimal
    ending_securities_market_value: Decimal
    securities_market_value_change: Decimal

    beginning_cash: Decimal
    ending_cash: Decimal
    cash_change: Decimal

    beginning_cost_basis: Decimal
    ending_cost_basis: Decimal
    cost_basis_change: Decimal

    beginning_gain_loss: Decimal
    ending_gain_loss: Decimal
    gain_loss_change: Decimal

    beginning_forward_annual_dividend_income: Decimal
    ending_forward_annual_dividend_income: Decimal
    forward_annual_dividend_income_change: Decimal

    beginning_portfolio_yield: Decimal
    ending_portfolio_yield: Decimal
    portfolio_yield_change: Decimal

    beginning_income_yield_on_cost: Decimal
    ending_income_yield_on_cost: Decimal
    income_yield_on_cost_change: Decimal

    beginning_holding_count: int
    ending_holding_count: int
    holding_count_change: int

    holding_changes: tuple[HoldingChange, ...]

    @classmethod
    def from_snapshots(
        cls,
        beginning: Snapshot,
        ending: Snapshot,
    ) -> SnapshotComparison:
        """
        Create a comparison between two snapshots.

        The beginning snapshot must not be later than the ending snapshot.
        The snapshots themselves are never modified.
        """
        if not isinstance(beginning, Snapshot):
            raise TypeError("beginning must be a Snapshot.")

        if not isinstance(ending, Snapshot):
            raise TypeError("ending must be a Snapshot.")

        if beginning.snapshot_date > ending.snapshot_date:
            raise ValueError(
                "Beginning snapshot date cannot be later than ending "
                "snapshot date."
            )

        if beginning.portfolio_name != ending.portfolio_name:
            raise ValueError(
                "Snapshots must belong to the same portfolio."
            )

        beginning_holdings = cls._holding_map(beginning)
        ending_holdings = cls._holding_map(ending)

        symbols = sorted(
            set(beginning_holdings) | set(ending_holdings)
        )

        changes = tuple(
            HoldingChange.from_holdings(
                beginning_holdings.get(symbol),
                ending_holdings.get(symbol),
            )
            for symbol in symbols
        )

        beginning_total = _to_decimal(beginning.total_market_value)
        ending_total = _to_decimal(ending.total_market_value)

        beginning_securities = _to_decimal(
            beginning.securities_market_value
        )
        ending_securities = _to_decimal(
            ending.securities_market_value
        )

        beginning_cash = _to_decimal(beginning.cash_market_value)
        ending_cash = _to_decimal(ending.cash_market_value)

        beginning_cost = _to_decimal(beginning.total_cost_basis)
        ending_cost = _to_decimal(ending.total_cost_basis)

        beginning_gain = _to_decimal(beginning.total_gain_loss)
        ending_gain = _to_decimal(ending.total_gain_loss)

        beginning_income = _to_decimal(
            beginning.forward_annual_dividend_income
        )
        ending_income = _to_decimal(
            ending.forward_annual_dividend_income
        )

        beginning_yield = _to_decimal(beginning.portfolio_yield)
        ending_yield = _to_decimal(ending.portfolio_yield)

        beginning_income_yoc = _to_decimal(
            beginning.income_yield_on_cost
        )
        ending_income_yoc = _to_decimal(
            ending.income_yield_on_cost
        )

        return cls(
            beginning_date=beginning.snapshot_date,
            ending_date=ending.snapshot_date,
            portfolio_name=beginning.portfolio_name,
            beginning_total_market_value=beginning_total,
            ending_total_market_value=ending_total,
            total_market_value_change=ending_total - beginning_total,
            beginning_securities_market_value=beginning_securities,
            ending_securities_market_value=ending_securities,
            securities_market_value_change=(
                ending_securities - beginning_securities
            ),
            beginning_cash=beginning_cash,
            ending_cash=ending_cash,
            cash_change=ending_cash - beginning_cash,
            beginning_cost_basis=beginning_cost,
            ending_cost_basis=ending_cost,
            cost_basis_change=ending_cost - beginning_cost,
            beginning_gain_loss=beginning_gain,
            ending_gain_loss=ending_gain,
            gain_loss_change=ending_gain - beginning_gain,
            beginning_forward_annual_dividend_income=beginning_income,
            ending_forward_annual_dividend_income=ending_income,
            forward_annual_dividend_income_change=(
                ending_income - beginning_income
            ),
            beginning_portfolio_yield=beginning_yield,
            ending_portfolio_yield=ending_yield,
            portfolio_yield_change=ending_yield - beginning_yield,
            beginning_income_yield_on_cost=beginning_income_yoc,
            ending_income_yield_on_cost=ending_income_yoc,
            income_yield_on_cost_change=(
                ending_income_yoc - beginning_income_yoc
            ),
            beginning_holding_count=beginning.holding_count,
            ending_holding_count=ending.holding_count,
            holding_count_change=(
                ending.holding_count - beginning.holding_count
            ),
            holding_changes=changes,
        )

    @staticmethod
    def _holding_map(snapshot: Snapshot) -> dict[str, Holding]:
        """Build a normalized symbol-to-holding map for a snapshot."""
        holdings: dict[str, Holding] = {}

        for holding in snapshot.holdings:
            symbol = holding.symbol.strip().upper()

            if not symbol:
                raise ValueError(
                    "Snapshot contains a holding with an empty symbol."
                )

            if symbol in holdings:
                raise ValueError(
                    f"Snapshot contains duplicate holding symbol: {symbol}"
                )

            holdings[symbol] = holding

        return holdings

    @property
    def common_holdings(self) -> tuple[HoldingChange, ...]:
        """Return holdings present in both snapshots."""
        return tuple(
            change
            for change in self.holding_changes
            if change.status == "common"
        )

    @property
    def added_holdings(self) -> tuple[HoldingChange, ...]:
        """Return holdings present only in the ending snapshot."""
        return tuple(
            change
            for change in self.holding_changes
            if change.status == "added"
        )

    @property
    def removed_holdings(self) -> tuple[HoldingChange, ...]:
        """Return holdings present only in the beginning snapshot."""
        return tuple(
            change
            for change in self.holding_changes
            if change.status == "removed"
        )

    @property
    def added_symbols(self) -> tuple[str, ...]:
        """Return symbols added between the two snapshots."""
        return tuple(
            change.symbol for change in self.added_holdings
        )

    @property
    def removed_symbols(self) -> tuple[str, ...]:
        """Return symbols removed between the two snapshots."""
        return tuple(
            change.symbol for change in self.removed_holdings
        )

    @property
    def common_symbols(self) -> tuple[str, ...]:
        """Return symbols present in both snapshots."""
        return tuple(
            change.symbol for change in self.common_holdings
        )

    def get_holding_change(self, symbol: str) -> HoldingChange:
        """Return the comparison for a specific security."""
        normalized_symbol = symbol.strip().upper()

        for change in self.holding_changes:
            if change.symbol == normalized_symbol:
                return change

        raise KeyError(
            f"Holding not found in comparison: {normalized_symbol}"
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize the complete comparison to a dictionary."""
        return {
            "beginning_date": self.beginning_date.isoformat(),
            "ending_date": self.ending_date.isoformat(),
            "portfolio_name": self.portfolio_name,
            "beginning_total_market_value": str(
                self.beginning_total_market_value
            ),
            "ending_total_market_value": str(
                self.ending_total_market_value
            ),
            "total_market_value_change": str(
                self.total_market_value_change
            ),
            "beginning_securities_market_value": str(
                self.beginning_securities_market_value
            ),
            "ending_securities_market_value": str(
                self.ending_securities_market_value
            ),
            "securities_market_value_change": str(
                self.securities_market_value_change
            ),
            "beginning_cash": str(self.beginning_cash),
            "ending_cash": str(self.ending_cash),
            "cash_change": str(self.cash_change),
            "beginning_cost_basis": str(self.beginning_cost_basis),
            "ending_cost_basis": str(self.ending_cost_basis),
            "cost_basis_change": str(self.cost_basis_change),
            "beginning_gain_loss": str(self.beginning_gain_loss),
            "ending_gain_loss": str(self.ending_gain_loss),
            "gain_loss_change": str(self.gain_loss_change),
            "beginning_forward_annual_dividend_income": str(
                self.beginning_forward_annual_dividend_income
            ),
            "ending_forward_annual_dividend_income": str(
                self.ending_forward_annual_dividend_income
            ),
            "forward_annual_dividend_income_change": str(
                self.forward_annual_dividend_income_change
            ),
            "beginning_portfolio_yield": str(
                self.beginning_portfolio_yield
            ),
            "ending_portfolio_yield": str(self.ending_portfolio_yield),
            "portfolio_yield_change": str(
                self.portfolio_yield_change
            ),
            "beginning_income_yield_on_cost": str(
                self.beginning_income_yield_on_cost
            ),
            "ending_income_yield_on_cost": str(
                self.ending_income_yield_on_cost
            ),
            "income_yield_on_cost_change": str(
                self.income_yield_on_cost_change
            ),
            "beginning_holding_count": self.beginning_holding_count,
            "ending_holding_count": self.ending_holding_count,
            "holding_count_change": self.holding_count_change,
            "holding_changes": [
                change.to_dict()
                for change in self.holding_changes
            ],
        }