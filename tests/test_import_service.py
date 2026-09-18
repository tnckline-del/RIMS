"""Tests for the RIMS import service."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.import_service import (
    ImportService,
    PositionsValidationResult,
    TransactionsValidationResult,
    validate_positions_file,
    validate_transactions_file,
)


def test_import_service_can_be_created() -> None:
    """ImportService can be instantiated."""
    service = ImportService()

    assert isinstance(service, ImportService)


def test_missing_positions_file_returns_invalid_result(
    tmp_path: Path,
) -> None:
    """A missing positions file produces a structured validation failure."""
    service = ImportService()
    missing_file = tmp_path / "missing_positions.csv"

    result = service.validate_positions(missing_file)

    assert isinstance(result, PositionsValidationResult)
    assert result.is_valid is False
    assert result.source_file == "missing_positions.csv"
    assert result.holding_count == 0
    assert result.is_reconciled is False
    assert result.import_result is None
    assert result.error is not None
    assert "File not found" in result.error


def test_missing_transaction_file_returns_invalid_result(
    tmp_path: Path,
) -> None:
    """A missing transaction file produces a structured validation failure."""
    service = ImportService()
    missing_file = tmp_path / "missing_transactions.csv"

    result = service.validate_transactions(
        missing_file,
        account="Test Account",
    )

    assert isinstance(result, TransactionsValidationResult)
    assert result.is_valid is False
    assert result.source_file == "missing_transactions.csv"
    assert result.account == "Test Account"
    assert result.transaction_count == 0
    assert result.income_transaction_count == 0
    assert result.recurring_income_amount == Decimal("0")
    assert result.start_date is None
    assert result.end_date is None
    assert result.import_result is None
    assert result.error is not None
    assert "File not found" in result.error


def test_blank_transaction_account_returns_invalid_result(
    tmp_path: Path,
) -> None:
    """A transaction import requires an account."""
    service = ImportService()
    transaction_file = tmp_path / "transactions.csv"
    transaction_file.write_text("Date,Action\n")

    result = service.validate_transactions(
        transaction_file,
        account="   ",
    )

    assert result.is_valid is False
    assert result.account == ""
    assert result.transaction_count == 0
    assert result.import_result is None
    assert result.error == "Account is required for Schwab transaction imports."


def test_positions_validation_uses_existing_importer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Positions validation delegates parsing to the existing importer."""
    from app.services import import_service

    class FakePortfolio:
        holding_count = 44

    class FakeResult:
        portfolio = FakePortfolio()
        market_value_difference = Decimal("0.00")
        cost_basis_difference = Decimal("0.00")
        is_reconciled = True

    captured: dict[str, object] = {}

    def fake_import(
        file_path: Path,
        portfolio_name: str,
    ) -> FakeResult:
        captured["file_path"] = file_path
        captured["portfolio_name"] = portfolio_name
        return FakeResult()

    monkeypatch.setattr(
        import_service,
        "import_schwab_csv",
        fake_import,
    )

    positions_file = tmp_path / "positions.csv"
    positions_file.write_text("test")

    result = ImportService().validate_positions(
        positions_file,
        portfolio_name="Test Portfolio",
    )

    assert result.is_valid is True
    assert result.source_file == "positions.csv"
    assert result.holding_count == 44
    assert result.market_value_difference == Decimal("0.00")
    assert result.cost_basis_difference == Decimal("0.00")
    assert result.is_reconciled is True
    assert result.error is None
    assert result.import_result is not None
    assert captured["file_path"] == positions_file
    assert captured["portfolio_name"] == "Test Portfolio"


