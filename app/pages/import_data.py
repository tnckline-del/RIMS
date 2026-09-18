"""RIMS Import Data page."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.services.import_service import ImportService


def render_import_data() -> None:
    """Render the Schwab import validation page."""
    st.title("Import Data")
    st.caption(
        "Select Schwab files and validate them before they are imported into RIMS."
    )
    st.divider()

    service = ImportService()

    st.header("Schwab Positions")

    positions_file = st.file_uploader(
        "Select a Schwab positions CSV file",
        type=["csv"],
        key="positions_file",
        help="Choose an All-Accounts-Positions CSV exported from Schwab.",
    )

    if positions_file is not None:
        st.write(f"**Selected file:** {positions_file.name}")

        if st.button("Validate Positions File", key="validate_positions"):
            temp_path = _save_uploaded_file(
                positions_file,
                "positions",
            )

            try:
                result = service.validate_positions(temp_path)
            finally:
                temp_path.unlink(missing_ok=True)

            _display_positions_result(result)

    st.divider()

    st.header("Schwab Transactions")

    transaction_file = st.file_uploader(
        "Select a Schwab transactions CSV file",
        type=["csv"],
        key="transaction_file",
        help="Choose a Schwab transaction history CSV exported from Schwab.",
    )

    transaction_account = st.text_input(
        "RIMS account name",
        key="transaction_account",
        placeholder="Example: Contributory-111",
        help="Schwab transaction exports do not contain the RIMS account name.",
    )

    if transaction_file is not None:
        st.write(f"**Selected file:** {transaction_file.name}")

        if st.button(
            "Validate Transactions File",
            key="validate_transactions",
        ):
            temp_path = _save_uploaded_file(
                transaction_file,
                "transactions",
            )

            try:
                result = service.validate_transactions(
                    temp_path,
                    account=transaction_account,
                )
            finally:
                temp_path.unlink(missing_ok=True)

            _display_transactions_result(result)


def _save_uploaded_file(uploaded_file, category: str) -> Path:
    """Save an uploaded file temporarily for the existing import service."""
    import tempfile

    suffix = Path(uploaded_file.name).suffix or ".csv"

    with tempfile.NamedTemporaryFile(
        prefix=f"rims_{category}_",
        suffix=suffix,
        delete=False,
    ) as temporary_file:
        temporary_file.write(uploaded_file.getbuffer())
        return Path(temporary_file.name)


def _display_positions_result(result) -> None:
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


def _display_transactions_result(result) -> None:
    """Display transaction validation results."""
    if not result.is_valid:
        st.error(f"Transaction validation failed: {result.error}")
        return

    st.success("Transactions file validated successfully.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Transactions", result.transaction_count)

    with col2:
        st.metric("Income Transactions", result.income_transaction_count)

    with col3:
        st.metric(
            "Recurring Income",
            f"${result.recurring_income_amount:,.2f}",
        )

    if result.start_date is not None and result.end_date is not None:
        st.write(
            f"**Transaction date range:** "
            f"{result.start_date:%m/%d/%Y} – {result.end_date:%m/%d/%Y}"
        )


def main() -> None:
    """Run the Import Data page."""
    render_import_data()


if __name__ == "__main__":
    main()
