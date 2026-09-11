"""
Repository access for persisted RIMS investment transactions.

Sprint 19F provides a RIMS-level interface for managing and querying
multiple persisted historical transaction datasets.

Responsibilities:
    - Register transaction datasets with the repository.
    - Persist datasets through TransactionStore.
    - Discover persisted datasets.
    - Load one or all datasets.
    - Combine transactions across accounts.
    - Filter historical transactions without modifying them.
    - Preserve account and source-file provenance.

This module does not import Schwab CSV files, classify transactions,
or perform income analysis. Those responsibilities belong to the
importer, transaction model, and analysis layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from .transaction import (
    IncomeType,
    InvestmentTransaction,
    TransactionType,
)
from .transaction_store import TransactionDataset, TransactionStore


@dataclass(frozen=True, slots=True)
class TransactionRepository:
    """
    Repository for persisted historical investment transactions.

    The repository is backed by TransactionStore and treats persisted
    datasets as historical records that should not be modified silently.
    """

    store: TransactionStore

    @classmethod
    def from_path(cls, storage_path: str | Path) -> TransactionRepository:
        """
        Create a repository backed by the supplied storage directory.
        """
        return cls(store=TransactionStore(storage_path))

    def save_dataset(
        self,
        dataset: TransactionDataset,
        overwrite: bool = False,
    ) -> Path:
        """
        Persist one transaction dataset through the underlying store.

        Existing datasets are protected unless overwrite=True is
        explicitly supplied.
        """
        return self.store.save(dataset, overwrite=overwrite)

    def load_dataset(self, dataset_id: str) -> TransactionDataset:
        """
        Load one persisted transaction dataset.

        Structural or value errors in persisted data are surfaced as a
        repository-level ValueError rather than exposing implementation-
        specific errors such as KeyError.
        """
        try:
            return self.store.load(dataset_id)
        except FileNotFoundError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid transaction dataset '{dataset_id}': {exc}"
            ) from exc

    def dataset_ids(self) -> tuple[str, ...]:
        """
        Return all persisted dataset identifiers in deterministic order.
        """
        return tuple(self.store.list_datasets())

    def load_all_datasets(self) -> tuple[TransactionDataset, ...]:
        """
        Load all persisted datasets in dataset-id order.
        """
        return tuple(
            self.load_dataset(dataset_id)
            for dataset_id in self.dataset_ids()
        )

    def all_transactions(self) -> tuple[InvestmentTransaction, ...]:
        """
        Return all persisted transactions in chronological order.

        Transactions with the same date retain deterministic ordering based
        on dataset identifier and their original order within each dataset.
        """
        transactions: list[tuple[str, int, InvestmentTransaction]] = []

        for dataset in self.load_all_datasets():
            for index, transaction in enumerate(dataset.transactions):
                transactions.append(
                    (dataset.dataset_id, index, transaction)
                )

        transactions.sort(
            key=lambda item: (
                item[2].transaction_date,
                item[0],
                item[1],
            )
        )

        return tuple(
            transaction
            for _, _, transaction in transactions
        )

    def transactions_by_account(
        self,
        account: str,
    ) -> tuple[InvestmentTransaction, ...]:
        """
        Return persisted transactions for one account.
        """
        normalized_account = account.strip()

        if not normalized_account:
            raise ValueError("account cannot be blank.")

        return tuple(
            transaction
            for transaction in self.all_transactions()
            if transaction.account == normalized_account
        )

    def transactions_by_symbol(
        self,
        symbol: str,
    ) -> tuple[InvestmentTransaction, ...]:
        """
        Return persisted transactions for one security symbol.

        Symbol matching is case-insensitive.
        """
        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("symbol cannot be blank.")

        return tuple(
            transaction
            for transaction in self.all_transactions()
            if (
                transaction.symbol is not None
                and transaction.symbol.upper() == normalized_symbol
            )
        )

    def transactions_by_date_range(
        self,
        start_date: date,
        end_date: date,
    ) -> tuple[InvestmentTransaction, ...]:
        """
        Return transactions whose dates fall within an inclusive range.
        """
        if not isinstance(start_date, date):
            raise TypeError("start_date must be a date.")

        if not isinstance(end_date, date):
            raise TypeError("end_date must be a date.")

        if start_date > end_date:
            raise ValueError(
                "start_date cannot be later than end_date."
            )

        return tuple(
            transaction
            for transaction in self.all_transactions()
            if start_date
            <= transaction.transaction_date
            <= end_date
        )

    def transactions_by_income_type(
        self,
        income_type: IncomeType,
    ) -> tuple[InvestmentTransaction, ...]:
        """
        Return income transactions matching the supplied income type.
        """
        if not isinstance(income_type, IncomeType):
            raise TypeError(
                "income_type must be an IncomeType."
            )

        return tuple(
            transaction
            for transaction in self.all_transactions()
            if transaction.income_type == income_type
        )

    def transactions_by_transaction_type(
        self,
        transaction_type: TransactionType,
    ) -> tuple[InvestmentTransaction, ...]:
        """
        Return transactions matching the supplied transaction type.
        """
        if not isinstance(transaction_type, TransactionType):
            raise TypeError(
                "transaction_type must be a TransactionType."
            )

        return tuple(
            transaction
            for transaction in self.all_transactions()
            if transaction.transaction_type == transaction_type
        )

    def income_transactions(
        self,
    ) -> tuple[InvestmentTransaction, ...]:
        """
        Return all persisted income transactions.
        """
        return tuple(
            transaction
            for transaction in self.all_transactions()
            if transaction.is_income
        )

    def recurring_income_transactions(
        self,
    ) -> tuple[InvestmentTransaction, ...]:
        """
        Return all persisted recurring income transactions.
        """
        return tuple(
            transaction
            for transaction in self.all_transactions()
            if transaction.is_recurring_income
        )

    def total_income(
        self,
    ) -> Decimal:
        """
        Return the total amount of all persisted income transactions.
        """
        return sum(
            (
                transaction.amount
                for transaction in self.income_transactions()
            ),
            Decimal("0"),
        )

    def total_recurring_income(
        self,
    ) -> Decimal:
        """
        Return the total amount of all persisted recurring income.
        """
        return sum(
            (
                transaction.amount
                for transaction in self.recurring_income_transactions()
            ),
            Decimal("0"),
        )

    def accounts(self) -> tuple[str, ...]:
        """
        Return all accounts represented in persisted transaction history.
        """
        return tuple(
            sorted(
                {
                    transaction.account
                    for transaction in self.all_transactions()
                }
            )
        )

    def symbols(self) -> tuple[str, ...]:
        """
        Return all non-null security symbols represented in the history.
        """
        return tuple(
            sorted(
                {
                    transaction.symbol
                    for transaction in self.all_transactions()
                    if transaction.symbol is not None
                }
            )
        )