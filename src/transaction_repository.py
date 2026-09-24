"""
Repository access for persisted RIMS investment transactions.

Sprint 19F provides a RIMS-level interface for managing and querying
multiple persisted historical transaction datasets.

Sprint 22D extends the repository with controlled append behavior and
deterministic transaction-level duplicate detection.

Sprint 22G extends controlled transaction-dataset provenance by recording
the ImportOperation identifier that created a persisted dataset when
available.

Responsibilities:
    - Register transaction datasets with the repository.
    - Persist datasets through TransactionStore.
    - Discover persisted datasets.
    - Load one or all datasets.
    - Combine transactions across accounts.
    - Filter historical transactions without modifying them.
    - Preserve account and source-file provenance.
    - Preserve originating import-operation provenance when available.
    - Create deterministic transaction identities.
    - Append only previously unseen transactions.

This module does not import Schwab CSV files, classify transactions,
or perform income analysis. Those responsibilities belong to the
importer, transaction model, and analysis layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from .transaction import (
    IncomeCharacter,
    IncomeType,
    InvestmentTransaction,
    TaxCharacter,
    TransactionType,
)
from .transaction_store import TransactionDataset, TransactionStore


@dataclass(frozen=True, slots=True)
class TransactionAppendResult:
    """
    Result of appending a transaction batch while suppressing duplicates.

    transactions_received:
        Number of transactions supplied to the append operation.

    transactions_added:
        Number of previously unseen transactions persisted.

    duplicates_skipped:
        Number of transactions rejected because their identity already
        existed either in persisted history or earlier in the incoming batch.

    dataset_path:
        Path of the newly created dataset when at least one transaction
        was added. None when the entire batch was duplicate.

    dataset_created:
        True when a new dataset was persisted.
    """

    transactions_received: int
    transactions_added: int
    duplicates_skipped: int
    dataset_path: Path | None
    added_transactions: tuple[InvestmentTransaction, ...]

    @property
    def dataset_created(self) -> bool:
        """Return True when a new transaction dataset was created."""
        return self.dataset_path is not None


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

    def find_dataset_by_import_id(
        self,
        import_id: str,
    ) -> TransactionDataset | None:
        """
        Return the persisted transaction dataset created by an import.

        The import identifier is controlled provenance established by the
        controlled transaction import workflow. Legacy datasets without
        import provenance are ignored.

        Returns:
            The matching TransactionDataset, or None when no dataset is
            associated with the supplied import_id.

        Raises:
            ValueError: If import_id is blank or has surrounding whitespace.
        """
        if not isinstance(import_id, str):
            raise TypeError("import_id must be a string.")

        normalized_import_id = import_id.strip()

        if not normalized_import_id:
            raise ValueError("import_id cannot be blank.")

        if import_id != normalized_import_id:
            raise ValueError(
                "import_id cannot have leading or trailing whitespace."
            )

        matches = [
            dataset
            for dataset in self.load_all_datasets()
            if dataset.import_id == normalized_import_id
        ]

        if not matches:
            return None

        if len(matches) > 1:
            raise ValueError(
                "Multiple transaction datasets are associated with "
                f"import_id '{normalized_import_id}'."
            )

        return matches[0]

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
        Return distinct persisted account identifiers in sorted order.
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
        Return distinct persisted security symbols in sorted order.

        Transactions without a symbol are excluded.
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

    @staticmethod
    def transaction_fingerprint(
        transaction: InvestmentTransaction,
    ) -> str:
        """
        Return a deterministic identity for one transaction.

        Source-file provenance is intentionally excluded from the
        fingerprint so that the same financial transaction appearing in
        overlapping Schwab exports is treated as a duplicate.
        """
        if not isinstance(
            transaction,
            InvestmentTransaction,
        ):
            raise TypeError(
                "transaction must be an InvestmentTransaction."
            )

        canonical_data = {
            "account": transaction.account,
            "transaction_date": transaction.transaction_date.isoformat(),
            "action": transaction.action,
            "symbol": transaction.symbol,
            "description": transaction.description,
            "amount": str(transaction.amount),
            "transaction_type": transaction.transaction_type.value,
            "income_type": (
                transaction.income_type.value
                if transaction.income_type is not None
                else None
            ),
            "income_character": (
                transaction.income_character.value
                if transaction.income_character is not None
                else None
            ),
            "tax_character": (
                transaction.tax_character.value
                if transaction.tax_character is not None
                else None
            ),
            "quantity": (
                str(transaction.quantity)
                if transaction.quantity is not None
                else None
            ),
            "price": (
                str(transaction.price)
                if transaction.price is not None
                else None
            ),
            "fees_and_commissions": str(
                transaction.fees_and_commissions
            ),
        }

        payload = json.dumps(
            canonical_data,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return hashlib.sha256(payload).hexdigest()

    def transaction_fingerprints(
        self,
    ) -> frozenset[str]:
        """
        Return fingerprints for all persisted transactions.

        The result is immutable and suitable for duplicate detection.
        """
        return frozenset(
            self.transaction_fingerprint(transaction)
            for transaction in self.all_transactions()
        )

    def append_unique_transactions(
        self,
        dataset_id: str,
        account: str,
        source_file: str,
        transactions: tuple[InvestmentTransaction, ...],
        import_id: str | None = None,
    ) -> TransactionAppendResult:
        """
        Append only transactions not already present in the repository.

        Duplicate detection operates at the transaction level rather than
        the source-file level. This allows a later Schwab export to overlap
        an earlier export without creating duplicate historical transactions.

        Transactions already persisted are skipped.

        Duplicate transactions appearing more than once in the incoming
        batch are also skipped after their first occurrence.

        When at least one new transaction exists, only those new transactions
        are persisted in a new immutable TransactionDataset.

        When every incoming transaction is a duplicate, no new dataset is
        created and dataset_path is None.

        Args:
            import_id:
                Optional ImportOperation identifier associated with the
                controlled import that created the dataset.
        """
        normalized_dataset_id = dataset_id.strip()
        normalized_account = account.strip()
        normalized_source_file = Path(source_file).name.strip()

        if not normalized_dataset_id:
            raise ValueError("dataset_id cannot be blank.")

        if not normalized_account:
            raise ValueError("account cannot be blank.")

        if not normalized_source_file:
            raise ValueError("source_file cannot be blank.")

        if import_id is not None:
            if not isinstance(import_id, str):
                raise TypeError("import_id must be a string or None.")

            if not import_id.strip():
                raise ValueError("import_id cannot be blank.")

            if import_id != import_id.strip():
                raise ValueError(
                    "import_id cannot have leading or trailing whitespace."
                )

        if not isinstance(transactions, tuple):
            raise TypeError(
                "transactions must be a tuple of InvestmentTransaction."
            )

        for transaction in transactions:
            if not isinstance(transaction, InvestmentTransaction):
                raise TypeError(
                    "transactions must contain only "
                    "InvestmentTransaction objects."
                )

            if transaction.account != normalized_account:
                raise ValueError(
                    "transaction account does not match the supplied account."
                )

            if transaction.source_file != normalized_source_file:
                raise ValueError(
                    "transaction source_file does not match the supplied "
                    "source_file."
                )

        existing_fingerprints = self.transaction_fingerprints()

        new_transactions: list[InvestmentTransaction] = []
        seen_in_batch: set[str] = set()
        duplicates_skipped = 0

        for transaction in transactions:
            fingerprint = self.transaction_fingerprint(transaction)

            if (
                fingerprint in existing_fingerprints
                or fingerprint in seen_in_batch
            ):
                duplicates_skipped += 1
                continue

            seen_in_batch.add(fingerprint)
            new_transactions.append(transaction)

        if not new_transactions:
            return TransactionAppendResult(
                transactions_received=len(transactions),
                transactions_added=0,
                duplicates_skipped=duplicates_skipped,
                dataset_path=None,
                added_transactions=(),
            )

        dataset = TransactionDataset(
            dataset_id=normalized_dataset_id,
            account=normalized_account,
            source_file=normalized_source_file,
            transactions=tuple(new_transactions),
            import_id=import_id,
        )

        dataset_path = self.save_dataset(dataset)

        return TransactionAppendResult(
            transactions_received=len(transactions),
            transactions_added=len(new_transactions),
            duplicates_skipped=duplicates_skipped,
            dataset_path=dataset_path,
            added_transactions=tuple(new_transactions),
        )
