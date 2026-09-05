"""
Purpose:
    Define the Portfolio data model used by the Retirement Income
    Management System (RIMS).

Responsibilities:
    - Manage a collection of Holding objects.
    - Calculate portfolio-level valuation metrics.
    - Calculate portfolio-level income metrics.
    - Calculate position allocation.
    - Provide holding lookup and validation.

Dependencies:
    Python standard library only.
    RIMS Holding model.

Revision History:
    0.2.0 - Initial Portfolio data model.

Author:
    RIMS Development Team
"""

from __future__ import annotations

from dataclasses import dataclass, field

from decimal import Decimal

from src.holding import Holding


@dataclass
class Portfolio:
    """Represent and analyze a collection of investment holdings."""

    name: str = "RIMS Portfolio"
    holdings: list[Holding] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the portfolio after initialization."""
        self.name = self.name.strip()

        if not self.name:
            raise ValueError("Portfolio name cannot be empty.")

        self.validate()

    def validate(self) -> None:
        """Validate the holdings contained in the portfolio."""
        symbols: set[str] = set()

        for holding in self.holdings:
            if not isinstance(holding, Holding):
                raise TypeError("Portfolio holdings must be Holding objects.")

            if holding.symbol in symbols:
                raise ValueError(
                    f"Duplicate holding symbol: {holding.symbol}"
                )

            symbols.add(holding.symbol)

    def add_holding(self, holding: Holding) -> None:
        """Add a holding to the portfolio."""
        if not isinstance(holding, Holding):
            raise TypeError("Portfolio holdings must be Holding objects.")

        if self.get_holding(holding.symbol) is not None:
            raise ValueError(
                f"Holding {holding.symbol} already exists in the portfolio."
            )

        self.holdings.append(holding)

    def remove_holding(self, symbol: str) -> Holding:
        """Remove and return a holding by symbol."""
        normalized_symbol = symbol.strip().upper()

        for index, holding in enumerate(self.holdings):
            if holding.symbol == normalized_symbol:
                return self.holdings.pop(index)

        raise KeyError(f"Holding {normalized_symbol} was not found.")

    def get_holding(self, symbol: str) -> Holding | None:
        """Return a holding by symbol, or None if it is not found."""
        normalized_symbol = symbol.strip().upper()

        for holding in self.holdings:
            if holding.symbol == normalized_symbol:
                return holding

        return None

    @property
    def holding_count(self) -> int:
        """Return the number of holdings in the portfolio."""
        return len(self.holdings)

    @property
    def total_market_value(self) -> Decimal:
        """Return the total current market value of the portfolio."""
        return sum(
            (holding.market_value for holding in self.holdings),
            Decimal("0"),
        )

    @property
    def total_cost_basis(self) -> Decimal:
        """Return the total cost basis of the portfolio."""
        return sum(
            (holding.cost_basis for holding in self.holdings),
            Decimal("0"),
        )

    @property
    def total_gain_loss(self) -> Decimal:
        """Return the total unrealized gain or loss."""
        return self.total_market_value - self.total_cost_basis

    @property
    def total_gain_loss_percent(self) -> Decimal:
        """Return total unrealized gain/loss as a percentage."""
        if self.total_cost_basis == 0:
            return Decimal("0")

        return (
            self.total_gain_loss / self.total_cost_basis
        ) * Decimal("100")

    @property
    def forward_annual_dividend_income(self) -> Decimal:
        """
        Return projected annual dividend income for the portfolio.

        This is the primary income metric used by RIMS.
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
        Return projected annual dividend income divided by
        current portfolio market value.
        """
        if self.total_market_value == 0:
            return Decimal("0")

        return (
            self.forward_annual_dividend_income
            / self.total_market_value
        ) * Decimal("100")

    @property
    def income_yield_on_cost(self) -> Decimal:
        """Return projected annual income as a percentage of cost basis."""
        if self.total_cost_basis == 0:
            return Decimal("0")

        return (
            self.forward_annual_dividend_income
            / self.total_cost_basis
        ) * Decimal("100")

    def position_weight(self, symbol: str) -> Decimal:
        """Return a holding's percentage of total portfolio value."""
        holding = self.get_holding(symbol)

        if holding is None:
            raise KeyError(f"Holding {symbol.upper()} was not found.")

        if self.total_market_value == 0:
            return Decimal("0")

        return (
            holding.market_value / self.total_market_value
        ) * Decimal("100")

    def income_contribution(self, symbol: str) -> Decimal:
        """Return a holding's percentage of total annual income."""
        holding = self.get_holding(symbol)

        if holding is None:
            raise KeyError(f"Holding {symbol.upper()} was not found.")

        if self.forward_annual_dividend_income == 0:
            return Decimal("0")

        return (
            holding.annual_dividend_income
            / self.forward_annual_dividend_income
        ) * Decimal("100")

    def to_dict(self) -> dict[str, object]:
        """Return portfolio-level metrics as a dictionary."""
        return {
            "name": self.name,
            "holding_count": self.holding_count,
            "total_market_value": self.total_market_value,
            "total_cost_basis": self.total_cost_basis,
            "total_gain_loss": self.total_gain_loss,
            "total_gain_loss_percent": self.total_gain_loss_percent,
            "forward_annual_dividend_income": (
                self.forward_annual_dividend_income
            ),
            "portfolio_yield": self.portfolio_yield,
            "income_yield_on_cost": self.income_yield_on_cost,
        }