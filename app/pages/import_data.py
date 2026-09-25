"""RIMS Import Data page."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

from app.app_config import (
    FORWARD_INCOME_DIR,
    IMPORT_OPERATION_DIR,
    SNAPSHOT_DIR,
    TRANSACTION_DIR,
)
from app.services.import_service import ImportService
from src.controlled_positions_import import (
    ControlledPositionsImportService,
)
from src.controlled_transaction_import import (
    ControlledTransactionImportService,
)
from src.import_health import ImportHealthService
from src.import_operation import ImportStatus
from src.import_operation_store import ImportOperationStore
from src.import_reconciliation import ImportReconciliationService
from src.post_import_processing import PostImportProcessingCoordinator
from src.snapshot_store import SnapshotStore
from src.transaction_repository import TransactionRepository


# Session-state keys
POSITIONS_FILE_NAME = "import_positions_file_name"
POSITIONS_FILE_BYTES = "import_positions_file_bytes"
POSITIONS_VALIDATION = "import_positions_validation"
POSITIONS_IMPORT_RESULT = "import_positions_import_result"
POSITIONS_IMPORTED_FILE = "import_positions_imported_file"

TRANSACTION_FILE_NAME = "import_transaction_file_name"
TRANSACTION_FILE_BYTES = "import_transaction_file_bytes"
TRANSACTION_ACCOUNT = "import_transaction_account"
TRANSACTION_VALIDATION = "import_transaction_validation"
TRANSACTION_IMPORT_RESULT = "import_transaction_import_result"
TRANSACTION_IMPORTED_FILE = "import_transaction_imported_file"

def _calculate_uploaded_file_hash(file_bytes: bytes) -> str:
    """Return the SHA-256 hash for uploaded file content."""
    return hashlib.sha256(file_bytes).hexdigest()


def render_import_data() -> None:
    """Render the controlled Schwab import workflow."""
    st.title("Import Data")
    st.caption(
        "Select Schwab files, validate them, review the results, "
        "and explicitly import them into RIMS."
    )
    st.divider()

    import_service = ImportService()
    (
        positions_importer,
        transactions_importer,
        reconciliation_service,
        health_service,
    ) = _build_application_services()

    import_operation_store = ImportOperationStore(
        IMPORT_OPERATION_DIR,
    )

    _render_import_health(health_service)

    st.divider()

    _render_import_history(
        import_operation_store=import_operation_store,
        reconciliation_service=reconciliation_service,
    )

    st.divider()

    _render_positions_section(
        import_service=import_service,
        positions_importer=positions_importer,
        reconciliation_service=reconciliation_service,
    )

    st.divider()

    _render_transactions_section(
        import_service=import_service,
        transactions_importer=transactions_importer,
        reconciliation_service=reconciliation_service,
    )


def _build_application_services() -> tuple[
    ControlledPositionsImportService,
    ControlledTransactionImportService,
    ImportReconciliationService,
    ImportHealthService,
]:
    """Build the application services used by the import workflow."""
    import_operation_store = ImportOperationStore(
        IMPORT_OPERATION_DIR,
    )
    snapshot_store = SnapshotStore(SNAPSHOT_DIR)
    transaction_repository = TransactionRepository.from_path(
        TRANSACTION_DIR,
    )

    positions_importer = ControlledPositionsImportService(
        import_operation_store=import_operation_store,
        snapshot_store=snapshot_store,
    )

    transactions_importer = ControlledTransactionImportService(
        import_operation_store=import_operation_store,
        transaction_repository=transaction_repository,
    )

    post_import_processing_coordinator = PostImportProcessingCoordinator(
        positions_import_service=positions_importer,
        transaction_repository=transaction_repository,
        forward_income_storage_path=str(FORWARD_INCOME_DIR),
    )

    reconciliation_service = ImportReconciliationService(
        import_operation_store=import_operation_store,
        snapshot_store=snapshot_store,
        transaction_repository=transaction_repository,
        post_import_processing_coordinator=post_import_processing_coordinator,
    )

    health_service = ImportHealthService(
        import_operation_store=import_operation_store,
    )

    return (
        positions_importer,
        transactions_importer,
        reconciliation_service,
        health_service,
    )


def _render_positions_section(
    import_service: ImportService,
    positions_importer: ControlledPositionsImportService,
    reconciliation_service: ImportReconciliationService,
) -> None:
    """Render the positions validation and import workflow."""
    st.header("Schwab Positions")

    positions_file = st.file_uploader(
        "Select a Schwab positions CSV file",
        type=["csv"],
        key="positions_file",
        help="Choose an All-Accounts-Positions CSV exported from Schwab.",
    )

    if positions_file is not None:
        _handle_positions_file_selection(
            positions_file,
            import_service,
        )


    validation_result = st.session_state.get(
        POSITIONS_VALIDATION,
    )

    if validation_result is not None:
        _display_positions_result(validation_result)

        if validation_result.is_valid:
            imported_file_hash = st.session_state.get(POSITIONS_IMPORTED_FILE)
            current_file_bytes = st.session_state.get(POSITIONS_FILE_BYTES)

            current_file_hash = (
                _calculate_uploaded_file_hash(current_file_bytes)
                if current_file_bytes is not None
                else None
            )

            if imported_file_hash == current_file_hash:
                st.success(
                    "This positions file has already been imported into RIMS."
                )
            else:
                st.warning(
                    "Importing will permanently add this validated "
                    "positions data to RIMS."
                )

                if st.button(
                    "IMPORT POSITIONS INTO RIMS",
                    key="import_positions",
                    type="primary",
                ):
                    _import_positions(
                        positions_importer=positions_importer,
                        reconciliation_service=reconciliation_service,
                    )

    import_result = st.session_state.get(
        POSITIONS_IMPORT_RESULT,
    )


    if import_result is not None:
        _display_positions_import_result(import_result)


def _handle_positions_file_selection(
    uploaded_file: Any,
    import_service: ImportService,
) -> None:
    """Store a newly selected positions file and invalidate prior results."""
    filename = uploaded_file.name
    file_bytes = uploaded_file.getvalue()

    previous_filename = st.session_state.get(
        POSITIONS_FILE_NAME,
    )

    if (
        previous_filename is not None
        and previous_filename != filename
    ):
        _clear_positions_state()

    if (
        st.session_state.get(POSITIONS_FILE_NAME) != filename
        or st.session_state.get(POSITIONS_FILE_BYTES) != file_bytes
    ):
        st.session_state[POSITIONS_FILE_NAME] = filename
        st.session_state[POSITIONS_FILE_BYTES] = file_bytes
        st.session_state.pop(POSITIONS_VALIDATION, None)
        st.session_state.pop(POSITIONS_IMPORT_RESULT, None)
        st.session_state.pop(POSITIONS_IMPORTED_FILE, None)

    st.write(f"**Selected file:** {filename}")

    if st.button(
        "Validate Positions File",
        key="validate_positions",
    ):
        _validate_positions_file(import_service)


def _validate_positions_file(
        import_service: ImportService,
    ) -> None:
    """Validate the currently selected positions file."""
    filename = st.session_state.get(POSITIONS_FILE_NAME)
    file_bytes = st.session_state.get(POSITIONS_FILE_BYTES)

    if not filename or file_bytes is None:
        st.error("Select a positions file before validating.")
        return

    temporary_path = _write_temporary_file(
        file_bytes=file_bytes,
        filename=filename,
        category="positions",
    )

    try:
        result = import_service.validate_positions(
            temporary_path,
        )
    finally:
        temporary_path.unlink(missing_ok=True)

    st.session_state[POSITIONS_VALIDATION] = result
    st.session_state.pop(POSITIONS_IMPORT_RESULT, None)


def _import_positions(
    positions_importer: ControlledPositionsImportService,
    reconciliation_service: ImportReconciliationService,
) -> None:
    """Import the validated positions file through the controlled service."""
    filename = st.session_state.get(POSITIONS_FILE_NAME)
    file_bytes = st.session_state.get(POSITIONS_FILE_BYTES)
    validation_result = st.session_state.get(POSITIONS_VALIDATION)

    if not filename or file_bytes is None:
        st.error("The validated positions file is no longer available.")
        return

    if validation_result is None:
        st.error("Validate the positions file before importing.")
        return

    temporary_path = _write_temporary_file(
        file_bytes=file_bytes,
        filename=filename,
        category="positions",
    )

    try:
        result = positions_importer.import_positions(
            validation_result=validation_result,
            source_file=temporary_path,
        )
    except Exception as exc:
        st.error(f"Positions import failed: {exc}")
        return
    finally:
        temporary_path.unlink(missing_ok=True)

    st.session_state[POSITIONS_IMPORT_RESULT] = result
    st.session_state[POSITIONS_IMPORTED_FILE] = _calculate_uploaded_file_hash(
        file_bytes
    )
    st.session_state.pop(POSITIONS_VALIDATION, None)

    reconciliation_result = reconciliation_service.reconcile(
        positions_import=result,
    )

    if reconciliation_result.reconciled:
        st.success("Positions import completed and reconciled.")
    else:
        st.error(
            "Positions import completed, but post-import reconciliation "
            "failed. Use Recover in Import History."
        )


def _display_positions_result(result: Any) -> None:
    """Display positions validation results."""
    if not result.is_valid:
        st.error(f"Positions validation failed: {result.error}")
        return

    if result.is_reconciled:
        st.success("Positions file validated and reconciled.")
    else:
        st.warning(
            "Positions file was parsed, but the Schwab reconciliation "
            "did not pass the current tolerance."
        )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Holdings", result.holding_count)

    with col2:
        st.metric(
            "Market Value Difference",
            f"${result.market_value_difference:,.2f}",
        )

    with col3:
        st.metric(
            "Cost Basis Difference",
            f"${result.cost_basis_difference:,.2f}",
        )

    reporting_date = _get_positions_reporting_date(result)

    if reporting_date is not None:
        st.write(
            f"**Schwab reporting date:** "
            f"{reporting_date:%m/%d/%Y}"
        )


def _get_positions_reporting_date(result: Any):
    """Return the Schwab reporting date when available."""
    if result.import_result is None:
        return None

    return result.import_result.reporting_date


def _display_positions_import_result(result: Any) -> None:
    """Display the result of a successful positions import."""
    st.success("Positions imported successfully.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Snapshot Date",
            f"{result.snapshot.snapshot_date:%m/%d/%Y}",
        )

    with col2:
        st.metric(
            "Holdings Imported",
            len(result.snapshot.holdings),
        )

    with col3:
        status = (
            "Advanced"
            if result.current_portfolio_advanced
            else "Not Changed"
        )
        st.metric("Current Portfolio", status)

    if result.current_portfolio_advanced:
        st.write(
            "The imported positions snapshot is now the current "
            "portfolio because its Schwab reporting date is newer "
            "than the previous current snapshot."
        )
    else:
        st.write(
            "The historical snapshot was imported successfully, "
            "but the current portfolio was not changed because "
            "a newer positions snapshot already exists."
        )




def _render_transactions_section(
    import_service: ImportService,
    transactions_importer: ControlledTransactionImportService,
    reconciliation_service: ImportReconciliationService,
) -> None:
    """Render the transaction validation and import workflow."""
    st.header("Schwab Transactions")

    transaction_file = st.file_uploader(
        "Select a Schwab transactions CSV file",
        type=["csv"],
        key="transaction_file",
        help="Choose a Schwab transaction history CSV exported from Schwab.",
    )

    transaction_account = st.text_input(
        "RIMS account name",
        key="transaction_account_input",
        placeholder="Example: Contributory-111",
        help="Schwab transaction exports do not contain the RIMS account name.",
    )

    _handle_transaction_account_change(transaction_account)

    if transaction_file is not None:
        _handle_transaction_file_selection(
            transaction_file,
            import_service,
        )

    validation_result = st.session_state.get(
        TRANSACTION_VALIDATION,
    )

    if validation_result is not None:
        _display_transactions_result(validation_result)

        if validation_result.is_valid:
            imported_file_hash = st.session_state.get(
                TRANSACTION_IMPORTED_FILE,
            )
            current_file_bytes = st.session_state.get(
                TRANSACTION_FILE_BYTES,
            )

            current_file_hash = (
                _calculate_uploaded_file_hash(current_file_bytes)
                if current_file_bytes is not None
                else None
            )

            if imported_file_hash == current_file_hash:
                st.success(
                    "This transactions file has already been imported into RIMS."
                )
            else:
                st.warning(
                    "Importing will permanently add validated transactions "
                    "to RIMS."
                )

                if st.button(
                    "IMPORT TRANSACTIONS INTO RIMS",
                    key="import_transactions",
                    type="primary",
                ):
                    _import_transactions(
                        transactions_importer=transactions_importer,
                        reconciliation_service=reconciliation_service,
                    )

    import_result = st.session_state.get(
        TRANSACTION_IMPORT_RESULT,
    )

    if import_result is not None:
        _display_transaction_import_result(import_result)


def _handle_transaction_file_selection(
    uploaded_file: Any,
    import_service: ImportService,
) -> None:
    """Store a newly selected transaction file."""
    filename = uploaded_file.name
    file_bytes = uploaded_file.getvalue()

    previous_filename = st.session_state.get(
        TRANSACTION_FILE_NAME,
    )

    if (
        previous_filename is not None
        and previous_filename != filename
    ):
        _clear_transaction_validation_state()

    if (
        st.session_state.get(TRANSACTION_FILE_NAME) != filename
        or st.session_state.get(TRANSACTION_FILE_BYTES) != file_bytes
    ):
        st.session_state[TRANSACTION_FILE_NAME] = filename
        st.session_state[TRANSACTION_FILE_BYTES] = file_bytes
        _clear_transaction_validation_state()
        st.session_state.pop(TRANSACTION_IMPORTED_FILE, None)

    st.write(f"**Selected file:** {filename}")

    if st.button(
        "Validate Transactions File",
        key="validate_transactions",
    ):
        _validate_transactions_file(import_service)


def _handle_transaction_account_change(account: str) -> None:
    """Invalidate transaction validation when the account changes."""
    previous_account = st.session_state.get(
        TRANSACTION_ACCOUNT,
    )

    normalized_account = account.strip()

    if (
        previous_account is not None
        and previous_account != normalized_account
    ):
        _clear_transaction_validation_state()

    st.session_state[TRANSACTION_ACCOUNT] = normalized_account


def _validate_transactions_file(
    import_service: ImportService,
) -> None:
    """Validate the currently selected transaction file."""
    filename = st.session_state.get(TRANSACTION_FILE_NAME)
    file_bytes = st.session_state.get(TRANSACTION_FILE_BYTES)
    account = st.session_state.get(TRANSACTION_ACCOUNT, "")

    if not filename or file_bytes is None:
        st.error("Select a transaction file before validating.")
        return

    if not account:
        st.error("Enter the RIMS account name before validating.")
        return

    temporary_path = _write_temporary_file(
        file_bytes=file_bytes,
        filename=filename,
        category="transactions",
    )

    try:
        result = import_service.validate_transactions(
            temporary_path,
            account=account,
        )
    finally:
        temporary_path.unlink(missing_ok=True)

    st.session_state[TRANSACTION_VALIDATION] = result
    st.session_state.pop(TRANSACTION_IMPORT_RESULT, None)


def _import_transactions(
    transactions_importer: ControlledTransactionImportService,
    reconciliation_service: ImportReconciliationService,
) -> None:
    """Import validated transactions through the controlled service."""
    filename = st.session_state.get(TRANSACTION_FILE_NAME)
    file_bytes = st.session_state.get(TRANSACTION_FILE_BYTES)
    validation_result = st.session_state.get(
        TRANSACTION_VALIDATION,
    )

    if not filename or file_bytes is None:
        st.error("The validated transaction file is no longer available.")
        return

    if validation_result is None:
        st.error("Validate the transaction file before importing.")
        return

    temporary_path = _write_temporary_file(
        file_bytes=file_bytes,
        filename=filename,
        category="transactions",
    )

    try:
        result = transactions_importer.import_transactions(
            validation_result=validation_result,
            source_file=temporary_path,
        )
    except Exception as exc:
        st.error(f"Transaction import failed: {exc}")
        return
    finally:
        temporary_path.unlink(missing_ok=True)

    st.session_state[TRANSACTION_IMPORT_RESULT] = result
    st.session_state[TRANSACTION_IMPORTED_FILE] = _calculate_uploaded_file_hash(
        file_bytes
    )
    st.session_state.pop(TRANSACTION_VALIDATION, None)

    reconciliation_result = reconciliation_service.reconcile(
        transactions_import=result,
    )

    if reconciliation_result.reconciled:
        st.success("Transaction import completed and reconciled.")
    else:
        st.error(
            "Transaction import completed, but post-import reconciliation "
            "failed. Use Recover in Import History."
        )


def _display_transactions_result(result: Any) -> None:
    """Display transaction validation results."""
    if not result.is_valid:
        st.error(f"Transaction validation failed: {result.error}")
        return

    st.success("Transactions file validated successfully.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Transactions", result.transaction_count)

    with col2:
        st.metric(
            "Income Transactions",
            result.income_transaction_count,
        )

    with col3:
        st.metric(
            "Recurring Income",
            f"${result.recurring_income_amount:,.2f}",
        )

    if result.start_date is not None and result.end_date is not None:
        st.write(
            f"**Transaction date range:** "
            f"{result.start_date:%m/%d/%Y} – "
            f"{result.end_date:%m/%d/%Y}"
        )


def _display_transaction_import_result(result: Any) -> None:
    """Display the result of a successful transaction import."""
    st.success("Transactions processed successfully.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Transactions Received",
            result.source_transaction_count,
        )

    with col2:
        st.metric(
            "Transactions Added",
            result.transactions_added,
        )

    with col3:
        st.metric(
            "Duplicates Skipped",
            result.duplicates_skipped,
        )

    col4, col5 = st.columns(2)

    with col4:
        st.metric(
            "Income Transactions Added",
            result.income_transactions_added,
        )

    with col5:
        st.metric(
            "Recurring Income Transactions Added",
            result.recurring_income_transactions_added,
        )

    if result.transactions_added == 0:
        st.info(
            "No new transactions were added. All transactions in "
            "the file were already present in RIMS."
        )


def _render_import_health(
    health_service: ImportHealthService,
) -> None:
    """Render the current persisted import health."""
    health = health_service.get_health()

    st.subheader("Import Health")

    if health.total_operations == 0:
        st.info(health.summary)
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Imports", health.total_operations)

    with col2:
        st.metric("Reconciled", health.reconciled_operations)

    with col3:
        st.metric(
            "Reconciliation Issues",
            health.reconciliation_failed_operations,
        )

    if health.reconciliation_failed_operations:
        st.warning(health.summary)
    elif health.all_reconciled:
        st.success(health.summary)
    else:
        st.info(health.summary)


def _render_import_history(
    import_operation_store: ImportOperationStore,
    reconciliation_service: ImportReconciliationService,
) -> None:
    """Render persisted import operations and recovery actions."""
    operations = import_operation_store.list_operations()

    st.subheader("Import History")

    if not operations:
        st.info("No import operations recorded.")
        return

    operations = sorted(
        operations,
        key=lambda operation: operation.imported_at,
        reverse=True,
    )

    for operation in operations:
        st.write(f"**{operation.source_file}**")
        st.write(
            f"Type: {operation.file_type.value}  |  "
            f"Status: {operation.status.value}"
        )

        if operation.account:
            st.write(f"Account: {operation.account}")

        st.write(
            f"Imported: "
            f"{operation.imported_at:%m/%d/%Y %I:%M %p}"
        )

        if operation.status is ImportStatus.RECONCILIATION_FAILED:
            st.warning("This import requires reconciliation.")

            if st.button(
                "Recover",
                key=f"recover_import_{operation.import_id}",
                type="primary",
            ):
                _recover_import(
                    import_id=operation.import_id,
                    reconciliation_service=reconciliation_service,
                )

        elif operation.status is ImportStatus.RECONCILED:
            st.success("Reconciled")

        elif operation.status is ImportStatus.IMPORTED:
            st.info("Imported — pending reconciliation")

        elif operation.status is ImportStatus.IMPORT_FAILED:
            st.error("Import failed")

        elif operation.status is ImportStatus.VALIDATION_FAILED:
            st.error("Validation failed")

        st.divider()


def _recover_import(
    import_id: str,
    reconciliation_service: ImportReconciliationService,
) -> None:
    """Recover one failed import operation."""
    try:
        result = reconciliation_service.recover(import_id)
    except Exception as exc:
        st.error(f"Import recovery failed: {exc}")
        return

    if result.reconciled:
        st.success("Import recovery completed and the import is reconciled.")
        st.rerun()
    else:
        st.error(
            "Import recovery did not complete successfully. "
            "Review the import history and try again."
        )


def _clear_positions_state() -> None:
    """Clear all positions workflow state."""
    for key in (
        POSITIONS_FILE_NAME,
        POSITIONS_FILE_BYTES,
        POSITIONS_VALIDATION,
        POSITIONS_IMPORT_RESULT,
        POSITIONS_IMPORTED_FILE,
    ):
        st.session_state.pop(key, None)


def _clear_transaction_validation_state() -> None:
    """Clear transaction validation and import results."""
    st.session_state.pop(TRANSACTION_VALIDATION, None)
    st.session_state.pop(TRANSACTION_IMPORT_RESULT, None)


def _write_temporary_file(
    file_bytes: bytes,
    filename: str,
    category: str,
) -> Path:
    """Write uploaded bytes to a temporary CSV file."""
    temporary_directory = Path(tempfile.gettempdir())
    temporary_path = temporary_directory / filename

    temporary_path.write_bytes(file_bytes)

    return temporary_path


def main() -> None:
    """Run the Import Data page."""
    render_import_data()


if __name__ == "__main__":
    main()
