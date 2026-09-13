from datetime import date
from decimal import Decimal

import pytest

from src.forward_income import ForwardIncomeAssumption
from src.forward_income_store import ForwardIncomeStore


def make_assumption(
    symbol: str,
    income: str,
    notes: str = "",
) -> ForwardIncomeAssumption:
    return ForwardIncomeAssumption(
        symbol=symbol,
        forward_annual_income=Decimal(income),
        effective_date=date(2026, 9, 7),
        source="Test",
        notes=notes,
    )


def test_missing_store_returns_empty_tuple(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    assert store.load() == ()


def test_save_and_load_round_trip(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    assumptions = (
        make_assumption("ARCC", "2058.24", "Current distribution"),
        make_assumption("BXSL", "2528.68"),
    )

    store.save(assumptions)

    loaded = store.load()

    assert loaded == assumptions


def test_saved_file_exists(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    store.save(
        (
            make_assumption("ARCC", "2058.24"),
        )
    )

    assert store.file_path.exists()
    assert store.file_path.name == "forward_income.json"


def test_decimal_precision_is_preserved(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    assumption = make_assumption(
        "ARCC",
        "2058.123456789",
    )

    store.save((assumption,))

    loaded = store.load()

    assert loaded[0].forward_annual_income == Decimal(
        "2058.123456789"
    )


def test_effective_date_is_preserved(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    assumption = make_assumption("ARCC", "2058.24")

    store.save((assumption,))

    loaded = store.load()

    assert loaded[0].effective_date == date(2026, 9, 7)


def test_source_and_notes_are_preserved(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    assumption = make_assumption(
        "ARCC",
        "2058.24",
        "Based on current declared distribution",
    )

    store.save((assumption,))

    loaded = store.load()

    assert loaded[0].source == "Test"
    assert loaded[0].notes == (
        "Based on current declared distribution"
    )


def test_save_creates_storage_directory(tmp_path) -> None:
    storage_path = tmp_path / "forward_income"

    store = ForwardIncomeStore(storage_path)

    store.save(
        (
            make_assumption("ARCC", "2058.24"),
        )
    )

    assert storage_path.exists()
    assert store.file_path.exists()


def test_save_requires_tuple(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    with pytest.raises(TypeError):
        store.save(
            [
                make_assumption("ARCC", "2058.24"),
            ]
        )


def test_save_rejects_invalid_assumption(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    with pytest.raises(TypeError):
        store.save((object(),))


def test_save_rejects_duplicate_symbols(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    with pytest.raises(ValueError):
        store.save(
            (
                make_assumption("ARCC", "2058.24"),
                make_assumption("ARCC", "2100"),
            )
        )


def test_load_rejects_non_list_json(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)
    store.file_path.parent.mkdir(parents=True, exist_ok=True)
    store.file_path.write_text(
        '{"symbol": "ARCC"}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_load_rejects_invalid_fields(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)
    store.file_path.parent.mkdir(parents=True, exist_ok=True)
    store.file_path.write_text(
        '[{"symbol": "ARCC"}]',
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_load_rejects_duplicate_symbols(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)
    store.file_path.parent.mkdir(parents=True, exist_ok=True)

    store.file_path.write_text(
        """
[
  {
    "symbol": "ARCC",
    "forward_annual_income": "2058.24",
    "effective_date": "2026-09-07",
    "source": "Test",
    "notes": ""
  },
  {
    "symbol": "ARCC",
    "forward_annual_income": "2100",
    "effective_date": "2026-09-07",
    "source": "Test",
    "notes": ""
  }
]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_load_rejects_invalid_decimal(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)
    store.file_path.parent.mkdir(parents=True, exist_ok=True)

    store.file_path.write_text(
        """
[
  {
    "symbol": "ARCC",
    "forward_annual_income": "not-a-number",
    "effective_date": "2026-09-07",
    "source": "Test",
    "notes": ""
  }
]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_load_rejects_invalid_date(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)
    store.file_path.parent.mkdir(parents=True, exist_ok=True)

    store.file_path.write_text(
        """
[
  {
    "symbol": "ARCC",
    "forward_annual_income": "2058.24",
    "effective_date": "not-a-date",
    "source": "Test",
    "notes": ""
  }
]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_save_overwrites_existing_dataset(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    store.save(
        (
            make_assumption("ARCC", "2058.24"),
        )
    )

    store.save(
        (
            make_assumption("BXSL", "2528.68"),
        )
    )

    loaded = store.load()

    assert loaded == (
        make_assumption("BXSL", "2528.68"),
    )


def test_loaded_assumptions_are_forward_income_assumptions(
    tmp_path,
) -> None:
    store = ForwardIncomeStore(tmp_path)

    store.save(
        (
            make_assumption("ARCC", "2058.24"),
        )
    )

    loaded = store.load()

    assert isinstance(
        loaded[0],
        ForwardIncomeAssumption,
    )