"""
Purpose:
    Import Schwab position data into the Retirement Income Management
    System (RIMS).

Responsibilities:
    - Read Schwab position CSV files.
    - Identify Schwab account sections and data headers.
    - Distinguish securities, cash, and subtotal rows.
    - Convert Schwab values into RIMS data types.
    - Create Holding objects.
    - Consolidate duplicate securities across accounts.
    - Validate imported data.
    - Preserve the original Schwab source file.
    - Report Schwab-to-RIMS reconciliation information.

Dependencies:
    Python standard library only.
    RIMS Holding and Portfolio models.

Revision History:
    0.2.0 - Initial Schwab CSV importer.
    0.2.1 - Added defensive row classification, cash handling,
            duplicate consolidation, and reconciliation reporting.

Author:
    RIMS Development Team
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.holding import Holding
from src.portfolio import Portfolio


SCHWAB_REQUIRED_COLUMNS = {
    "Symbol",
    "Description",
    "Sector",
    "Qty (Quantity)",
    "Price",
    "Cost Basis",
    "Mkt Val (Market Value)",
    "Div $",
    "Div Yld (Dividend Yield)",
    "Asset Type",
}

SCHWAB_CASH_SYMBOL = "Cash & Cash Investments"
SCHWAB_TOTAL_SYMBOL = "Positions Total"


@dataclass(slots=True)
class SchwabImportResult:
    """Represent the result of importing a Schwab positions file."""

    portfolio: Portfolio
    cash_market_value: Decimal
    schwab_market_value: Decimal
    schwab_cost_basis: Decimal
    imported_market_value: Decimal
    imported_cost_basis: Decimal

    @property
    def total_reconciled_market_value(self) -> Decimal:
        """Return securities plus cash market value."""
        return self.imported_market_value + self.cash_market_value

    @property
    def market_value_difference(self) -> Decimal:
        """Return the difference between Schwab and RIMS market value."""
        return (
            self.schwab_market_value
            - self.total_reconciled_market_value
        )

    @property
    def cost_basis_difference(self) -> Decimal:
        """Return the difference between Schwab and RIMS cost basis."""
        return (
            self.schwab_cost_basis
            - self.imported_cost_basis
        )
    @property
    def is_reconciled(self) -> bool:
        """Return True when values reconcile within the import tolerance."""
        reconciliation_tolerance = Decimal("0.10")

        return (
            abs(self.market_value_difference)
            <= reconciliation_tolerance
            and abs(self.cost_basis_difference)
            <= reconciliation_tolerance
        )


def parse_decimal(value: str | None) -> Decimal:
    """Convert a Schwab numeric field into Decimal."""
    if value is None:
        return Decimal("0")

    cleaned_value = (
        value.strip()
        .replace(",", "")
        .replace("$", "")
        .replace("%", "")
    )

    if not cleaned_value or cleaned_value == "--":
        return Decimal("0")

    try:
        return Decimal(cleaned_value)
    except InvalidOperation as exc:
        raise ValueError(
            f"Unable to convert '{value}' to a numeric value."
        ) from exc


def parse_date(value: str | None) -> date | None:
    """Convert a Schwab date string to a date."""
    if value is None:
        return None

    cleaned_value = value.strip()

    if not cleaned_value or cleaned_value in {"--", "N/A"}:
        return None

    for date_format in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(
                cleaned_value,
                date_format,
            ).date()
        except ValueError:
            continue

    raise ValueError(
        f"Unable to convert '{value}' to a valid date."
    )


def find_header_rows(csv_path: Path) -> list[int]:
    """Find every row containing the Schwab position headers."""
    header_rows: list[int] = []

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        rows = csv.reader(csv_file)

        for row_number, row in enumerate(rows):
            normalized_headers = {
                column.strip()
                for column in row
                if column.strip()
            }

            if SCHWAB_REQUIRED_COLUMNS.issubset(normalized_headers):
                header_rows.append(row_number)

    if not header_rows:
        raise ValueError(
            "Unable to locate a supported Schwab position-data "
            "header row."
        )

    return header_rows


def find_header_row(csv_path: Path) -> int:
    """Return the first Schwab position-data header row."""
    return find_header_rows(csv_path)[0]


def classify_row(
    record: dict[str, str],
) -> str:
    """
    Classify a Schwab CSV row.

    Returns:
        "security" for an investment position.
        "cash" for Schwab cash holdings.
        "total" for account subtotal rows.
        "header" for repeated column headers.
        "blank" for empty rows.
        "other" for unrecognized rows.
    """
    symbol = record.get("Symbol", "").strip()

    if not symbol:
        return "blank"

    if symbol == "Symbol":
        return "header"

    if symbol == SCHWAB_CASH_SYMBOL:
        return "cash"

    if symbol == SCHWAB_TOTAL_SYMBOL:
        return "total"

    return "security"


def read_schwab_rows(
    csv_path: Path,
) -> list[dict[str, str]]:
    """
    Read all recognized Schwab position records from a CSV file.

    Repeated column headers, subtotal rows, and blank rows are excluded.
    Cash rows are retained so they can be tracked separately.
    """
    header_rows = find_header_rows(csv_path)

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        rows = list(csv.reader(csv_file))

    records: list[dict[str, str]] = []

    for header_row in header_rows:
        if header_row >= len(rows):
            raise ValueError(
                "Schwab header row is outside the CSV file."
            )

        headers = [
            column.strip()
            for column in rows[header_row]
        ]

        next_header_row = len(rows)

        for candidate_header in header_rows:
            if candidate_header > header_row:
                next_header_row = candidate_header
                break

        for row in rows[header_row + 1:next_header_row]:
            if not any(column.strip() for column in row):
                continue

            padded_row = row + [""] * (
                len(headers) - len(row)
            )

            record = {
                headers[index]: padded_row[index].strip()
                for index in range(len(headers))
                if headers[index]
            }

            row_type = classify_row(record)

            if row_type in {"security", "cash"}:
                records.append(record)

    return records


def holding_from_schwab_record(
    record: dict[str, str],
) -> Holding:
    """Create a Holding object from one Schwab security record."""
    if classify_row(record) != "security":
        raise ValueError(
            "Only security rows can be converted into Holdings."
        )

    return Holding(
        symbol=record["Symbol"],
        description=record.get("Description", ""),
        asset_type=record.get("Asset Type", ""),
        sector=record.get("Sector", ""),
        shares=parse_decimal(
            record.get("Qty (Quantity)")
        ),
        price=parse_decimal(
            record.get("Price")
        ),
        cost_basis=parse_decimal(
            record.get("Cost Basis")
        ),
        dividend_per_share=parse_decimal(
            record.get("Div $")
        ),
        dividend_yield=parse_decimal(
            record.get("Div Yld (Dividend Yield)")
        ),
        dividend_pay_date=parse_date(
            record.get("Div Pay Date")
        ),
        ex_dividend_date=parse_date(
            record.get("Ex-Div (Ex-Dividend Date)")
        ),
    )


def calculate_schwab_totals(
    records: list[dict[str, str]],
) -> tuple[Decimal, Decimal, Decimal]:
    """
    Calculate Schwab totals from recognized position records.

    Returns:
        A tuple containing:
            securities market value
            cash market value
            securities cost basis
    """
    securities_market_value = Decimal("0")
    cash_market_value = Decimal("0")
    securities_cost_basis = Decimal("0")

    for record in records:
        row_type = classify_row(record)

        if row_type == "security":
            securities_market_value += parse_decimal(
                record.get("Mkt Val (Market Value)")
            )
            securities_cost_basis += parse_decimal(
                record.get("Cost Basis")
            )

        elif row_type == "cash":
            cash_market_value += parse_decimal(
                record.get("Mkt Val (Market Value)")
            )

    return (
        securities_market_value,
        cash_market_value,
        securities_cost_basis,
    )


def import_schwab_csv(
    csv_path: str | Path,
    portfolio_name: str = "RIMS Portfolio",
) -> SchwabImportResult:
    """
    Import a Schwab position CSV into RIMS.

    Duplicate securities appearing in multiple Schwab accounts are
    consolidated into a single RIMS Holding.

    Schwab cash is tracked separately and is not treated as a security.

    The source CSV is read only and is never modified.
    """
    path = Path(csv_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Schwab CSV file was not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Schwab CSV path is not a file: {path}"
        )

    records = read_schwab_rows(path)

    if not records:
        raise ValueError(
            "The Schwab CSV contains no recognized position records."
        )

    (
        schwab_security_market_value,
        cash_market_value,
        schwab_cost_basis,
    ) = calculate_schwab_totals(records)

    holdings_by_symbol: dict[str, Holding] = {}

    for record in records:
        if classify_row(record) != "security":
            continue

        holding = holding_from_schwab_record(record)
        symbol = holding.symbol

        if symbol not in holdings_by_symbol:
            holdings_by_symbol[symbol] = holding
            continue

        existing = holdings_by_symbol[symbol]

        existing.shares += holding.shares
        existing.cost_basis += holding.cost_basis

    holdings = list(holdings_by_symbol.values())

    portfolio = Portfolio(
        name=portfolio_name,
        holdings=holdings,
    )

    imported_market_value = portfolio.total_market_value
    imported_cost_basis = portfolio.total_cost_basis

    return SchwabImportResult(
        portfolio=portfolio,
        cash_market_value=cash_market_value,
        schwab_market_value=(
            schwab_security_market_value
            + cash_market_value
        ),
        schwab_cost_basis=schwab_cost_basis,
        imported_market_value=imported_market_value,
        imported_cost_basis=imported_cost_basis,
    )


def main() -> int:
    """Provide a command-line Schwab import and reconciliation test."""
    parser = argparse.ArgumentParser(
        description="Import a Schwab CSV into RIMS."
    )

    parser.add_argument(
        "csv_file",
        type=Path,
        help="Path to the Schwab positions CSV file.",
    )

    args = parser.parse_args()

    result = import_schwab_csv(args.csv_file)
    portfolio = result.portfolio

    print()
    print("RIMS Schwab Import")
    print("=" * 60)
    print(f"Holdings:                 {portfolio.holding_count}")
    print(
        "RIMS securities value:    "
        f"${result.imported_market_value:,.2f}"
    )
    print(
        "Schwab securities value:  "
        f"${result.schwab_market_value - result.cash_market_value:,.2f}"
    )
    print(
        "Schwab cash:              "
        f"${result.cash_market_value:,.2f}"
    )
    print(
        "Schwab total value:       "
        f"${result.schwab_market_value:,.2f}"
    )
    print(
        "RIMS cost basis:          "
        f"${result.imported_cost_basis:,.2f}"
    )
    print(
        "Schwab cost basis:        "
        f"${result.schwab_cost_basis:,.2f}"
    )
    print(
        "Market value difference:  "
        f"${result.market_value_difference:,.2f}"
    )
    print(
        "Cost basis difference:    "
        f"${result.cost_basis_difference:,.2f}"
    )
    print(
        "Forward annual dividend:  "
        f"${portfolio.forward_annual_dividend_income:,.2f}"
    )
    print(
        "Portfolio yield:          "
        f"{portfolio.portfolio_yield:.2f}%"
    )

    print()

    if result.is_reconciled:
        print("RECONCILIATION STATUS:    RECONCILED")
        return 0

    print("RECONCILIATION STATUS:    DIFFERENCE DETECTED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())