"""
Purpose:
    Define the RIMS Holding entity.

Responsibilities:
    - Represent a single investment holding.
    - Store position, cost basis, pricing, dividend, and classification data.
    - Use an authoritative market value when provided by an external source.
    - Fall back to shares multiplied by price when no authoritative market
      value is available.
    - Calculate gain/loss and income metrics.
    - Support price and dividend updates.
    - Provide dictionary serialization for reporting and workbook use.

Dependencies:
    Python standard library only.

Revision History:
    0.2.0 - Initial Holding entity.
    0.2.0 - Added authoritative market value with calculated fallback.

Author:
    RIMS Development Team
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from typing import Any


def _to_decimal(value: Decimal | float | int) -> Decimal:
    """
    Convert a numeric value to Decimal without introducing binary
    floating-point representation errors.
    """
    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


@dataclass(slots=True)
class Holding:
    """
    Represent a single investment holding.

    Market value:
        If market_value is supplied, it is treated as the authoritative
        market value from the source system, such as Schwab.

        If market_value is omitted or None, RIMS calculates market value
        as shares multiplied by price.

        After initialization, market_value is always stored as a Decimal.
    """

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

    # Authoritative market value when supplied by the source system.
    # If None, __post_init__ replaces it with shares * price.
    market_value: Decimal | None = None

    def __post_init__(self) -> None:
        """Normalize numeric values and validate the holding."""

        self.shares = _to_decimal(self.shares)
        self.price = _to_decimal(self.price)
        self.cost_basis = _to_decimal(self.cost_basis)
        self.dividend_per_share = _to_decimal(self.dividend_per_share)
        self.dividend_yield = _to_decimal(self.dividend_yield)

        if self.market_value is None:
            self.market_value = self.shares * self.price
        else:
            self.market_value = _to_decimal(self.market_value)

        if not self.symbol or not self.symbol.strip():
            raise ValueError("Holding symbol cannot be blank.")

        if self.shares < 0:
            raise ValueError("Holding shares cannot be negative.")

        if self.price < 0:
            raise ValueError("Holding price cannot be negative.")

        if self.cost_basis < 0:
            raise ValueError("Holding cost basis cannot be negative.")

        if self.market_value < 0:
            raise ValueError("Holding market value cannot be negative.")

        if self.dividend_per_share < 0:
            raise ValueError("Dividend per share cannot be negative.")

        if self.dividend_yield < 0:
            raise ValueError("Dividend yield cannot be negative.")

    @property
    def calculated_market_value(self) -> Decimal:
        """
        Calculate market value from shares multiplied by price.

        This is retained separately so RIMS can compare the calculated
        value with an authoritative source-system market value.
        """
        return self.shares * self.price

    @property
    def gain_loss(self) -> Decimal:
        """Return the unrealized gain or loss in dollars."""
        return self.market_value - self.cost_basis

    @property
    def gain_loss_percent(self) -> Decimal:
        """
        Return unrealized gain/loss as a percentage of cost basis.

        Returns zero when cost basis is zero.
        """
        if self.cost_basis == 0:
            return Decimal("0")

        return (self.gain_loss / self.cost_basis) * Decimal("100")

    @property
    def annual_dividend_income(self) -> Decimal:
        """
        Return forward annual dividend income in dollars.

        This is the primary income metric used by RIMS.
        """
        return self.shares * self.dividend_per_share

    @property
    def portfolio_yield(self) -> Decimal:
        """
        Return forward annual dividend income as a percentage of
        current market value.

        Returns zero when market value is zero.
        """
        if self.market_value == 0:
            return Decimal("0")

        return (self.annual_dividend_income / self.market_value) * Decimal("100")

    @property
    def income_yield_on_cost(self) -> Decimal:
        """
        Return forward annual dividend income as a percentage of
        cost basis.

        Returns zero when cost basis is zero.
        """
        if self.cost_basis == 0:
            return Decimal("0")

        return (self.annual_dividend_income / self.cost_basis) * Decimal("100")

    def update_price(self, price: Decimal | float | int) -> None:
        """
        Update the quoted price.

        Important:
            Updating price does NOT overwrite an authoritative market
            value supplied by the source system.

        If the holding was created using the calculated fallback, the
        market value is recalculated from shares multiplied by the new
        price.
        """
        new_price = _to_decimal(price)

        if new_price < 0:
            raise ValueError("Holding price cannot be negative.")

        old_calculated_value = self.calculated_market_value

        self.price = new_price

        # If the existing market value was the calculated fallback,
        # continue using the calculated value after a price update.
        #
        # If it was an authoritative source-system value, preserve it.
        if self.market_value == old_calculated_value:
            self.market_value = self.calculated_market_value

    def update_market_value(
        self,
        market_value: Decimal | float | int | None,
    ) -> None:
        """
        Update the authoritative market value.

        Passing None restores the calculated fallback:
            shares * price
        """
        if market_value is None:
            self.market_value = self.calculated_market_value
            return

        new_market_value = _to_decimal(market_value)

        if new_market_value < 0:
            raise ValueError("Holding market value cannot be negative.")

        self.market_value = new_market_value

    def update_dividend(
        self,
        dividend_per_share: Decimal | float | int,
        dividend_yield: Decimal | float | int | None = None,
    ) -> None:
        """
        Update dividend information.

        dividend_yield is optional because RIMS can calculate income
        metrics directly from dividend_per_share and market value.
        """
        new_dividend = _to_decimal(dividend_per_share)

        if new_dividend < 0:
            raise ValueError("Dividend per share cannot be negative.")

        self.dividend_per_share = new_dividend

        if dividend_yield is not None:
            new_yield = _to_decimal(dividend_yield)

            if new_yield < 0:
                raise ValueError("Dividend yield cannot be negative.")

            self.dividend_yield = new_yield

    def to_dict(self) -> dict[str, Any]:
        """
        Return the holding as a dictionary suitable for reporting,
        workbook generation, or serialization.
        """
        data = asdict(self)

        data["calculated_market_value"] = self.calculated_market_value
        data["gain_loss"] = self.gain_loss
        data["gain_loss_percent"] = self.gain_loss_percent
        data["annual_dividend_income"] = self.annual_dividend_income
        data["portfolio_yield"] = self.portfolio_yield
        data["income_yield_on_cost"] = self.income_yield_on_cost

        return data