"""
Real-data integration test for Sprint 19I.

This test connects:
    - The current Schwab all-account positions export.
    - The persisted historical RIMS transaction repository.
    - The Sprint 19I income/portfolio reconciliation service.

The test is read-only. It does not modify source CSV files or the
historical transaction repository.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from decimal import Decimal

from src.importer import import_schwab_csv
from src.income_portfolio import IncomePortfolio
from src.transaction_repository import TransactionRepository


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CURRENT_POSITIONS_FILE = (
    Path.home()
    / "Downloads"
    / "All-Accounts-Positions-2026-09-07-173949.csv"
)

TRANSACTION_REPOSITORY_PATH = PROJECT_ROOT / "data" / "transactions"


class TestIncomePortfolioIntegration(unittest.TestCase):
    """Validate Sprint 19I against the user's real RIMS data."""

    @classmethod
    def setUpClass(cls) -> None:
        if not CURRENT_POSITIONS_FILE.exists():
            raise FileNotFoundError(
                f"Current Schwab positions file not found: "
                f"{CURRENT_POSITIONS_FILE}"
            )

        if not TRANSACTION_REPOSITORY_PATH.exists():
            raise FileNotFoundError(
                f"Transaction repository not found: "
                f"{TRANSACTION_REPOSITORY_PATH}"
            )

        import_result = import_schwab_csv(
            CURRENT_POSITIONS_FILE,
            portfolio_name="RIMS Integration Test Portfolio",
        )

        repository = TransactionRepository.from_path(
            TRANSACTION_REPOSITORY_PATH
        )

        cls.portfolio = import_result.portfolio
        cls.repository = repository

        cls.result = IncomePortfolio(
            portfolio=cls.portfolio,
            transactions=repository.all_transactions(),
        ).reconcile()

    def test_current_portfolio_contains_expected_number_of_holdings(
        self,
    ) -> None:
        self.assertEqual(
            len(self.portfolio.holdings),
            44,
        )

    def test_historical_transaction_count_is_preserved(self) -> None:
        self.assertEqual(
            len(self.repository.all_transactions()),
            779,
        )

    def test_historical_income_count_is_preserved(self) -> None:
        self.assertEqual(
            len(self.repository.income_transactions()),
            751,
        )

    def test_historical_recurring_income_is_preserved(self) -> None:
        self.assertEqual(
            self.repository.total_recurring_income(),
            Decimal("65533.10"),
        )

    def test_reconciliation_has_current_holdings(self) -> None:
        current_holdings = (
            self.result.current_holdings_with_history
            + self.result.current_holdings_without_history
        )

        self.assertGreater(
            len(current_holdings),
            0,
        )

    def test_reconciliation_has_historical_symbols(self) -> None:
        historical_symbols = (
            self.result.current_holdings_with_history
            + self.result.historical_symbols_not_currently_held
        )

        self.assertGreater(
            len(historical_symbols),
            0,
        )

    def test_income_reconciliation_components_are_decimal(self) -> None:
        self.assertIsInstance(
            self.result.total_historical_income_from_current_holdings,
            Decimal,
        )
        self.assertIsInstance(
            self.result.total_recurring_income_from_current_holdings,
            Decimal,
        )
        self.assertIsInstance(
            self.result.total_historical_income_from_no_longer_held,
            Decimal,
        )
        self.assertIsInstance(
            self.result.total_symbolless_historical_income,
            Decimal,
        )

    def test_current_holding_categories_do_not_overlap(self) -> None:
        with_history = set(
            self.result.current_holdings_with_history
        )
        without_history = set(
            self.result.current_holdings_without_history
        )

        self.assertTrue(
            with_history.isdisjoint(without_history)
        )

    def test_historical_not_currently_held_is_disjoint_from_current(
        self,
    ) -> None:
        current_symbols = set(
            self.result.current_holdings_with_history
            + self.result.current_holdings_without_history
        )

        historical_not_held = set(
            self.result.historical_symbols_not_currently_held
        )

        self.assertTrue(
            current_symbols.isdisjoint(historical_not_held)
        )

    def test_current_holding_income_totals_are_non_negative(self) -> None:
        self.assertGreaterEqual(
            self.result.total_historical_income_from_current_holdings,
            Decimal("0"),
        )
        self.assertGreaterEqual(
            self.result.total_recurring_income_from_current_holdings,
            Decimal("0"),
        )

    def test_recurring_income_does_not_exceed_total_income(self) -> None:
        self.assertLessEqual(
            self.result.total_recurring_income_from_current_holdings,
            self.result.total_historical_income_from_current_holdings,
        )

    def test_symbolless_income_is_not_assigned_to_a_security(self) -> None:
        self.assertNotIn(
            None,
            self.result.historical_income_by_current_holding,
        )
        self.assertNotIn(
            "",
            self.result.historical_income_by_current_holding,
        )

    def test_reconciliation_does_not_modify_repository_transactions(
        self,
    ) -> None:
        transactions_before = self.repository.all_transactions()

        IncomePortfolio(
            portfolio=self.portfolio,
            transactions=transactions_before,
        ).reconcile()

        transactions_after = self.repository.all_transactions()

        self.assertEqual(
            transactions_before,
            transactions_after,
        )


if __name__ == "__main__":
    unittest.main()