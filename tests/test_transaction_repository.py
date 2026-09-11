"""
Automated tests for the RIMS transaction repository.

Sprint 19G validates repository behavior, filtering, error handling,
and protection of persisted historical transaction data.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.transaction import (
    IncomeCharacter,
    IncomeType,
    InvestmentTransaction,
    TaxCharacter,
    TransactionType,
)
from src.transaction_repository import TransactionRepository
from src.transaction_store import dataset_from_transactions


class TestTransactionRepository(unittest.TestCase):
    """Test TransactionRepository behavior."""

    ACCOUNT = "Test Account"
    SOURCE_FILE = "test.csv"

    def setUp(self) -> None:
        """Create an isolated temporary repository for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = TransactionRepository.from_path(
            Path(self.temp_dir.name)
        )

    def tearDown(self) -> None:
        """Remove the isolated repository."""
        self.temp_dir.cleanup()

    def make_transaction(
        self,
        transaction_date: date,
        symbol: str | None,
        amount: str,
        action: str = "Cash Dividend",
        income_type: IncomeType = IncomeType.DIVIDEND,
        income_character: IncomeCharacter = IncomeCharacter.RECURRING,
    ) -> InvestmentTransaction:
        """Create a valid test transaction."""
        return InvestmentTransaction(
            account=self.ACCOUNT,
            transaction_date=transaction_date,
            action=action,
            symbol=symbol,
            description="Test transaction",
            amount=Decimal(amount),
            transaction_type=TransactionType.INCOME,
            income_type=income_type,
            income_character=income_character,
            tax_character=TaxCharacter.UNKNOWN,
            source_file=self.SOURCE_FILE,
        )

    def save_dataset(
        self,
        dataset_id: str = "test-dataset",
        transactions: tuple[InvestmentTransaction, ...] | None = None,
    ) -> None:
        """Persist a test dataset."""
        if transactions is None:
            transactions = (
                self.make_transaction(
                    date(2025, 1, 15),
                    "AAA",
                    "100.00",
                ),
                self.make_transaction(
                    date(2025, 2, 15),
                    "BBB",
                    "200.00",
                ),
                self.make_transaction(
                    date(2025, 3, 15),
                    None,
                    "50.00",
                ),
            )

        dataset = dataset_from_transactions(
            dataset_id,
            self.ACCOUNT,
            self.SOURCE_FILE,
            transactions,
        )
        self.repo.save_dataset(dataset)

    def test_empty_repository(self) -> None:
        """An empty repository returns empty collections and zero totals."""
        self.assertEqual(self.repo.dataset_ids(), ())
        self.assertEqual(self.repo.load_all_datasets(), ())
        self.assertEqual(self.repo.all_transactions(), ())
        self.assertEqual(self.repo.income_transactions(), ())
        self.assertEqual(self.repo.recurring_income_transactions(), ())
        self.assertEqual(self.repo.accounts(), ())
        self.assertEqual(self.repo.symbols(), ())
        self.assertEqual(self.repo.total_income(), Decimal("0"))
        self.assertEqual(
            self.repo.total_recurring_income(),
            Decimal("0"),
        )

    def test_account_filter(self) -> None:
        """Account filtering returns only matching transactions."""
        self.save_dataset()

        transactions = self.repo.transactions_by_account(
            self.ACCOUNT
        )

        self.assertEqual(len(transactions), 3)
        self.assertTrue(
            all(
                transaction.account == self.ACCOUNT
                for transaction in transactions
            )
        )

    def test_blank_account_filter_rejected(self) -> None:
        """Blank account filters are rejected."""
        self.save_dataset()

        with self.assertRaises(ValueError):
            self.repo.transactions_by_account("")

        with self.assertRaises(ValueError):
            self.repo.transactions_by_account("   ")

    def test_symbol_filter_is_case_insensitive(self) -> None:
        """Symbol filtering is case-insensitive."""
        self.save_dataset()

        transactions = self.repo.transactions_by_symbol("aaa")

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].symbol, "AAA")

    def test_blank_symbol_filter_rejected(self) -> None:
        """Blank symbol filters are rejected."""
        with self.assertRaises(ValueError):
            self.repo.transactions_by_symbol("")

        with self.assertRaises(ValueError):
            self.repo.transactions_by_symbol("   ")

    def test_date_range_is_inclusive(self) -> None:
        """Date-range filtering includes both endpoints."""
        self.save_dataset()

        transactions = self.repo.transactions_by_date_range(
            date(2025, 1, 15),
            date(2025, 2, 15),
        )

        self.assertEqual(len(transactions), 2)

    def test_invalid_date_range_rejected(self) -> None:
        """Reversed date ranges are rejected."""
        with self.assertRaises(ValueError):
            self.repo.transactions_by_date_range(
                date(2025, 3, 1),
                date(2025, 2, 1),
            )

    def test_invalid_date_types_rejected(self) -> None:
        """Non-date range arguments are rejected."""
        with self.assertRaises(TypeError):
            self.repo.transactions_by_date_range(
                "2025-01-01",  # type: ignore[arg-type]
                date(2025, 2, 1),
            )

        with self.assertRaises(TypeError):
            self.repo.transactions_by_date_range(
                date(2025, 1, 1),
                "2025-02-01",  # type: ignore[arg-type]
            )

    def test_income_type_filter(self) -> None:
        """Income-type filtering returns matching transactions."""
        self.save_dataset()

        transactions = self.repo.transactions_by_income_type(
            IncomeType.DIVIDEND
        )

        self.assertEqual(len(transactions), 3)

    def test_invalid_income_type_rejected(self) -> None:
        """Invalid income types are rejected."""
        with self.assertRaises(TypeError):
            self.repo.transactions_by_income_type(
                "Dividend"  # type: ignore[arg-type]
            )

    def test_transaction_type_filter(self) -> None:
        """Transaction-type filtering returns matching transactions."""
        self.save_dataset()

        transactions = self.repo.transactions_by_transaction_type(
            TransactionType.INCOME
        )

        self.assertEqual(len(transactions), 3)

    def test_invalid_transaction_type_rejected(self) -> None:
        """Invalid transaction types are rejected."""
        with self.assertRaises(TypeError):
            self.repo.transactions_by_transaction_type(
                "Income"  # type: ignore[arg-type]
            )

    def test_income_totals(self) -> None:
        """Income totals are calculated correctly."""
        self.save_dataset()

        self.assertEqual(
            self.repo.total_income(),
            Decimal("350.00"),
        )
        self.assertEqual(
            self.repo.total_recurring_income(),
            Decimal("350.00"),
        )

    def test_special_income_excluded_from_recurring(self) -> None:
        """Special income remains income but is excluded from recurring."""
        recurring = self.make_transaction(
            date(2025, 1, 15),
            "AAA",
            "100.00",
        )
        special = self.make_transaction(
            date(2025, 2, 15),
            "AAA",
            "50.00",
            action="Special Dividend",
            income_character=IncomeCharacter.SPECIAL,
        )

        self.save_dataset(
            transactions=(recurring, special)
        )

        self.assertEqual(
            self.repo.total_income(),
            Decimal("150.00"),
        )
        self.assertEqual(
            self.repo.total_recurring_income(),
            Decimal("100.00"),
        )

    def test_transactions_are_chronologically_ordered(self) -> None:
        """Combined transactions are returned in chronological order."""
        transactions = (
            self.make_transaction(
                date(2025, 3, 15),
                "AAA",
                "300.00",
            ),
            self.make_transaction(
                date(2025, 1, 15),
                "AAA",
                "100.00",
            ),
            self.make_transaction(
                date(2025, 2, 15),
                "AAA",
                "200.00",
            ),
        )

        self.save_dataset(transactions=transactions)

        dates = [
            transaction.transaction_date
            for transaction in self.repo.all_transactions()
        ]

        self.assertEqual(
            dates,
            [
                date(2025, 1, 15),
                date(2025, 2, 15),
                date(2025, 3, 15),
            ],
        )

    def test_duplicate_dataset_is_rejected(self) -> None:
        """Saving an existing dataset without overwrite is rejected."""
        self.save_dataset()

        dataset = self.repo.load_dataset("test-dataset")

        with self.assertRaises(FileExistsError):
            self.repo.save_dataset(dataset)

    def test_corrupt_json_is_rejected_clearly(self) -> None:
        """Malformed persisted JSON raises a repository-level error."""
        path = Path(self.temp_dir.name) / "corrupt.json"
        path.write_text(
            '{"dataset_id": "corrupt",',
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            self.repo.load_dataset("corrupt")

    def test_missing_required_json_data_is_rejected(self) -> None:
        """Structurally invalid JSON raises a repository-level error."""
        path = Path(self.temp_dir.name) / "invalid.json"
        path.write_text(
            json.dumps({"dataset_id": "invalid"}),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            self.repo.load_dataset("invalid")

    def test_source_provenance_is_preserved(self) -> None:
        """Source-file provenance survives repository loading."""
        self.save_dataset()

        transactions = self.repo.all_transactions()

        self.assertEqual(
            len(transactions),
            3,
        )
        self.assertTrue(
            all(
                transaction.source_file == self.SOURCE_FILE
                for transaction in transactions
            )
        )


if __name__ == "__main__":
    unittest.main()