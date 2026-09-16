"""Application configuration for RIMS."""

from __future__ import annotations

from pathlib import Path


# Application identity
APP_NAME = "Retirement Income Management System"
APP_SHORT_NAME = "RIMS"
APP_VERSION = "0.2.0"


# Project directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"


# Streamlit page configuration
PAGE_TITLE = "RIMS"
PAGE_ICON = "R"
LAYOUT = "wide"