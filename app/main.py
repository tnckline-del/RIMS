"""Main entry point for the RIMS Streamlit application."""

from __future__ import annotations

import streamlit as st

from app.app_config import LAYOUT, PAGE_ICON, PAGE_TITLE
from app.pages.dashboard import render_dashboard
from app.pages.import_data import render_import_data


def configure_page() -> None:
    """Configure the Streamlit page."""
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout=LAYOUT,
    )


def render_application() -> None:
    """Render the RIMS application navigation and pages."""
    pages = [
        st.Page(
            render_dashboard,
            title="Dashboard",
            url_path="dashboard",
        ),
        st.Page(
            render_import_data,
            title="Import Data",
            url_path="import-data",
        ),
    ]

    navigation = st.navigation(pages)
    navigation.run()


def main() -> None:
    """Run the RIMS application."""
    configure_page()
    render_application()


if __name__ == "__main__":
    main()