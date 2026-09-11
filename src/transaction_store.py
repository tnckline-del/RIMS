"""
Persistent storage for RIMS investment transactions.

Sprint 19E provides durable storage and retrieval for the normalized
InvestmentTransaction model created in Sprint 19A.

Responsibilities:
    - Save transaction datasets as JSON.
    - Load previously saved transaction datasets.
    - List available transaction datasets.
    - Preserve Decimal and date values exactly.
    - Preserve enum classifications.
    - Preserve account and source-file provenance.
    - Prevent accidental overwriting of existing datasets.

This module does not import Schwab CSV files and does not perform
income analysis. Those responsibilities belong to the importer and
analysis layers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from .transaction import (
    IncomeCharacter,
    IncomeType,
    InvestmentTransaction,
    TaxCharacter,
    TransactionType,
)


@dataclass(frozen=True, slots=True)
class TransactionDataset:
    """
    Metadata and transactions for one persisted historical dataset.
    """

    dataset_id: str
    account: str
    source_file: str
    transactions: tuple[InvestmentTransaction, ...]

    @property
    def transaction_count(self) -> int:
        """Return the number of transactions in the dataset."""
        return len(self.transactions)

    @property
    def start_date(self) -> date | None:
        """Return the earliest transaction date, if transactions exist."""
        if not self.transactions:
            return None

        return min(
            transaction.transaction_date
            for transaction in self.transactions
        )

    @property
    def end_date(self) -> date | None:
        """Return the latest transaction date, if transactions exist."""
        if not self.transactions:
            return None

        return max(
            transaction.transaction_date
            for transaction in self.transactions
        )


class TransactionStore:
    """
    Manage persistent storage of historical investment transactions.

    Each dataset is stored as one JSON file identified by dataset_id.
    Existing datasets cannot be overwritten unless overwrite=True is
    explicitly supplied.
    """

    FILE_SUFFIX = ".json"

    def __init__(self, storage_path: str | Path) -> None:
        """
        Initialize the transaction store.

        Args:
            storage_path: Directory where transaction datasets are stored.
        """
        self.storage_path = Path(storage_path)

    def _dataset_path(self, dataset_id: str) -> Path:
        """Return the filesystem path for a dataset identifier."""
        self._validate_dataset_id(dataset_id)
        return self.storage_path / f"{dataset_id}{self.FILE_SUFFIX}"

    def save(
        self,
        dataset: TransactionDataset,
        overwrite: bool = False,
    ) -> Path:
        """
        Save a transaction dataset as JSON.

        Args:
            dataset: TransactionDataset to persist.
            overwrite: Explicitly allow replacement of an existing dataset.

        Returns:
            Path to the saved dataset.

        Raises:
            TypeError: If dataset is not a TransactionDataset.
            FileExistsError: If the dataset already exists and overwrite
                is False.
            ValueError: If dataset metadata is invalid.
        """
        if not isinstance(dataset, TransactionDataset):
            raise TypeError(
                "TransactionStore requires a TransactionDataset."
            )

        self._validate_dataset(dataset)

        self.storage_path.mkdir(parents=True, exist_ok=True)

        path = self._dataset_path(dataset.dataset_id)

        if path.exists() and not overwrite:
            raise FileExistsError(
                f"Transaction dataset already exists: {path}"
            )

        data = self._serialize(dataset)

        with path.open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=2,
                sort_keys=True,
            )
            file.write("\n")

        return path

    def load(self, dataset_id: str) -> TransactionDataset:
        """
        Load a transaction dataset from persistent storage.

        Raises:
            FileNotFoundError: If the requested dataset does not exist.
        """
        path = self._dataset_path(dataset_id)

        if not path.exists():
            raise FileNotFoundError(
                f"Transaction dataset not found: {path}"
            )

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return self._deserialize(data)

    def list_datasets(self) -> list[str]:
        """
        Return available dataset identifiers in deterministic order.
        """
        if not self.storage_path.exists():
            return []

        dataset_ids: list[str] = []

        for path in self.storage_path.glob(
            f"*{self.FILE_SUFFIX}"
        ):
            dataset_ids.append(path.stem)

        return sorted(dataset_ids)

    def delete(self, dataset_id: str) -> None:
        """
        Delete a persisted dataset explicitly.

        This operation is intentionally separate from save() so that
        normal imports can never silently destroy historical data.
        """
        path = self._dataset_path(dataset_id)

        if not path.exists():
            raise FileNotFoundError(
                f"Transaction dataset not found: {path}"
            )

        path.unlink()

    @staticmethod
    def _validate_dataset_id(dataset_id: str) -> None:
        """Validate a dataset identifier before using it as a filename."""
        if not isinstance(dataset_id, str):
            raise TypeError("dataset_id must be a string.")

        if not dataset_id.strip():
            raise ValueError("dataset_id cannot be blank.")

        if dataset_id != dataset_id.strip():
            raise ValueError(
                "dataset_id cannot have leading or trailing whitespace."
            )

        if "/" in dataset_id or "\\" in dataset_id:
            raise ValueError(
                "dataset_id cannot contain path separators."
            )

        if dataset_id in {".", ".."}:
            raise ValueError(
                "dataset_id cannot be a filesystem navigation name."
            )

    @staticmethod
    def _validate_dataset(dataset: TransactionDataset) -> None:
        """Validate dataset metadata and transaction contents."""
        if not dataset.dataset_id.strip():
            raise ValueError("dataset_id cannot be blank.")

        if not dataset.account.strip():
            raise ValueError("account cannot be blank.")

        if not dataset.source_file.strip():
            raise ValueError("source_file cannot be blank.")

        for transaction in dataset.transactions:
            if not isinstance(
                transaction,
                InvestmentTransaction,
            ):
                raise TypeError(
                    "All dataset entries must be InvestmentTransaction "
                    "objects."
                )

            if transaction.account != dataset.account:
                raise ValueError(
                    "All transactions must belong to the dataset account."
                )

            if transaction.source_file != dataset.source_file:
                raise ValueError(
                    "All transactions must have the dataset source_file."
                )

    @staticmethod
    def _serialize(
        dataset: TransactionDataset,
    ) -> dict[str, Any]:
        """Convert a TransactionDataset into JSON-compatible data."""
        return {
            "dataset_id": dataset.dataset_id,
            "account": dataset.account,
            "source_file": dataset.source_file,
            "transaction_count": dataset.transaction_count,
            "start_date": (
                dataset.start_date.isoformat()
                if dataset.start_date
                else None
            ),
            "end_date": (
                dataset.end_date.isoformat()
                if dataset.end_date
                else None
            ),
            "transactions": [
                TransactionStore._serialize_transaction(transaction)
                for transaction in dataset.transactions
            ],
        }

    @staticmethod
    def _serialize_transaction(
        transaction: InvestmentTransaction,
    ) -> dict[str, Any]:
        """Convert one InvestmentTransaction into JSON-compatible data."""
        data = transaction.to_dict()

        return TransactionStore._convert_value(data)

    @staticmethod
    def _convert_value(value: Any) -> Any:
        """Recursively convert Decimal and date values for JSON."""
        if isinstance(value, Decimal):
            return str(value)

        if isinstance(value, date):
            return value.isoformat()

        if isinstance(value, dict):
            return {
                key: TransactionStore._convert_value(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple)):
            return [
                TransactionStore._convert_value(item)
                for item in value
            ]

        return value

    @staticmethod
    def _deserialize(
        data: dict[str, Any],
    ) -> TransactionDataset:
        """Reconstruct a TransactionDataset from stored JSON data."""
        transactions = tuple(
            TransactionStore._deserialize_transaction(
                transaction_data
            )
            for transaction_data in data["transactions"]
        )

        dataset = TransactionDataset(
            dataset_id=data["dataset_id"],
            account=data["account"],
            source_file=data["source_file"],
            transactions=transactions,
        )

        TransactionStore._validate_dataset(dataset)

        stored_count = data.get("transaction_count")

        if stored_count != dataset.transaction_count:
            raise ValueError(
                "Stored transaction_count does not match transaction data."
            )

        return dataset

    @staticmethod
    def _deserialize_transaction(
        data: dict[str, Any],
    ) -> InvestmentTransaction:
        """Reconstruct an InvestmentTransaction from stored JSON."""
        return InvestmentTransaction(
            account=data["account"],
            transaction_date=date.fromisoformat(
                data["transaction_date"]
            ),
            action=data["action"],
            symbol=data.get("symbol"),
            description=data["description"],
            amount=Decimal(data["amount"]),
            transaction_type=TransactionType(
                data["transaction_type"]
            ),
            income_type=(
                IncomeType(data["income_type"])
                if data.get("income_type") is not None
                else None
            ),
            income_character=(
                IncomeCharacter(data["income_character"])
                if data.get("income_character") is not None
                else None
            ),
            tax_character=(
                TaxCharacter(data["tax_character"])
                if data.get("tax_character") is not None
                else None
            ),
            quantity=(
                Decimal(data["quantity"])
                if data.get("quantity") is not None
                else None
            ),
            price=(
                Decimal(data["price"])
                if data.get("price") is not None
                else None
            ),
            fees_and_commissions=Decimal(
                data["fees_and_commissions"]
            ),
            source_file=data.get("source_file"),
        )


def dataset_from_transactions(
    dataset_id: str,
    account: str,
    source_file: str,
    transactions: Iterable[InvestmentTransaction],
) -> TransactionDataset:
    """
    Create a TransactionDataset from an iterable of transactions.

    The transactions are stored in their supplied order. The transaction
    model itself remains unchanged.
    """
    return TransactionDataset(
        dataset_id=dataset_id,
        account=account,
        source_file=source_file,
        transactions=tuple(transactions),
    )