"""RIMS Income Analysis page."""

from __future__ import annotations

import streamlit as st

from app.app_config import (
    IMPORT_OPERATION_DIR,
    SNAPSHOT_DIR,
    TRANSACTION_DIR,
)
from app.services.income_analysis_service import (
    create_income_analysis_service,
)


def render_income_analysis() -> None:
    """Render the current portfolio income analysis."""
    income_service = create_income_analysis_service(
        import_operation_path=IMPORT_OPERATION_DIR,
        snapshot_path=SNAPSHOT_DIR,
        transaction_path=TRANSACTION_DIR,
    )

    analysis = income_service.analyze()

    st.title("Income Analysis")
    st.caption(
        "Current portfolio recurring income and income concentration."
    )

    if analysis is None:
        st.warning("Current portfolio data is not available.")
        return

    st.divider()

    st.header("Portfolio Income Summary")

    summary_col1, summary_col2, summary_col3 = st.columns(3)

    with summary_col1:
        st.metric(
            "Portfolio Value",
            f"${analysis.market_value:,.2f}",
        )

    with summary_col2:
        st.metric(
            "Trailing 12-Month Income",
            f"${analysis.trailing_12_month_recurring_income:,.2f}",
        )

    with summary_col3:
        st.metric(
            "Trailing 12-Month Income Yield",
            f"{analysis.trailing_12_month_income_yield:.2f}%",
        )

    income_count_col1, income_count_col2 = st.columns(2)

    with income_count_col1:
        st.metric(
            "Holdings With Recorded Income",
            f"{analysis.holdings_with_income:,}",
        )

    with income_count_col2:
        st.metric(
            "Holdings Without Recorded Income",
            f"{analysis.holdings_without_income:,}",
        )

    st.divider()

    st.header("Income Concentration")

    concentration_col1, concentration_col2 = st.columns(2)

    with concentration_col1:
        if analysis.largest_income_holding_symbol is not None:
            st.metric(
                "Largest Income-Producing Holding",
                analysis.largest_income_holding_symbol,
                f"${analysis.largest_income_holding_amount:,.2f} "
                f"({analysis.largest_income_holding_weight:.2f}% of income)",
            )
        else:
            st.metric(
                "Largest Income-Producing Holding",
                "None",
            )

    with concentration_col2:
        st.metric(
            "Top 5 Holdings' Share of Income",
            f"{analysis.top_five_income_weight:.2f}%",
        )
    st.divider()

    st.header("Holding-by-Holding Income Analysis")

    table_holdings = sorted(
        analysis.holdings,
        key=lambda holding: holding.trailing_12_month_recurring_income,
        reverse=True,
    )

    table_rows = [
        {
            "Symbol": holding.symbol,
            "Market Value": holding.market_value,
            "Portfolio %": float(holding.portfolio_weight),
            "Cost Basis": holding.cost_basis,
            "Unrealized Gain/Loss": (
                f"{holding.unrealized_gain_loss:+,.2f} "
                f"({holding.unrealized_gain_loss_percent:+.2f}%)"
            ),
            "All-History Income": holding.all_history_recurring_income,
            "TTM Income": holding.trailing_12_month_recurring_income,
            "Income %": float(holding.income_weight),
            "TTM Yield": float(holding.trailing_12_month_yield),
            "Yield on Cost": float(holding.yield_on_cost),
        }
        for holding in table_holdings
    ]

    st.dataframe(
        table_rows,
        width="stretch",
        hide_index=True,
        column_config={
            "Symbol": st.column_config.TextColumn(
                "Symbol",
                width="small",
                help="Ticker symbol for the current holding.",
            ),
            "Market Value": st.column_config.NumberColumn(
                "Market Value",
                format="$%,.2f",
                help="Current market value of the holding.",
            ),
            "Portfolio %": st.column_config.NumberColumn(
                "Portfolio %",
                format="%.2f%%",
                help=(
                    "Holding's percentage of the current portfolio "
                    "market value."
                ),
            ),
            "Cost Basis": st.column_config.NumberColumn(
                "Cost Basis",
                format="$%,.2f",
                help="Recorded cost basis of the current holding.",
            ),
            "All-History Income": st.column_config.NumberColumn(
                "All-History Income",
                format="$%,.2f",
                help=(
                    "Recurring income recorded for this holding across "
                    "all available transaction history."
                ),
            ),
            "TTM Income": st.column_config.NumberColumn(
                "TTM Income",
                format="$%,.2f",
                help=(
                    "Recurring income recorded for this holding during "
                    "the trailing 12 months."
                ),
            ),
            "Income %": st.column_config.NumberColumn(
                "Income %",
                format="%.2f%%",
                help=(
                    "Holding's percentage of total trailing 12-month "
                    "recurring income from current holdings."
                ),
            ),
            "Unrealized Gain/Loss": st.column_config.TextColumn(
                "Unrealized Gain/Loss",
                help=(
                    "Unrealized gain or loss compares the current market "
                    "value with the recorded cost basis. The percentage "
                    "is calculated as (market value / cost basis - 1) × 100."
                ),
            ),
            "TTM Yield": st.column_config.NumberColumn(
                "TTM Yield",
                format="%.2f%%",
                help=(
                    "TTM recurring income divided by the holding's "
                    "current market value."
                ),
            ),
            "Yield on Cost": st.column_config.NumberColumn(
                "Yield on Cost",
                format="%.2f%%",
                help=(
                    "TTM recurring income divided by the holding's "
                    "recorded cost basis."
                ),
            ),
        },
    )

def main() -> None:
    """Run the Income Analysis page."""
    render_income_analysis()


if __name__ == "__main__":
    main()
