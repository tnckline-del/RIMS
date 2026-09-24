"""Tests for factual import lifecycle health reporting."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from src.import_health import ImportHealth, ImportHealthService
from src.import_operation import (
    ImportFileType,
    ImportOperation,
    ImportStatus,
)
from src.import_operation_store import ImportOperationStore


def make_operation(
    import_id: str,
    status: ImportStatus,
) -> ImportOperation:
    """Create a valid test import operation."""
    return ImportOperation(
        import_id=import_id,
        source_file=f"{import_id}.csv",
        file_type=ImportFileType.TRANSACTIONS,
        file_hash="a" * 64,
        account="Test Account",
        reporting_start_date=None,
        reporting_end_date=None,
        imported_at=datetime(2026, 9, 24, 10, 0, 0),
        status=status,
    )


def build_service(
    tmp_path: Path,
) -> tuple[ImportHealthService, ImportOperationStore]:
    """Create an import health service using temporary storage."""
    store = ImportOperationStore(tmp_path / "operations")

    return (
        ImportHealthService(store),
        store,
    )


def test_empty_store_reports_no_operations(
    tmp_path: Path,
) -> None:
    """An empty operation store has a factual empty-state summary."""
    service, _ = build_service(tmp_path)

    health = service.get_health()

    assert isinstance(health, ImportHealth)
    assert health.total_operations == 0
    assert health.reconciled_operations == 0
    assert health.reconciliation_failed_operations == 0
    assert health.reconciliation_failed_import_ids == ()
    assert health.all_reconciled is False
    assert health.unresolved_reconciliation_count == 0
    assert health.summary == "No import operations recorded."


def test_all_reconciled_reports_complete_state(
    tmp_path: Path,
) -> None:
    """All reconciled operations produce the complete-state summary."""
    service, store = build_service(tmp_path)

    store.save(
        make_operation(
            "import-1",
            ImportStatus.RECONCILED,
        )
    )
    store.save(
        make_operation(
            "import-2",
            ImportStatus.RECONCILED,
        )
    )

    health = service.get_health()

    assert health.total_operations == 2
    assert health.reconciled_operations == 2
    assert health.reconciliation_failed_operations == 0
    assert health.reconciliation_failed_import_ids == ()
    assert health.all_reconciled is True
    assert health.unresolved_reconciliation_count == 0
    assert health.summary == "All imports reconciled."


def test_reconciliation_failure_is_identified(
    tmp_path: Path,
) -> None:
    """A reconciliation failure is identified by its persisted import ID."""
    service, store = build_service(tmp_path)

    store.save(
        make_operation(
            "import-1",
            ImportStatus.RECONCILED,
        )
    )
    store.save(
        make_operation(
            "import-2",
            ImportStatus.RECONCILIATION_FAILED,
        )
    )

    health = service.get_health()

    assert health.total_operations == 2
    assert health.reconciled_operations == 1
    assert health.reconciliation_failed_operations == 1
    assert health.reconciliation_failed_import_ids == ("import-2",)
    assert health.all_reconciled is False
    assert health.unresolved_reconciliation_count == 1
    assert health.summary == "1 import require reconciliation."


def test_multiple_reconciliation_failures_are_identified(
    tmp_path: Path,
) -> None:
    """Multiple reconciliation failures are all reported."""
    service, store = build_service(tmp_path)

    store.save(
        make_operation(
            "import-1",
            ImportStatus.RECONCILED,
        )
    )
    store.save(
        make_operation(
            "import-2",
            ImportStatus.RECONCILIATION_FAILED,
        )
    )
    store.save(
        make_operation(
            "import-3",
            ImportStatus.RECONCILIATION_FAILED,
        )
    )

    health = service.get_health()

    assert health.total_operations == 3
    assert health.reconciled_operations == 1
    assert health.reconciliation_failed_operations == 2
    assert health.reconciliation_failed_import_ids == (
        "import-2",
        "import-3",
    )
    assert health.all_reconciled is False
    assert health.unresolved_reconciliation_count == 2
    assert health.summary == "2 imports require reconciliation."


@pytest.mark.parametrize(
    "status",
    [
        ImportStatus.VALIDATED,
        ImportStatus.CONFIRMED,
        ImportStatus.STAGED,
        ImportStatus.IMPORTED,
        ImportStatus.VALIDATION_FAILED,
        ImportStatus.IMPORT_FAILED,
    ],
)
def test_non_reconciliation_failure_status_is_not_counted_as_failure(
    tmp_path: Path,
    status: ImportStatus,
) -> None:
    """Only RECONCILIATION_FAILED counts as an unresolved reconciliation."""
    service, store = build_service(tmp_path)

    store.save(
        make_operation(
            "import-1",
            status,
        )
    )

    health = service.get_health()

    assert health.total_operations == 1
    assert health.reconciled_operations == 0
    assert health.reconciliation_failed_operations == 0
    assert health.reconciliation_failed_import_ids == ()
    assert health.all_reconciled is False
    assert health.unresolved_reconciliation_count == 0
    assert health.summary == "1 import(s) not yet reconciled."


def test_service_requires_import_operation_store(
    tmp_path: Path,
) -> None:
    """The service requires the authoritative operation store."""
    with pytest.raises(
        TypeError,
        match="ImportHealthService requires an ImportOperationStore",
    ):
        ImportHealthService(object())  # type: ignore[arg-type]
