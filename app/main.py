"""Main entry point for the RIMS Streamlit application."""

from __future__ import annotations

import streamlit as st

from app.app_config import APP_NAME, APP_SHORT_NAME, LAYOUT, PAGE_ICON, PAGE_TITLE
from app.pages.dashboard import render_dashboard


def configure_page() -> None:
    """Configure the Streamlit page."""
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout=LAYOUT,
    )


def render_application() -> None:
    """Render the RIMS application."""
    st.title(APP_SHORT_NAME)
    st.caption(APP_NAME)

    st.divider()

    render_dashboard()


def main() -> None:
    """Run the RIMS application."""
    configure_page()
    render_application()


if __name__ == "__main__":
    main()