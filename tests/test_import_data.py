"""Tests for the RIMS Import Data page."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.pages.import_data import (
    POSITIONS_FILE_BYTES,
    POSITIONS_FILE_NAME,
    POSITIONS_IMPORT_RESULT,
    POSITIONS_IMPORTED_FILE,
    POSITIONS_VALIDATION,
    _calculate_uploaded_file_hash,
    _display_positions_result,
    _display_transactions_result,
    _import_positions,
    TRANSACTION_FILE_BYTES,
    TRANSACTION_FILE_NAME,
    TRANSACTION_IMPORT_RESULT,
    TRANSACTION_IMPORTED_FILE,
    TRANSACTION_VALIDATION,
    TRANSACTION_ACCOUNT,
    _import_transactions,
    _handle_transaction_account_change,
)

from app.services.import_service import (
    PositionsValidationResult,
    TransactionsValidationResult,
)


def test_positions_display_handles_validation_failure(
    monkeypatch,
) -> None:
    """Positions validation failures are displayed as errors."""
    messages: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.error",
        lambda message: messages.append(message),
    )

    result = PositionsValidationResult(
        is_valid=False,
        source_file="invalid.csv",
        holding_count=0,
        market_value_difference=Decimal("0"),
        cost_basis_difference=Decimal("0"),
        is_reconciled=False,
        error="Invalid Schwab positions file",
    )

    _display_positions_result(result)

    assert messages == [
        "Positions validation failed: Invalid Schwab positions file"
    ]


def test_positions_display_handles_reconciled_result(
    monkeypatch,
) -> None:
    """A reconciled positions result is displayed as success."""
    messages: list[str] = []
    metrics: list[tuple[str, object]] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.success",
        lambda message: messages.append(message),
    )
    monkeypatch.setattr(
        "app.pages.import_data.st.metric",
        lambda label, value: metrics.append((label, value)),
    )

    result = PositionsValidationResult(
        is_valid=True,
        source_file="positions.csv",
        holding_count=44,
        market_value_difference=Decimal("0.00"),
        cost_basis_difference=Decimal("0.00"),
        is_reconciled=True,
    )

    _display_positions_result(result)

    assert messages == ["Positions file validated and reconciled."]
    assert metrics == [
        ("Holdings", 44),
        ("Market Value Difference", "$0.00"),
        ("Cost Basis Difference", "$0.00"),
    ]


def test_positions_display_handles_unreconciled_result(
    monkeypatch,
) -> None:
    """An unreconciled positions result is displayed as a warning."""
    messages: list[str] = []
    warnings: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.success",
        lambda message: messages.append(message),
    )
    monkeypatch.setattr(
        "app.pages.import_data.st.warning",
        lambda message: warnings.append(message),
    )
    monkeypatch.setattr(
        "app.pages.import_data.st.metric",
        lambda label, value: None,
    )

    result = PositionsValidationResult(
        is_valid=True,
        source_file="positions.csv",
        holding_count=44,
        market_value_difference=Decimal("1.00"),
        cost_basis_difference=Decimal("2.00"),
        is_reconciled=False,
    )

    _display_positions_result(result)

    assert messages == []
    assert len(warnings) == 1
    assert "reconciliation did not pass" in warnings[0]


def test_transactions_display_handles_validation_failure(
    monkeypatch,
) -> None:
    """Transaction validation failures are displayed as errors."""
    messages: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.error",
        lambda message: messages.append(message),
    )

    result = TransactionsValidationResult(
        is_valid=False,
        source_file="invalid.csv",
        account="Contributory-111",
        transaction_count=0,
        income_transaction_count=0,
        recurring_income_amount=Decimal("0"),
        start_date=None,
        end_date=None,
        error="Could not locate the Schwab transaction header row.",
    )

    _display_transactions_result(result)

    assert messages == [
        "Transaction validation failed: "
        "Could not locate the Schwab transaction header row."
    ]


def test_transactions_display_handles_valid_result(
    monkeypatch,
) -> None:
    """A valid transaction result displays its key validation information."""
    messages: list[str] = []
    metrics: list[tuple[str, object]] = []
    writes: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.success",
        lambda message: messages.append(message),
    )
    monkeypatch.setattr(
        "app.pages.import_data.st.metric",
        lambda label, value: metrics.append((label, value)),
    )
    monkeypatch.setattr(
        "app.pages.import_data.st.write",
        lambda message: writes.append(message),
    )

    result = TransactionsValidationResult(
        is_valid=True,
        source_file="transactions.csv",
        account="Contributory-111",
        transaction_count=22,
        income_transaction_count=21,
        recurring_income_amount=Decimal("2855.75"),
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )

    _display_transactions_result(result)

    assert messages == ["Transactions file validated successfully."]
    assert metrics == [
        ("Transactions", 22),
        ("Income Transactions", 21),
        ("Recurring Income", "$2,855.75"),
    ]
    assert writes == [
        "**Transaction date range:** 07/01/2026 – 07/31/2026"
    ]


def test_transactions_display_handles_empty_date_range(
    monkeypatch,
) -> None:
    """A valid transaction result without transactions omits the date range."""
    messages: list[str] = []
    metrics: list[tuple[str, object]] = []
    writes: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.success",
        lambda message: messages.append(message),
    )
    monkeypatch.setattr(
        "app.pages.import_data.st.metric",
        lambda label, value: metrics.append((label, value)),
    )
    monkeypatch.setattr(
        "app.pages.import_data.st.write",
        lambda message: writes.append(message),
    )

    result = TransactionsValidationResult(
        is_valid=True,
        source_file="empty.csv",
        account="Test Account",
        transaction_count=0,
        income_transaction_count=0,
        recurring_income_amount=Decimal("0"),
        start_date=None,
        end_date=None,
    )

    _display_transactions_result(result)

    assert messages == ["Transactions file validated successfully."]
    assert metrics == [
        ("Transactions", 0),
        ("Income Transactions", 0),
        ("Recurring Income", "$0.00"),
    ]
    assert writes == []

def test_uploaded_file_hash_is_deterministic() -> None:
    """Uploaded file hashing uses SHA-256 deterministically."""
    file_bytes = b"RIMS test file contents"

    first_hash = _calculate_uploaded_file_hash(file_bytes)
    second_hash = _calculate_uploaded_file_hash(file_bytes)

    assert first_hash == second_hash
    assert len(first_hash) == 64

def test_uploaded_file_hash_changes_when_file_content_changes() -> None:
    """Different uploaded file contents produce different hashes."""
    first_hash = _calculate_uploaded_file_hash(
        b"RIMS test file contents"
    )
    second_hash = _calculate_uploaded_file_hash(
        b"Different RIMS test file contents"
    )

    assert first_hash != second_hash

def test_import_positions_failure_does_not_mark_file_as_imported(
    monkeypatch,
) -> None:
    """A failed positions import does not record an imported-file hash."""
    session_state = {
        POSITIONS_FILE_NAME: "positions.csv",
        POSITIONS_FILE_BYTES: b"positions test data",
        POSITIONS_VALIDATION: object(),
    }
    errors: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.session_state",
        session_state,
    )
    monkeypatch.setattr(
        "app.pages.import_data.st.error",
        lambda message: errors.append(message),
    )

    class FailingPositionsImporter:
        def import_positions(self, **kwargs):
            raise RuntimeError("controlled import failed")

    _import_positions(FailingPositionsImporter())

    assert errors == ["Positions import failed: controlled import failed"]
    assert POSITIONS_IMPORT_RESULT not in session_state
    assert POSITIONS_IMPORTED_FILE not in session_state
    assert POSITIONS_VALIDATION in session_state

def test_import_positions_success_records_hash_and_clears_validation(
    monkeypatch,
) -> None:
    """A successful positions import records its hash and clears validation."""
    file_bytes = b"positions test data"
    validation_result = object()
    import_result = object()

    session_state = {
        POSITIONS_FILE_NAME: "positions.csv",
        POSITIONS_FILE_BYTES: file_bytes,
        POSITIONS_VALIDATION: validation_result,
    }

    monkeypatch.setattr(
        "app.pages.import_data.st.session_state",
        session_state,
    )

    class SuccessfulPositionsImporter:
        def import_positions(self, **kwargs):
            assert kwargs["validation_result"] is validation_result
            assert kwargs["source_file"].exists()
            return import_result

    _import_positions(SuccessfulPositionsImporter())

    assert session_state[POSITIONS_IMPORT_RESULT] is import_result
    assert (
        session_state[POSITIONS_IMPORTED_FILE]
        == _calculate_uploaded_file_hash(file_bytes)
    )
    assert POSITIONS_VALIDATION not in session_state

def test_import_positions_success_records_hash_and_clears_validation(
    monkeypatch,
) -> None:
    """A successful positions import records its hash and clears validation."""
    file_bytes = b"positions test data"
    validation_result = object()
    import_result = object()

    session_state = {
        POSITIONS_FILE_NAME: "positions.csv",
        POSITIONS_FILE_BYTES: file_bytes,
        POSITIONS_VALIDATION: validation_result,
    }

    monkeypatch.setattr(
        "app.pages.import_data.st.session_state",
        session_state,
    )

    class SuccessfulPositionsImporter:
        def import_positions(self, **kwargs):
            assert kwargs["validation_result"] is validation_result
            assert kwargs["source_file"].exists()
            return import_result

    _import_positions(SuccessfulPositionsImporter())

    assert session_state[POSITIONS_IMPORT_RESULT] is import_result
    assert (
        session_state[POSITIONS_IMPORTED_FILE]
        == _calculate_uploaded_file_hash(file_bytes)
    )
    assert POSITIONS_VALIDATION not in session_state

def test_import_transactions_failure_does_not_mark_file_as_imported(
    monkeypatch,
) -> None:
    """A failed transaction import does not record an imported-file hash."""
    session_state = {
        TRANSACTION_FILE_NAME: "transactions.csv",
        TRANSACTION_FILE_BYTES: b"transactions test data",
        TRANSACTION_VALIDATION: object(),
    }
    errors: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.session_state",
        session_state,
    )
    monkeypatch.setattr(
        "app.pages.import_data.st.error",
        lambda message: errors.append(message),
    )

    class FailingTransactionsImporter:
        def import_transactions(self, **kwargs):
            raise RuntimeError("controlled transaction import failed")

    _import_transactions(FailingTransactionsImporter())

    assert errors == [
        "Transaction import failed: controlled transaction import failed"
    ]
    assert TRANSACTION_IMPORT_RESULT not in session_state
    assert TRANSACTION_IMPORTED_FILE not in session_state
    assert TRANSACTION_VALIDATION in session_state

def test_import_transactions_success_records_hash_and_clears_validation(
    monkeypatch,
) -> None:
    """A successful transaction import records its hash and clears validation."""
    file_bytes = b"transactions test data"
    validation_result = object()
    import_result = object()

    session_state = {
        TRANSACTION_FILE_NAME: "transactions.csv",
        TRANSACTION_FILE_BYTES: file_bytes,
        TRANSACTION_VALIDATION: validation_result,
    }

    monkeypatch.setattr(
        "app.pages.import_data.st.session_state",
        session_state,
    )

    class SuccessfulTransactionsImporter:
        def import_transactions(self, **kwargs):
            assert kwargs["validation_result"] is validation_result
            assert kwargs["source_file"].exists()
            return import_result

    _import_transactions(SuccessfulTransactionsImporter())

    assert session_state[TRANSACTION_IMPORT_RESULT] is import_result
    assert (
        session_state[TRANSACTION_IMPORTED_FILE]
        == _calculate_uploaded_file_hash(file_bytes)
    )
    assert TRANSACTION_VALIDATION not in session_state

def test_transaction_account_change_clears_validation_and_import_result(
    monkeypatch,
) -> None:
    """Changing the transaction account invalidates prior transaction results."""
    session_state = {
        TRANSACTION_ACCOUNT: "Contributory-111",
        TRANSACTION_VALIDATION: object(),
        TRANSACTION_IMPORT_RESULT: object(),
    }

    monkeypatch.setattr(
        "app.pages.import_data.st.session_state",
        session_state,
    )

    _handle_transaction_account_change("Contributory-941")

    assert session_state[TRANSACTION_ACCOUNT] == "Contributory-941"
    assert TRANSACTION_VALIDATION not in session_state
    assert TRANSACTION_IMPORT_RESULT not in session_state

def test_transaction_account_unchanged_preserves_validation_and_import_result(
    monkeypatch,
) -> None:
    """Keeping the same transaction account preserves prior results."""
    validation_result = object()
    import_result = object()

    session_state = {
        TRANSACTION_ACCOUNT: "Contributory-111",
        TRANSACTION_VALIDATION: validation_result,
        TRANSACTION_IMPORT_RESULT: import_result,
    }

    monkeypatch.setattr(
        "app.pages.import_data.st.session_state",
        session_state,
    )

    _handle_transaction_account_change("Contributory-111")

    assert session_state[TRANSACTION_ACCOUNT] == "Contributory-111"
    assert session_state[TRANSACTION_VALIDATION] is validation_result
    assert session_state[TRANSACTION_IMPORT_RESULT] is import_result
