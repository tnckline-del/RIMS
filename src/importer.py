"""
Purpose:
    Import Schwab position CSV files into RIMS.

Responsibilities:
    - Parse Schwab account sections.
    - Identify security and cash rows.
    - Convert Schwab values to RIMS data types.
    - Create Holding objects.
    - Consolidate duplicate securities across accounts.
    - Preserve Schwab market value as the authoritative market value.
    - Calculate Schwab totals for reconciliation.
    - Provide a command-line import test.

Dependencies:
    Python standard library only.

Revision History:
    0.2.0 - Initial Schwab CSV importer.
    0.2.0 - Added authoritative Schwab market value support.

Author:
    RIMS Development Team
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
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
    "Div Pay Date",
    "Ex-Div (Ex-Dividend Date)",
    "Asset Type",
}


@dataclass(slots=True)
class SchwabImportResult:
    """
    Store the results of a Schwab CSV import.
    """

    portfolio: Portfolio
    cash_market_value: Decimal
    schwab_market_value: Decimal
    schwab_cost_basis: Decimal
    imported_market_value: Decimal
    imported_cost_basis: Decimal

    @property
    def total_reconciled_market_value(self) -> Decimal:
        """Return imported securities plus Schwab cash."""
        return self.imported_market_value + self.cash_market_value

    @property
    def market_value_difference(self) -> Decimal:
        """
        Return the difference between RIMS securities market value and
        Schwab securities market value.
        """
        return self.imported_market_value - self.schwab_market_value

    @property
    def cost_basis_difference(self) -> Decimal:
        """
        Return the difference between RIMS and Schwab cost basis.
        """
        return self.imported_cost_basis - self.schwab_cost_basis

    @property
    def is_reconciled(self) -> bool:
        """
        Return True when market value and cost basis differences are
        within the temporary reconciliation tolerance.
        """
        tolerance = Decimal("0.10")

        return (
            abs(self.market_value_difference) <= tolerance
            and abs(self.cost_basis_difference) <= tolerance
        )


def parse_decimal(value: str | None) -> Decimal:
    """
    Convert a Schwab numeric field to Decimal.

    Handles:
        - commas
        - dollar signs
        - percent signs
        - '--'
        - blank values
        - None
        - parenthesized negative values
    """
    if value is None:
        return Decimal("0")

    cleaned = value.strip()

    if not cleaned or cleaned in {"--", "N/A"}:
        return Decimal("0")

    negative = cleaned.startswith("(") and cleaned.endswith(")")

    if negative:
        cleaned = cleaned[1:-1]

    cleaned = (
        cleaned
        .replace(",", "")
        .replace("$", "")
        .replace("%", "")
        .strip()
    )

    if not cleaned:
        return Decimal("0")

    result = Decimal(cleaned)

    return -result if negative else result


def parse_date(value: str | None) -> date | None:
    """
    Convert a Schwab date field to a Python date.

    Supported formats:
        MM/DD/YYYY
        MM/DD/YY
    """
    if value is None:
        return None

    cleaned = value.strip()

    if not cleaned or cleaned in {"--", "N/A"}:
        return None

    for date_format in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(cleaned, date_format).date()
        except ValueError:
            continue

    raise ValueError(f"Unable to parse Schwab date: {value!r}")


def find_header_rows(rows: list[list[str]]) -> list[int]:
    """
    Find all Schwab header rows.

    Schwab repeats the column header for each account section.
    """
    header_rows: list[int] = []

    for index, row in enumerate(rows):
        row_values = {cell.strip() for cell in row if cell.strip()}

        if SCHWAB_REQUIRED_COLUMNS.issubset(row_values):
            header_rows.append(index)

    return header_rows


def find_header_row(rows: list[list[str]]) -> int:
    """
    Return the first Schwab header row.

    Raises:
        ValueError: If no valid Schwab header is found.
    """
    header_rows = find_header_rows(rows)

    if not header_rows:
        raise ValueError("No valid Schwab header row found.")

    return header_rows[0]


def classify_row(row: dict[str, str]) -> str:
    """
    Classify a Schwab CSV row.

    Returns:
        security
        cash
        total
        header
        blank
        other
    """
    symbol = row.get("Symbol", "").strip()
    description = row.get("Description", "").strip()

    # Completely blank row.
    if not symbol and not description:
        return "blank"

    # Repeated Schwab column header.
    if symbol == "Symbol":
        return "header"

    # Schwab cash row. Depending on the CSV section, Schwab may place
    # the cash description in either Symbol or Description.
    if (
        symbol == "Cash & Cash Investments"
        or description == "Cash & Cash Investments"
    ):
        return "cash"

    # Schwab positions total row. Depending on the CSV section,
    # "Positions Total" may appear in either Symbol or Description.
    if (
        symbol == "Positions Total"
        or description == "Positions Total"
    ):
        return "total"

    # Other non-security summary rows.
    if symbol in {
        "Account Total",
        "Total",
    }:
        return "total"

    # A normal security has a symbol.
    if symbol:
        return "security"

    return "other"

def read_schwab_rows(
    csv_path: str | Path,
) -> tuple[list[dict[str, str]], Decimal]:
    """
    Read Schwab security and cash rows from all account sections.

    Returns:
        security_rows, cash_market_value
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Schwab CSV not found: {csv_path}")

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        rows = list(csv.reader(file))

    header_rows = find_header_rows(rows)

    if not header_rows:
        raise ValueError("No Schwab position headers found.")

    security_rows: list[dict[str, str]] = []
    cash_market_value = Decimal("0")

    for header_index in header_rows:
        header = [
            cell.strip()
            for cell in rows[header_index]
        ]

        next_header_index = next(
            (
                index
                for index in header_rows
                if index > header_index
            ),
            len(rows),
        )

        for raw_row in rows[header_index + 1 : next_header_index]:
            padded_row = raw_row + [""] * (
                len(header) - len(raw_row)
            )

            row = {
                header[index]: padded_row[index].strip()
                for index in range(len(header))
                if header[index]
            }

            row_type = classify_row(row)

            if row_type == "security":
                security_rows.append(row)

            elif row_type == "cash":
                cash_market_value += parse_decimal(
                    row.get("Mkt Val (Market Value)")
                )

    return security_rows, cash_market_value


