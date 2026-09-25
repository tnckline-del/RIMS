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


# Persistent RIMS data directories
SNAPSHOT_DIR = DATA_DIR / "snapshots"
TRANSACTION_DIR = DATA_DIR / "transactions"
IMPORT_OPERATION_DIR = DATA_DIR / "imports" / "operations"
FORWARD_INCOME_DIR = DATA_DIR / "forward_income"


# Streamlit page configuration
PAGE_TITLE = "RIMS"
PAGE_ICON = "R"
LAYOUT = "wide"