def test_transaction_validation_uses_existing_importer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transaction validation delegates parsing to the existing importer."""
    from app.services import import_service

    class FakeTransaction:
        def __init__(self, transaction_date) -> None:
            self.transaction_date = transaction_date

    class FakeResult:
        transactions = (
            FakeTransaction(date(2026, 1, 2)),
            FakeTransaction(date(2026, 9, 4)),
        )
        transaction_count = 2
        income_transaction_count = 2
        recurring_income_amount = Decimal("125.50")

    captured: dict[str, object] = {}

    def fake_import(
        file_path: Path,
        account: str,
    ) -> FakeResult:
        captured["file_path"] = file_path
        captured["account"] = account
        return FakeResult()

    monkeypatch.setattr(
        import_service,
        "import_schwab_income_csv",
        fake_import,
    )

    transaction_file = tmp_path / "transactions.csv"
    transaction_file.write_text("test")

    result = ImportService().validate_transactions(
        transaction_file,
        account="  Contributory-111  ",
    )

    assert result.is_valid is True
    assert result.source_file == "transactions.csv"
    assert result.account == "Contributory-111"
    assert result.transaction_count == 2
    assert result.income_transaction_count == 2
    assert result.recurring_income_amount == Decimal("125.50")
    assert result.start_date == date(2026, 1, 2)
    assert result.end_date == date(2026, 9, 4)
    assert result.error is None
    assert result.import_result is not None
    assert captured["file_path"] == transaction_file
    assert captured["account"] == "Contributory-111"


def test_positions_importer_error_is_structured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Importer errors are returned rather than raised to the UI layer."""
    from app.services import import_service

    def fake_import(
        file_path: Path,
        portfolio_name: str,
    ):
        raise ValueError("Invalid Schwab positions file")

    monkeypatch.setattr(
        import_service,
        "import_schwab_csv",
        fake_import,
    )

    positions_file = tmp_path / "invalid_positions.csv"
    positions_file.write_text("invalid")

    result = ImportService().validate_positions(positions_file)

    assert result.is_valid is False
    assert result.error == "Invalid Schwab positions file"
    assert result.import_result is None


def test_transaction_importer_error_is_structured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transaction importer errors are returned rather than raised."""
    from app.services import import_service

    def fake_import(
        file_path: Path,
        account: str,
    ):
        raise ValueError("Invalid Schwab transaction file")

    monkeypatch.setattr(
        import_service,
        "import_schwab_income_csv",
        fake_import,
    )

    transaction_file = tmp_path / "invalid_transactions.csv"
    transaction_file.write_text("invalid")

    result = ImportService().validate_transactions(
        transaction_file,
        account="Test Account",
    )

    assert result.is_valid is False
    assert result.error == "Invalid Schwab transaction file"
    assert result.import_result is None


def test_positions_convenience_function(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The positions convenience function delegates to ImportService."""
    positions_file = tmp_path / "positions.csv"
    positions_file.write_text("invalid")

    monkeypatch.setattr(
        ImportService,
        "validate_positions",
        lambda self, file_path, portfolio_name="Schwab Portfolio":
        PositionsValidationResult(
            is_valid=True,
            source_file=Path(file_path).name,
            holding_count=10,
            market_value_difference=Decimal("0"),
            cost_basis_difference=Decimal("0"),
            is_reconciled=True,
        ),
    )

    result = validate_positions_file(positions_file)

    assert result.is_valid is True
    assert result.source_file == "positions.csv"
    assert result.holding_count == 10


def test_transactions_convenience_function(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The transaction convenience function delegates to ImportService."""
    transaction_file = tmp_path / "transactions.csv"
    transaction_file.write_text("invalid")

    monkeypatch.setattr(
        ImportService,
        "validate_transactions",
        lambda self, file_path, account:
        TransactionsValidationResult(
            is_valid=True,
            source_file=Path(file_path).name,
            account=account,
            transaction_count=5,
            income_transaction_count=3,
            recurring_income_amount=Decimal("250"),
            start_date=None,
            end_date=None,
        ),
    )

    result = validate_transactions_file(
        transaction_file,
        "Test Account",
    )

    assert result.is_valid is True
    assert result.source_file == "transactions.csv"
    assert result.account == "Test Account"
    assert result.transaction_count == 5
