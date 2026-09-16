"""RIMS Dashboard page."""

from __future__ import annotations

import streamlit as st


def render_dashboard() -> None:
    """Render the initial RIMS Dashboard."""
    st.title("Dashboard")

    st.caption(
        "Portfolio, retirement income, attention items, and system status."
    )

    st.divider()

    st.header("Portfolio Overview")

    portfolio_col1, portfolio_col2 = st.columns(2)

    with portfolio_col1:
        st.metric("Portfolio Value", "Not Connected")

    with portfolio_col2:
        st.metric("Holdings", "Not Connected")

    st.header("Retirement Income")

    income_col1, income_col2 = st.columns(2)

    with income_col1:
        st.metric("Forward Annual Income", "Not Connected")

    with income_col2:
        st.metric("Income Target", "Not Connected")

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