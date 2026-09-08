"""
Purpose:
    Analyze the composition, concentration, and distribution of
    forward annual dividend income within a portfolio.

Responsibilities:
    - Calculate holding-level income contributions.
    - Rank holdings by forward annual dividend income.
    - Calculate income concentration.
    - Aggregate income by asset type.
    - Aggregate income by sector.
    - Identify holdings below a minimum yield.
    - Identify holdings above a high-yield review threshold.
    - Provide portfolio-level income metrics.
    - Serialize analysis results.

Dependencies:
    - Python standard library.
    - RIMS Holding and Portfolio components.

Revision History:
    0.2.0 - Initial portfolio income analysis implementation.

Author:
    RIMS Development Team
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .holding import Holding
from .portfolio import Portfolio


@dataclass(frozen=True, slots=True)
class IncomeHoldingAnalysis:
    """Represent income analysis for one portfolio holding."""

    symbol: str
    description: str
    asset_type: str
    sector: str
    annual_dividend_income: Decimal
    income_contribution_percent: Decimal
    market_value: Decimal
    portfolio_weight_percent: Decimal
    dividend_yield: Decimal
    income_yield_on_cost: Decimal


@dataclass(frozen=True, slots=True)
class IncomeGroupAnalysis:
    """Represent aggregated income for an asset type or sector."""

    category: str
    annual_dividend_income: Decimal
    income_contribution_percent: Decimal
    market_value: Decimal
    portfolio_weight_percent: Decimal


@dataclass(frozen=True, slots=True)
class IncomeAnalysis:
    """Analyze the composition and concentration of portfolio income."""

    portfolio_name: str
    total_market_value: Decimal
    total_forward_annual_dividend_income: Decimal
    portfolio_yield: Decimal
    income_yield_on_cost: Decimal
    holding_count: int
    minimum_yield: Decimal
    high_yield_review_threshold: Decimal
    holdings: tuple[IncomeHoldingAnalysis, ...]
    asset_type_analysis: tuple[IncomeGroupAnalysis, ...]
    sector_analysis: tuple[IncomeGroupAnalysis, ...]

    @classmethod
    def from_portfolio(
        cls,
        portfolio: Portfolio,
        minimum_yield: Decimal | float | int = Decimal("5"),
        high_yield_review_threshold: Decimal | float | int = Decimal("10"),
    ) -> IncomeAnalysis:
        """
        Create an income analysis from a Portfolio.

        The Portfolio and Holding objects are not modified.
        """
        if not isinstance(portfolio, Portfolio):
            raise TypeError("portfolio must be a Portfolio object")

        minimum_yield_decimal = cls._to_decimal(minimum_yield)
        high_yield_decimal = cls._to_decimal(high_yield_review_threshold)

        if minimum_yield_decimal < 0:
            raise ValueError("minimum_yield cannot be negative")

        if high_yield_decimal < 0:
            raise ValueError(
                "high_yield_review_threshold cannot be negative"
            )

        holdings = tuple(
            cls._analyze_holding(
                holding=holding,
                portfolio=portfolio,
            )
            for holding in portfolio.holdings
        )

        ranked_holdings = tuple(
            sorted(
                holdings,
                key=lambda holding: (
                    holding.annual_dividend_income,
                    holding.symbol,
                ),
                reverse=True,
            )
        )

        asset_type_analysis = cls._group_analysis(
            holdings=ranked_holdings,
            category_getter=lambda holding: holding.asset_type,
            total_income=portfolio.forward_annual_dividend_income,
            total_market_value=portfolio.total_market_value,
        )

        sector_analysis = cls._group_analysis(
            holdings=ranked_holdings,
            category_getter=lambda holding: holding.sector,
            total_income=portfolio.forward_annual_dividend_income,
            total_market_value=portfolio.total_market_value,
        )

        return cls(
            portfolio_name=portfolio.name,
            total_market_value=portfolio.total_market_value,
            total_forward_annual_dividend_income=(
                portfolio.forward_annual_dividend_income
            ),
            portfolio_yield=portfolio.portfolio_yield,
            income_yield_on_cost=portfolio.income_yield_on_cost,
            holding_count=portfolio.holding_count,
            minimum_yield=minimum_yield_decimal,
            high_yield_review_threshold=high_yield_decimal,
            holdings=ranked_holdings,
            asset_type_analysis=asset_type_analysis,
            sector_analysis=sector_analysis,
        )

    @staticmethod
    def _to_decimal(
        value: Decimal | float | int,
    ) -> Decimal:
        """Convert a numeric value to Decimal."""
        if isinstance(value, Decimal):
            return value

        return Decimal(str(value))

    @classmethod
    def _analyze_holding(
        cls,
        holding: Holding,
        portfolio: Portfolio,
    ) -> IncomeHoldingAnalysis:
        """Create an income analysis record for one holding."""

        total_income = portfolio.forward_annual_dividend_income
        total_market_value = portfolio.total_market_value

        annual_income = holding.annual_dividend_income

        if total_income == 0:
            income_contribution_percent = Decimal("0")
        else:
            income_contribution_percent = (
                annual_income / total_income * Decimal("100")
            )

        if total_market_value == 0:
            portfolio_weight_percent = Decimal("0")
        else:
            portfolio_weight_percent = (
                holding.market_value
                / total_market_value
                * Decimal("100")
            )

        return IncomeHoldingAnalysis(
            symbol=holding.symbol,
            description=holding.description,
            asset_type=holding.asset_type,
            sector=holding.sector,
            annual_dividend_income=annual_income,
            income_contribution_percent=income_contribution_percent,
            market_value=holding.market_value,
            portfolio_weight_percent=portfolio_weight_percent,
            dividend_yield=holding.dividend_yield,
            income_yield_on_cost=holding.income_yield_on_cost,
        )

    @staticmethod
    def _group_analysis(
        holdings: tuple[IncomeHoldingAnalysis, ...],
        category_getter: Any,
        total_income: Decimal,
        total_market_value: Decimal,
    ) -> tuple[IncomeGroupAnalysis, ...]:
        """Aggregate income and market value by a holding category."""

        grouped: dict[str, dict[str, Decimal]] = {}

        for holding in holdings:
            category = category_getter(holding) or "Unclassified"

            if category not in grouped:
                grouped[category] = {
                    "income": Decimal("0"),
                    "market_value": Decimal("0"),
                }

            grouped[category]["income"] += holding.annual_dividend_income
            grouped[category]["market_value"] += holding.market_value

        results = []

        for category, values in grouped.items():
            income = values["income"]
            market_value = values["market_value"]

            if total_income == 0:
                income_contribution_percent = Decimal("0")
            else:
                income_contribution_percent = (
                    income / total_income * Decimal("100")
                )

            if total_market_value == 0:
                portfolio_weight_percent = Decimal("0")
            else:
                portfolio_weight_percent = (
                    market_value
                    / total_market_value
                    * Decimal("100")
                )

            results.append(
                IncomeGroupAnalysis(
                    category=category,
                    annual_dividend_income=income,
                    income_contribution_percent=(
                        income_contribution_percent
                    ),
                    market_value=market_value,
                    portfolio_weight_percent=portfolio_weight_percent,
                )
            )

        return tuple(
            sorted(
                results,
                key=lambda group: (
                    group.annual_dividend_income,
                    group.category,
                ),
                reverse=True,
            )
        )

    @property
    def top_income_holding(self) -> IncomeHoldingAnalysis | None:
        """Return the holding producing the most annual income."""
        if not self.holdings:
            return None

        return self.holdings[0]

    def top_income_holdings(
        self,
        count: int,
    ) -> tuple[IncomeHoldingAnalysis, ...]:
        """Return the top income-producing holdings."""
        if count < 0:
            raise ValueError("count cannot be negative")

        return self.holdings[:count]

    def income_concentration(self, count: int) -> Decimal:
        """
        Return the percentage of portfolio income produced by the top
        number of income-producing holdings.
        """
        if count < 0:
            raise ValueError("count cannot be negative")

        return sum(
            (
                holding.income_contribution_percent
                for holding in self.top_income_holdings(count)
            ),
            Decimal("0"),
        )

    @property
    def top_1_income_concentration(self) -> Decimal:
        """Return income concentration of the top holding."""
        return self.income_concentration(1)

    @property
    def top_3_income_concentration(self) -> Decimal:
        """Return income concentration of the top three holdings."""
        return self.income_concentration(3)

    @property
    def top_5_income_concentration(self) -> Decimal:
        """Return income concentration of the top five holdings."""
        return self.income_concentration(5)

    @property
    def top_10_income_concentration(self) -> Decimal:
        """Return income concentration of the top ten holdings."""
        return self.income_concentration(10)

    @property
    def holdings_below_minimum_yield(
        self,
    ) -> tuple[IncomeHoldingAnalysis, ...]:
        """Return holdings below the configured minimum yield."""
        return tuple(
            holding
            for holding in self.holdings
            if holding.dividend_yield < self.minimum_yield
        )

    @property
    def holdings_above_high_yield_threshold(
        self,
    ) -> tuple[IncomeHoldingAnalysis, ...]:
        """Return holdings above the configured high-yield review threshold."""
        return tuple(
            holding
            for holding in self.holdings
            if holding.dividend_yield > self.high_yield_review_threshold
        )

    def asset_type(self, category: str) -> IncomeGroupAnalysis | None:
        """Return analysis for a specific asset type."""
        for group in self.asset_type_analysis:
            if group.category == category:
                return group

        return None

    def sector(self, category: str) -> IncomeGroupAnalysis | None:
        """Return analysis for a specific sector."""
        for group in self.sector_analysis:
            if group.category == category:
                return group

        return None

    def to_dict(self) -> dict:
        """Serialize the income analysis into a dictionary."""

        return {
            "portfolio_name": self.portfolio_name,
            "total_market_value": str(self.total_market_value),
            "total_forward_annual_dividend_income": str(
                self.total_forward_annual_dividend_income
            ),
            "portfolio_yield": str(self.portfolio_yield),
            "income_yield_on_cost": str(self.income_yield_on_cost),
            "holding_count": self.holding_count,
            "minimum_yield": str(self.minimum_yield),
            "high_yield_review_threshold": str(
                self.high_yield_review_threshold
            ),
            "top_1_income_concentration": str(
                self.top_1_income_concentration
            ),
            "top_3_income_concentration": str(
                self.top_3_income_concentration
            ),
            "top_5_income_concentration": str(
                self.top_5_income_concentration
            ),
            "top_10_income_concentration": str(
                self.top_10_income_concentration
            ),
            "holdings_below_minimum_yield": [
                holding.symbol
                for holding in self.holdings_below_minimum_yield
            ],
            "holdings_above_high_yield_threshold": [
                holding.symbol
                for holding in self.holdings_above_high_yield_threshold
            ],
            "holdings": [
                {
                    "symbol": holding.symbol,
                    "description": holding.description,
                    "asset_type": holding.asset_type,
                    "sector": holding.sector,
                    "annual_dividend_income": str(
                        holding.annual_dividend_income
                    ),
                    "income_contribution_percent": str(
                        holding.income_contribution_percent
                    ),
                    "market_value": str(holding.market_value),
                    "portfolio_weight_percent": str(
                        holding.portfolio_weight_percent
                    ),
                    "dividend_yield": str(holding.dividend_yield),
                    "income_yield_on_cost": str(
                        holding.income_yield_on_cost
                    ),
                }
                for holding in self.holdings
            ],
            "asset_type_analysis": [
                {
                    "category": group.category,
                    "annual_dividend_income": str(
                        group.annual_dividend_income
                    ),
                    "income_contribution_percent": str(
                        group.income_contribution_percent
                    ),
                    "market_value": str(group.market_value),
                    "portfolio_weight_percent": str(
                        group.portfolio_weight_percent
                    ),
                }
                for group in self.asset_type_analysis
            ],
            "sector_analysis": [
                {
                    "category": group.category,
                    "annual_dividend_income": str(
                        group.annual_dividend_income
                    ),
                    "income_contribution_percent": str(
                        group.income_contribution_percent
                    ),
                    "market_value": str(group.market_value),
                    "portfolio_weight_percent": str(
                        group.portfolio_weight_percent
                    ),
                }
                for group in self.sector_analysis
            ],
        }