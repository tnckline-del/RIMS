"""Tests for the RIMS application foundation."""

from __future__ import annotations

from pathlib import Path

from app.app_config import (
    APP_NAME,
    APP_SHORT_NAME,
    APP_VERSION,
    DATA_DIR,
    LAYOUT,
    OUTPUT_DIR,
    PAGE_ICON,
    PAGE_TITLE,
    PROJECT_ROOT,
)
from app.main import configure_page, main, render_application
from app.pages.dashboard import main as dashboard_main
from app.pages.dashboard import render_dashboard


def test_application_identity() -> None:
    """Application identity is defined correctly."""
    assert APP_SHORT_NAME == "RIMS"
    assert APP_NAME == "Retirement Income Management System"
    assert APP_VERSION == "0.2.0"


def test_project_root_is_rims_directory() -> None:
    """Project root resolves to the RIMS project directory."""
    assert PROJECT_ROOT.name == "RIMS"
    assert PROJECT_ROOT.is_dir()


def test_application_data_directories_are_under_project_root() -> None:
    """Application data directories are located under the project root."""
    assert DATA_DIR.parent == PROJECT_ROOT
    assert OUTPUT_DIR.parent == PROJECT_ROOT


def test_streamlit_page_configuration() -> None:
    """Streamlit page configuration has the approved values."""
    assert PAGE_TITLE == "RIMS"
    assert PAGE_ICON == "R"
    assert LAYOUT == "wide"


def test_main_module_is_callable() -> None:
    """Main application functions are available."""
    assert callable(configure_page)
    assert callable(render_application)
    assert callable(main)


def test_dashboard_module_is_callable() -> None:
    """Dashboard functions are available."""
    assert callable(render_dashboard)
    assert callable(dashboard_main)


def test_application_files_exist() -> None:
    """Required application foundation files exist."""
    required_files = (
        PROJECT_ROOT / "app" / "__init__.py",
        PROJECT_ROOT / "app" / "app_config.py",
        PROJECT_ROOT / "app" / "main.py",
        PROJECT_ROOT / "app" / "pages" / "dashboard.py",
        PROJECT_ROOT / "app" / "services" / "__init__.py",
    )

    for file_path in required_files:
        assert file_path.is_file(), f"Missing application file: {file_path}"


def test_application_paths_are_path_objects() -> None:
    """Application directory settings use pathlib paths."""
    assert isinstance(PROJECT_ROOT, Path)
    assert isinstance(DATA_DIR, Path)
    assert isinstance(OUTPUT_DIR, Path)