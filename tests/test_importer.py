from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.importer import (
    SchwabImportResult,
    import_schwab_csv,
    parse_reporting_date,
)


REAL_SCHWAB_FILE = Path(
    "/Users/timothykline/Downloads/"
    "All-Accounts-Positions-2026-09-07-173949.csv"
)


def test_parse_reporting_date_from_schwab_header() -> None:
    header = (
        '"Positions for All-Accounts as of 05:39 PM ET, 09/07/2026"'
    )

    result = parse_reporting_date(header)

    assert result == date(2026, 9, 7)


def test_parse_reporting_date_accepts_different_time() -> None:
    header = (
        '"Positions for All-Accounts as of 09:15 AM ET, 12/31/2025"'
    )

    result = parse_reporting_date(header)

    assert result == date(2025, 12, 31)


def test_parse_reporting_date_rejects_missing_reporting_date() -> None:
    header = '"Positions for All-Accounts"'

    with pytest.raises(
        ValueError,
        match="Unable to parse Schwab reporting date",
    ):
        parse_reporting_date(header)


def test_parse_reporting_date_rejects_invalid_date() -> None:
    header = (
        '"Positions for All-Accounts as of 05:39 PM ET, 13/45/2026"'
    )

    with pytest.raises(
        ValueError,
        match="Unable to parse Schwab reporting date",
    ):
        parse_reporting_date(header)


@pytest.mark.skipif(
    not REAL_SCHWAB_FILE.exists(),
    reason="Real Schwab integration file not available.",
)
def test_import_schwab_csv_returns_reporting_date() -> None:
    result = import_schwab_csv(REAL_SCHWAB_FILE)

    assert isinstance(result, SchwabImportResult)
    assert result.reporting_date == date(2026, 9, 7)


@pytest.mark.skipif(
    not REAL_SCHWAB_FILE.exists(),
    reason="Real Schwab integration file not available.",
)
def test_import_schwab_csv_preserves_reconciliation() -> None:
    result = import_schwab_csv(REAL_SCHWAB_FILE)

    assert result.reporting_date == date(2026, 9, 7)
    assert result.is_reconciled is True
    assert result.market_value_difference == Decimal("0")
    assert result.cost_basis_difference == Decimal("0")