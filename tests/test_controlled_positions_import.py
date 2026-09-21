from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.import_service import PositionsValidationResult
from src.controlled_positions_import import (
    ControlledPositionsImportService,
)
from src.import_operation import (
    ImportFileType,
    ImportOperation,
    ImportStatus,
    calculate_file_hash,
)
from src.import_operation_store import ImportOperationStore
from src.importer import import_schwab_csv
from src.snapshot import Snapshot
from src.snapshot_store import SnapshotStore


REAL_SCHWAB_FILE = Path(
    "/Users/timothykline/Downloads/"
    "All-Accounts-Positions-2026-09-07-173949.csv"
)


def build_service(tmp_path: Path) -> ControlledPositionsImportService:
    """Create a controlled positions import service for testing."""
    import_store = ImportOperationStore(
        tmp_path / "import_operations"
    )
    snapshot_store = SnapshotStore(
        tmp_path / "snapshots"
    )

    return ControlledPositionsImportService(
        import_operation_store=import_store,
        snapshot_store=snapshot_store,
    )


def build_validation_result(
    source_file: Path,
) -> PositionsValidationResult:
    """Create a real validated positions result."""
    import_result = import_schwab_csv(source_file)

    return PositionsValidationResult(
        is_valid=import_result.is_reconciled,
        source_file=str(source_file),
        holding_count=len(import_result.portfolio.holdings),
        market_value_difference=import_result.market_value_difference,
        cost_basis_difference=import_result.cost_basis_difference,
        is_reconciled=import_result.is_reconciled,
        import_result=import_result,
    )


@pytest.mark.skipif(
    not REAL_SCHWAB_FILE.is_file(),
    reason="Real Schwab positions file is not available.",
)
def test_import_validated_positions_creates_snapshot_and_operation(
    tmp_path: Path,
) -> None:
    """A valid positions file creates a snapshot and imported operation."""
    service = build_service(tmp_path)
    validation_result = build_validation_result(REAL_SCHWAB_FILE)

    result = service.import_positions(
        validation_result,
        REAL_SCHWAB_FILE,
    )

    assert result.operation.status is ImportStatus.IMPORTED
    assert result.operation.file_type is ImportFileType.POSITIONS
    assert result.operation.reporting_start_date == date(2026, 9, 7)
    assert result.operation.reporting_end_date == date(2026, 9, 7)

    assert result.snapshot.snapshot_date == date(2026, 9, 7)
    assert result.snapshot_path.is_file()

    assert result.current_portfolio_advanced is True

    import_store = ImportOperationStore(
        tmp_path / "import_operations"
    )
    saved_operation = import_store.load(result.operation.import_id)

    assert saved_operation.status is ImportStatus.IMPORTED

    snapshot_store = SnapshotStore(tmp_path / "snapshots")
    saved_snapshot = snapshot_store.load(date(2026, 9, 7))

    assert saved_snapshot.snapshot_date == date(2026, 9, 7)
    assert len(saved_snapshot.holdings) == 44


@pytest.mark.skipif(
    not REAL_SCHWAB_FILE.is_file(),
    reason="Real Schwab positions file is not available.",
)
def test_import_preserves_file_hash(
    tmp_path: Path,
) -> None:
    """The import operation records the SHA-256 source-file hash."""
    service = build_service(tmp_path)
    validation_result = build_validation_result(REAL_SCHWAB_FILE)

    result = service.import_positions(
        validation_result,
        REAL_SCHWAB_FILE,
    )

    assert result.operation.file_hash == calculate_file_hash(
        REAL_SCHWAB_FILE
    )


@pytest.mark.skipif(
    not REAL_SCHWAB_FILE.is_file(),
    reason="Real Schwab positions file is not available.",
)
def test_duplicate_file_is_rejected(
    tmp_path: Path,
) -> None:
    """The same source file cannot be imported twice."""
    service = build_service(tmp_path)
    validation_result = build_validation_result(REAL_SCHWAB_FILE)

    service.import_positions(
        validation_result,
        REAL_SCHWAB_FILE,
    )

    with pytest.raises(FileExistsError):
        service.import_positions(
            validation_result,
            REAL_SCHWAB_FILE,
        )


