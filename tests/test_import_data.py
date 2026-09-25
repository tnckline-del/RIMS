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
    _render_import_health,
    _render_import_history,
    _recover_import,
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

from src.import_operation import ImportFileType, ImportStatus

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


def test_build_application_services_wires_import_workflow(
    monkeypatch,
) -> None:
    """Application services are built with the expected shared dependencies."""
    import_data_module = __import__(
        "app.pages.import_data",
        fromlist=["_build_application_services"],
    )

    captured: dict[str, object] = {}

    class FakeImportOperationStore:
        def __init__(self, path):
            captured["import_operation_store"] = self
            captured["import_operation_dir"] = path

    class FakeSnapshotStore:
        def __init__(self, path):
            captured["snapshot_store"] = self
            captured["snapshot_dir"] = path

    class FakeTransactionRepository:
        @classmethod
        def from_path(cls, path):
            instance = cls()
            captured["transaction_repository"] = instance
            captured["transaction_dir"] = path
            return instance

    class FakePositionsImporter:
        def __init__(self, **kwargs):
            captured["positions_importer_kwargs"] = kwargs

    class FakeTransactionsImporter:
        def __init__(self, **kwargs):
            captured["transactions_importer_kwargs"] = kwargs

    class FakeCoordinator:
        def __init__(self, **kwargs):
            captured["coordinator_kwargs"] = kwargs

    class FakeReconciliationService:
        def __init__(self, **kwargs):
            captured["reconciliation_kwargs"] = kwargs

    class FakeHealthService:
        def __init__(self, **kwargs):
            captured["health_kwargs"] = kwargs

    monkeypatch.setattr(
        import_data_module,
        "ImportOperationStore",
        FakeImportOperationStore,
    )
    monkeypatch.setattr(
        import_data_module,
        "SnapshotStore",
        FakeSnapshotStore,
    )
    monkeypatch.setattr(
        import_data_module,
        "TransactionRepository",
        FakeTransactionRepository,
    )
    monkeypatch.setattr(
        import_data_module,
        "ControlledPositionsImportService",
        FakePositionsImporter,
    )
    monkeypatch.setattr(
        import_data_module,
        "ControlledTransactionImportService",
        FakeTransactionsImporter,
    )
    monkeypatch.setattr(
        import_data_module,
        "PostImportProcessingCoordinator",
        FakeCoordinator,
    )
    monkeypatch.setattr(
        import_data_module,
        "ImportReconciliationService",
        FakeReconciliationService,
    )
    monkeypatch.setattr(
        import_data_module,
        "ImportHealthService",
        FakeHealthService,
    )

    services = import_data_module._build_application_services()

    positions_importer, transactions_importer, reconciliation_service, health_service = (
        services
    )

    assert positions_importer is not None
    assert transactions_importer is not None
    assert reconciliation_service is not None
    assert health_service is not None

    assert (
        captured["coordinator_kwargs"]["positions_import_service"]
        is positions_importer
    )
    assert (
        captured["coordinator_kwargs"]["transaction_repository"]
        is captured["transaction_repository"]
    )
    assert (
        captured["coordinator_kwargs"]["forward_income_storage_path"]
        == str(import_data_module.FORWARD_INCOME_DIR)
    )

    assert (
        captured["reconciliation_kwargs"]["import_operation_store"]
        is captured["import_operation_store"]
    )
    assert (
        captured["reconciliation_kwargs"]["snapshot_store"]
        is captured["snapshot_store"]
    )
    assert (
        captured["reconciliation_kwargs"]["transaction_repository"]
        is captured["transaction_repository"]
    )
    assert (
        captured["reconciliation_kwargs"]["post_import_processing_coordinator"]
        is not None
    )

    assert (
        captured["health_kwargs"]["import_operation_store"]
        is captured["import_operation_store"]
    )


def test_import_health_shows_info_when_no_operations(
    monkeypatch,
) -> None:
    """Import health shows an informational message when there are no operations."""
    messages: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.info",
        lambda message: messages.append(message),
    )

    class EmptyHealth:
        total_operations = 0
        summary = "No import operations recorded."

    class HealthService:
        def get_health(self):
            return EmptyHealth()

    _render_import_health(HealthService())

    assert messages == ["No import operations recorded."]


def test_import_history_shows_reconciled_operation(
    monkeypatch,
) -> None:
    """Import history shows a reconciled operation as successful."""
    messages: list[str] = []
    writes: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.success",
        lambda message: messages.append(message),
    )
    monkeypatch.setattr(
        "app.pages.import_data.st.write",
        lambda message: writes.append(message),
    )

    class Operation:
        source_file = "positions.csv"
        file_type = ImportFileType.POSITIONS
        status = ImportStatus.RECONCILED
        account = "Contributory-111"
        imported_at = date(2026, 9, 24)
        import_id = "test-import"

    class OperationStore:
        def list_operations(self):
            return [Operation()]

    class ReconciliationService:
        pass

    _render_import_history(
        import_operation_store=OperationStore(),
        reconciliation_service=ReconciliationService(),
    )

    assert messages == ["Reconciled"]
    assert writes[0] == "**positions.csv**"


