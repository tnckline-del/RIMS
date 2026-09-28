"""RIMS Dashboard page."""

from __future__ import annotations

import streamlit as st

from app.app_config import (
    IMPORT_OPERATION_DIR,
    SNAPSHOT_DIR,
    TRANSACTION_DIR,
)
from app.services.dashboard_service import create_dashboard_service


def render_dashboard() -> None:
    """Render the RIMS Dashboard."""
    dashboard_service = create_dashboard_service(
        import_operation_path=IMPORT_OPERATION_DIR,
        snapshot_path=SNAPSHOT_DIR,
        transaction_path=TRANSACTION_DIR,
    )

    portfolio = dashboard_service.load_current_portfolio()

    st.title("Dashboard")

    st.caption(
        "Portfolio, retirement income, attention items, and system status."
    )

    st.divider()

    st.header("Portfolio Overview")

    portfolio_col1, portfolio_col2 = st.columns(2)

    with portfolio_col1:
        if portfolio is not None:
            st.metric(
                "Portfolio Value",
                f"${portfolio.total_market_value:,.2f}",
            )
        else:
            st.metric("Portfolio Value", "Not Connected")

    with portfolio_col2:
        if portfolio is not None:
            st.metric(
                "Holdings",
                f"{portfolio.holding_count:,}",
            )
        else:
            st.metric("Holdings", "Not Connected")

    st.header("Retirement Income")

    income_col1, income_col2, income_col3 = st.columns(3)

    income_composition = dashboard_service.trailing_income_composition()

    with income_col1:
        st.metric(
            "Trailing 12-Month Income",
            f"${income_composition.total:,.2f}",
        )

    with income_col2:
        st.metric(
            "Dividends",
            f"${income_composition.dividends:,.2f}",
        )

    with income_col3:
        st.metric(
            "Interest",
            f"${income_composition.interest:,.2f}",
        )

    st.header("Attention Required")

    st.info(
        "Income and portfolio review items will appear here when the "
        "underlying RIMS services are connected."
    )

    st.header("System Status")

    status_col1, status_col2 = st.columns(2)

    with status_col1:
        st.write("**Portfolio Data:** Not Connected")
        st.write("**Transaction Data:** Not Connected")

    with status_col2:
        st.write("**Forward Income:** Not Connected")
        st.write("**Last Update:** Not Connected")


def main() -> None:
    """Run the Dashboard page."""
    render_dashboard()


if __name__ == "__main__":
    main()
