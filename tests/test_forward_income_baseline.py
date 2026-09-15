from decimal import Decimal

import pytest

from src.forward_income_baseline import ForwardIncomeBaseline
from src.forward_income_change import ForwardIncomePositionState


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


def test_save_and_load_round_trip(tmp_path) -> None:
    store = ForwardIncomeBaseline(tmp_path)

    states = (
        make_state("ARCC", "100", "2.00"),
        make_state("BXSL", "200", "2.50"),
    )

    store.save(states)

    assert store.load() == states


def test_missing_file_returns_empty_tuple(tmp_path) -> None:
    store = ForwardIncomeBaseline(tmp_path)

    assert store.load() == ()


def test_save_creates_storage_directory(tmp_path) -> None:
    storage_path = tmp_path / "baseline"

    store = ForwardIncomeBaseline(storage_path)

    store.save(
        (
            make_state(),
        )
    )

    assert storage_path.exists()
    assert store.file_path.exists()


def test_file_path_uses_expected_name(tmp_path) -> None:
    store = ForwardIncomeBaseline(tmp_path)

    assert store.file_path.name == "forward_income_baseline.json"


def test_save_rejects_non_tuple(tmp_path) -> None:
    store = ForwardIncomeBaseline(tmp_path)

    with pytest.raises(TypeError):
        store.save(
            [make_state()]
        )


def test_save_rejects_invalid_state(tmp_path) -> None:
    store = ForwardIncomeBaseline(tmp_path)

    with pytest.raises(TypeError):
        store.save(
            (object(),)
        )


def test_save_rejects_duplicate_symbols(tmp_path) -> None:
    store = ForwardIncomeBaseline(tmp_path)

    with pytest.raises(ValueError):
        store.save(
            (
                make_state("ARCC"),
                make_state("ARCC", "200"),
            )
        )


def test_load_rejects_non_list_json(tmp_path) -> None:
    store = ForwardIncomeBaseline(tmp_path)

    store.file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    store.file_path.write_text(
        '{"symbol": "ARCC"}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_load_rejects_non_object_record(tmp_path) -> None:
    store = ForwardIncomeBaseline(tmp_path)

    store.file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    store.file_path.write_text(
        "[1]",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_load_rejects_invalid_fields(tmp_path) -> None:
    store = ForwardIncomeBaseline(tmp_path)

    store.file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    store.file_path.write_text(
        (
            '[{"symbol": "ARCC", '
            '"shares": "100", '
            '"income": "2.00"}]'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_load_rejects_invalid_shares(tmp_path) -> None:
    store = ForwardIncomeBaseline(tmp_path)

    store.file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    store.file_path.write_text(
        (
            '[{"symbol": "ARCC", '
            '"shares": "not-a-number", '
            '"forward_annual_income_per_share": "2.00"}]'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_load_rejects_invalid_income_per_share(tmp_path) -> None:
    store = ForwardIncomeBaseline(tmp_path)

    store.file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    store.file_path.write_text(
        (
            '[{"symbol": "ARCC", '
            '"shares": "100", '
            '"forward_annual_income_per_share": "not-a-number"}]'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_load_rejects_duplicate_symbols(tmp_path) -> None:
    store = ForwardIncomeBaseline(tmp_path)

    store.file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    store.file_path.write_text(
        (
            '['
            '{"symbol": "ARCC", "shares": "100", '
            '"forward_annual_income_per_share": "2.00"},'
            '{"symbol": "ARCC", "shares": "200", '
            '"forward_annual_income_per_share": "2.50"}'
            ']'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_save_overwrites_previous_baseline(tmp_path) -> None:
    store = ForwardIncomeBaseline(tmp_path)

    store.save(
        (
            make_state("ARCC", "100", "2.00"),
        )
    )

    store.save(
        (
            make_state("ARCC", "150", "1.80"),
        )
    )

    loaded = store.load()

    assert loaded == (
        make_state("ARCC", "150", "1.80"),
    )


def test_decimal_precision_is_preserved(tmp_path) -> None:
    store = ForwardIncomeBaseline(tmp_path)

    state = make_state(
        "ARCC",
        "100.123456789",
        "2.058123456789",
    )

    store.save((state,))

    loaded = store.load()

    assert loaded[0].shares == Decimal("100.123456789")
    assert (
        loaded[0].forward_annual_income_per_share
        == Decimal("2.058123456789")
    )


def test_loaded_objects_are_position_states(tmp_path) -> None:
    store = ForwardIncomeBaseline(tmp_path)

    store.save(
        (
            make_state(),
        )
    )

    loaded = store.load()

    assert isinstance(
        loaded[0],
        ForwardIncomePositionState,
    )