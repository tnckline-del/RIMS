"""
Purpose:
    Import Schwab Dividends & Interest transaction exports into RIMS.

Responsibilities:
    - Read Schwab Dividends & Interest CSV exports.
    - Preserve account-level transaction identity.
    - Preserve Schwab's original transaction action.
    - Convert Schwab transactions into InvestmentTransaction objects.
    - Classify dividend, interest, capital-gain, and other income.
    - Classify recurring, special, reinvested, prior-year, and adjustment income.
    - Preserve qualified and non-qualified tax character when identifiable.
    - Preserve Schwab transaction quantities, prices, and fees when available.
    - Preserve the source filename for auditability.
    - Support importing one file or multiple account files.

Dependencies:
    Python standard library only.
    RIMS src.transaction module.

Revision History:
    0.2.0 - Initial Schwab Dividends & Interest importer.

Author:
    RIMS Development Team
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.transaction import (
    IncomeCharacter,
    IncomeType,
    InvestmentTransaction,
    TaxCharacter,
    TransactionType,
)


@dataclass(frozen=True, slots=True)
class SchwabIncomeImportResult:
    """Result of importing one Schwab Dividends & Interest file."""

    source_file: str
    account: str
    transactions: tuple[InvestmentTransaction, ...]

    @property
    def transaction_count(self) -> int:
        """Return the number of imported transactions."""

        return len(self.transactions)

    @property
    def income_transactions(self) -> tuple[InvestmentTransaction, ...]:
        """Return transactions classified as investment income."""

        return tuple(
            transaction
            for transaction in self.transactions
            if transaction.is_income
        )

    @property
    def income_transaction_count(self) -> int:
        """Return the number of income transactions."""

        return len(self.income_transactions)

    @property
    def recurring_income_transactions(
        self,
    ) -> tuple[InvestmentTransaction, ...]:
        """Return transactions classified as recurring income."""

        return tuple(
            transaction
            for transaction in self.transactions
            if transaction.is_recurring_income
        )

    @property
    def recurring_income_amount(self) -> Decimal:
        """Return the total amount classified as recurring income."""

        return sum(
            (
                transaction.amount
                for transaction in self.recurring_income_transactions
            ),
            Decimal("0"),
        )


def parse_decimal(value: str | None) -> Decimal | None:
    """
    Parse a Schwab numeric value into Decimal.

    Schwab may use blank fields when a value is unavailable.
    """

    if value is None:
        return None

    cleaned = value.strip()

    if not cleaned or cleaned == "--":
        return None

    cleaned = cleaned.replace("$", "").replace(",", "")

    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(
            f"Unable to parse Schwab numeric value: {value!r}"
        ) from exc


def parse_transaction_date(value: str | None) -> date:
    """
    Parse the transaction date from a Schwab date field.

    Schwab may append text such as:

        08/17/2026 as of 08/15/2026

    The transaction date is the first date in the field.
    """

    if value is None:
        raise ValueError("Schwab transaction date is required.")

    cleaned = value.strip()

    if not cleaned:
        raise ValueError("Schwab transaction date is required.")

    match = re.match(r"^(\d{1,2}/\d{1,2}/\d{2,4})", cleaned)

    if match is None:
        raise ValueError(
            f"Unable to parse Schwab transaction date: {value!r}"
        )

    date_text = match.group(1)

    for date_format in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(
                date_text,
                date_format,
            ).date()
        except ValueError:
            continue

    raise ValueError(
        f"Unable to parse Schwab transaction date: {value!r}"
    )


def normalize_header(value: str | None) -> str:
    """Normalize a CSV header for reliable comparison."""

    if value is None:
        return ""

    return " ".join(value.strip().split())


def find_transaction_header(rows: list[list[str]]) -> int:
    """
    Locate the Schwab transaction-table header row.

    The current Schwab Dividends & Interest export normally begins
    directly with the header, but searching makes the importer tolerant
    of introductory rows in future exports.
    """

    required_columns = {
        "Date",
        "Action",
        "Symbol",
        "Description",
        "Quantity",
        "Price",
        "Fees & Comm",
        "Amount",
    }

    for index, row in enumerate(rows):
        normalized = {
            normalize_header(value)
            for value in row
        }

        if required_columns.issubset(normalized):
            return index

    raise ValueError(
        "Could not locate the Schwab transaction header row."
    )


def _header_mapping(header: list[str]) -> dict[str, int]:
    """Create a normalized header-to-column-index mapping."""

    mapping: dict[str, int] = {}

    for index, value in enumerate(header):
        normalized = normalize_header(value)

        if normalized:
            mapping[normalized] = index

    return mapping


def _get_value(
    row: list[str],
    mapping: dict[str, int],
    column: str,
) -> str:
    """Return a value from a Schwab row by normalized column name."""

    index = mapping.get(column)

    if index is None or index >= len(row):
        return ""

    return row[index].strip()


def classify_transaction(
    action: str,
) -> tuple[
    TransactionType,
    IncomeType | None,
    IncomeCharacter | None,
    TaxCharacter | None,
]:
    """
    Classify a Schwab transaction action.

    The original Schwab action is preserved separately on the transaction.
    This function assigns the RIMS analytical classifications.
    """

    normalized = " ".join(
        action.strip().split()
    ).lower()

    dividend_actions = {
        "cash dividend": (
            IncomeType.DIVIDEND,
            IncomeCharacter.RECURRING,
            TaxCharacter.UNKNOWN,
        ),
        "qualified dividend": (
            IncomeType.DIVIDEND,
            IncomeCharacter.RECURRING,
            TaxCharacter.QUALIFIED,
        ),
        "non-qualified div": (
            IncomeType.DIVIDEND,
            IncomeCharacter.RECURRING,
            TaxCharacter.NON_QUALIFIED,
        ),
        "special dividend": (
            IncomeType.DIVIDEND,
            IncomeCharacter.SPECIAL,
            TaxCharacter.UNKNOWN,
        ),
        "special qual div": (
            IncomeType.DIVIDEND,
            IncomeCharacter.SPECIAL,
            TaxCharacter.QUALIFIED,
        ),
        "special non qual div": (
            IncomeType.DIVIDEND,
            IncomeCharacter.SPECIAL,
            TaxCharacter.NON_QUALIFIED,
        ),
        "reinvest dividend": (
            IncomeType.DIVIDEND,
            IncomeCharacter.REINVESTED,
            TaxCharacter.UNKNOWN,
        ),
        "pr yr cash div": (
            IncomeType.DIVIDEND,
            IncomeCharacter.PRIOR_YEAR,
            TaxCharacter.UNKNOWN,
        ),
        "pr yr non-qual div": (
            IncomeType.DIVIDEND,
            IncomeCharacter.PRIOR_YEAR,
            TaxCharacter.NON_QUALIFIED,
        ),
        "div adjustment": (
            IncomeType.DIVIDEND,
            IncomeCharacter.ADJUSTMENT,
            TaxCharacter.UNKNOWN,
        ),
        "non-qual div adj": (
            IncomeType.DIVIDEND,
            IncomeCharacter.ADJUSTMENT,
            TaxCharacter.NON_QUALIFIED,
        ),
    }

    if normalized in dividend_actions:
        income_type, character, tax_character = (
            dividend_actions[normalized]
        )

        return (
            TransactionType.INCOME,
            income_type,
            character,
            tax_character,
        )

    interest_actions = {
        "bond interest": (
            IncomeType.INTEREST,
            IncomeCharacter.RECURRING,
            TaxCharacter.ORDINARY,
        ),
        "bank interest": (
            IncomeType.INTEREST,
            IncomeCharacter.RECURRING,
            TaxCharacter.ORDINARY,
        ),
    }

    if normalized in interest_actions:
        income_type, character, tax_character = (
            interest_actions[normalized]
        )

        return (
            TransactionType.INCOME,
            income_type,
            character,
            tax_character,
        )

    capital_gain_actions = {
        "long term cap gain": IncomeCharacter.RECURRING,
        "short term cap gain": IncomeCharacter.RECURRING,
        "long term cap gain reinvest": IncomeCharacter.REINVESTED,
        "short term cap gain reinvest": IncomeCharacter.REINVESTED,
    }

    if normalized in capital_gain_actions:
        return (
            TransactionType.INCOME,
            IncomeType.CAPITAL_GAIN_DISTRIBUTION,
            capital_gain_actions[normalized],
            TaxCharacter.UNKNOWN,
        )

    if normalized == "reinvest shares":
        return (
            TransactionType.PURCHASE,
            None,
            None,
            None,
        )

    return (
        TransactionType.OTHER,
        None,
        None,
        None,
    )


def transaction_from_schwab_row(
    row: list[str],
    mapping: dict[str, int],
    account: str,
    source_file: str,
) -> InvestmentTransaction:
    """Convert one Schwab transaction row into an InvestmentTransaction."""

    transaction_date = parse_transaction_date(
        _get_value(row, mapping, "Date")
    )

    action = _get_value(row, mapping, "Action")
    symbol = _get_value(row, mapping, "Symbol")
    description = _get_value(row, mapping, "Description")

    amount = parse_decimal(
        _get_value(row, mapping, "Amount")
    )

    if amount is None:
        amount = Decimal("0")

    quantity = parse_decimal(
        _get_value(row, mapping, "Quantity")
    )

    price = parse_decimal(
        _get_value(row, mapping, "Price")
    )

    fees = parse_decimal(
        _get_value(row, mapping, "Fees & Comm")
    )

    if fees is None:
        fees = Decimal("0")

    transaction_type, income_type, income_character, tax_character = (
        classify_transaction(action)
    )

    return InvestmentTransaction(
        account=account,
        transaction_date=transaction_date,
        action=action,
        symbol=symbol or None,
        description=description,
        amount=amount,
        transaction_type=transaction_type,
        income_type=income_type,
        income_character=income_character,
        tax_character=tax_character,
        quantity=quantity,
        price=price,
        fees_and_commissions=fees,
        source_file=source_file,
    )


def import_schwab_income_csv(
    csv_path: str | Path,
    account: str,
) -> SchwabIncomeImportResult:
    """
    Import one Schwab Dividends & Interest CSV file.

    Account identity is supplied explicitly because Schwab's transaction
    CSV does not contain the account name.

    All rows are preserved as InvestmentTransaction objects. Unsupported
    actions are classified as Other rather than silently discarded.
    """

    path = Path(csv_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Schwab transaction file not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Schwab transaction path is not a file: {path}"
        )

    account = account.strip()

    if not account:
        raise ValueError(
            "Schwab account name cannot be blank."
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        rows = list(csv.reader(file))

    if not rows:
        raise ValueError(
            f"Schwab transaction file is empty: {path}"
        )

    header_index = find_transaction_header(rows)

    header = rows[header_index]
    mapping = _header_mapping(header)

    transactions: list[InvestmentTransaction] = []

    for row in rows[header_index + 1 :]:
        if not any(value.strip() for value in row):
            continue

        date_value = _get_value(row, mapping, "Date")

        if not date_value:
            continue

        transactions.append(
            transaction_from_schwab_row(
                row=row,
                mapping=mapping,
                account=account,
                source_file=path.name,
            )
        )

    return SchwabIncomeImportResult(
        source_file=path.name,
        account=account,
        transactions=tuple(transactions),
    )


def import_schwab_income_files(
    files_with_accounts: list[tuple[str | Path, str]]
    | tuple[tuple[str | Path, str], ...],
) -> tuple[InvestmentTransaction, ...]:
    """
    Import multiple Schwab Dividends & Interest files.

    Each item must contain:

        (csv_path, account)

    Transactions from all supplied account files are combined while
    retaining account identity and source filename.
    """

    transactions: list[InvestmentTransaction] = []

    for csv_path, account in files_with_accounts:
        result = import_schwab_income_csv(
            csv_path=csv_path,
            account=account,
        )

        transactions.extend(result.transactions)

    return tuple(transactions)


def main() -> None:
    """
    Provide a simple command-line import validation.

    Usage:

        python3 -m src.schwab_income_importer FILE ACCOUNT
    """

    import sys

    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: python3 -m src.schwab_income_importer "
            "<schwab_csv> <account>"
        )

    result = import_schwab_income_csv(
        csv_path=sys.argv[1],
        account=sys.argv[2],
    )

    print(f"Source file: {result.source_file}")
    print(f"Account: {result.account}")
    print(f"Transactions: {result.transaction_count}")
    print(
        f"Income transactions: "
        f"{result.income_transaction_count}"
    )
    print(
        "Recurring income amount: "
        f"${result.recurring_income_amount:,.2f}"
    )


if __name__ == "__main__":
    main()