"""
Tests for the controlled Schwab transaction import service.

These tests exercise the boundary between validated transaction data,
transaction persistence, and import-operation tracking.

The tests intentionally use synthetic InvestmentTransaction objects rather
than depending on a personal Schwab export file.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.import_service import TransactionsValidationResult
from src.controlled_transaction_import import (
    ControlledTransactionImportService,
)
from src.import_operation import ImportStatus
from src.import_operation_store import ImportOperationStore
from src.transaction import (
    IncomeCharacter,
    IncomeType,
    InvestmentTransaction,
    TaxCharacter,
    TransactionType,
)
from src.transaction_repository import TransactionRepository


ACCOUNT = "TEST-ACCOUNT"
SOURCE_FILE = "schwab-transactions-2026-09-07.csv"


@dataclass(frozen=True)
class FakeImportResult:
    """Minimal transaction import result used by these unit tests."""

    transactions: tuple[InvestmentTransaction, ...]


def make_transaction(
    *,
    transaction_date: date = date(2026, 9, 1),
    symbol: str = "ARCC",
    amount: str = "100.00",
    action: str = "Cash Dividend",
    income_character: IncomeCharacter = IncomeCharacter.RECURRING,
    source_file: str = SOURCE_FILE,
) -> InvestmentTransaction:
    """Create a valid test income transaction."""
    return InvestmentTransaction(
        account=ACCOUNT,
        transaction_date=transaction_date,
        action=action,
        symbol=symbol,
        description="Test transaction",
        amount=Decimal(amount),
        transaction_type=TransactionType.INCOME,
        income_type=IncomeType.DIVIDEND,
        income_character=income_character,
        tax_character=TaxCharacter.UNKNOWN,
        source_file=source_file,
    )


def make_purchase_transaction(
    *,
    transaction_date: date = date(2026, 9, 2),
    symbol: str = "ARCC",
    amount: str = "-1000.00",
    source_file: str = SOURCE_FILE,
) -> InvestmentTransaction:
    """Create a valid non-income test transaction."""
    return InvestmentTransaction(
        account=ACCOUNT,
        transaction_date=transaction_date,
        action="Buy",
        symbol=symbol,
        description="Test purchase",
        amount=Decimal(amount),
        transaction_type=TransactionType.PURCHASE,
        source_file=source_file,
    )


def make_validation_result(
    source_path: Path,
    transactions: tuple[InvestmentTransaction, ...],
    *,
    account: str = ACCOUNT,
    is_valid: bool = True,
    import_result: FakeImportResult | None = None,
) -> TransactionsValidationResult:
    """Create a transaction validation result for testing."""
    if import_result is None:
        import_result = FakeImportResult(transactions=transactions)

    income_transactions = tuple(
        transaction
        for transaction in transactions
        if transaction.is_income
    )

    recurring_income_transactions = tuple(
        transaction
        for transaction in income_transactions
        if transaction.is_recurring_income
    )

    return TransactionsValidationResult(
        is_valid=is_valid,
        source_file=source_path.name,
        account=account,
        transaction_count=len(transactions),
        income_transaction_count=len(income_transactions),
        recurring_income_amount=sum(
            (
                transaction.amount
                for transaction in recurring_income_transactions
            ),
            Decimal("0"),
        ),
        start_date=(
            min(transaction.transaction_date for transaction in transactions)
            if transactions
            else None
        ),
        end_date=(
            max(transaction.transaction_date for transaction in transactions)
            if transactions
            else None
        ),
        import_result=import_result,
    )


def build_service(
    tmp_path: Path,
) -> ControlledTransactionImportService:
    """Create an isolated controlled transaction import service."""
    operation_store = ImportOperationStore(
        tmp_path / "import_operations"
    )
    transaction_repository = TransactionRepository.from_path(
        tmp_path / "transactions"
    )

    return ControlledTransactionImportService(
        import_operation_store=operation_store,
        transaction_repository=transaction_repository,
    )


def create_source_file(tmp_path: Path) -> Path:
    """Create a deterministic temporary source file."""
    source_file = tmp_path / SOURCE_FILE
    source_file.write_text(
        "synthetic Schwab transaction export\n",
        encoding="utf-8",
    )
    return source_file


def test_successful_import_persists_transactions_and_operation(
    tmp_path: Path,
) -> None:
    """A valid transaction import persists data and becomes IMPORTED."""
    service = build_service(tmp_path)
    source_file = create_source_file(tmp_path)

    transactions = (
        make_transaction(
            transaction_date=date(2026, 9, 1),
            symbol="ARCC",
            amount="100.00",
        ),
        make_purchase_transaction(),
    )

    validation_result = make_validation_result(
        source_file,
        transactions,
    )

    result = service.import_transactions(
        validation_result,
        source_file,
    )

    assert result.operation.status is ImportStatus.IMPORTED
    assert result.operation.file_type.value == "Transactions"
    assert result.operation.source_file == SOURCE_FILE
    assert result.operation.account == ACCOUNT
    assert result.operation.reporting_start_date == date(2026, 9, 1)
    assert result.operation.reporting_end_date == date(2026, 9, 2)

    assert result.source_transaction_count == 2
    assert result.transactions_added == 2
    assert result.duplicates_skipped == 0
    assert result.income_transactions_added == 1
    assert result.recurring_income_transactions_added == 1

    persisted = service.transaction_repository.all_transactions()

    assert len(persisted) == 2


def test_import_result_uses_transactions_actually_added(
    tmp_path: Path,
) -> None:
    """Income counts describe newly added transactions, not source totals."""
    service = build_service(tmp_path)
    source_file = create_source_file(tmp_path)

    first_transaction = make_transaction(
        transaction_date=date(2026, 9, 1),
        symbol="ARCC",
        amount="100.00",
        income_character=IncomeCharacter.RECURRING,
    )

    second_transaction = make_transaction(
        transaction_date=date(2026, 9, 2),
        symbol="BXSL",
        amount="200.00",
        income_character=IncomeCharacter.SPECIAL,
    )

    transactions = (
        first_transaction,
        second_transaction,
    )

    validation_result = make_validation_result(
        source_file,
        transactions,
    )

    result = service.import_transactions(
        validation_result,
        source_file,
    )

    assert result.transactions_added == 2
    assert result.income_transactions_added == 2
    assert result.recurring_income_transactions_added == 1
    assert len(result.append_result.added_transactions) == 2


def test_duplicate_transactions_are_skipped(
    tmp_path: Path,
) -> None:
    """Previously persisted transactions are not added a second time."""
    service = build_service(tmp_path)

    first_source = create_source_file(tmp_path)

    transaction = make_transaction(
        transaction_date=date(2026, 9, 1),
        symbol="ARCC",
        amount="100.00",
    )

    first_validation = make_validation_result(
        first_source,
        (transaction,),
    )

    first_result = service.import_transactions(
        first_validation,
        first_source,
    )

    assert first_result.transactions_added == 1

    second_source = tmp_path / "schwab-transactions-2026-09-14.csv"
    second_source.write_text(
        "synthetic Schwab transaction export - second file\n",
        encoding="utf-8",
    )    

    duplicate_transaction = make_transaction(
        transaction_date=date(2026, 9, 1),
        symbol="ARCC",
        amount="100.00",
        source_file=second_source.name,
    )

    second_validation = make_validation_result(
        second_source,
        (duplicate_transaction,),
    )

    second_result = service.import_transactions(
        second_validation,
        second_source,
    )

    assert second_result.operation.status is ImportStatus.IMPORTED
    assert second_result.transactions_added == 0
    assert second_result.duplicates_skipped == 1
    assert second_result.income_transactions_added == 0
    assert second_result.recurring_income_transactions_added == 0

    persisted = service.transaction_repository.all_transactions()

    assert len(persisted) == 1


def test_duplicate_source_file_is_rejected(
    tmp_path: Path,
) -> None:
    """The same physical source file cannot be imported twice."""
    service = build_service(tmp_path)
    source_file = create_source_file(tmp_path)

    transaction = make_transaction()

    validation_result = make_validation_result(
        source_file,
        (transaction,),
    )

    service.import_transactions(
        validation_result,
        source_file,
    )

    with pytest.raises(FileExistsError):
        service.import_transactions(
            validation_result,
            source_file,
        )


def test_invalid_validation_result_is_rejected(
    tmp_path: Path,
) -> None:
    """An invalid validation result cannot enter the import path."""
    service = build_service(tmp_path)
    source_file = create_source_file(tmp_path)

    transaction = make_transaction()

    validation_result = make_validation_result(
        source_file,
        (transaction,),
        is_valid=False,
    )

    with pytest.raises(ValueError, match="invalid"):
        service.import_transactions(
            validation_result,
            source_file,
        )


def test_source_filename_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    """The physical source filename must match the validated filename."""
    service = build_service(tmp_path)
    source_file = create_source_file(tmp_path)

    transaction = make_transaction()

    validation_result = TransactionsValidationResult(
        is_valid=True,
        source_file="different-file.csv",
        account=ACCOUNT,
        transaction_count=1,
        income_transaction_count=1,
        recurring_income_amount=Decimal("100.00"),
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 1),
        import_result=FakeImportResult(
            transactions=(transaction,),
        ),
    )

    with pytest.raises(ValueError, match="Source file name"):
        service.import_transactions(
            validation_result,
            source_file,
        )


def test_missing_source_file_is_rejected(
    tmp_path: Path,
) -> None:
    """A missing source file cannot be imported."""
    service = build_service(tmp_path)

    source_file = tmp_path / SOURCE_FILE

    validation_result = TransactionsValidationResult(
        is_valid=True,
        source_file=SOURCE_FILE,
        account=ACCOUNT,
        transaction_count=0,
        income_transaction_count=0,
        recurring_income_amount=Decimal("0"),
        start_date=None,
        end_date=None,
        import_result=FakeImportResult(
            transactions=(),
        ),
    )

    with pytest.raises(FileNotFoundError):
        service.import_transactions(
            validation_result,
            source_file,
        )


def test_missing_import_result_is_rejected(
    tmp_path: Path,
) -> None:
    """Validated results must retain the parsed transaction data."""
    service = build_service(tmp_path)
    source_file = create_source_file(tmp_path)

    validation_result = TransactionsValidationResult(
        is_valid=True,
        source_file=SOURCE_FILE,
        account=ACCOUNT,
        transaction_count=0,
        income_transaction_count=0,
        recurring_income_amount=Decimal("0"),
        start_date=None,
        end_date=None,
        import_result=None,
    )

    with pytest.raises(ValueError, match="import result"):
        service.import_transactions(
            validation_result,
            source_file,
        )


def test_wrong_validation_result_type_is_rejected(
    tmp_path: Path,
) -> None:
    """The controlled service requires its specific validation contract."""
    service = build_service(tmp_path)
    source_file = create_source_file(tmp_path)

    with pytest.raises(TypeError):
        service.import_transactions(
            object(),  # type: ignore[arg-type]
            source_file,
        )


def test_repository_failure_marks_operation_import_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repository failure changes the operation to IMPORT_FAILED."""
    service = build_service(tmp_path)
    source_file = create_source_file(tmp_path)

    transaction = make_transaction()

    validation_result = make_validation_result(
        source_file,
        (transaction,),
    )

    def fail_append(*args: object, **kwargs: object) -> object:
        """Simulate transaction persistence failure."""
        raise RuntimeError("simulated transaction persistence failure")

    monkeypatch.setattr(
        TransactionRepository,
        "append_unique_transactions",
        fail_append,
    )

    with pytest.raises(
        RuntimeError,
        match="simulated transaction persistence failure",
    ):
        service.import_transactions(
            validation_result,
            source_file,
        )

    operation_store = service.import_operation_store

    operations = operation_store.list_operations()

    assert len(operations) == 1
    assert operations[0].status is ImportStatus.IMPORT_FAILED

    assert (
        service.transaction_repository.all_transactions()
        == ()
    )
