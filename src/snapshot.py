"""
Purpose:
    Define the RIMS historical portfolio Snapshot entity.

Responsibilities:
    - Capture a portfolio at a specific point in time.
    - Preserve portfolio-level financial metrics.
    - Preserve cash separately from securities.
    - Preserve independent copies of individual holdings.
    - Prevent later changes to the live Portfolio from altering the snapshot.
    - Provide dictionary serialization for future storage and reporting.

Dependencies:
    Python standard library only.
    RIMS Portfolio and Holding entities.

Revision History:
    0.2.0 - Initial historical Snapshot entity.

Author:
    RIMS Development Team
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from src.portfolio import Portfolio
from src.holding import Holding


@dataclass(slots=True)
class Snapshot:
    """
    Represent a frozen point-in-time record of a RIMS Portfolio.

    A Snapshot is intentionally independent of the live Portfolio.
    Holdings are deep-copied when the Snapshot is created so that
    subsequent changes to the live portfolio cannot alter historical data.
    """

    snapshot_date: date
    portfolio_name: str
    holdings: list[Holding] = field(default_factory=list)
    cash_market_value: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        """Normalize snapshot data and validate the snapshot."""

        self.cash_market_value = Decimal(str(self.cash_market_value))

        if not self.portfolio_name or not self.portfolio_name.strip():
            raise ValueError("Snapshot portfolio name cannot be blank.")

        if self.cash_market_value < 0:
            raise ValueError(
                "Snapshot cash market value cannot be negative."
            )

        self.holdings = deepcopy(self.holdings)

    @classmethod
    def from_portfolio(
        cls,
        portfolio: Portfolio,
        snapshot_date: date,
        cash_market_value: Decimal | float | int = Decimal("0"),
    ) -> Snapshot:
        """
        Create a frozen Snapshot from a live Portfolio.

        Holdings are deep-copied so the resulting Snapshot is independent
        of the live Portfolio.
        """
        if not isinstance(portfolio, Portfolio):
            raise TypeError(
                "Snapshot requires a RIMS Portfolio."
            )

        return cls(
            snapshot_date=snapshot_date,
            portfolio_name=portfolio.name,
            holdings=deepcopy(portfolio.holdings),
            cash_market_value=Decimal(str(cash_market_value)),
        )

    @property
    def holding_count(self) -> int:
        """Return the number of securities in the snapshot."""
        return len(self.holdings)

    @property
    def securities_market_value(self) -> Decimal:
        """Return the total market value of securities."""
        return sum(
            (holding.market_value for holding in self.holdings),
            Decimal("0"),
        )

    @property
    def total_market_value(self) -> Decimal:
        """Return securities plus cash."""
        return (
            self.securities_market_value
            + self.cash_market_value
        )

    @property
    def total_cost_basis(self) -> Decimal:
        """Return the total cost basis of securities."""
        return sum(
            (holding.cost_basis for holding in self.holdings),
            Decimal("0"),
        )

    @property
    def total_gain_loss(self) -> Decimal:
        """Return total unrealized gain/loss."""
        return (
            self.securities_market_value
            - self.total_cost_basis
        )

    @property
    def total_gain_loss_percent(self) -> Decimal:
        """
        Return total unrealized gain/loss as a percentage of cost basis.

        Returns zero when cost basis is zero.
        """
        if self.total_cost_basis == 0:
            return Decimal("0")

        return (
            self.total_gain_loss
            / self.total_cost_basis
            * Decimal("100")
        )

    @property
    def forward_annual_dividend_income(self) -> Decimal:
        """
        Return total forward annual dividend income.
        """
        return sum(
            (
                holding.annual_dividend_income
                for holding in self.holdings
            ),
            Decimal("0"),
        )

    @property
    def portfolio_yield(self) -> Decimal:
        """
        Return forward annual dividend income as a percentage
        of total portfolio market value, including cash.

        Returns zero when total market value is zero.
        """
        if self.total_market_value == 0:
            return Decimal("0")

        return (
            self.forward_annual_dividend_income
            / self.total_market_value
            * Decimal("100")
        )

    @property
    def income_yield_on_cost(self) -> Decimal:
        """
        Return forward annual dividend income as a percentage
        of securities cost basis.

        Returns zero when cost basis is zero.
        """
        if self.total_cost_basis == 0:
            return Decimal("0")

        return (
            self.forward_annual_dividend_income
            / self.total_cost_basis
            * Decimal("100")
        )

    def get_holding(self, symbol: str) -> Holding:
        """
        Return a holding by symbol.

        Raises:
            KeyError: If the symbol is not present.
        """
        normalized_symbol = symbol.strip().upper()

        for holding in self.holdings:
            if holding.symbol.upper() == normalized_symbol:
                return holding

        raise KeyError(
            f"Holding not found in snapshot: {symbol}"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Return the snapshot as a dictionary suitable for future
        storage, reporting, or workbook generation.
        """
        return {
            "snapshot_date": self.snapshot_date,
            "portfolio_name": self.portfolio_name,
            "holding_count": self.holding_count,
            "securities_market_value": self.securities_market_value,
            "cash_market_value": self.cash_market_value,
            "total_market_value": self.total_market_value,
            "total_cost_basis": self.total_cost_basis,
            "total_gain_loss": self.total_gain_loss,
            "total_gain_loss_percent": (
                self.total_gain_loss_percent
            ),
            "forward_annual_dividend_income": (
                self.forward_annual_dividend_income
            ),
            "portfolio_yield": self.portfolio_yield,
            "income_yield_on_cost": (
                self.income_yield_on_cost
            ),
            "holdings": [
                holding.to_dict()
                for holding in self.holdings
            ],
        }