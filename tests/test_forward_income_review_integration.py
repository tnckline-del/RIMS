from decimal import Decimal

from src.forward_income_change import ForwardIncomeChangeReason
from src.forward_income_report import (
    ForwardIncomeReport,
    ForwardIncomeReportHolding,
)
from src.forward_income_review import (
    ForwardIncomeReviewReason,
    generate_forward_income_review,
)


def test_forward_income_review_with_real_report_shape() -> None:
    report = ForwardIncomeReport(
        holdings=(
            ForwardIncomeReportHolding(
                symbol="ARCC",
                shares=Decimal("972"),
                market_value=Decimal("10000"),
                forward_annual_income=Decimal("2000"),
                percentage_of_forward_income=Decimal("27.40"),
                change_reason=ForwardIncomeChangeReason.POSITION_CHANGE,
            ),
            ForwardIncomeReportHolding(
                symbol="BXSL",
                shares=Decimal("702"),
                market_value=Decimal("9000"),
                forward_annual_income=Decimal("2500"),
                percentage_of_forward_income=Decimal("34.25"),
                change_reason=None,
            ),
            ForwardIncomeReportHolding(
                symbol="PFLT",
                shares=Decimal("2074"),
                market_value=Decimal("8000"),
                forward_annual_income=Decimal("2800"),
                percentage_of_forward_income=Decimal("38.36"),
                change_reason=ForwardIncomeChangeReason.DIVIDEND_CHANGE,
            ),
            ForwardIncomeReportHolding(
                symbol="XYZ",
                shares=Decimal("100"),
                market_value=Decimal("5000"),
                forward_annual_income=Decimal("0"),
                percentage_of_forward_income=Decimal("0"),
                change_reason=None,
            ),
        ),
        total_market_value=Decimal("32000"),
        total_forward_annual_income=Decimal("7300"),
        holdings_with_forward_income=3,
        holdings_without_forward_income=1,
        income_concentration=Decimal("38.36"),
        largest_income_holding="PFLT",
    )

    result = generate_forward_income_review(report)

    assert result.review_count == 3
    assert [item.symbol for item in result.items] == [
        "ARCC",
        "PFLT",
        "XYZ",
    ]

    assert result.items[0].reason == (
        ForwardIncomeReviewReason.POSITION_CHANGE
    )
    assert result.items[1].reason == (
        ForwardIncomeReviewReason.DIVIDEND_CHANGE
    )
    assert result.items[2].reason == (
        ForwardIncomeReviewReason.FORWARD_INCOME_MISSING
    )