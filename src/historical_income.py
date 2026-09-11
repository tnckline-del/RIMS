"""
Historical income analysis for RIMS.

Sprint 19D analyzes actual historical investment income using the
multi-account IncomeAggregationResult produced by Sprint 19C.

This module reports historical facts and trends. It does not project
future income and does not make investment recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from .income_aggregation import IncomeAggregationResult
from .transaction import IncomeCharacter, IncomeType


@dataclass(frozen=True, slots=True)
class IncomeYearSummary:
    """Historical income summary for one calendar year."""

    year: int
    total_income: Decimal
    recurring_income: Decimal
    special_income: Decimal
    prior_year_income: Decimal
    income_adjustments: Decimal
    capital_gain_distributions: Decimal
    transaction_count: int
    income_transaction_count: int
    is_partial_year: bool = False


@dataclass(frozen=True, slots=True)
class IncomeTrend:
    """Year-over-year change in recurring historical income."""

    prior_year: int
    current_year: int
    prior_income: Decimal
    current_income: Decimal
    dollar_change: Decimal
    percentage_change: Decimal | None
    current_year_is_partial: bool


@dataclass(frozen=True, slots=True)
class HistoricalIncomeResult:
    """
    Complete historical income analysis.

    All amounts are actual transaction amounts. No future income is
    annualized or projected by this result.
    """

    aggregation: IncomeAggregationResult
    year_summaries: tuple[IncomeYearSummary, ...]
    recurring_income_by_account: Mapping[str, Decimal]
    recurring_income_by_symbol: Mapping[str, Decimal]
    recurring_income_by_type: Mapping[IncomeType, Decimal]
    income_by_account: Mapping[str, Decimal]
    income_by_symbol: Mapping[str, Decimal]
    income_by_type: Mapping[IncomeType, Decimal]
    trend: IncomeTrend | None

    @property
    def years(self) -> tuple[int, ...]:
        """Return analyzed calendar years."""
        return tuple(summary.year for summary in self.year_summaries)

    @property
    def total_historical_income(self) -> Decimal:
        """Return all historical income across all analyzed years."""
        return sum(
            (summary.total_income for summary in self.year_summaries),
            Decimal("0"),
        )

    @property
    def total_recurring_income(self) -> Decimal:
        """Return all historical recurring income across all analyzed years."""
        return sum(
            (summary.recurring_income for summary in self.year_summaries),
            Decimal("0"),
        )

    @property
    def latest_year(self) -> int | None:
        """Return the latest analyzed year."""
        return self.year_summaries[-1].year if self.year_summaries else None

    @property
    def latest_year_is_partial(self) -> bool:
        """Return whether the latest analyzed year is marked partial."""
        return (
            self.year_summaries[-1].is_partial_year
            if self.year_summaries
            else False
        )

    def year_summary(self, year: int) -> IncomeYearSummary | None:
        """Return the summary for a requested year, if present."""
        for summary in self.year_summaries:
            if summary.year == year:
                return summary
        return None


class HistoricalIncomeAnalyzer:
    """
    Analyze historical income from an IncomeAggregationResult.

    The analyzer requires no knowledge of Schwab's CSV format. It operates
    entirely on the normalized transaction model established by earlier
    RIMS sprints.
    """

    @classmethod
    def analyze(
        cls,
        aggregation: IncomeAggregationResult,
        *,
        partial_years: set[int] | None = None,
    ) -> HistoricalIncomeResult:
        """
        Analyze an existing income aggregation.

        Args:
            aggregation: Consolidated historical transactions.
            partial_years: Optional set of calendar years that should be
                explicitly marked as incomplete. This is supplied by the
                caller because transaction data alone cannot determine
                whether a calendar year is complete.

        Returns:
            HistoricalIncomeResult containing year, account, symbol,
            type, and trend analysis.
        """
        partial_years = partial_years or set()

        year_summaries = cls._build_year_summaries(
            aggregation,
            partial_years=partial_years,
        )

        recurring_income_by_account = aggregation.income_by_account(
            recurring_only=True
        )
        recurring_income_by_symbol = aggregation.income_by_symbol(
            recurring_only=True
        )
        recurring_income_by_type = aggregation.income_by_type(
            recurring_only=True
        )

        income_by_account = aggregation.income_by_account()
        income_by_symbol = aggregation.income_by_symbol()
        income_by_type = aggregation.income_by_type()

        trend = cls._build_latest_trend(year_summaries)

        return HistoricalIncomeResult(
            aggregation=aggregation,
            year_summaries=year_summaries,
            recurring_income_by_account=recurring_income_by_account,
            recurring_income_by_symbol=recurring_income_by_symbol,
            recurring_income_by_type=recurring_income_by_type,
            income_by_account=income_by_account,
            income_by_symbol=income_by_symbol,
            income_by_type=income_by_type,
            trend=trend,
        )

    @staticmethod
    def _build_year_summaries(
        aggregation: IncomeAggregationResult,
        *,
        partial_years: set[int],
    ) -> tuple[IncomeYearSummary, ...]:
        """Build one historical summary for each transaction year."""
        summaries: list[IncomeYearSummary] = []

        for year in aggregation.income_by_year().keys():
            all_income_transactions = tuple(
                transaction
                for transaction in aggregation.income_transactions
                if transaction.transaction_date.year == year
            )

            recurring_transactions = tuple(
                transaction
                for transaction in aggregation.recurring_income_transactions
                if transaction.transaction_date.year == year
            )

            total_income = sum(
                (transaction.amount for transaction in all_income_transactions),
                Decimal("0"),
            )

            recurring_income = sum(
                (transaction.amount for transaction in recurring_transactions),
                Decimal("0"),
            )

            special_income = sum(
                (
                    transaction.amount
                    for transaction in all_income_transactions
                    if transaction.income_character
                    == IncomeCharacter.SPECIAL
                ),
                Decimal("0"),
            )

            prior_year_income = sum(
                (
                    transaction.amount
                    for transaction in all_income_transactions
                    if transaction.income_character
                    == IncomeCharacter.PRIOR_YEAR
                ),
                Decimal("0"),
            )

            income_adjustments = sum(
                (
                    transaction.amount
                    for transaction in all_income_transactions
                    if transaction.income_character
                    == IncomeCharacter.ADJUSTMENT
                ),
                Decimal("0"),
            )

            capital_gain_distributions = sum(
                (
                    transaction.amount
                    for transaction in all_income_transactions
                    if transaction.is_capital_gain_distribution
                ),
                Decimal("0"),
            )

            summaries.append(
                IncomeYearSummary(
                    year=year,
                    total_income=total_income,
                    recurring_income=recurring_income,
                    special_income=special_income,
                    prior_year_income=prior_year_income,
                    income_adjustments=income_adjustments,
                    capital_gain_distributions=capital_gain_distributions,
                    transaction_count=sum(
                        1
                        for transaction in aggregation.transactions
                        if transaction.transaction_date.year == year
                    ),
                    income_transaction_count=len(all_income_transactions),
                    is_partial_year=year in partial_years,
                )
            )

        return tuple(sorted(summaries, key=lambda summary: summary.year))

    @staticmethod
    def _build_latest_trend(
        year_summaries: tuple[IncomeYearSummary, ...],
    ) -> IncomeTrend | None:
        """
        Compare the two latest analyzed years.

        The percentage is still calculated when the current year is partial,
        but the result explicitly identifies that limitation.
        """
        if len(year_summaries) < 2:
            return None

        prior = year_summaries[-2]
        current = year_summaries[-1]

        dollar_change = current.recurring_income - prior.recurring_income

        if prior.recurring_income == Decimal("0"):
            percentage_change = None
        else:
            percentage_change = (
                dollar_change / prior.recurring_income
            ) * Decimal("100")

        return IncomeTrend(
            prior_year=prior.year,
            current_year=current.year,
            prior_income=prior.recurring_income,
            current_income=current.recurring_income,
            dollar_change=dollar_change,
            percentage_change=percentage_change,
            current_year_is_partial=current.is_partial_year,
        )


def analyze_historical_income(
    aggregation: IncomeAggregationResult,
    *,
    partial_years: set[int] | None = None,
) -> HistoricalIncomeResult:
    """Convenience function for historical income analysis."""
    return HistoricalIncomeAnalyzer.analyze(
        aggregation,
        partial_years=partial_years,
    )