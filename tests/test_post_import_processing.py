"""
Tests for Sprint 22F post-import processing orchestration.

These tests verify that successful controlled imports trigger the correct
existing analytical services using authoritative persisted RIMS data.

The coordinator is tested as an orchestration layer. Financial calculations
remain owned by the existing analytical services.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.controlled_positions_import import (
    ControlledPositionsImportResult,
    ControlledPositionsImportService,
)
from src.controlled_transaction_import import (
    ControlledTransactionImportResult,
)
from src.forward_income import ForwardIncomeAssumption
from src.forward_income_manager import ForwardIncomeManager
from src.forward_income_store import ForwardIncomeStore
from src.holding import Holding
from src.import_operation import (
    ImportFileType,
    ImportOperation,
    ImportStatus,
)
from src.import_operation_store import ImportOperationStore
from src.post_import_processing import (
    PostImportProcessingCoordinator,
    PostImportProcessingResult,
)
from src.portfolio import Portfolio
from src.snapshot import Snapshot
from src.snapshot_store import SnapshotStore
from src.transaction import (
    IncomeCharacter,
    IncomeType,
    InvestmentTransaction,
    TaxCharacter,
    TransactionType,
)
from src.transaction_repository import TransactionRepository


ACCOUNT = "TEST-ACCOUNT"
POSITIONS_IMPORT_ID = "positions-test-import"
TRANSACTIONS_IMPORT_ID = "transactions-test-import"
FILE_HASH = "a" * 64


def make_holding(
    *,
    symbol: str = "ARCC",
    shares: str = "100",
) -> Holding:
    """Create a minimal holding for coordinator tests."""
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
    """Create a minimal current portfolio."""
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
    income_character: IncomeCharacter = IncomeCharacter.RECURRING,
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
        income_character=income_character,
        tax_character=TaxCharacter.UNKNOWN,
        source_file="test-transactions.csv",
    )


def make_operation(
    *,
    import_id: str,
    file_type: ImportFileType,
) -> ImportOperation:
    """Create an imported operation fixture."""
    return ImportOperation(
        import_id=import_id,
        source_file=f"{file_type.value.lower()}-test.csv",
        file_type=file_type,
        file_hash=FILE_HASH,
        account=ACCOUNT,
        reporting_start_date=date(2026, 9, 1),
        reporting_end_date=date(2026, 9, 1),
        imported_at=datetime(2026, 9, 1, 12, 0, 0),
        status=ImportStatus.IMPORTED,
    )


def make_positions_result(
    tmp_path: Path,
    portfolio: Portfolio | None = None,
) -> ControlledPositionsImportResult:
    """Create a successful positions import result."""
    if portfolio is None:
        portfolio = make_portfolio()

    snapshot = Snapshot.from_portfolio(
        portfolio,
        snapshot_date=date(2026, 9, 1),
    )

    snapshot_path = tmp_path / "snapshots" / "2026-09-01.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    return ControlledPositionsImportResult(
        operation=make_operation(
            import_id=POSITIONS_IMPORT_ID,
            file_type=ImportFileType.POSITIONS,
        ),
        snapshot=snapshot,
        snapshot_path=snapshot_path,
        current_portfolio_advanced=True,
    )


def make_transaction_result(
    *,
    transactions_added: int,
) -> ControlledTransactionImportResult:
    """Create a successful transaction import result."""
    transactions = (
        make_transaction(),
    )

    from src.transaction_repository import TransactionAppendResult

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
        ),
        source_transaction_count=len(transactions),
        transactions_added=transactions_added,
        duplicates_skipped=(
            len(transactions) - transactions_added
        ),
        income_transactions_added=(
            transactions_added
        ),
        recurring_income_transactions_added=(
            transactions_added
        ),
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 1),
        append_result=append_result,
    )


def build_positions_service(
    tmp_path: Path,
) -> ControlledPositionsImportService:
    """Create an isolated positions service."""
    operation_store = ImportOperationStore(
        tmp_path / "import_operations"
    )
    snapshot_store = SnapshotStore(
        tmp_path / "snapshots"
    )

    return ControlledPositionsImportService(
        import_operation_store=operation_store,
        snapshot_store=snapshot_store,
    )


def build_repository(
    tmp_path: Path,
) -> TransactionRepository:
    """Create an isolated transaction repository."""
    return TransactionRepository.from_path(
        tmp_path / "transactions"
    )


def build_coordinator(
    tmp_path: Path,
) -> PostImportProcessingCoordinator:
    """Create an isolated post-import processing coordinator."""
    return PostImportProcessingCoordinator(
        positions_import_service=build_positions_service(tmp_path),
        transaction_repository=build_repository(tmp_path),
        forward_income_storage_path=str(
            tmp_path / "forward_income"
        ),
    )


def persist_current_portfolio(
    tmp_path: Path,
    portfolio: Portfolio | None = None,
) -> None:
    """Persist a current positions snapshot and imported operation."""
    if portfolio is None:
        portfolio = make_portfolio()

    operation_store = ImportOperationStore(
        tmp_path / "import_operations"
    )
    snapshot_store = SnapshotStore(
        tmp_path / "snapshots"
    )

    snapshot = Snapshot.from_portfolio(
        portfolio,
        snapshot_date=date(2026, 9, 1),
    )

    snapshot_store.save(snapshot)

    operation_store.save(
        make_operation(
            import_id=POSITIONS_IMPORT_ID,
            file_type=ImportFileType.POSITIONS,
        )
    )


def persist_transaction(
    tmp_path: Path,
    transaction: InvestmentTransaction | None = None,
) -> None:
    """Persist one authoritative transaction."""
    if transaction is None:
        transaction = make_transaction()

    repository = build_repository(tmp_path)

    repository.append_unique_transactions(
        dataset_id="dataset-1",
        account=ACCOUNT,
        source_file="test-transactions.csv",
        transactions=(transaction,),
    )


def save_forward_income_assumption(
    tmp_path: Path,
) -> None:
    """Persist the forward-income assumption used by tests."""
    store = ForwardIncomeStore(tmp_path / "forward_income")
    store.save(
        (
            ForwardIncomeAssumption(
                symbol="ARCC",
                forward_annual_income_per_share=Decimal("20.00"),
                effective_date=date(2026, 9, 1),
                source="Test",
            ),
        )
    )


def test_positions_import_runs_current_and_forward_income(
    tmp_path: Path,
) -> None:
    """Positions import triggers Current and Forward Income."""
    persist_current_portfolio(tmp_path)
    save_forward_income_assumption(tmp_path)

    coordinator = build_coordinator(tmp_path)
    positions_result = make_positions_result(tmp_path)

    result = coordinator.process(
        positions_import=positions_result,
    )

    assert result.positions_processed is True
    assert result.transactions_processed is False

    assert result.current_income_processed is True
    assert result.forward_income_processed is True
    assert result.historical_income_processed is False

    assert result.current_income is not None
    assert result.forward_income is not None
    assert result.historical_income is None

    assert result.positions_import_id == POSITIONS_IMPORT_ID
    assert result.transactions_import_id is None

    assert result.analyses_run == (
        "current_income",
        "forward_income",
    )


def test_transaction_import_with_new_transactions_runs_historical_and_current(
    tmp_path: Path,
) -> None:
    """New transactions trigger Historical and Current Income."""
    persist_current_portfolio(tmp_path)
    persist_transaction(tmp_path)

    coordinator = build_coordinator(tmp_path)
    transaction_result = make_transaction_result(
        transactions_added=1,
    )

    result = coordinator.process(
        transactions_import=transaction_result,
    )

    assert result.positions_processed is False
    assert result.transactions_processed is True

    assert result.current_income_processed is True
    assert result.forward_income_processed is False
    assert result.historical_income_processed is True

    assert result.current_income is not None
    assert result.historical_income is not None
    assert result.forward_income is None

    assert result.positions_import_id is None
    assert result.transactions_import_id == TRANSACTIONS_IMPORT_ID

    assert result.analyses_run == (
        "current_income",
        "historical_income",
    )


def test_duplicate_only_transaction_import_runs_no_transaction_analysis(
    tmp_path: Path,
) -> None:
    """An all-duplicate transaction import does not trigger analysis."""
    persist_current_portfolio(tmp_path)
    persist_transaction(tmp_path)

    coordinator = build_coordinator(tmp_path)
    transaction_result = make_transaction_result(
        transactions_added=0,
    )

    result = coordinator.process(
        transactions_import=transaction_result,
    )

    assert result.positions_processed is False
    assert result.transactions_processed is True

    assert result.current_income_processed is False
    assert result.forward_income_processed is False
    assert result.historical_income_processed is False

    assert result.current_income is None
    assert result.forward_income is None
    assert result.historical_income is None

    assert result.analyses_run == ()


def test_combined_import_runs_all_applicable_analysis(
    tmp_path: Path,
) -> None:
    """Positions plus new transactions trigger all three analyses."""
    persist_current_portfolio(tmp_path)
    persist_transaction(tmp_path)
    save_forward_income_assumption(tmp_path)

    coordinator = build_coordinator(tmp_path)

    positions_result = make_positions_result(tmp_path)
    transaction_result = make_transaction_result(
        transactions_added=1,
    )

    result = coordinator.process(
        positions_import=positions_result,
        transactions_import=transaction_result,
    )

    assert result.positions_processed is True
    assert result.transactions_processed is True

    assert result.current_income_processed is True
    assert result.forward_income_processed is True
    assert result.historical_income_processed is True

    assert result.analyses_run == (
        "current_income",
        "forward_income",
        "historical_income",
    )


def test_combined_import_with_duplicate_transactions_still_processes_positions(
    tmp_path: Path,
) -> None:
    """A positions import still triggers position-driven analysis."""
    persist_current_portfolio(tmp_path)
    save_forward_income_assumption(tmp_path)

    coordinator = build_coordinator(tmp_path)

    positions_result = make_positions_result(tmp_path)
    transaction_result = make_transaction_result(
        transactions_added=0,
    )

    result = coordinator.process(
        positions_import=positions_result,
        transactions_import=transaction_result,
    )

    assert result.current_income_processed is True
    assert result.forward_income_processed is True
    assert result.historical_income_processed is False

    assert result.analyses_run == (
        "current_income",
        "forward_income",
    )


def test_authoritative_transaction_dataset_is_used(
    tmp_path: Path,
) -> None:
    """Analysis uses transactions persisted in the repository."""
    persist_current_portfolio(tmp_path)

    persisted_transaction = make_transaction(
        amount="275.00",
    )
    persist_transaction(
        tmp_path,
        persisted_transaction,
    )

    coordinator = build_coordinator(tmp_path)
    transaction_result = make_transaction_result(
        transactions_added=1,
    )

    result = coordinator.process(
        transactions_import=transaction_result,
    )

    assert result.transactions_available == 1
    assert result.income_transactions_available == 1
    assert result.recurring_income_transactions_available == 1

    assert result.historical_income is not None
    assert (
        result.historical_income.total_historical_income
        == Decimal("275.00")
    )


def test_missing_current_portfolio_fails_processing(
    tmp_path: Path,
) -> None:
    """Transaction processing requires an authoritative current portfolio."""
    coordinator = build_coordinator(tmp_path)
    transaction_result = make_transaction_result(
        transactions_added=1,
    )

    with pytest.raises(
        RuntimeError,
        match="No current portfolio is available",
    ):
        coordinator.process(
            transactions_import=transaction_result,
        )


def test_no_import_result_is_rejected(
    tmp_path: Path,
) -> None:
    """At least one successful import result is required."""
    coordinator = build_coordinator(tmp_path)

    with pytest.raises(
        ValueError,
        match="At least one successful import result",
    ):
        coordinator.process()


def test_wrong_positions_import_type_is_rejected(
    tmp_path: Path,
) -> None:
    """Invalid positions trigger types are rejected."""
    coordinator = build_coordinator(tmp_path)

    with pytest.raises(TypeError):
        coordinator.process(
            positions_import=object(),  # type: ignore[arg-type]
        )


def test_wrong_transaction_import_type_is_rejected(
    tmp_path: Path,
) -> None:
    """Invalid transaction trigger types are rejected."""
    coordinator = build_coordinator(tmp_path)

    with pytest.raises(TypeError):
        coordinator.process(
            transactions_import=object(),  # type: ignore[arg-type]
        )


def test_result_is_immutable(
    tmp_path: Path,
) -> None:
    """The processing result cannot be mutated."""
    persist_current_portfolio(tmp_path)

    coordinator = build_coordinator(tmp_path)
    result = coordinator.process(
        positions_import=make_positions_result(tmp_path),
    )

    assert isinstance(result, PostImportProcessingResult)

    with pytest.raises(AttributeError):
        result.positions_processed = False  # type: ignore[misc]


def test_processing_does_not_create_analysis_result_files(
    tmp_path: Path,
) -> None:
    """The coordinator does not create a separate analysis persistence layer."""
    persist_current_portfolio(tmp_path)
    persist_transaction(tmp_path)
    save_forward_income_assumption(tmp_path)

    coordinator = build_coordinator(tmp_path)

    coordinator.process(
        positions_import=make_positions_result(tmp_path),
        transactions_import=make_transaction_result(
            transactions_added=1,
        ),
    )

    unexpected_analysis_files = list(
        tmp_path.glob("**/*analysis*")
    )

    assert unexpected_analysis_files == []


def test_forward_income_baseline_is_updated_by_existing_manager(
    tmp_path: Path,
) -> None:
    """Forward Income persistence remains owned by ForwardIncomeManager."""
    persist_current_portfolio(tmp_path)
    save_forward_income_assumption(tmp_path)

    coordinator = build_coordinator(tmp_path)

    coordinator.process(
        positions_import=make_positions_result(tmp_path),
    )

    manager = ForwardIncomeManager(
        make_portfolio(),
        tmp_path / "forward_income",
    )

    baseline = manager.run()

    assert baseline.analysis.total_forward_annual_income == Decimal(
        "2000.00"
    )
    