def test_import_history_shows_reconciliation_failure_and_recovers(
    monkeypatch,
) -> None:
    """Import history shows a failed reconciliation and supports recovery."""
    warnings: list[str] = []
    buttons: list[str] = []
    recovery_calls: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.warning",
        lambda message: warnings.append(message),
    )
    monkeypatch.setattr(
        "app.pages.import_data.st.button",
        lambda label, **kwargs: buttons.append(label) or True,
    )

    class Operation:
        source_file = "positions.csv"
        file_type = ImportFileType.POSITIONS
        status = ImportStatus.RECONCILIATION_FAILED
        account = "Contributory-111"
        imported_at = date(2026, 9, 24)
        import_id = "test-import"

    class OperationStore:
        def list_operations(self):
            return [Operation()]

    class ReconciliationService:
        def recover(self, import_id):
            recovery_calls.append(import_id)

            class RecoveryResult:
                reconciled = False

            return RecoveryResult()

    _render_import_history(
        import_operation_store=OperationStore(),
        reconciliation_service=ReconciliationService(),
    )

    assert warnings == ["This import requires reconciliation."]
    assert buttons == ["Recover"]
    assert recovery_calls == ["test-import"]


def test_recover_import_shows_success_and_reruns(
    monkeypatch,
) -> None:
    """Successful import recovery shows success and reruns the page."""
    messages: list[str] = []
    reruns: list[bool] = []
    recovery_calls: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.success",
        lambda message: messages.append(message),
    )
    monkeypatch.setattr(
        "app.pages.import_data.st.rerun",
        lambda: reruns.append(True),
    )

    class ReconciliationService:
        def recover(self, import_id):
            recovery_calls.append(import_id)

            class RecoveryResult:
                reconciled = True

            return RecoveryResult()

    _recover_import(
        import_id="test-import",
        reconciliation_service=ReconciliationService(),
    )

    assert recovery_calls == ["test-import"]
    assert messages == [
        "Import recovery completed and the import is reconciled."
    ]
    assert reruns == [True]


def test_recover_import_shows_error_when_recovery_raises(
    monkeypatch,
) -> None:
    """Import recovery reports an error when recovery raises."""
    errors: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.error",
        lambda message: errors.append(message),
    )

    class ReconciliationService:
        def recover(self, import_id):
            raise RuntimeError("controlled recovery failure")

    _recover_import(
        import_id="test-import",
        reconciliation_service=ReconciliationService(),
    )

    assert errors == [
        "Import recovery failed: controlled recovery failure"
    ]


def test_recover_import_shows_error_when_recovery_is_not_reconciled(
    monkeypatch,
) -> None:
    """Import recovery reports an error when reconciliation remains unresolved."""
    errors: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.error",
        lambda message: errors.append(message),
    )

    class ReconciliationService:
        def recover(self, import_id):
            class RecoveryResult:
                reconciled = False

            return RecoveryResult()

    _recover_import(
        import_id="test-import",
        reconciliation_service=ReconciliationService(),
    )

    assert errors == [
        "Import recovery did not complete successfully. "
        "Review the import history and try again."
    ]


def test_import_health_warns_when_reconciliation_has_failed(
    monkeypatch,
) -> None:
    """Import health shows a warning when reconciliation issues exist."""
    warnings: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.warning",
        lambda message: warnings.append(message),
    )

    class UnhealthyImportHealth:
        total_operations = 3
        reconciled_operations = 2
        reconciliation_failed_operations = 1
        all_reconciled = False
        summary = "1 import requires reconciliation."

    class HealthService:
        def get_health(self):
            return UnhealthyImportHealth()

    _render_import_health(HealthService())

    assert warnings == ["1 import requires reconciliation."]


def test_import_health_shows_success_when_all_reconciled(
    monkeypatch,
) -> None:
    """Import health shows success when all imports are reconciled."""
    messages: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.success",
        lambda message: messages.append(message),
    )

    class HealthyImportHealth:
        total_operations = 3
        reconciled_operations = 3
        reconciliation_failed_operations = 0
        all_reconciled = True
        summary = "All imports are reconciled."

    class HealthService:
        def get_health(self):
            return HealthyImportHealth()

    _render_import_health(HealthService())

    assert messages == ["All imports are reconciled."]


def test_import_health_shows_info_when_reconciliation_is_pending(
    monkeypatch,
) -> None:
    """Import health shows info when reconciliation is still pending."""
    messages: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.info",
        lambda message: messages.append(message),
    )

    class PendingImportHealth:
        total_operations = 3
        reconciled_operations = 2
        reconciliation_failed_operations = 0
        all_reconciled = False
        summary = "1 import is pending reconciliation."

    class HealthService:
        def get_health(self):
            return PendingImportHealth()

    _render_import_health(HealthService())

    assert messages == ["1 import is pending reconciliation."]