def holding_from_schwab_record(row: dict[str, str]) -> Holding:
    """
    Convert one Schwab security row into a Holding.
    """
    return Holding(
        symbol=row.get("Symbol", "").strip(),
        description=row.get("Description", "").strip(),
        asset_type=row.get("Asset Type", "").strip(),
        sector=row.get("Sector", "").strip(),
        shares=parse_decimal(row.get("Qty (Quantity)")),
        price=parse_decimal(row.get("Price")),
        cost_basis=parse_decimal(row.get("Cost Basis")),
        market_value=parse_decimal(
            row.get("Mkt Val (Market Value)")
        ),
        dividend_per_share=parse_decimal(
            row.get("Div $")
        ),
        dividend_yield=parse_decimal(
            row.get("Div Yld (Dividend Yield)")
        ),
        dividend_pay_date=parse_date(
            row.get("Div Pay Date")
        ),
        ex_dividend_date=parse_date(
            row.get("Ex-Div (Ex-Dividend Date)")
        ),
    )


def calculate_schwab_totals(
    rows: list[dict[str, str]],
) -> tuple[Decimal, Decimal]:
    """
    Calculate Schwab security market value and cost basis totals
    directly from imported security rows.
    """
    market_value = Decimal("0")
    cost_basis = Decimal("0")

    for row in rows:
        market_value += parse_decimal(
            row.get("Mkt Val (Market Value)")
        )
        cost_basis += parse_decimal(
            row.get("Cost Basis")
        )

    return market_value, cost_basis


def import_schwab_csv(
    csv_path: str | Path,
    portfolio_name: str = "Schwab Portfolio",
) -> SchwabImportResult:
    """
    Import a Schwab CSV into a RIMS Portfolio.

    Duplicate securities appearing in multiple Schwab accounts are
    consolidated into one Holding.

    Schwab's market value is authoritative and is summed across
    duplicate security records.
    """
    rows, cash_market_value = read_schwab_rows(csv_path)

    portfolio = Portfolio(name=portfolio_name)

    for row in rows:
        holding = holding_from_schwab_record(row)

        try:
            existing = portfolio.get_holding(holding.symbol)
        except KeyError:
            existing = None

        if existing is None:
            portfolio.add_holding(holding)
            continue

        # Consolidate duplicate symbols across Schwab accounts.
        existing.shares += holding.shares
        existing.cost_basis += holding.cost_basis

        # Schwab market value is authoritative.
        existing.market_value += holding.market_value

        # Dividend information is based on the security, so retain
        # the latest imported per-share dividend and yield.
        existing.dividend_per_share = holding.dividend_per_share
        existing.dividend_yield = holding.dividend_yield
        existing.dividend_pay_date = holding.dividend_pay_date
        existing.ex_dividend_date = holding.ex_dividend_date

    schwab_market_value, schwab_cost_basis = (
        calculate_schwab_totals(rows)
    )

    imported_market_value = portfolio.total_market_value
    imported_cost_basis = portfolio.total_cost_basis

    return SchwabImportResult(
        portfolio=portfolio,
        cash_market_value=cash_market_value,
        schwab_market_value=schwab_market_value,
        schwab_cost_basis=schwab_cost_basis,
        imported_market_value=imported_market_value,
        imported_cost_basis=imported_cost_basis,
    )


def main() -> int:
    """
    Run the Schwab import from the command line.
    """
    if len(sys.argv) != 2:
        print(
            "Usage: python3 -m src.importer "
            "<schwab_csv_path>"
        )
        return 1

    csv_path = sys.argv[1]

    try:
        result = import_schwab_csv(csv_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print()
    print("RIMS Schwab Import")
    print("=" * 60)
    print(
        f"Holdings:                 "
        f"{result.portfolio.holding_count}"
    )
    print(
        f"RIMS securities value:    "
        f"${result.imported_market_value:,.2f}"
    )
    print(
        f"Schwab securities value:  "
        f"${result.schwab_market_value:,.2f}"
    )
    print(
        f"Schwab cash:              "
        f"${result.cash_market_value:,.2f}"
    )
    print(
        f"Schwab total value:       "
        f"${result.total_reconciled_market_value:,.2f}"
    )
    print(
        f"RIMS cost basis:          "
        f"${result.imported_cost_basis:,.2f}"
    )
    print(
        f"Schwab cost basis:        "
        f"${result.schwab_cost_basis:,.2f}"
    )
    print(
        f"Market value difference:  "
        f"${result.market_value_difference:,.2f}"
    )
    print(
        f"Cost basis difference:    "
        f"${result.cost_basis_difference:,.2f}"
    )
    print(
        f"Forward annual dividend:  "
        f"${result.portfolio.forward_annual_dividend_income:,.2f}"
    )
    print(
        f"Portfolio yield:          "
        f"{result.portfolio.portfolio_yield:.2f}%"
    )
    print()
    print(
        "RECONCILIATION STATUS:    "
        + (
            "RECONCILED"
            if result.is_reconciled
            else "DIFFERENCE DETECTED"
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())