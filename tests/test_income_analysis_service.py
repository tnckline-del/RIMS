from decimal import Decimal
from pathlib import Path

from app.services.income_analysis_service import IncomeAnalysisService
from src.import_operation_store import ImportOperationStore
from src.snapshot_store import SnapshotStore
from src.transaction_repository import TransactionRepository


def create_income_analysis_service() -> IncomeAnalysisService:
    return IncomeAnalysisService(
        ImportOperationStore(Path("data/imports/operations")),
        SnapshotStore(Path("data/snapshots")),
        TransactionRepository.from_path(Path("data/transactions")),
    )


def test_income_analysis_exposes_current_and_historical_income_reconciliation():
    service = create_income_analysis_service()

    result = service.analyze()

    assert result is not None
    assert result.all_history_recurring_income == Decimal("61155.51")
    assert result.all_history_income_from_no_longer_held == Decimal("5016.21")
    assert result.all_history_symbolless_income == Decimal("87.33")

def test_trailing_12_month_recurring_income_from_current_holdings():
    service = create_income_analysis_service()

    result = service.analyze()

    assert result is not None
    assert result.trailing_12_month_recurring_income == Decimal("52046.93")
    assert result.trailing_12_month_income_yield.quantize(
        Decimal("0.0001")
    ) == Decimal("7.2091")

def test_holding_analysis_calculates_pflt_income_metrics():
    service = create_income_analysis_service()

    result = service.analyze()

    assert result is not None

    pflt = next(
        holding for holding in result.holdings
        if holding.symbol == "PFLT"
    )

    assert pflt.market_value == Decimal("15326.86")
    assert pflt.cost_basis == Decimal("21712.24")
    assert pflt.trailing_12_month_recurring_income == Decimal("2166.17")

    assert pflt.portfolio_weight.quantize(
        Decimal("0.0001")
    ) == Decimal("2.1229")

    assert pflt.income_weight.quantize(
        Decimal("0.0001")
    ) == Decimal("4.1620")

    assert pflt.income_vs_portfolio_weight.quantize(
        Decimal("0.0001")
    ) == Decimal("2.0390")

    assert pflt.trailing_12_month_yield.quantize(
        Decimal("0.0001")
    ) == Decimal("14.1332")

    assert pflt.yield_on_cost.quantize(
        Decimal("0.0001")
    ) == Decimal("9.9767")

def test_income_analysis_excludes_zero_value_account_records():
    service = create_income_analysis_service()

    result = service.analyze()

    assert result is not None
    assert len(result.holdings) == 42

def test_portfolio_weights_reconcile_to_100_percent():
    service = create_income_analysis_service()

    result = service.analyze()

    assert result is not None

    total_portfolio_weight = sum(
        holding.portfolio_weight
        for holding in result.holdings
    )

    assert total_portfolio_weight.quantize(
        Decimal("0.0001")
    ) == Decimal("100.0000")

def test_ttm_income_weights_reconcile_to_100_percent():
    service = create_income_analysis_service()

    result = service.analyze()

    assert result is not None

    total_income_weight = sum(
        holding.income_weight
        for holding in result.holdings
    )

    assert total_income_weight.quantize(
        Decimal("0.0001")
    ) == Decimal("100.0000")

def test_current_holdings_income_counts():
    service = create_income_analysis_service()

    result = service.analyze()

    assert result is not None
    assert result.holdings_with_income == 41
    assert result.holdings_without_income == 1
