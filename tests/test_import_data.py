"""Tests for the RIMS Import Data page."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.pages.import_data import (
    _display_positions_result,
    _display_transactions_result,
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
