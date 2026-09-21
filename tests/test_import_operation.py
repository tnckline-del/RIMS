"""Tests for the RIMS import operation model."""

from datetime import date, datetime, timezone

import pytest

from src.import_operation import (
    ImportFileType,
    ImportOperation,
    ImportStatus,
    calculate_file_hash,
)


VALID_HASH = "a" * 64
IMPORTED_AT = datetime(
    2026,
    9,
    20,
    12,
    30,
    tzinfo=timezone.utc,
)


def make_operation(**overrides: object) -> ImportOperation:
    """Create a valid ImportOperation for testing."""
    values: dict[str, object] = {
        "import_id": "import-001",
        "source_file": "positions.csv",
        "file_type": ImportFileType.POSITIONS,
        "file_hash": VALID_HASH,
        "account": None,
        "reporting_start_date": date(2026, 9, 7),
        "reporting_end_date": date(2026, 9, 7),
        "imported_at": IMPORTED_AT,
        "status": ImportStatus.VALIDATED,
    }
    values.update(overrides)
    return ImportOperation(**values)


def test_creates_valid_positions_operation() -> None:
    operation = make_operation()

    assert operation.import_id == "import-001"
    assert operation.source_file == "positions.csv"
    assert operation.file_type == ImportFileType.POSITIONS
    assert operation.file_hash == VALID_HASH
    assert operation.account is None
    assert operation.reporting_start_date == date(2026, 9, 7)
    assert operation.reporting_end_date == date(2026, 9, 7)
    assert operation.imported_at == IMPORTED_AT
    assert operation.status == ImportStatus.VALIDATED


def test_creates_valid_transaction_operation() -> None:
    operation = make_operation(
        source_file="transactions.csv",
        file_type=ImportFileType.TRANSACTIONS,
        account="Contributory-111",
        reporting_start_date=date(2026, 7, 1),
        reporting_end_date=date(2026, 7, 31),
    )

    assert operation.file_type == ImportFileType.TRANSACTIONS
    assert operation.account == "Contributory-111"
    assert operation.reporting_start_date == date(2026, 7, 1)
    assert operation.reporting_end_date == date(2026, 7, 31)


def test_normalizes_import_id_source_file_hash_and_account() -> None:
    operation = make_operation(
        import_id="  import-001  ",
        source_file=" /tmp/positions.csv ",
        file_hash=VALID_HASH.upper(),
        account="  Contributory-111  ",
    )

    assert operation.import_id == "import-001"
    assert operation.source_file == "positions.csv"
    assert operation.file_hash == VALID_HASH
    assert operation.account == "Contributory-111"


def test_blank_account_becomes_none() -> None:
    operation = make_operation(account="   ")

    assert operation.account is None


@pytest.mark.parametrize(
    "field, value",
    [
        ("import_id", ""),
        ("source_file", ""),
        ("file_hash", ""),
    ],
)
def test_rejects_blank_required_text(field: str, value: str) -> None:
    with pytest.raises(ValueError):
        make_operation(**{field: value})


@pytest.mark.parametrize(
    "file_hash",
    [
        "a" * 63,
        "a" * 65,
        "g" * 64,
        "not-a-sha256-hash",
    ],
)
def test_rejects_invalid_sha256_hash(file_hash: str) -> None:
    with pytest.raises(ValueError):
        make_operation(file_hash=file_hash)


def test_rejects_invalid_file_type() -> None:
    with pytest.raises(TypeError):
        make_operation(file_type="Positions")


def test_rejects_invalid_status() -> None:
    with pytest.raises(TypeError):
        make_operation(status="Validated")


def test_rejects_invalid_reporting_start_date() -> None:
    with pytest.raises(TypeError):
        make_operation(reporting_start_date="2026-09-07")


def test_rejects_invalid_reporting_end_date() -> None:
    with pytest.raises(TypeError):
        make_operation(reporting_end_date="2026-09-07")


def test_rejects_reversed_reporting_dates() -> None:
    with pytest.raises(ValueError):
        make_operation(
            reporting_start_date=date(2026, 9, 8),
            reporting_end_date=date(2026, 9, 7),
        )


def test_rejects_invalid_imported_at() -> None:
    with pytest.raises(TypeError):
        make_operation(imported_at="2026-09-20T12:30:00")


def test_to_dict_serializes_enum_and_date_values() -> None:
    operation = make_operation(account="Contributory-111")

    data = operation.to_dict()

    assert data == {
        "import_id": "import-001",
        "source_file": "positions.csv",
        "file_type": "Positions",
        "file_hash": VALID_HASH,
        "account": "Contributory-111",
        "reporting_start_date": "2026-09-07",
        "reporting_end_date": "2026-09-07",
        "imported_at": "2026-09-20T12:30:00+00:00",
        "status": "Validated",
    }


def test_operation_is_immutable() -> None:
    operation = make_operation()

    with pytest.raises(AttributeError):
        operation.status = ImportStatus.CONFIRMED


def test_calculate_file_hash_returns_sha256(tmp_path) -> None:
    import hashlib

    file_path = tmp_path / "sample.txt"
    content = b"RIMS test file"
    file_path.write_bytes(content)

    expected_hash = hashlib.sha256(content).hexdigest()

    assert calculate_file_hash(file_path) == expected_hash


def test_same_file_contents_produce_same_hash(tmp_path) -> None:
    first_file = tmp_path / "first.txt"
    second_file = tmp_path / "second.txt"

    first_file.write_bytes(b"identical contents")
    second_file.write_bytes(b"identical contents")

    assert calculate_file_hash(first_file) == calculate_file_hash(
        second_file
    )


def test_different_file_contents_produce_different_hashes(tmp_path) -> None:
    first_file = tmp_path / "first.txt"
    second_file = tmp_path / "second.txt"

    first_file.write_bytes(b"first contents")
    second_file.write_bytes(b"different contents")

    assert calculate_file_hash(first_file) != calculate_file_hash(
        second_file
    )


def test_calculate_file_hash_accepts_string_path(tmp_path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(b"RIMS test file")

    assert calculate_file_hash(str(file_path)) == calculate_file_hash(
        file_path
    )


def test_calculate_file_hash_missing_file_raises(tmp_path) -> None:
    file_path = tmp_path / "missing.txt"

    with pytest.raises(FileNotFoundError):
        calculate_file_hash(file_path)


def test_calculate_file_hash_directory_raises(tmp_path) -> None:
    directory = tmp_path / "directory"
    directory.mkdir()

    with pytest.raises(ValueError):
        calculate_file_hash(directory)
