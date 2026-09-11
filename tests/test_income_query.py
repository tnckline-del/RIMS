"""
Automated tests for the RIMS historical income query service.

Sprint 19H validates repository-backed historical income queries without
forecasting, annualization, or investment recommendations.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.income_query import IncomeQuery
from src.transaction import (
    IncomeCharacter,
    IncomeType,
    InvestmentTransaction,
    TaxCharacter,
    TransactionType,
)
from src.transaction_repository import TransactionRepository
from src.transaction_store import dataset_from_transactions


class TestIncomeQuery(unittest.TestCase):
    """Test IncomeQuery behavior."""

    ACCOUNT = "Test Account"
    SOURCE_FILE = "test.csv"

    def setUp(self) -> None:
        """Create an isolated repository and query service."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = TransactionRepository.from_path(
            Path(self.temp_dir.name)
        )
        self.query = IncomeQuery(self.repository)

    def tearDown(self) -> None:
        """Remove the isolated repository."""
        self.temp_dir.cleanup()

    def make_transaction(
        self,
        transaction_date: date,
        symbol: str | None,
        amount: str,
        *,
        income_type: IncomeType = IncomeType.DIVIDEND,
        income_character: IncomeCharacter = IncomeCharacter.RECURRING,
        action: str = "Cash Dividend",
    ) -> InvestmentTransaction:
        """Create a valid income transaction."""
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

    def save_transactions(
        self,
        transactions: tuple[InvestmentTransaction, ...],
    ) -> None:
        """Persist test transactions."""
        dataset = dataset_from_transactions(
            "test-dataset",
            self.ACCOUNT,
            self.SOURCE_FILE,
            transactions,
        )
        self.repository.save_dataset(dataset)

    def test_empty_repository(self) -> None:
        """Empty repository returns zero for all income totals."""
        self.assertEqual(
            self.query.total_income(),
            Decimal("0"),
        )
        self.assertEqual(
            self.query.total_recurring_income(),
            Decimal("0"),
        )
        self.assertEqual(
            self.query.total_special_income(),
            Decimal("0"),
        )
        self.assertEqual(
            self.query.total_reinvested_income(),
            Decimal("0"),
        )
        self.assertEqual(
            self.query.total_prior_year_income(),
            Decimal("0"),
        )
        self.assertEqual(
            self.query.total_income_adjustments(),
            Decimal("0"),
        )
        self.assertEqual(
            self.query.total_capital_gain_distributions(),
            Decimal("0"),
        )

    def test_income_by_account(self) -> None:
        """Account query returns total historical income."""
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
        )

        self.save_transactions(transactions)

        self.assertEqual(
            self.query.income_by_account(self.ACCOUNT),
            Decimal("300.00"),
        )

    def test_recurring_income_by_account(self) -> None:
        """Recurring-only account query excludes special income."""
        transactions = (
            self.make_transaction(
                date(2025, 1, 15),
                "AAA",
                "100.00",
            ),
            self.make_transaction(
                date(2025, 2, 15),
                "AAA",
                "50.00",
                income_character=IncomeCharacter.SPECIAL,
                action="Special Dividend",
            ),
        )

        self.save_transactions(transactions)

        self.assertEqual(
            self.query.income_by_account(
                self.ACCOUNT,
                recurring_only=True,
            ),
            Decimal("100.00"),
        )

    def test_income_by_symbol_is_case_insensitive(self) -> None:
        """Symbol queries are case-insensitive."""
        transactions = (
            self.make_transaction(
                date(2025, 1, 15),
                "AAA",
                "125.00",
            ),
        )

        self.save_transactions(transactions)

        self.assertEqual(
            self.query.income_by_symbol("aaa"),
            Decimal("125.00"),
        )

    def test_income_by_income_type(self) -> None:
        """Income-type queries return the correct amount."""
        transactions = (
            self.make_transaction(
                date(2025, 1, 15),
                "AAA",
                "100.00",
                income_type=IncomeType.DIVIDEND,
            ),
            self.make_transaction(
                date(2025, 2, 15),
                None,
                "25.00",
                income_type=IncomeType.INTEREST,
                action="Bank Interest",
            ),
        )

        self.save_transactions(transactions)

        self.assertEqual(
            self.query.income_by_income_type(
                IncomeType.DIVIDEND
            ),
            Decimal("100.00"),
        )
        self.assertEqual(
            self.query.income_by_income_type(
                IncomeType.INTEREST
            ),
            Decimal("25.00"),
        )

    def test_income_by_date_range_is_inclusive(self) -> None:
        """Date-range queries include both endpoints."""
        transactions = (
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
            self.make_transaction(
                date(2025, 3, 15),
                "AAA",
                "300.00",
            ),
        )

        self.save_transactions(transactions)

        self.assertEqual(
            self.query.income_by_date_range(
                date(2025, 1, 15),
                date(2025, 2, 15),
            ),
            Decimal("300.00"),
        )

    def test_income_by_year(self) -> None:
        """Year query returns income based on transaction date."""
        transactions = (
            self.make_transaction(
                date(2025, 1, 15),
                "AAA",
                "100.00",
            ),
            self.make_transaction(
                date(2026, 1, 15),
                "AAA",
                "250.00",
            ),
        )

        self.save_transactions(transactions)

        self.assertEqual(
            self.query.income_by_year(2025),
            Decimal("100.00"),
        )
        self.assertEqual(
            self.query.income_by_year(2026),
            Decimal("250.00"),
        )

    def test_recurring_income_by_year(self) -> None:
        """Recurring year query excludes special income."""
        transactions = (
            self.make_transaction(
                date(2025, 1, 15),
                "AAA",
                "100.00",
            ),
            self.make_transaction(
                date(2025, 6, 15),
                "AAA",
                "50.00",
                income_character=IncomeCharacter.SPECIAL,
                action="Special Dividend",
            ),
        )

        self.save_transactions(transactions)

        self.assertEqual(
            self.query.income_by_year(
                2025,
                recurring_only=True,
            ),
            Decimal("100.00"),
        )

    def test_special_income_by_year(self) -> None:
        """Special income is separately queryable."""
        transactions = (
            self.make_transaction(
                date(2025, 1, 15),
                "AAA",
                "100.00",
            ),
            self.make_transaction(
                date(2025, 6, 15),
                "AAA",
                "35.00",
                income_character=IncomeCharacter.SPECIAL,
                action="Special Dividend",
            ),
        )

        self.save_transactions(transactions)

        self.assertEqual(
            self.query.special_income_by_year(2025),
            Decimal("35.00"),
        )

    def test_reinvested_income_by_year(self) -> None:
        """Reinvested income remains income."""
        transactions = (
            self.make_transaction(
                date(2025, 3, 15),
                "AAA",
                "75.00",
                income_character=IncomeCharacter.REINVESTED,
                action="Reinvest Dividend",
            ),
        )

        self.save_transactions(transactions)

        self.assertEqual(
            self.query.reinvested_income_by_year(2025),
            Decimal("75.00"),
        )
        self.assertEqual(
            self.query.income_by_year(2025),
            Decimal("75.00"),
        )

    def test_prior_year_income_by_year(self) -> None:
        """Prior-year income is separately queryable."""
        transactions = (
            self.make_transaction(
                date(2026, 3, 15),
                "AAA",
                "40.00",
                income_character=IncomeCharacter.PRIOR_YEAR,
                action="Pr Yr Cash Div",
            ),
        )

        self.save_transactions(transactions)

        self.assertEqual(
            self.query.prior_year_income_by_year(2026),
            Decimal("40.00"),
        )

    def test_income_adjustments_by_year(self) -> None:
        """Income adjustments are separately queryable."""
        transactions = (
            self.make_transaction(
                date(2026, 4, 15),
                "AAA",
                "-12.00",
                income_character=IncomeCharacter.ADJUSTMENT,
                action="Div Adjustment",
            ),
        )

        self.save_transactions(transactions)

        self.assertEqual(
            self.query.income_adjustments_by_year(2026),
            Decimal("-12.00"),
        )

    def test_capital_gain_distributions_by_year(self) -> None:
        """Capital-gain distributions remain visible but are not recurring."""
        transactions = (
            self.make_transaction(
                date(2025, 12, 15),
                "AAA",
                "20.00",
                income_type=IncomeType.CAPITAL_GAIN_DISTRIBUTION,
                income_character=IncomeCharacter.RECURRING,
                action="Long Term Cap Gain",
            ),
        )

        self.save_transactions(transactions)

        self.assertEqual(
            self.query.capital_gain_distributions_by_year(2025),
            Decimal("20.00"),
        )
        self.assertEqual(
            self.query.income_by_year(2025),
            Decimal("20.00"),
        )
        self.assertEqual(
            self.query.income_by_year(
                2025,
                recurring_only=True,
            ),
            Decimal("0"),
        )

    def test_reinvest_shares_are_not_double_counted(self) -> None:
        """Reinvest Shares does not add a second income amount."""
        dividend = self.make_transaction(
            date(2025, 5, 15),
            "AAA",
            "50.00",
            income_character=IncomeCharacter.REINVESTED,
            action="Reinvest Dividend",
        )

        reinvest_shares = InvestmentTransaction(
            account=self.ACCOUNT,
            transaction_date=date(2025, 5, 15),
            action="Reinvest Shares",
            symbol="AAA",
            description="Test reinvest shares",
            amount=Decimal("-50.00"),
            transaction_type=TransactionType.PURCHASE,
            quantity=Decimal("1"),
            price=Decimal("50"),
            source_file=self.SOURCE_FILE,
        )

        self.save_transactions(
            (
                dividend,
                reinvest_shares,
            )
        )

        self.assertEqual(
            self.query.total_income(),
            Decimal("50.00"),
        )

    def test_invalid_year_rejected(self) -> None:
        """Non-integer years are rejected."""
        with self.assertRaises(TypeError):
            self.query.income_by_year(
                "2025"  # type: ignore[arg-type]
            )

        with self.assertRaises(TypeError):
            self.query.special_income_by_year(
                "2025"  # type: ignore[arg-type]
            )

    def test_invalid_date_range_is_rejected(self) -> None:
        """Invalid date ranges are rejected by the repository."""
        with self.assertRaises(TypeError):
            self.query.income_by_date_range(
                "2025-01-01",  # type: ignore[arg-type]
                date(2025, 2, 1),
            )

        with self.assertRaises(ValueError):
            self.query.income_by_date_range(
                date(2025, 3, 1),
                date(2025, 2, 1),
            )


if __name__ == "__main__":
    unittest.main()