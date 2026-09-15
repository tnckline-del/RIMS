from decimal import Decimal

import pytest

from src.forward_income_change import (
    ForwardIncomeChangeReason,
    ForwardIncomePositionState,
    compare_forward_income_states,
    classify_forward_income_change,
)


def make_state(
    symbol: str = "ARCC",
    shares: str = "100",
    income_per_share: str = "2.00",
) -> ForwardIncomePositionState:
    return ForwardIncomePositionState(
        symbol=symbol,
        shares=Decimal(shares),
        forward_annual_income_per_share=Decimal(income_per_share),
    )


def test_new_position() -> None:
    result = classify_forward_income_change(
        None,
        make_state(),
    )

    assert result == ForwardIncomeChangeReason.NEW_POSITION


def test_position_change() -> None:
    result = classify_forward_income_change(
        make_state(shares="100"),
        make_state(shares="150"),
    )

    assert result == ForwardIncomeChangeReason.POSITION_CHANGE


def test_dividend_change() -> None:
    result = classify_forward_income_change(
        make_state(income_per_share="2.00"),
        make_state(income_per_share="1.80"),
    )

    assert result == ForwardIncomeChangeReason.DIVIDEND_CHANGE


def test_position_and_dividend_change() -> None:
    result = classify_forward_income_change(
        make_state(
            shares="100",
            income_per_share="2.00",
        ),
        make_state(
            shares="150",
            income_per_share="1.80",
        ),
    )

    assert result == (
        ForwardIncomeChangeReason.POSITION_AND_DIVIDEND_CHANGE
    )


def test_no_change() -> None:
    result = classify_forward_income_change(
        make_state(),
        make_state(),
    )

    assert result == ForwardIncomeChangeReason.NO_CHANGE


def test_position_closed_when_current_has_zero_shares() -> None:
    result = classify_forward_income_change(
        make_state(shares="100"),
        make_state(shares="0"),
    )

    assert result == ForwardIncomeChangeReason.POSITION_CLOSED


def test_position_closed_when_current_state_is_missing() -> None:
    result = classify_forward_income_change(
        make_state(shares="100"),
        None,
    )

    assert result == ForwardIncomeChangeReason.POSITION_CLOSED


def test_new_position_requires_positive_shares() -> None:
    with pytest.raises(ValueError):
        classify_forward_income_change(
            None,
            make_state(shares="0"),
        )


def test_both_states_missing_is_invalid() -> None:
    with pytest.raises(ValueError):
        classify_forward_income_change(None, None)


def test_symbols_must_match() -> None:
    with pytest.raises(ValueError):
        classify_forward_income_change(
            make_state(symbol="ARCC"),
            make_state(symbol="BXSL"),
        )


def test_zero_to_positive_is_new_position() -> None:
    result = classify_forward_income_change(
        make_state(shares="0"),
        make_state(shares="100"),
    )

    assert result == ForwardIncomeChangeReason.NEW_POSITION


def test_zero_to_zero_is_no_change() -> None:
    result = classify_forward_income_change(
        make_state(shares="0"),
        make_state(shares="0"),
    )

    assert result == ForwardIncomeChangeReason.NO_CHANGE


def test_compare_current_positions() -> None:
    previous = (
        make_state("ARCC", "100", "2.00"),
        make_state("BXSL", "100", "2.50"),
    )

    current = (
        make_state("ARCC", "150", "2.00"),
        make_state("BXSL", "100", "2.25"),
    )

    result = compare_forward_income_states(
        previous,
        current,
    )

    reasons = {
        change.state.symbol: change.reason
        for change in result
    }

    assert reasons["ARCC"] == ForwardIncomeChangeReason.POSITION_CHANGE
    assert reasons["BXSL"] == ForwardIncomeChangeReason.DIVIDEND_CHANGE


def test_compare_detects_position_and_dividend_change() -> None:
    previous = (
        make_state("ARCC", "100", "2.00"),
    )

    current = (
        make_state("ARCC", "150", "1.80"),
    )

    result = compare_forward_income_states(
        previous,
        current,
    )

    assert result[0].reason == (
        ForwardIncomeChangeReason.POSITION_AND_DIVIDEND_CHANGE
    )


def test_compare_detects_new_position() -> None:
    previous = (
        make_state("ARCC", "100", "2.00"),
    )

    current = (
        make_state("ARCC", "100", "2.00"),
        make_state("BXSL", "100", "2.50"),
    )

    result = compare_forward_income_states(
        previous,
        current,
    )

    reasons = {
        change.state.symbol: change.reason
        for change in result
    }

    assert reasons["BXSL"] == ForwardIncomeChangeReason.NEW_POSITION


def test_compare_detects_closed_position() -> None:
    previous = (
        make_state("ARCC", "100", "2.00"),
        make_state("BXSL", "100", "2.50"),
    )

    current = (
        make_state("ARCC", "100", "2.00"),
    )

    result = compare_forward_income_states(
        previous,
        current,
    )

    bxsl = next(
        change
        for change in result
        if change.state.symbol == "BXSL"
    )

    assert bxsl.reason == ForwardIncomeChangeReason.POSITION_CLOSED
    assert bxsl.state.shares == Decimal("0")


def test_closed_position_is_not_returned_twice() -> None:
    previous = (
        make_state("ARCC", "100", "2.00"),
        make_state("BXSL", "100", "2.50"),
    )

    current = (
        make_state("ARCC", "100", "2.00"),
    )

    result = compare_forward_income_states(
        previous,
        current,
    )

    assert [change.state.symbol for change in result] == [
        "ARCC",
        "BXSL",
    ]


def test_closed_position_disappears_when_already_absent() -> None:
    previous = (
        make_state("ARCC", "100", "2.00"),
    )

    current = ()

    first_result = compare_forward_income_states(
        previous,
        current,
    )

    assert len(first_result) == 1
    assert first_result[0].reason == (
        ForwardIncomeChangeReason.POSITION_CLOSED
    )

    second_result = compare_forward_income_states(
        (),
        (),
    )

    assert second_result == ()