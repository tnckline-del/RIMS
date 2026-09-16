"""Forward income review and exception reporting."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .forward_income_change import ForwardIncomeChangeReason
from .forward_income_report import (
    ForwardIncomeReport,
    ForwardIncomeReportHolding,
)


class ForwardIncomeReviewReason(str, Enum):
    """Reasons a forward-income item requires user review."""

    NEW_POSITION = "New Position"
    POSITION_CHANGE = "Position Change"
    DIVIDEND_CHANGE = "Dividend Change"
    POSITION_AND_DIVIDEND_CHANGE = "Position & Dividend Change"
    POSITION_CLOSED = "Position Closed"
    FORWARD_INCOME_MISSING = "Forward Annual Income Missing"


@dataclass(frozen=True, slots=True)
class ForwardIncomeReviewItem:
    """One forward-income item requiring user attention."""

    symbol: str
    reason: ForwardIncomeReviewReason
    shares: object
    forward_annual_income: object


@dataclass(frozen=True, slots=True)
class ForwardIncomeReview:
    """Concise summary of forward-income items requiring attention."""

    items: tuple[ForwardIncomeReviewItem, ...]
    review_count: int


class ForwardIncomeReviewer:
    """Create a concise review from a forward-income report."""

    def __init__(self, report: ForwardIncomeReport) -> None:
        if not isinstance(report, ForwardIncomeReport):
            raise TypeError("report must be a ForwardIncomeReport")

        self._report = report

    def generate(self) -> ForwardIncomeReview:
        """Identify holdings that require user review."""

        items = tuple(
            self._to_review_item(holding)
            for holding in self._report.holdings
            if self._requires_review(holding)
        )

        return ForwardIncomeReview(
            items=items,
            review_count=len(items),
        )

    @staticmethod
    def _requires_review(
        holding: ForwardIncomeReportHolding,
    ) -> bool:
        """Return whether a holding requires user attention."""

        if holding.change_reason is not None:
            return True

        return holding.forward_annual_income <= 0

    @staticmethod
    def _to_review_item(
        holding: ForwardIncomeReportHolding,
    ) -> ForwardIncomeReviewItem:
        """Convert a report holding to a review item."""

        reason = ForwardIncomeReviewer._review_reason(holding)

        return ForwardIncomeReviewItem(
            symbol=holding.symbol,
            reason=reason,
            shares=holding.shares,
            forward_annual_income=holding.forward_annual_income,
        )

    @staticmethod
    def _review_reason(
        holding: ForwardIncomeReportHolding,
    ) -> ForwardIncomeReviewReason:
        """Translate report information into a user-facing review reason."""

        reason_map = {
            ForwardIncomeChangeReason.NEW_POSITION: (
                ForwardIncomeReviewReason.NEW_POSITION
            ),
            ForwardIncomeChangeReason.POSITION_CHANGE: (
                ForwardIncomeReviewReason.POSITION_CHANGE
            ),
            ForwardIncomeChangeReason.DIVIDEND_CHANGE: (
                ForwardIncomeReviewReason.DIVIDEND_CHANGE
            ),
            ForwardIncomeChangeReason.POSITION_AND_DIVIDEND_CHANGE: (
                ForwardIncomeReviewReason.POSITION_AND_DIVIDEND_CHANGE
            ),
            ForwardIncomeChangeReason.POSITION_CLOSED: (
                ForwardIncomeReviewReason.POSITION_CLOSED
            ),
        }

        if holding.change_reason is not None:
            return reason_map[holding.change_reason]

        return ForwardIncomeReviewReason.FORWARD_INCOME_MISSING


def generate_forward_income_review(
    report: ForwardIncomeReport,
) -> ForwardIncomeReview:
    """Generate a concise forward-income review."""

    return ForwardIncomeReviewer(report).generate()