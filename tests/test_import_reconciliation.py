"""
Tests for Sprint 22G import reconciliation and lifecycle management.

These tests verify that one independently imported CSV can move from
IMPORTED to RECONCILED or RECONCILIATION_FAILED without changing the
underlying imported data.

Financial calculations remain covered by the Sprint 22F tests.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.controlled_positions_import import (
    ControlledPositionsImportResult,
)
from src.controlled_transaction_import import (
    ControlledTransactionImportResult,
)
from src.holding import Holding
from src.import_operation import (
    ImportFileType,
    ImportOperation,
    ImportStatus,
)
from src.import_operation_store import ImportOperationStore
from src.snapshot_store import SnapshotStore
from src.transaction_repository import TransactionRepository
from src.import_reconciliation import (
    ImportReconciliationResult,
    ImportReconciliationService,
)
from src.post_import_processing import (
    PostImportProcessingCoordinator,
)
from src.portfolio import Portfolio
from src.snapshot import Snapshot
from src.transaction import (
    IncomeCharacter,
    IncomeType,
    InvestmentTransaction,
    TaxCharacter,
    TransactionType,
)
from src.transaction_repository import TransactionAppendResult


ACCOUNT = "TEST-ACCOUNT"
POSITIONS_IMPORT_ID = "positions-test-import"
TRANSACTIONS_IMPORT_ID = "transactions-test-import"
FILE_HASH = "a" * 64


def make_holding(
    *,
    symbol: str = "ARCC",
    shares: str = "100",
) -> Holding:
    """Create a minimal holding for reconciliation tests."""
    return Holding(
        symbol=symbol,
        description="Test holding",
        asset_type="Equity",
        sector="Financials",
        shares=Decimal(shares),
        price=Decimal("20.00"),
        cost_basis=Decimal("1800.00"),
        dividend_per_share=Decimal("0"),
        dividend_yield=Decimal("0"),
        market_value=Decimal("2000.00"),
    )


def make_portfolio(
    *,
    symbol: str = "ARCC",
    shares: str = "100",
) -> Portfolio:
    """Create a minimal portfolio."""
    return Portfolio(
        name="Test Portfolio",
        holdings=[
            make_holding(
                symbol=symbol,
                shares=shares,
            )
        ],
    )


def make_transaction(
    *,
    transaction_date: date = date(2026, 9, 1),
    symbol: str = "ARCC",
    amount: str = "100.00",
    source_file: str = "test-transactions.csv",
) -> InvestmentTransaction:
    """Create a deterministic income transaction."""
    return InvestmentTransaction(
        account=ACCOUNT,
        transaction_date=transaction_date,
        action="Cash Dividend",
        symbol=symbol,
        description="Test dividend",
        amount=Decimal(amount),
        transaction_type=TransactionType.INCOME,
        income_type=IncomeType.DIVIDEND,
        income_character=IncomeCharacter.RECURRING,
        tax_character=TaxCharacter.UNKNOWN,
        source_file=source_file,
    )


def make_operation(
    *,
    import_id: str,
    file_type: ImportFileType,
    status: ImportStatus = ImportStatus.IMPORTED,
) -> ImportOperation:
    """Create an import operation fixture."""
    return ImportOperation(
        import_id=import_id,
        source_file=f"{file_type.value.lower()}-test.csv",
        file_type=file_type,
        file_hash=FILE_HASH,
        account=ACCOUNT,
        reporting_start_date=date(2026, 9, 1),
        reporting_end_date=date(2026, 9, 1),
        imported_at=datetime(2026, 9, 1, 12, 0, 0),
        status=status,
    )


def make_positions_result(
    tmp_path: Path,
    *,
    status: ImportStatus = ImportStatus.IMPORTED,
) -> ControlledPositionsImportResult:
    """Create a successful positions import result."""
    snapshot = Snapshot.from_portfolio(
        make_portfolio(),
        snapshot_date=date(2026, 9, 1),
    )

    snapshot_path = tmp_path / "snapshots" / "2026-09-01.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    return ControlledPositionsImportResult(
        operation=make_operation(
            import_id=POSITIONS_IMPORT_ID,
            file_type=ImportFileType.POSITIONS,
            status=status,
        ),
        snapshot=snapshot,
        snapshot_path=snapshot_path,
        current_portfolio_advanced=True,
    )


def make_transaction_result(
    *,
    status: ImportStatus = ImportStatus.IMPORTED,
    transactions_added: int = 1,
) -> ControlledTransactionImportResult:
    """Create a successful transaction import result."""
    transactions = (
        make_transaction(),
    )

    append_result = TransactionAppendResult(
        transactions_received=len(transactions),
        transactions_added=transactions_added,
        duplicates_skipped=(
            len(transactions) - transactions_added
        ),
        dataset_path=None,
        added_transactions=(
            transactions
            if transactions_added > 0
            else ()
        ),
    )

    return ControlledTransactionImportResult(
        operation=make_operation(
            import_id=TRANSACTIONS_IMPORT_ID,
            file_type=ImportFileType.TRANSACTIONS,
            status=status,
        ),
        source_transaction_count=len(transactions),
        transactions_added=transactions_added,
        duplicates_skipped=(
            len(transactions) - transactions_added
        ),
        income_transactions_added=transactions_added,
        recurring_income_transactions_added=transactions_added,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 1),
        append_result=append_result,
    )


class StubPostImportProcessingCoordinator(
    PostImportProcessingCoordinator,
):
    """Provide deterministic coordinator behavior for lifecycle tests."""

    def __init__(
        self,
        *,
        processing_result: object = None,
        error: Exception | None = None,
    ) -> None:
        """Initialize the stub without requiring production dependencies."""
        self.processing_result = processing_result
        self.error = error
        self.process_calls = 0
        self.received_positions_import = None
        self.received_transactions_import = None

    def process(
        self,
        positions_import=None,
        transactions_import=None,
    ):
        """Record the call and return or raise the configured outcome."""
        self.process_calls += 1
        self.received_positions_import = positions_import
        self.received_transactions_import = transactions_import

        if self.error is not None:
            raise self.error

        return self.processing_result


def build_service(
    tmp_path: Path,
    coordinator: StubPostImportProcessingCoordinator,
) -> tuple[
    ImportReconciliationService,
    ImportOperationStore,
    SnapshotStore,
    TransactionRepository,
]:
    """Build an isolated reconciliation service."""
    operation_store = ImportOperationStore(
        tmp_path / "import_operations"
    )

    snapshot_store = SnapshotStore(
        tmp_path / "snapshots"
    )

    transaction_repository = TransactionRepository.from_path(
        tmp_path / "transactions"
    )

    service = ImportReconciliationService(
        import_operation_store=operation_store,
        snapshot_store=snapshot_store,
        transaction_repository=transaction_repository,
        post_import_processing_coordinator=coordinator,
    )

    return (
        service,
        operation_store,
        snapshot_store,
        transaction_repository,
    )


def test_positions_import_is_marked_reconciled(
    tmp_path: Path,
) -> None:
    """A successful positions import becomes RECONCILED."""
    processing_result = object()
    coordinator = StubPostImportProcessingCoordinator(
        processing_result=processing_result,
    )
    service, operation_store, _, _ = build_service(
        tmp_path,
        coordinator,
    )

    positions_result = make_positions_result(tmp_path)

    result = service.reconcile(
        positions_import=positions_result,
    )

    assert isinstance(result, ImportReconciliationResult)
    assert result.reconciled is True
    assert result.reconciliation_failed is False
    assert result.operation.status is ImportStatus.RECONCILED
    assert result.operation.import_id == POSITIONS_IMPORT_ID
    assert result.processing_result is processing_result

    stored_operation = operation_store.load(
        POSITIONS_IMPORT_ID
    )

    assert stored_operation.status is ImportStatus.RECONCILED
    assert coordinator.process_calls == 1
    assert coordinator.received_positions_import is positions_result
    assert coordinator.received_transactions_import is None


def test_transaction_import_is_marked_reconciled(
    tmp_path: Path,
) -> None:
    """A successful transaction import becomes RECONCILED."""
    processing_result = object()
    coordinator = StubPostImportProcessingCoordinator(
        processing_result=processing_result,
    )
    service, operation_store, _, _ = build_service(
        tmp_path,
        coordinator,
    )

    transaction_result = make_transaction_result()

    result = service.reconcile(
        transactions_import=transaction_result,
    )

    assert result.reconciled is True
    assert result.reconciliation_failed is False
    assert result.operation.status is ImportStatus.RECONCILED
    assert result.operation.import_id == TRANSACTIONS_IMPORT_ID
    assert result.processing_result is processing_result

    stored_operation = operation_store.load(
        TRANSACTIONS_IMPORT_ID
    )

    assert stored_operation.status is ImportStatus.RECONCILED
    assert coordinator.process_calls == 1
    assert coordinator.received_positions_import is None
    assert coordinator.received_transactions_import is transaction_result


def test_processing_failure_becomes_reconciliation_failed(
    tmp_path: Path,
) -> None:
    """A processing failure becomes RECONCILIATION_FAILED."""
    coordinator = StubPostImportProcessingCoordinator(
        error=RuntimeError("processing failed"),
    )
    service, operation_store, _, _ = build_service(
        tmp_path,
        coordinator,
    )

    transaction_result = make_transaction_result()

    result = service.reconcile(
        transactions_import=transaction_result,
    )

    assert result.reconciled is False
    assert result.reconciliation_failed is True
    assert result.processing_result is None
    assert result.operation.status is ImportStatus.RECONCILIATION_FAILED
    assert result.operation.import_id == TRANSACTIONS_IMPORT_ID

    stored_operation = operation_store.load(
        TRANSACTIONS_IMPORT_ID
    )

    assert stored_operation.status is ImportStatus.RECONCILIATION_FAILED
    assert coordinator.process_calls == 1


def test_reconciliation_failure_preserves_import_operation(
    tmp_path: Path,
) -> None:
    """A reconciliation failure preserves the imported operation metadata."""
    coordinator = StubPostImportProcessingCoordinator(
        error=RuntimeError("processing failed"),
    )
    service, operation_store, _, _ = build_service(
        tmp_path,
        coordinator,
    )

    transaction_result = make_transaction_result()

    original_operation = transaction_result.operation

    result = service.reconcile(
        transactions_import=transaction_result,
    )

    stored_operation = operation_store.load(
        TRANSACTIONS_IMPORT_ID
    )

    assert stored_operation.import_id == original_operation.import_id
    assert stored_operation.source_file == original_operation.source_file
    assert stored_operation.file_type is original_operation.file_type
    assert stored_operation.file_hash == original_operation.file_hash
    assert stored_operation.account == original_operation.account
    assert (
        stored_operation.reporting_start_date
        == original_operation.reporting_start_date
    )
    assert (
        stored_operation.reporting_end_date
        == original_operation.reporting_end_date
    )
    assert stored_operation.imported_at == original_operation.imported_at
    assert stored_operation.status is ImportStatus.RECONCILIATION_FAILED

    assert result.operation.status is ImportStatus.RECONCILIATION_FAILED

def test_recover_positions_import_uses_persisted_snapshot(
    tmp_path: Path,
) -> None:
    """A failed positions import can be recovered from its Snapshot."""
    processing_result = object()
    coordinator = StubPostImportProcessingCoordinator(
        processing_result=processing_result,
    )
    service, operation_store, snapshot_store, _ = build_service(
        tmp_path,
        coordinator,
    )

    positions_result = make_positions_result(
        tmp_path,
        status=ImportStatus.RECONCILIATION_FAILED,
    )

    operation_store.save(
        positions_result.operation,
    )
    snapshot_store.save(
        positions_result.snapshot,
    )

    result = service.recover(
        POSITIONS_IMPORT_ID,
    )

    assert result.reconciled is True
    assert result.reconciliation_failed is False
    assert result.operation.status is ImportStatus.RECONCILED
    assert result.processing_result is processing_result

    assert coordinator.process_calls == 1
    assert coordinator.received_positions_import is not None
    assert (
        coordinator.received_positions_import.operation.import_id
        == POSITIONS_IMPORT_ID
    )
    assert (
        coordinator.received_positions_import.snapshot
        == positions_result.snapshot
    )
    assert coordinator.received_transactions_import is None

    stored_operation = operation_store.load(
        POSITIONS_IMPORT_ID
    )

    assert stored_operation.status is ImportStatus.RECONCILED


def test_recover_transaction_import_uses_persisted_dataset(
    tmp_path: Path,
) -> None:
    """A failed transaction import can be recovered from its dataset."""
    processing_result = object()
    coordinator = StubPostImportProcessingCoordinator(
        processing_result=processing_result,
    )
    service, operation_store, _, transaction_repository = build_service(
        tmp_path,
        coordinator,
    )

    transaction = make_transaction()

    transaction_result = make_transaction_result(
        status=ImportStatus.RECONCILIATION_FAILED,
    )

    operation_store.save(
        transaction_result.operation,
    )

    append_result = transaction_repository.append_unique_transactions(
        dataset_id="dataset-recovery-test",
        account=ACCOUNT,
        source_file="test-transactions.csv",
        transactions=(transaction,),
        import_id=TRANSACTIONS_IMPORT_ID,
    )

    assert append_result.transactions_added == 1

    result = service.recover(
        TRANSACTIONS_IMPORT_ID,
    )

    assert result.reconciled is True
    assert result.reconciliation_failed is False
    assert result.operation.status is ImportStatus.RECONCILED
    assert result.processing_result is processing_result

    assert coordinator.process_calls == 1
    assert coordinator.received_positions_import is None
    assert coordinator.received_transactions_import is not None
    assert (
        coordinator.received_transactions_import.operation.import_id
        == TRANSACTIONS_IMPORT_ID
    )
    assert (
        coordinator.received_transactions_import.transactions_added
        == 1
    )
    assert (
        coordinator.received_transactions_import.append_result
        .added_transactions
        == (transaction,)
    )

    datasets = transaction_repository.load_all_datasets()

    assert len(datasets) == 1
    assert datasets[0].import_id == TRANSACTIONS_IMPORT_ID
    assert datasets[0].transactions == (transaction,)

    stored_operation = operation_store.load(
        TRANSACTIONS_IMPORT_ID
    )

    assert stored_operation.status is ImportStatus.RECONCILED

@pytest.mark.parametrize(
    "status",
    [
        ImportStatus.RECONCILED,
        ImportStatus.CONFIRMED,
        ImportStatus.STAGED,
        ImportStatus.VALIDATION_FAILED,
        ImportStatus.IMPORT_FAILED,
        ImportStatus.RECONCILIATION_FAILED,
    ],
)

def test_non_imported_operation_cannot_be_reconciled(
    tmp_path: Path,
    status: ImportStatus,
) -> None:
    """Only an IMPORTED operation can enter reconciliation."""
    coordinator = StubPostImportProcessingCoordinator()
    service, operation_store, _, _ = build_service(
        tmp_path,
        coordinator,
    )

    transaction_result = make_transaction_result(
        status=status,
    )

    operation_store.save(
        transaction_result.operation,
    )

    with pytest.raises(
        ValueError,
        match="Only IMPORTED operations can be reconciled",
    ):
        service.reconcile(
            transactions_import=transaction_result,
        )

    assert coordinator.process_calls == 0

    stored_operation = operation_store.load(
        TRANSACTIONS_IMPORT_ID
    )

    assert stored_operation.status is status


def test_no_import_result_is_rejected(
    tmp_path: Path,
) -> None:
    """Reconciliation requires exactly one import result."""
    coordinator = StubPostImportProcessingCoordinator()
    service, _, _, _ = build_service(
        tmp_path,
        coordinator,
    )

    with pytest.raises(
        ValueError,
        match="Exactly one successful import result is required",
    ):
        service.reconcile()

    assert coordinator.process_calls == 0


def test_positions_and_transactions_cannot_be_reconciled_together(
    tmp_path: Path,
) -> None:
    """Independent import lifecycles cannot be combined."""
    coordinator = StubPostImportProcessingCoordinator()
    service, _, _, _ = build_service(
        tmp_path,
        coordinator,
    )

    positions_result = make_positions_result(tmp_path)
    transaction_result = make_transaction_result()

    with pytest.raises(
        ValueError,
        match="must be reconciled independently",
    ):
        service.reconcile(
            positions_import=positions_result,
            transactions_import=transaction_result,
        )

    assert coordinator.process_calls == 0


def test_reconciliation_result_reflects_persisted_status(
    tmp_path: Path,
) -> None:
    """The returned operation reflects the lifecycle state written to disk."""
    coordinator = StubPostImportProcessingCoordinator(
        processing_result=object(),
    )
    service, operation_store, _, _ = build_service(
        tmp_path,
        coordinator,
    )

    positions_result = make_positions_result(tmp_path)

    result = service.reconcile(
        positions_import=positions_result,
    )

    stored_operation = operation_store.load(
        POSITIONS_IMPORT_ID
    )

    assert result.operation == stored_operation
    assert result.operation.status is ImportStatus.RECONCILED


def test_recover_transaction_after_later_import_preserves_both_datasets(
    tmp_path: Path,
) -> None:
    """Recovery remains isolated after a later transaction import."""
    processing_result = object()
    coordinator = StubPostImportProcessingCoordinator(
        processing_result=processing_result,
    )
    service, operation_store, _, transaction_repository = build_service(
        tmp_path,
        coordinator,
    )

    failed_import_id = "transactions-failed"
    later_import_id = "transactions-later"

    failed_operation = make_operation(
        import_id=failed_import_id,
        file_type=ImportFileType.TRANSACTIONS,
        status=ImportStatus.RECONCILIATION_FAILED,
    )

    later_operation = make_operation(
        import_id=later_import_id,
        file_type=ImportFileType.TRANSACTIONS,
        status=ImportStatus.RECONCILED,
    )

    operation_store.save(failed_operation)
    operation_store.save(later_operation)

    failed_transaction = make_transaction(
        transaction_date=date(2026, 9, 1),
        symbol="ARCC",
        amount="100.00",
        source_file="transactions-failed.csv",
    )

    later_transaction = make_transaction(
        transaction_date=date(2026, 9, 2),
        symbol="BXSL",
        amount="200.00",
        source_file="transactions-later.csv",
    )

    failed_append = transaction_repository.append_unique_transactions(
        dataset_id="dataset-failed",
        account=ACCOUNT,
        source_file="transactions-failed.csv",
        transactions=(failed_transaction,),
        import_id=failed_import_id,
    )

    later_append = transaction_repository.append_unique_transactions(
        dataset_id="dataset-later",
        account=ACCOUNT,
        source_file="transactions-later.csv",
        transactions=(later_transaction,),
        import_id=later_import_id,
    )

    assert failed_append.transactions_added == 1
    assert later_append.transactions_added == 1

    result = service.recover(failed_import_id)

    assert result.reconciled is True
    assert result.reconciliation_failed is False
    assert result.operation.status is ImportStatus.RECONCILED
    assert result.processing_result is processing_result

    assert coordinator.process_calls == 1
    assert coordinator.received_positions_import is None
    assert coordinator.received_transactions_import is not None

    recovered_import = coordinator.received_transactions_import

    assert recovered_import.operation.import_id == failed_import_id
    assert recovered_import.transactions_added == 1
    assert (
        recovered_import.append_result.added_transactions
        == (failed_transaction,)
    )

    datasets = transaction_repository.load_all_datasets()

    assert len(datasets) == 2

    datasets_by_import_id = {
        dataset.import_id: dataset
        for dataset in datasets
    }

    assert datasets_by_import_id[failed_import_id].transactions == (
        failed_transaction,
    )
    assert datasets_by_import_id[later_import_id].transactions == (
        later_transaction,
    )

    stored_failed_operation = operation_store.load(
        failed_import_id,
    )

    assert stored_failed_operation.status is ImportStatus.RECONCILED


def test_recover_reconciled_transaction_is_safe_and_does_not_reprocess(
    tmp_path: Path,
) -> None:
    """A reconciled operation is not processed again by recovery."""
    processing_result = object()
    coordinator = StubPostImportProcessingCoordinator(
        processing_result=processing_result,
    )
    service, operation_store, _, transaction_repository = build_service(
        tmp_path,
        coordinator,
    )

    import_id = "transactions-already-reconciled"

    operation = make_operation(
        import_id=import_id,
        file_type=ImportFileType.TRANSACTIONS,
        status=ImportStatus.RECONCILED,
    )

    operation_store.save(operation)

    transaction = make_transaction(
        source_file="transactions-already-reconciled.csv",
    )

    append_result = transaction_repository.append_unique_transactions(
        dataset_id="dataset-already-reconciled",
        account=ACCOUNT,
        source_file="transactions-already-reconciled.csv",
        transactions=(transaction,),
        import_id=import_id,
    )

    assert append_result.transactions_added == 1

    with pytest.raises(ValueError, match="RECONCILIATION_FAILED"):
        service.recover(import_id)

    assert coordinator.process_calls == 0

    stored_operation = operation_store.load(import_id)

    assert stored_operation.status is ImportStatus.RECONCILED

    datasets = transaction_repository.load_all_datasets()

    assert len(datasets) == 1
    assert datasets[0].transactions == (transaction,)
