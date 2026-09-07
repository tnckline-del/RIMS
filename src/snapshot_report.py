"""
Purpose:
    Generate a human-readable historical portfolio report from a
    SnapshotComparison.

Responsibilities:
    - Present portfolio-level historical changes.
    - Present retirement-income changes prominently.
    - Identify added and removed holdings.
    - Identify the largest increases and decreases in forward annual
      dividend income.
    - Present holding-level changes.
    - Preserve the distinction between market-value change and investment
      performance.

Dependencies:
    Python standard library only.
    RIMS SnapshotComparison classes.

Revision History:
    0.2.0 - Initial historical snapshot reporting capability.

Author:
    RIMS Development Team
"""

from __future__ import annotations

from decimal import Decimal

from .snapshot_comparison import HoldingChange, SnapshotComparison


class SnapshotReport:
    """
    Generate a readable text report from a SnapshotComparison.

    This report intentionally describes changes in portfolio market value
    rather than investment performance or total return.
    """

    def __init__(self, comparison: SnapshotComparison) -> None:
        """Initialize the report with a snapshot comparison."""
        if not isinstance(comparison, SnapshotComparison):
            raise TypeError("comparison must be a SnapshotComparison.")

        self.comparison = comparison

    def generate(self) -> str:
        """Generate and return the complete historical comparison report."""
        sections = [
            self._header(),
            self._portfolio_summary(),
            self._income_analysis(),
            self._holding_activity(),
            self._income_highlights(),
            self._holding_details(),
        ]

        return "\n\n".join(sections)

    def _header(self) -> str:
        """Generate the report header."""
        c = self.comparison

        return "\n".join(
            [
                "RIMS HISTORICAL SNAPSHOT COMPARISON",
                "=" * 50,
                f"Portfolio:       {c.portfolio_name}",
                f"Beginning date:  {c.beginning_date.isoformat()}",
                f"Ending date:     {c.ending_date.isoformat()}",
            ]
        )

    def _portfolio_summary(self) -> str:
        """Generate the portfolio-level summary section."""
        c = self.comparison

        return "\n".join(
            [
                "PORTFOLIO SUMMARY",
                "-" * 50,
                self._change_line(
                    "Total market value",
                    c.beginning_total_market_value,
                    c.ending_total_market_value,
                    c.total_market_value_change,
                ),
                self._change_line(
                    "Securities value",
                    c.beginning_securities_market_value,
                    c.ending_securities_market_value,
                    c.securities_market_value_change,
                ),
                self._change_line(
                    "Cash",
                    c.beginning_cash,
                    c.ending_cash,
                    c.cash_change,
                ),
                self._change_line(
                    "Cost basis",
                    c.beginning_cost_basis,
                    c.ending_cost_basis,
                    c.cost_basis_change,
                ),
                self._change_line(
                    "Gain/loss",
                    c.beginning_gain_loss,
                    c.ending_gain_loss,
                    c.gain_loss_change,
                ),
                self._integer_change_line(
                    "Holding count",
                    c.beginning_holding_count,
                    c.ending_holding_count,
                    c.holding_count_change,
                ),
            ]
        )

    def _income_analysis(self) -> str:
        """Generate the retirement-income analysis section."""
        c = self.comparison

        return "\n".join(
            [
                "RETIREMENT INCOME ANALYSIS",
                "-" * 50,
                self._change_line(
                    "Forward annual dividend income",
                    c.beginning_forward_annual_dividend_income,
                    c.ending_forward_annual_dividend_income,
                    c.forward_annual_dividend_income_change,
                ),
                self._percentage_line(
                    "Portfolio yield",
                    c.beginning_portfolio_yield,
                    c.ending_portfolio_yield,
                    c.portfolio_yield_change,
                ),
                self._percentage_line(
                    "Income yield on cost",
                    c.beginning_income_yield_on_cost,
                    c.ending_income_yield_on_cost,
                    c.income_yield_on_cost_change,
                ),
            ]
        )

    def _holding_activity(self) -> str:
        """Generate the added/removed/common holdings section."""
        c = self.comparison

        lines = [
            "HOLDING ACTIVITY",
            "-" * 50,
            f"Common holdings: {len(c.common_holdings)}",
            f"Added holdings:  {len(c.added_holdings)}",
            f"Removed holdings: {len(c.removed_holdings)}",
        ]

        if c.added_symbols:
            lines.append(
                f"Added symbols:   {', '.join(c.added_symbols)}"
            )
        else:
            lines.append("Added symbols:   None")

        if c.removed_symbols:
            lines.append(
                f"Removed symbols: {', '.join(c.removed_symbols)}"
            )
        else:
            lines.append("Removed symbols: None")

        return "\n".join(lines)

    def _income_highlights(self) -> str:
        """Generate the largest positive and negative income changes."""
        changes = [
            change
            for change in self.comparison.holding_changes
            if change.annual_dividend_income_change != 0
        ]

        lines = [
            "INCOME IMPACT HIGHLIGHTS",
            "-" * 50,
        ]

        if not changes:
            lines.append("No change in forward annual dividend income.")
            return "\n".join(lines)

        increases = sorted(
            (
                change
                for change in changes
                if change.annual_dividend_income_change > 0
            ),
            key=lambda change: change.annual_dividend_income_change,
            reverse=True,
        )

        decreases = sorted(
            (
                change
                for change in changes
                if change.annual_dividend_income_change < 0
            ),
            key=lambda change: change.annual_dividend_income_change,
        )

        if increases:
            lines.append("Largest income increases:")
            for change in increases[:5]:
                lines.append(
                    f"  {change.symbol:<8} "
                    f"{self._signed_currency(change.annual_dividend_income_change)}"
                )
        else:
            lines.append("Largest income increases: None")

        if decreases:
            lines.append("Largest income decreases:")
            for change in decreases[:5]:
                lines.append(
                    f"  {change.symbol:<8} "
                    f"{self._signed_currency(change.annual_dividend_income_change)}"
                )
        else:
            lines.append("Largest income decreases: None")

        return "\n".join(lines)

    def _holding_details(self) -> str:
        """Generate detailed holding-level changes."""
        lines = [
            "HOLDING-LEVEL CHANGES",
            "-" * 50,
        ]

        if not self.comparison.holding_changes:
            lines.append("No holdings to report.")
            return "\n".join(lines)

        for change in self.comparison.holding_changes:
            lines.extend(self._format_holding_change(change))

        return "\n".join(lines)

    def _format_holding_change(
        self,
        change: HoldingChange,
    ) -> list[str]:
        """Format one holding change."""
        status = change.status.upper()

        return [
            f"{change.symbol} [{status}]",
            (
                f"  Shares:             "
                f"{change.beginning_shares} -> {change.ending_shares} "
                f"({self._signed_decimal(change.shares_change)})"
            ),
            (
                f"  Market value:      "
                f"{self._currency(change.beginning_market_value)} -> "
                f"{self._currency(change.ending_market_value)} "
                f"({self._signed_currency(change.market_value_change)})"
            ),
            (
                f"  Cost basis:        "
                f"{self._currency(change.beginning_cost_basis)} -> "
                f"{self._currency(change.ending_cost_basis)} "
                f"({self._signed_currency(change.cost_basis_change)})"
            ),
            (
                f"  Gain/loss:         "
                f"{self._currency(change.beginning_gain_loss)} -> "
                f"{self._currency(change.ending_gain_loss)} "
                f"({self._signed_currency(change.gain_loss_change)})"
            ),
            (
                f"  Annual dividend:   "
                f"{self._currency(change.beginning_annual_dividend_income)} -> "
                f"{self._currency(change.ending_annual_dividend_income)} "
                f"({self._signed_currency(change.annual_dividend_income_change)})"
            ),
        ]

    @staticmethod
    def _currency(value: Decimal) -> str:
        """Format a Decimal as currency."""
        return f"${value:,.2f}"

    @staticmethod
    def _signed_currency(value: Decimal) -> str:
        """Format a Decimal as signed currency."""
        if value > 0:
            return f"+${value:,.2f}"
        if value < 0:
            return f"-${abs(value):,.2f}"
        return "$0.00"

    @staticmethod
    def _signed_decimal(value: Decimal) -> str:
        """Format a Decimal as a signed numeric value."""
        if value > 0:
            return f"+{value}"
        if value < 0:
            return str(value)
        return "0"

    @staticmethod
    def _change_line(
        label: str,
        beginning: Decimal,
        ending: Decimal,
        change: Decimal,
    ) -> str:
        """Format a beginning/end/change financial metric."""
        return (
            f"{label:<32}"
            f"{SnapshotReport._currency(beginning):>14} -> "
            f"{SnapshotReport._currency(ending):>14} "
            f"({SnapshotReport._signed_currency(change)})"
        )

    @staticmethod
    def _percentage_line(
        label: str,
        beginning: Decimal,
        ending: Decimal,
        change: Decimal,
    ) -> str:
        """Format a beginning/end/change percentage metric."""
        return (
            f"{label:<32}"
            f"{beginning:>8.2f}% -> "
            f"{ending:>8.2f}% "
            f"({SnapshotReport._signed_percentage_points(change)})"
        )

    @staticmethod
    def _signed_percentage_points(value: Decimal) -> str:
        """Format a percentage-point change."""
        if value > 0:
            return f"+{value:.2f} pp"
        if value < 0:
            return f"{value:.2f} pp"
        return "0.00 pp"

    @staticmethod
    def _integer_change_line(
        label: str,
        beginning: int,
        ending: int,
        change: int,
    ) -> str:
        """Format a beginning/end/change integer metric."""
        sign = f"+{change}" if change > 0 else str(change)

        return (
            f"{label:<32}"
            f"{beginning:>8} -> "
            f"{ending:>8} "
            f"({sign})"
        )

    def __str__(self) -> str:
        """Return the generated report."""
        return self.generate()