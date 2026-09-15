from datetime import date
from decimal import Decimal
import json

import pytest

from src.forward_income import ForwardIncomeAssumption
from src.forward_income_store import ForwardIncomeStore


def make_assumption(
    symbol: str,
    income_per_share: str,
    notes: str = "",
) -> ForwardIncomeAssumption:
    return ForwardIncomeAssumption(
        symbol=symbol,
        forward_annual_income_per_share=Decimal(income_per_share),
        effective_date=date(2026, 9, 7),
        source="Test",
        notes=notes,
    )


def test_save_and_load_round_trip(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    assumptions = (
        make_assumption("ARCC", "2.05824", "Current distribution"),
        make_assumption("BXSL", "2.52868"),
    )

    store.save(assumptions)

    loaded = store.load()

    assert loaded == assumptions


def test_saved_file_exists(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    store.save(
        (
            make_assumption("ARCC", "2.05824"),
        )
    )

    assert store.file_path.exists()


def test_decimal_precision_is_preserved(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    assumption = make_assumption(
        "ARCC",
        "2.058123456789",
    )

    store.save((assumption,))

    loaded = store.load()

    assert (
        loaded[0].forward_annual_income_per_share
        == Decimal("2.058123456789")
    )


def test_effective_date_is_preserved(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    assumption = make_assumption("ARCC", "2.05824")

    store.save((assumption,))

    loaded = store.load()

    assert loaded[0].effective_date == date(2026, 9, 7)


def test_source_and_notes_are_preserved(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    assumption = make_assumption(
        "ARCC",
        "2.05824",
        "Based on current declared distribution",
    )

    store.save((assumption,))

    loaded = store.load()

    assert loaded[0].source == "Test"
    assert loaded[0].notes == "Based on current declared distribution"


def test_save_creates_storage_directory(tmp_path) -> None:
    storage_path = tmp_path / "forward_income"

    store = ForwardIncomeStore(storage_path)

    store.save(
        (
            make_assumption("ARCC", "2.05824"),
        )
    )

    assert storage_path.exists()
    assert store.file_path.exists()


def test_save_rejects_non_tuple(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    with pytest.raises(TypeError):
        store.save(
            [make_assumption("ARCC", "2.05824")]
        )


def test_save_rejects_invalid_assumption(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    with pytest.raises(TypeError):
        store.save(
            (object(),)
        )


def test_save_rejects_duplicate_symbols(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    with pytest.raises(ValueError):
        store.save(
            (
                make_assumption("ARCC", "2.05824"),
                make_assumption("ARCC", "2.10"),
            )
        )


def test_load_missing_file_returns_empty_tuple(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    assert store.load() == ()


def test_load_rejects_non_list_json(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    store.file_path.parent.mkdir(parents=True, exist_ok=True)
    store.file_path.write_text(
        '{"symbol": "ARCC"}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_load_rejects_non_object_record(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    store.file_path.parent.mkdir(parents=True, exist_ok=True)
    store.file_path.write_text(
        '[1]',
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_load_rejects_invalid_fields(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    store.file_path.parent.mkdir(parents=True, exist_ok=True)
    store.file_path.write_text(
        json.dumps(
            [
                {
                    "symbol": "ARCC",
                    "forward_annual_income": "2.05824",
                    "effective_date": "2026-09-07",
                    "source": "Test",
                    "notes": "",
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_load_rejects_invalid_decimal(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    store.file_path.parent.mkdir(parents=True, exist_ok=True)
    store.file_path.write_text(
        json.dumps(
            [
                {
                    "symbol": "ARCC",
                    "forward_annual_income_per_share": "not-a-number",
                    "effective_date": "2026-09-07",
                    "source": "Test",
                    "notes": "",
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_load_rejects_invalid_date(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    store.file_path.parent.mkdir(parents=True, exist_ok=True)
    store.file_path.write_text(
        json.dumps(
            [
                {
                    "symbol": "ARCC",
                    "forward_annual_income_per_share": "2.05824",
                    "effective_date": "not-a-date",
                    "source": "Test",
                    "notes": "",
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_load_rejects_duplicate_symbols(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    store.file_path.parent.mkdir(parents=True, exist_ok=True)
    store.file_path.write_text(
        json.dumps(
            [
                {
                    "symbol": "ARCC",
                    "forward_annual_income_per_share": "2.05824",
                    "effective_date": "2026-09-07",
                    "source": "Test",
                    "notes": "",
                },
                {
                    "symbol": "ARCC",
                    "forward_annual_income_per_share": "2.10",
                    "effective_date": "2026-09-07",
                    "source": "Test",
                    "notes": "",
                },
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.load()


def test_save_overwrites_existing_dataset(tmp_path) -> None:
    store = ForwardIncomeStore(tmp_path)

    store.save(
        (
            make_assumption("ARCC", "2.05824"),
        )
    )

    store.save(
        (
            make_assumption("BXSL", "2.52868"),
        )
    )

    loaded = store.load()

    assert len(loaded) == 1
    assert loaded[0].symbol == "BXSL"


def test_loaded_assumptions_are_forward_income_assumptions(
    tmp_path,
) -> None:
    store = ForwardIncomeStore(tmp_path)

    store.save(
        (
            make_assumption("ARCC", "2.05824"),
        )
    )

    loaded = store.load()

    assert isinstance(
        loaded[0],
        ForwardIncomeAssumption,
    )