"""Forward income change classification."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class ForwardIncomeChangeReason(str, Enum):
    """Reason for a change in a holding's forward income."""

    NEW_POSITION = "New Position"
    POSITION_CHANGE = "Position Change"
    DIVIDEND_CHANGE = "Dividend Change"
    POSITION_AND_DIVIDEND_CHANGE = "Position & Dividend Change"
    POSITION_CLOSED = "Position Closed"
    NO_CHANGE = "No Change"


@dataclass(frozen=True, slots=True)
class ForwardIncomePositionState:
    """State of a holding used for change comparison."""

    symbol: str
    shares: Decimal
    forward_annual_income_per_share: Decimal


@dataclass(frozen=True, slots=True)
class ForwardIncomeChange:
    """A holding's current state and its change reason."""

    state: ForwardIncomePositionState
    reason: ForwardIncomeChangeReason


def classify_forward_income_change(
    previous: ForwardIncomePositionState | None,
    current: ForwardIncomePositionState | None,
) -> ForwardIncomeChangeReason:
    """Classify the change between two forward income position states."""

    if previous is None and current is None:
        raise ValueError(
            "previous and current cannot both be None"
        )

    if previous is None:
        if current is None:
            raise ValueError(
                "current state is required for a new position"
            )

        if current.shares <= Decimal("0"):
            raise ValueError(
                "a new position must have positive shares"
            )

        return ForwardIncomeChangeReason.NEW_POSITION

    if current is None:
        if previous.shares <= Decimal("0"):
            raise ValueError(
                "a closed position must have had positive shares"
            )

        return ForwardIncomeChangeReason.POSITION_CLOSED

    if previous.symbol != current.symbol:
        raise ValueError(
            "previous and current symbols must match"
        )

    previous_has_position = previous.shares > Decimal("0")
    current_has_position = current.shares > Decimal("0")

    if previous_has_position and not current_has_position:
        return ForwardIncomeChangeReason.POSITION_CLOSED

    if not previous_has_position and current_has_position:
        return ForwardIncomeChangeReason.NEW_POSITION

    position_changed = previous.shares != current.shares

    dividend_changed = (
        previous.forward_annual_income_per_share
        != current.forward_annual_income_per_share
    )

    if position_changed and dividend_changed:
        return ForwardIncomeChangeReason.POSITION_AND_DIVIDEND_CHANGE

    if position_changed:
        return ForwardIncomeChangeReason.POSITION_CHANGE

    if dividend_changed:
        return ForwardIncomeChangeReason.DIVIDEND_CHANGE

    return ForwardIncomeChangeReason.NO_CHANGE


def compare_forward_income_states(
    previous_states: tuple[ForwardIncomePositionState, ...],
    current_states: tuple[ForwardIncomePositionState, ...],
) -> tuple[ForwardIncomeChange, ...]:
    """Compare previous and current holding states.

    Current positions are returned in current-state order. A position that
    has been closed is included once, using its previous state with zero
    shares, so it appears in the final report and can then disappear from
    later reports.
    """

    previous_by_symbol = {
        state.symbol: state
        for state in previous_states
    }

    current_by_symbol = {
        state.symbol: state
        for state in current_states
    }

    changes: list[ForwardIncomeChange] = []

    for current in current_states:
        previous = previous_by_symbol.get(current.symbol)

        reason = classify_forward_income_change(
            previous,
            current,
        )

        changes.append(
            ForwardIncomeChange(
                state=current,
                reason=reason,
            )
        )

    for previous in previous_states:
        if previous.symbol in current_by_symbol:
            continue

        closed_state = ForwardIncomePositionState(
            symbol=previous.symbol,
            shares=Decimal("0"),
            forward_annual_income_per_share=(
                previous.forward_annual_income_per_share
            ),
        )

        changes.append(
            ForwardIncomeChange(
                state=closed_state,
                reason=ForwardIncomeChangeReason.POSITION_CLOSED,
            )
        )

    return tuple(changes)