def test_import_history_shows_info_when_no_operations(
    monkeypatch,
) -> None:
    """Import history shows an informational message when empty."""
    messages: list[str] = []

    monkeypatch.setattr(
        "app.pages.import_data.st.info",
        lambda message: messages.append(message),
    )

    class EmptyOperationStore:
        def list_operations(self):
            return []

    class ReconciliationService:
        pass

    _render_import_history(
        import_operation_store=EmptyOperationStore(),
        reconciliation_service=ReconciliationService(),
    )

    assert messages == ["No import operations recorded."]


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

    _import_positions(
        FailingPositionsImporter(),
        object(),
    )

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
    reconciliation_calls = []

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

    class SuccessfulReconciliationService:
        def reconcile(self, **kwargs):
            reconciliation_calls.append(kwargs)

            class ReconciliationResult:
                reconciled = True

            return ReconciliationResult()

    _import_positions(
        SuccessfulPositionsImporter(),
        SuccessfulReconciliationService(),
    )

    assert session_state[POSITIONS_IMPORT_RESULT] is import_result
    assert reconciliation_calls == [{"positions_import": import_result}]
    assert (
        session_state[POSITIONS_IMPORTED_FILE]
        == _calculate_uploaded_file_hash(file_bytes)
    )
    assert POSITIONS_VALIDATION not in session_state

def test_import_positions_reconciliation_failure_shows_error(
    monkeypatch,
) -> None:
    """A positions import reports a reconciliation failure."""
    file_bytes = b"positions test data"
    validation_result = object()
    import_result = object()
    errors: list[str] = []

    session_state = {
        POSITIONS_FILE_NAME: "positions.csv",
        POSITIONS_FILE_BYTES: file_bytes,
        POSITIONS_VALIDATION: validation_result,
    }

    monkeypatch.setattr(
        "app.pages.import_data.st.session_state",
        session_state,
    )
    monkeypatch.setattr(
        "app.pages.import_data.st.error",
        lambda message: errors.append(message),
    )


    class SuccessfulPositionsImporter:
        def import_positions(self, **kwargs):
            assert kwargs["validation_result"] is validation_result
            assert kwargs["source_file"].exists()
            return import_result

    class FailedReconciliationService:
        def reconcile(self, **kwargs):
            assert kwargs == {"positions_import": import_result}

            class ReconciliationResult:
                reconciled = False

            return ReconciliationResult()
    _import_positions(
        SuccessfulPositionsImporter(),
        FailedReconciliationService(),
    )
    assert errors == [
        "Positions import completed, but post-import reconciliation "
        "failed. Use Recover in Import History."
    ]
    assert session_state[POSITIONS_IMPORT_RESULT] is import_result
    assert (
        session_state[POSITIONS_IMPORTED_FILE]
        == _calculate_uploaded_file_hash(file_bytes)
    )
    assert POSITIONS_VALIDATION not in session_state

def test_import_transactions_reconciliation_failure_shows_error(
    monkeypatch,
) -> None:
    """A transaction import reports a reconciliation failure."""
    file_bytes = b"transactions test data"
    validation_result = object()
    import_result = object()
    errors: list[str] = []

    session_state = {
        TRANSACTION_FILE_NAME: "transactions.csv",
        TRANSACTION_FILE_BYTES: file_bytes,
        TRANSACTION_VALIDATION: validation_result,
    }

    monkeypatch.setattr(
        "app.pages.import_data.st.session_state",
        session_state,
    )
    monkeypatch.setattr(
        "app.pages.import_data.st.error",
        lambda message: errors.append(message),
    )

    class SuccessfulTransactionsImporter:
        def import_transactions(self, **kwargs):
            assert kwargs["validation_result"] is validation_result
            assert kwargs["source_file"].exists()
            return import_result

    class FailedReconciliationService:
        def reconcile(self, **kwargs):
            assert kwargs == {"transactions_import": import_result}

            class ReconciliationResult:
                reconciled = False

            return ReconciliationResult()

    _import_transactions(
        SuccessfulTransactionsImporter(),
        FailedReconciliationService(),
    )

    assert errors == [
        "Transaction import completed, but post-import reconciliation "
        "failed. Use Recover in Import History."
    ]
    assert session_state[TRANSACTION_IMPORT_RESULT] is import_result
    assert (
        session_state[TRANSACTION_IMPORTED_FILE]
        == _calculate_uploaded_file_hash(file_bytes)
    )
    assert TRANSACTION_VALIDATION not in session_state


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

    _import_transactions(
        FailingTransactionsImporter(),
        object(),
    )

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
    reconciliation_calls = []

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

    class SuccessfulReconciliationService:
        def reconcile(self, **kwargs):
            reconciliation_calls.append(kwargs)
            class ReconciliationResult:
                reconciled = True

            return ReconciliationResult()

    _import_transactions(
        SuccessfulTransactionsImporter(),
        SuccessfulReconciliationService(),
    )

    assert session_state[TRANSACTION_IMPORT_RESULT] is import_result
    assert (
        session_state[TRANSACTION_IMPORTED_FILE]
        == _calculate_uploaded_file_hash(file_bytes)
    )
    assert TRANSACTION_VALIDATION not in session_state
    assert reconciliation_calls == [
        {"transactions_import": import_result}
    ]

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