def test_invalid_validation_result_is_rejected(
    tmp_path: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """An invalid validation result cannot enter the import workflow."""
    source_file = tmp_path_factory.mktemp("source") / "positions.csv"
    source_file.write_text("test data\n", encoding="utf-8")

    validation_result = PositionsValidationResult(
        is_valid=False,
        source_file=str(source_file),
        holding_count=0,
        market_value_difference=Decimal("1.00"),
        cost_basis_difference=Decimal("1.00"),
        is_reconciled=False,
        error="Validation failed.",
        import_result=None,
    )

    service = build_service(tmp_path)

    with pytest.raises(ValueError, match="invalid"):
        service.import_positions(
            validation_result,
            source_file,
        )


def test_missing_import_result_is_rejected(
    tmp_path: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """A valid flag without parsed import data cannot be imported."""
    source_file = tmp_path_factory.mktemp("source") / "positions.csv"
    source_file.write_text("test data\n", encoding="utf-8")

    validation_result = PositionsValidationResult(
        is_valid=True,
        source_file=str(source_file),
        holding_count=0,
        market_value_difference=Decimal("0.00"),
        cost_basis_difference=Decimal("0.00"),
        is_reconciled=True,
        import_result=None,
    )

    service = build_service(tmp_path)

    with pytest.raises(
        ValueError,
        match="does not contain an import result",
    ):
        service.import_positions(
            validation_result,
            source_file,
        )


def test_wrong_validation_result_type_is_rejected(
    tmp_path: Path,
) -> None:
    """Only PositionsValidationResult may enter this workflow."""
    service = build_service(tmp_path)

    with pytest.raises(TypeError):
        service.import_positions(
            validation_result=object(),  # type: ignore[arg-type]
            source_file=tmp_path / "positions.csv",
        )


def test_missing_source_file_is_rejected(
    tmp_path: Path,
) -> None:
    """A missing source file cannot be imported."""
    service = build_service(tmp_path)

    with pytest.raises(TypeError):
        service.import_positions(
            validation_result=object(),  # type: ignore[arg-type]
            source_file=tmp_path / "missing.csv",
        )


@pytest.mark.skipif(
    not REAL_SCHWAB_FILE.is_file(),
    reason="Real Schwab positions file is not available.",
)
def test_import_does_not_modify_source_file(
    tmp_path: Path,
) -> None:
    """The controlled import reads but does not modify the source file."""
    original_bytes = REAL_SCHWAB_FILE.read_bytes()

    service = build_service(tmp_path)
    validation_result = build_validation_result(REAL_SCHWAB_FILE)

    service.import_positions(
        validation_result,
        REAL_SCHWAB_FILE,
    )

    assert REAL_SCHWAB_FILE.read_bytes() == original_bytes


@pytest.mark.skipif(
    not REAL_SCHWAB_FILE.is_file(),
    reason="Real Schwab positions file is not available.",
)
def test_snapshot_uses_schwab_reporting_date(
    tmp_path: Path,
) -> None:
    """The historical snapshot date comes from Schwab, not import time."""
    service = build_service(tmp_path)
    validation_result = build_validation_result(REAL_SCHWAB_FILE)

    result = service.import_positions(
        validation_result,
        REAL_SCHWAB_FILE,
    )

    assert result.snapshot.snapshot_date == date(2026, 9, 7)
    assert result.operation.reporting_start_date == date(2026, 9, 7)
    assert result.operation.reporting_end_date == date(2026, 9, 7)


def test_load_current_portfolio_returns_none_when_empty(
    tmp_path: Path,
) -> None:
    """No current portfolio exists before a positions import."""
    service = build_service(tmp_path)

    assert service.load_current_portfolio() is None


def test_current_portfolio_uses_latest_reporting_date(
    tmp_path: Path,
) -> None:
    """The latest successful positions snapshot is the current portfolio."""
    import_store = ImportOperationStore(
        tmp_path / "import_operations"
    )
    snapshot_store = SnapshotStore(
        tmp_path / "snapshots"
    )
    service = ControlledPositionsImportService(
        import_operation_store=import_store,
        snapshot_store=snapshot_store,
    )

    older_snapshot = Snapshot(
        snapshot_date=date(2026, 8, 31),
        portfolio_name="Older Portfolio",
        holdings=[],
        cash_market_value=Decimal("100.00"),
    )
    newer_snapshot = Snapshot(
        snapshot_date=date(2026, 9, 7),
        portfolio_name="Newer Portfolio",
        holdings=[],
        cash_market_value=Decimal("200.00"),
    )

    snapshot_store.save(older_snapshot)
    snapshot_store.save(newer_snapshot)

    from datetime import datetime

    import_store.save(
        ImportOperation(
            import_id="positions-2026-08-31-old",
            source_file="older.csv",
            file_type=ImportFileType.POSITIONS,
            file_hash="a" * 64,
            account=None,
            reporting_start_date=date(2026, 8, 31),
            reporting_end_date=date(2026, 8, 31),
            imported_at=datetime.now().astimezone(),
            status=ImportStatus.IMPORTED,
        )
    )
    import_store.save(
        ImportOperation(
            import_id="positions-2026-09-07-new",
            source_file="newer.csv",
            file_type=ImportFileType.POSITIONS,
            file_hash="b" * 64,
            account=None,
            reporting_start_date=date(2026, 9, 7),
            reporting_end_date=date(2026, 9, 7),
            imported_at=datetime.now().astimezone(),
            status=ImportStatus.IMPORTED,
        )
    )

    current = service.load_current_portfolio()

    assert current is not None
    assert current.snapshot_date == date(2026, 9, 7)
    assert current.portfolio_name == "Newer Portfolio"
    assert current.cash_market_value == Decimal("200.00")


def test_older_import_does_not_replace_newer_current_portfolio(
    tmp_path: Path,
) -> None:
    """
    Importing an older reporting date does not move the current portfolio
    backward in time.
    """
    import_store = ImportOperationStore(
        tmp_path / "import_operations"
    )
    snapshot_store = SnapshotStore(
        tmp_path / "snapshots"
    )
    service = ControlledPositionsImportService(
        import_operation_store=import_store,
        snapshot_store=snapshot_store,
    )

    from datetime import datetime

    newer_snapshot = Snapshot(
        snapshot_date=date(2026, 9, 7),
        portfolio_name="Newer Portfolio",
        holdings=[],
        cash_market_value=Decimal("200.00"),
    )
    older_snapshot = Snapshot(
        snapshot_date=date(2026, 8, 31),
        portfolio_name="Older Portfolio",
        holdings=[],
        cash_market_value=Decimal("100.00"),
    )

    snapshot_store.save(newer_snapshot)
    snapshot_store.save(older_snapshot)

    import_store.save(
        ImportOperation(
            import_id="positions-2026-09-07-new",
            source_file="newer.csv",
            file_type=ImportFileType.POSITIONS,
            file_hash="c" * 64,
            account=None,
            reporting_start_date=date(2026, 9, 7),
            reporting_end_date=date(2026, 9, 7),
            imported_at=datetime.now().astimezone(),
            status=ImportStatus.IMPORTED,
        )
    )
    import_store.save(
        ImportOperation(
            import_id="positions-2026-08-31-old",
            source_file="older.csv",
            file_type=ImportFileType.POSITIONS,
            file_hash="d" * 64,
            account=None,
            reporting_start_date=date(2026, 8, 31),
            reporting_end_date=date(2026, 8, 31),
            imported_at=datetime.now().astimezone(),
            status=ImportStatus.IMPORTED,
        )
    )

    current = service.load_current_portfolio()

    assert current is not None
    assert current.snapshot_date == date(2026, 9, 7)
    assert current.portfolio_name == "Newer Portfolio"


def test_failed_import_is_not_current(
    tmp_path: Path,
) -> None:
    """A failed positions import cannot become the current portfolio."""
    import_store = ImportOperationStore(
        tmp_path / "import_operations"
    )
    snapshot_store = SnapshotStore(
        tmp_path / "snapshots"
    )
    service = ControlledPositionsImportService(
        import_operation_store=import_store,
        snapshot_store=snapshot_store,
    )

    from datetime import datetime

    snapshot = Snapshot(
        snapshot_date=date(2026, 9, 7),
        portfolio_name="Failed Portfolio",
        holdings=[],
        cash_market_value=Decimal("300.00"),
    )
    snapshot_store.save(snapshot)

    import_store.save(
        ImportOperation(
            import_id="positions-failed",
            source_file="failed.csv",
            file_type=ImportFileType.POSITIONS,
            file_hash="e" * 64,
            account=None,
            reporting_start_date=date(2026, 9, 7),
            reporting_end_date=date(2026, 9, 7),
            imported_at=datetime.now().astimezone(),
            status=ImportStatus.IMPORT_FAILED,
        )
    )

    assert service.load_current_portfolio() is None
