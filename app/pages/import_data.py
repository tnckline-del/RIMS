"""RIMS Import Data page."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

from app.app_config import (
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
from src.import_operation_store import ImportOperationStore
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
    positions_importer, transactions_importer = _build_import_services()

    _render_positions_section(
        import_service=import_service,
        positions_importer=positions_importer,
    )

    st.divider()

    _render_transactions_section(
        import_service=import_service,
        transactions_importer=transactions_importer,
    )


def _build_import_services() -> tuple[
    ControlledPositionsImportService,
    ControlledTransactionImportService,
]:
    """Build controlled import services using application storage paths."""
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

    return positions_importer, transactions_importer


def _render_positions_section(
    import_service: ImportService,
    positions_importer: ControlledPositionsImportService,
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
    suffix = Path(filename).suffix or ".csv"

    with tempfile.NamedTemporaryFile(
        prefix=f"rims_{category}_",
        suffix=suffix,
        delete=False,
    ) as temporary_file:
        temporary_file.write(file_bytes)
        return Path(temporary_file.name)


def main() -> None:
    """Run the Import Data page."""
    render_import_data()


if __name__ == "__main__":
    main()
