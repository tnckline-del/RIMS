"""
Purpose:
    Orchestrate the RIMS historical portfolio analysis workflow.

Responsibilities:
    - Create historical snapshots from portfolios.
    - Persist snapshots through SnapshotStore.
    - Load stored historical snapshots.
    - Compare historical snapshots.
    - Generate human-readable historical reports.
    - Keep orchestration separate from core business logic.

Dependencies:
    Python standard library.
    RIMS Portfolio, Snapshot, SnapshotStore, SnapshotComparison,
    and SnapshotReport classes.

Revision History:
    0.2.0 - Initial historical analysis orchestration capability.

Author:
    RIMS Development Team
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from .portfolio import Portfolio
from .snapshot import Snapshot
from .snapshot_comparison import SnapshotComparison
from .snapshot_report import SnapshotReport
from .snapshot_store import SnapshotStore


class HistoricalAnalysis:
    """
    Orchestrate creation, storage, retrieval, comparison, and reporting
    of historical RIMS portfolio snapshots.

    This class intentionally contains orchestration logic only. Financial
    calculations remain in the Portfolio, Snapshot, and SnapshotComparison
    classes.
    """

    def __init__(self, storage_path: str | Path) -> None:
        """
        Initialize historical analysis using the supplied snapshot storage
        location.
        """
        self.store = SnapshotStore(storage_path)

    def create_snapshot(
        self,
        portfolio: Portfolio,
        snapshot_date: date,
        cash_market_value: Decimal | float | int = Decimal("0"),
    ) -> Snapshot:
        """
        Create a historical snapshot from a current portfolio.

        The source portfolio is not modified.
        """
        if not isinstance(portfolio, Portfolio):
            raise TypeError("portfolio must be a Portfolio.")

        if not isinstance(snapshot_date, date):
            raise TypeError("snapshot_date must be a date.")

        return Snapshot.from_portfolio(
            portfolio=portfolio,
            snapshot_date=snapshot_date,
            cash_market_value=Decimal(str(cash_market_value)),
        )

    def save_snapshot(
        self,
        snapshot: Snapshot,
        overwrite: bool = False,
    ) -> Path:
        """Persist a snapshot through SnapshotStore."""
        if not isinstance(snapshot, Snapshot):
            raise TypeError("snapshot must be a Snapshot.")

        return self.store.save(
            snapshot=snapshot,
            overwrite=overwrite,
        )

    def create_and_save_snapshot(
        self,
        portfolio: Portfolio,
        snapshot_date: date,
        cash_market_value: Decimal | float | int = Decimal("0"),
        overwrite: bool = False,
    ) -> Snapshot:
        """
        Create and persist a historical snapshot in one operation.
        """
        snapshot = self.create_snapshot(
            portfolio=portfolio,
            snapshot_date=snapshot_date,
            cash_market_value=cash_market_value,
        )

        self.save_snapshot(
            snapshot=snapshot,
            overwrite=overwrite,
        )

        return snapshot

    def load_snapshot(self, snapshot_date: date) -> Snapshot:
        """Load a historical snapshot by date."""
        if not isinstance(snapshot_date, date):
            raise TypeError("snapshot_date must be a date.")

        return self.store.load(snapshot_date)

    def list_snapshot_dates(self) -> list[date]:
        """Return all available historical snapshot dates."""
        return self.store.list_dates()

    def compare_snapshots(
        self,
        beginning_date: date,
        ending_date: date,
    ) -> SnapshotComparison:
        """
        Load two historical snapshots and compare them.
        """
        beginning = self.load_snapshot(beginning_date)
        ending = self.load_snapshot(ending_date)

        return SnapshotComparison.from_snapshots(
            beginning=beginning,
            ending=ending,
        )

    def generate_report(
        self,
        beginning_date: date,
        ending_date: date,
    ) -> str:
        """
        Generate a human-readable report for two stored snapshots.
        """
        comparison = self.compare_snapshots(
            beginning_date=beginning_date,
            ending_date=ending_date,
        )

        return SnapshotReport(comparison).generate()

    def compare_snapshot_objects(
        self,
        beginning: Snapshot,
        ending: Snapshot,
    ) -> SnapshotComparison:
        """
        Compare two Snapshot objects without loading them from storage.

        This provides a convenient orchestration method for callers that
        already have Snapshot objects.
        """
        if not isinstance(beginning, Snapshot):
            raise TypeError("beginning must be a Snapshot.")

        if not isinstance(ending, Snapshot):
            raise TypeError("ending must be a Snapshot.")

        return SnapshotComparison.from_snapshots(
            beginning=beginning,
            ending=ending,
        )

    def generate_report_from_snapshots(
        self,
        beginning: Snapshot,
        ending: Snapshot,
    ) -> str:
        """
        Generate a report from two Snapshot objects without using storage.
        """
        comparison = self.compare_snapshot_objects(
            beginning=beginning,
            ending=ending,
        )

        return SnapshotReport(comparison).generate()