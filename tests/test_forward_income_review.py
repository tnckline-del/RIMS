from decimal import Decimal

import pytest

from src.forward_income_change import ForwardIncomeChangeReason
from src.forward_income_report import (
    ForwardIncomeReport,
    ForwardIncomeReportHolding,
)
from src.forward_income_review import (
    ForwardIncomeReviewReason,
    ForwardIncomeReviewer,
    generate_forward_income_review,
)


def make_holding(
    symbol: str,
    income: str,
    reason: ForwardIncomeChangeReason | None = None,
) -> ForwardIncomeReportHolding:
    return ForwardIncomeReportHolding(
        symbol=symbol,
        shares=Decimal("100"),
        market_value=Decimal("10000"),
        forward_annual_income=Decimal(income),
        percentage_of_forward_income=Decimal("10"),
        change_reason=reason,
    )


def make_report(
    holdings: tuple[ForwardIncomeReportHolding, ...],
) -> ForwardIncomeReport:
    return ForwardIncomeReport(
        holdings=holdings,
        total_market_value=Decimal("50000"),
        total_forward_annual_income=Decimal("5000"),
        holdings_with_forward_income=4,
        holdings_without_forward_income=1,
        income_concentration=Decimal("30"),
        largest_income_holding="ARCC",
    )


def test_reviewer_requires_forward_income_report() -> None:
    with pytest.raises(TypeError):
        ForwardIncomeReviewer("not a report")  # type: ignore[arg-type]


def test_no_change_holding_does_not_require_review() -> None:
    report = make_report(
        (make_holding("ARCC", "1000"),)
    )

    result = ForwardIncomeReviewer(report).generate()

    assert result.review_count == 0
    assert result.items == ()


def test_new_position_requires_review() -> None:
    report = make_report(
        (
            make_holding(
                "ARCC",
                "1000",
                ForwardIncomeChangeReason.NEW_POSITION,
            ),
        )
    )

    result = ForwardIncomeReviewer(report).generate()

    assert result.review_count == 1
    assert result.items[0].symbol == "ARCC"
    assert result.items[0].reason == ForwardIncomeReviewReason.NEW_POSITION


def test_position_change_requires_review() -> None:
    report = make_report(
        (
            make_holding(
                "BXSL",
                "1000",
                ForwardIncomeChangeReason.POSITION_CHANGE,
            ),
        )
    )

    result = ForwardIncomeReviewer(report).generate()

    assert result.items[0].reason == ForwardIncomeReviewReason.POSITION_CHANGE


def test_dividend_change_requires_review() -> None:
    report = make_report(
        (
            make_holding(
                "PFLT",
                "1000",
                ForwardIncomeChangeReason.DIVIDEND_CHANGE,
            ),
        )
    )

    result = ForwardIncomeReviewer(report).generate()

    assert result.items[0].reason == ForwardIncomeReviewReason.DIVIDEND_CHANGE


def test_position_and_dividend_change_requires_review() -> None:
    report = make_report(
        (
            make_holding(
                "MAIN",
                "1000",
                ForwardIncomeChangeReason.POSITION_AND_DIVIDEND_CHANGE,
            ),
        )
    )

    result = ForwardIncomeReviewer(report).generate()

    assert result.items[0].reason == (
        ForwardIncomeReviewReason.POSITION_AND_DIVIDEND_CHANGE
    )


def test_closed_position_requires_review() -> None:
    report = make_report(
        (
            make_holding(
                "ABC",
                "0",
                ForwardIncomeChangeReason.POSITION_CLOSED,
            ),
        )
    )

    result = ForwardIncomeReviewer(report).generate()

    assert result.review_count == 1
    assert result.items[0].symbol == "ABC"
    assert result.items[0].reason == ForwardIncomeReviewReason.POSITION_CLOSED
    assert result.items[0].shares == Decimal("100")


def test_missing_forward_income_requires_review() -> None:
    report = make_report(
        (
            make_holding("XYZ", "0"),
        )
    )

    result = ForwardIncomeReviewer(report).generate()

    assert result.review_count == 1
    assert result.items[0].symbol == "XYZ"
    assert result.items[0].reason == (
        ForwardIncomeReviewReason.FORWARD_INCOME_MISSING
    )


def test_review_only_contains_items_requiring_attention() -> None:
    report = make_report(
        (
            make_holding("ARCC", "1000"),
            make_holding(
                "BXSL",
                "900",
                ForwardIncomeChangeReason.DIVIDEND_CHANGE,
            ),
            make_holding("XYZ", "0"),
            make_holding("MAIN", "800"),
        )
    )

    result = generate_forward_income_review(report)

    assert result.review_count == 2
    assert [item.symbol for item in result.items] == ["BXSL", "XYZ"]


def test_review_preserves_income_and_shares() -> None:
    report = make_report(
        (
            make_holding(
                "ARCC",
                "2058.50",
                ForwardIncomeChangeReason.POSITION_CHANGE,
            ),
        )
    )

    result = ForwardIncomeReviewer(report).generate()

    assert result.items[0].shares == Decimal("100")
    assert result.items[0].forward_annual_income == Decimal("2058.50")


def test_review_does_not_modify_report() -> None:
    original_holding = make_holding(
        "ARCC",
        "1000",
        ForwardIncomeChangeReason.DIVIDEND_CHANGE,
    )
    report = make_report((original_holding,))

    ForwardIncomeReviewer(report).generate()

    assert report.holdings == (original_holding,)