"""
Purpose:
    Provide persistent storage and retrieval for RIMS historical Snapshots.

Responsibilities:
    - Save historical Snapshots as JSON files.
    - Load previously saved Snapshots.
    - List available Snapshot dates.
    - Prevent accidental overwriting of existing Snapshots.
    - Reconstruct Snapshot and Holding objects from stored data.

Dependencies:
    Python standard library only.
    RIMS Snapshot and Holding entities.

Revision History:
    0.2.0 - Initial historical Snapshot storage implementation.

Author:
    RIMS Development Team
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.holding import Holding
from src.snapshot import Snapshot


class SnapshotStore:
    """
    Manage persistent storage of RIMS historical Snapshots.

    Snapshots are stored as individual JSON files using the Snapshot
    date as the filename.
    """

    def __init__(self, storage_path: str | Path) -> None:
        """
        Initialize the Snapshot store.

        Args:
            storage_path: Directory where Snapshot files are stored.
        """
        self.storage_path = Path(storage_path)

    def _snapshot_path(self, snapshot_date: date) -> Path:
        """Return the filesystem path for a Snapshot date."""
        return self.storage_path / f"{snapshot_date.isoformat()}.json"

    def save(
        self,
        snapshot: Snapshot,
        overwrite: bool = False,
    ) -> Path:
        """
        Save a Snapshot to persistent JSON storage.

        Args:
            snapshot: Snapshot to save.
            overwrite: Allow replacement of an existing Snapshot
                when True.

        Returns:
            Path to the saved Snapshot file.

        Raises:
            TypeError: If snapshot is not a Snapshot.
            FileExistsError: If the Snapshot already exists and
                overwrite is False.
        """
        if not isinstance(snapshot, Snapshot):
            raise TypeError("SnapshotStore requires a Snapshot.")

        self.storage_path.mkdir(parents=True, exist_ok=True)

        path = self._snapshot_path(snapshot.snapshot_date)

        if path.exists() and not overwrite:
            raise FileExistsError(
                f"Snapshot already exists: {path}"
            )

        data = self._serialize(snapshot)

        with path.open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=2,
                sort_keys=True,
            )
            file.write("\n")

        return path

    def load(self, snapshot_date: date) -> Snapshot:
        """
        Load a Snapshot from persistent storage.

        Raises:
            FileNotFoundError: If no Snapshot exists for the date.
        """
        path = self._snapshot_path(snapshot_date)

        if not path.exists():
            raise FileNotFoundError(
                f"Snapshot not found: {path}"
            )

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return self._deserialize(data)

    def list_dates(self) -> list[date]:
        """
        Return all available Snapshot dates in chronological order.
        """
        if not self.storage_path.exists():
            return []

        dates: list[date] = []

        for path in self.storage_path.glob("*.json"):
            try:
                dates.append(
                    date.fromisoformat(path.stem)
                )
            except ValueError:
                continue

        return sorted(dates)

    @staticmethod
    def _serialize(snapshot: Snapshot) -> dict[str, Any]:
        """Convert a Snapshot into JSON-compatible data."""

        data = snapshot.to_dict()

        def convert(value: Any) -> Any:
            if isinstance(value, Decimal):
                return str(value)

            if isinstance(value, date):
                return value.isoformat()

            if isinstance(value, dict):
                return {
                    key: convert(item)
                    for key, item in value.items()
                }

            if isinstance(value, list):
                return [convert(item) for item in value]

            return value

        return convert(data)

    @staticmethod
    def _deserialize(data: dict[str, Any]) -> Snapshot:
        """Reconstruct a Snapshot from stored JSON data."""

        holdings = []

        for holding_data in data["holdings"]:
            holdings.append(
                Holding(
                    symbol=holding_data["symbol"],
                    description=holding_data["description"],
                    asset_type=holding_data["asset_type"],
                    sector=holding_data["sector"],
                    shares=Decimal(holding_data["shares"]),
                    price=Decimal(holding_data["price"]),
                    cost_basis=Decimal(holding_data["cost_basis"]),
                    dividend_per_share=Decimal(
                        holding_data["dividend_per_share"]
                    ),
                    dividend_yield=Decimal(
                        holding_data["dividend_yield"]
                    ),
                    dividend_pay_date=(
                        date.fromisoformat(
                            holding_data["dividend_pay_date"]
                        )
                        if holding_data["dividend_pay_date"]
                        else None
                    ),
                    ex_dividend_date=(
                        date.fromisoformat(
                            holding_data["ex_dividend_date"]
                        )
                        if holding_data["ex_dividend_date"]
                        else None
                    ),
                    market_value=Decimal(
                        holding_data["market_value"]
                    ),
                )
            )

        return Snapshot(
            snapshot_date=date.fromisoformat(
                data["snapshot_date"]
            ),
            portfolio_name=data["portfolio_name"],
            holdings=holdings,
            cash_market_value=Decimal(
                data["cash_market_value"]
            ),
        )