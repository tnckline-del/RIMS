"""
Purpose:
    Define the Holding data model used by the Retirement Income
    Management System (RIMS).

Responsibilities:
    - Represent a single portfolio investment.
    - Store position, valuation, cost-basis, and income information.
    - Calculate derived holding-level metrics.
    - Provide validation for core holding data.

Dependencies:
    Python standard library only.

Revision History:
    0.2.0 - Initial Holding data model.

Author:
    RIMS Development Team
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


def _to_decimal(value: Decimal | float | int) -> Decimal:
    """Convert a numeric value to Decimal for financial calculations."""
    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


@dataclass(slots=True)
class Holding:
    """Represent a single investment position in the portfolio."""

    symbol: str
    description: str
    asset_type: str
    sector: str
    shares: Decimal
    price: Decimal
    cost_basis: Decimal
    dividend_per_share: Decimal = Decimal("0")
    dividend_yield: Decimal = Decimal("0")
    dividend_pay_date: date | None = None
    ex_dividend_date: date | None = None

    def __post_init__(self) -> None:
        """Normalize numeric fields and validate the holding."""
        self.symbol = self.symbol.strip().upper()
        self.description = self.description.strip()
        self.asset_type = self.asset_type.strip()
        self.sector = self.sector.strip()

        self.shares = _to_decimal(self.shares)
        self.price = _to_decimal(self.price)
        self.cost_basis = _to_decimal(self.cost_basis)
        self.dividend_per_share = _to_decimal(self.dividend_per_share)
        self.dividend_yield = _to_decimal(self.dividend_yield)

        self.validate()

    def validate(self) -> None:
        """Validate the core data required for a holding."""
        if not self.symbol:
            raise ValueError("Holding symbol cannot be empty.")

        if self.shares < 0:
            raise ValueError("Holding shares cannot be negative.")

        if self.price < 0:
            raise ValueError("Holding price cannot be negative.")

        if self.cost_basis < 0:
            raise ValueError("Holding cost basis cannot be negative.")

        if self.dividend_per_share < 0:
            raise ValueError("Dividend per share cannot be negative.")

        if self.dividend_yield < 0:
            raise ValueError("Dividend yield cannot be negative.")

    @property
    def market_value(self) -> Decimal:
        """Return the current market value of the holding."""
        return self.shares * self.price

    @property
    def gain_loss(self) -> Decimal:
        """Return the unrealized gain or loss in dollars."""
        return self.market_value - self.cost_basis

    @property
    def gain_loss_percent(self) -> Decimal:
        """Return the unrealized gain or loss as a percentage."""
        if self.cost_basis == 0:
            return Decimal("0")

        return (self.gain_loss / self.cost_basis) * Decimal("100")

    @property
    def annual_dividend_income(self) -> Decimal:
        """Return projected annual dividend income for the position."""
        return self.shares * self.dividend_per_share

    @property
    def portfolio_yield(self) -> Decimal:
        """
        Return the holding's income yield based on current market value.

        This is useful for portfolio analysis but should not be confused
        with forward annual dividend income, which is the primary RIMS
        income metric.
        """
        if self.market_value == 0:
            return Decimal("0")

        return (
            self.annual_dividend_income / self.market_value
        ) * Decimal("100")

    @property
    def income_yield_on_cost(self) -> Decimal:
        """Return projected annual dividend income as a percentage of cost."""
        if self.cost_basis == 0:
            return Decimal("0")

        return (
            self.annual_dividend_income / self.cost_basis
        ) * Decimal("100")

    def update_price(self, price: Decimal | float | int) -> None:
        """Update the holding's current market price."""
        new_price = _to_decimal(price)

        if new_price < 0:
            raise ValueError("Holding price cannot be negative.")

        self.price = new_price

    def update_dividend(
        self,
        dividend_per_share: Decimal | float | int,
    ) -> None:
        """Update the projected annual dividend per share."""
        new_dividend = _to_decimal(dividend_per_share)

        if new_dividend < 0:
            raise ValueError("Dividend per share cannot be negative.")

        self.dividend_per_share = new_dividend

    def to_dict(self) -> dict[str, object]:
        """Return the holding as a dictionary for downstream processing."""
        return {
            "symbol": self.symbol,
            "description": self.description,
            "asset_type": self.asset_type,
            "sector": self.sector,
            "shares": self.shares,
            "price": self.price,
            "cost_basis": self.cost_basis,
            "market_value": self.market_value,
            "gain_loss": self.gain_loss,
            "gain_loss_percent": self.gain_loss_percent,
            "dividend_per_share": self.dividend_per_share,
            "annual_dividend_income": self.annual_dividend_income,
            "dividend_yield": self.dividend_yield,
            "portfolio_yield": self.portfolio_yield,
            "income_yield_on_cost": self.income_yield_on_cost,
            "dividend_pay_date": self.dividend_pay_date,
            "ex_dividend_date": self.ex_dividend_date,
        }