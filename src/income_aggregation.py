"""
Historical income aggregation for RIMS.

Sprint 19C establishes the analytical layer above the Schwab income
transaction importer. It combines transactions from multiple accounts
while preserving account-level identity and source-file provenance.

This module does not persist transactions and does not project future
dividend payments. It analyzes actual imported historical transactions.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable, Mapping

from .schwab_income_importer import SchwabIncomeImportResult
from .transaction import (
    IncomeCharacter,
    IncomeType,
    InvestmentTransaction,
)


@dataclass(frozen=True, slots=True)
class IncomeAggregationResult:
    """
    Immutable analytical result for a collection of investment transactions.

    The result retains the underlying transactions so additional analysis
    can be performed without re-importing the Schwab files.
    """

    transactions: tuple[InvestmentTransaction, ...]

    @property
    def transaction_count(self) -> int:
        """Return the total number of imported transactions."""
        return len(self.transactions)

    @property
    def income_transactions(self) -> tuple[InvestmentTransaction, ...]:
        """Return all transactions classified as income."""
        return tuple(transaction for transaction in self.transactions if transaction.is_income)

    @property
    def income_transaction_count(self) -> int:
        """Return the number of income transactions."""
        return len(self.income_transactions)

    @property
    def recurring_income_transactions(self) -> tuple[InvestmentTransaction, ...]:
        """
        Return recurring retirement-income transactions.

        Capital-gain distributions are excluded by the transaction model,
        even if their source action is otherwise classified as recurring.
        """
        return tuple(
            transaction
            for transaction in self.transactions
            if transaction.is_recurring_income
        )

    @property
    def recurring_income_transaction_count(self) -> int:
        """Return the number of recurring retirement-income transactions."""
        return len(self.recurring_income_transactions)

    @property
    def total_income_amount(self) -> Decimal:
        """Return the dollar amount of all income transactions."""
        return sum(
            (transaction.amount for transaction in self.income_transactions),
            Decimal("0"),
        )

    @property
    def recurring_income_amount(self) -> Decimal:
        """Return the dollar amount of recurring retirement income."""
        return sum(
            (transaction.amount for transaction in self.recurring_income_transactions),
            Decimal("0"),
        )

    @property
    def special_income_amount(self) -> Decimal:
        """Return income classified as special."""
        return self._sum_by_character(IncomeCharacter.SPECIAL)

    @property
    def reinvested_income_amount(self) -> Decimal:
        """Return income classified as reinvested."""
        return self._sum_by_character(IncomeCharacter.REINVESTED)

    @property
    def prior_year_income_amount(self) -> Decimal:
        """Return income classified as prior-year income."""
        return self._sum_by_character(IncomeCharacter.PRIOR_YEAR)

    @property
    def income_adjustment_amount(self) -> Decimal:
        """Return income classified as an adjustment."""
        return self._sum_by_character(IncomeCharacter.ADJUSTMENT)

    @property
    def capital_gain_distribution_amount(self) -> Decimal:
        """Return all capital-gain distribution income."""
        return sum(
            (
                transaction.amount
                for transaction in self.income_transactions
                if transaction.is_capital_gain_distribution
            ),
            Decimal("0"),
        )

    def accounts(self) -> tuple[str, ...]:
        """Return distinct account names in deterministic order."""
        return tuple(sorted({transaction.account for transaction in self.transactions}))

    def symbols(self) -> tuple[str, ...]:
        """
        Return distinct security symbols.

        Transactions without a symbol, such as bank interest, are excluded.
        """
        return tuple(
            sorted(
                {
                    transaction.symbol
                    for transaction in self.transactions
                    if transaction.symbol is not None
                }
            )
        )

    def income_by_account(
        self,
        *,
        recurring_only: bool = False,
    ) -> Mapping[str, Decimal]:
        """
        Return income totals grouped by account.

        Args:
            recurring_only: If True, include only recurring retirement income.
                Otherwise include all income transactions.
        """
        transactions = (
            self.recurring_income_transactions
            if recurring_only
            else self.income_transactions
        )

        totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

        for transaction in transactions:
            totals[transaction.account] += transaction.amount

        return dict(sorted(totals.items()))

    def income_by_type(
        self,
        *,
        recurring_only: bool = False,
    ) -> Mapping[IncomeType, Decimal]:
        """
        Return income totals grouped by income type.

        Capital-gain distributions remain visible here even though they are
        excluded from recurring retirement income.
        """
        transactions = (
            self.recurring_income_transactions
            if recurring_only
            else self.income_transactions
        )

        totals: dict[IncomeType, Decimal] = defaultdict(lambda: Decimal("0"))

        for transaction in transactions:
            if transaction.income_type is not None:
                totals[transaction.income_type] += transaction.amount

        return dict(
            sorted(
                totals.items(),
                key=lambda item: item[0].value,
            )
        )

    def income_by_character(self) -> Mapping[IncomeCharacter, Decimal]:
        """Return income totals grouped by income character."""
        totals: dict[IncomeCharacter, Decimal] = defaultdict(lambda: Decimal("0"))

        for transaction in self.income_transactions:
            if transaction.income_character is not None:
                totals[transaction.income_character] += transaction.amount

        return dict(
            sorted(
                totals.items(),
                key=lambda item: item[0].value,
            )
        )

    def income_by_symbol(
        self,
        *,
        recurring_only: bool = False,
    ) -> Mapping[str, Decimal]:
        """
        Return income totals grouped by security symbol.

        Transactions without a symbol are not included in this breakdown.
        """
        transactions = (
            self.recurring_income_transactions
            if recurring_only
            else self.income_transactions
        )

        totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

        for transaction in transactions:
            if transaction.symbol is not None:
                totals[transaction.symbol] += transaction.amount

        return dict(sorted(totals.items()))

    def income_by_year(
        self,
        *,
        recurring_only: bool = False,
    ) -> Mapping[int, Decimal]:
        """
        Return income totals grouped by transaction year.

        The year is based on the parsed Schwab transaction date.
        """
        transactions = (
            self.recurring_income_transactions
            if recurring_only
            else self.income_transactions
        )

        totals: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))

        for transaction in transactions:
            totals[transaction.transaction_date.year] += transaction.amount

        return dict(sorted(totals.items()))

    def income_by_date(
        self,
        *,
        recurring_only: bool = False,
    ) -> Mapping[date, Decimal]:
        """Return income totals grouped by transaction date."""
        transactions = (
            self.recurring_income_transactions
            if recurring_only
            else self.income_transactions
        )

        totals: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))

        for transaction in transactions:
            totals[transaction.transaction_date] += transaction.amount

        return dict(sorted(totals.items()))

    def _sum_by_character(self, character: IncomeCharacter) -> Decimal:
        """Return the amount of income transactions with a given character."""
        return sum(
            (
                transaction.amount
                for transaction in self.income_transactions
                if transaction.income_character == character
            ),
            Decimal("0"),
        )


class IncomeAggregator:
    """
    Combine Schwab income-import results into one analytical dataset.

    The aggregator does not alter the transactions. Account identity,
    source-file provenance, action, amount, and classification remain exactly
    as provided by the imported InvestmentTransaction objects.
    """

    @staticmethod
    def from_transactions(
        transactions: Iterable[InvestmentTransaction],
    ) -> IncomeAggregationResult:
        """
        Create an aggregation result from investment transactions.

        Transactions are sorted deterministically by date, account, symbol,
        action, description, and amount.
        """
        transaction_tuple = tuple(transactions)

        sorted_transactions = tuple(
            sorted(
                transaction_tuple,
                key=lambda transaction: (
                    transaction.transaction_date,
                    transaction.account,
                    transaction.symbol or "",
                    transaction.action,
                    transaction.description,
                    transaction.amount,
                ),
            )
        )

        return IncomeAggregationResult(transactions=sorted_transactions)

    @classmethod
    def from_import_results(
        cls,
        results: Iterable[SchwabIncomeImportResult],
    ) -> IncomeAggregationResult:
        """
        Combine multiple Schwab import results.

        Each imported transaction already contains its account and source
        file, so no account information is inferred or reconstructed here.
        """
        transactions: list[InvestmentTransaction] = []

        for result in results:
            transactions.extend(result.transactions)

        return cls.from_transactions(transactions)

    @classmethod
    def from_files(
        cls,
        files_with_accounts: Iterable[tuple[str, str]],
    ) -> IncomeAggregationResult:
        """
        Import and aggregate multiple Schwab income files.

        Args:
            files_with_accounts: Iterable of
                (CSV path, account name) pairs.

        Returns:
            A consolidated IncomeAggregationResult.
        """
        from .schwab_income_importer import import_schwab_income_files

        transactions = import_schwab_income_files(files_with_accounts)
        return cls.from_transactions(transactions)    

def aggregate_schwab_income(
    files_with_accounts: Iterable[tuple[str, str]],
) -> IncomeAggregationResult:
    """
    Convenience function for aggregating multiple Schwab income files.
    """
    return IncomeAggregator.from_files(files_with_accounts)