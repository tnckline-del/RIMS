"""Tests for persistent RIMS import operation storage."""

from datetime import date, datetime, timezone

import pytest

from src.import_operation import (
    ImportFileType,
    ImportOperation,
    ImportStatus,
)
from src.import_operation_store import ImportOperationStore


VALID_HASH = "a" * 64
SECOND_HASH = "b" * 64
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


def test_empty_store_lists_no_operations(tmp_path) -> None:
    store = ImportOperationStore(tmp_path)

    assert store.list_operations() == []


def test_save_creates_json_file(tmp_path) -> None:
    store = ImportOperationStore(tmp_path)
    operation = make_operation()

    path = store.save(operation)

    assert path == tmp_path / "import-001.json"
    assert path.exists()


def test_save_creates_storage_directory(tmp_path) -> None:
    storage_path = tmp_path / "imports"
    store = ImportOperationStore(storage_path)

    store.save(make_operation())

    assert storage_path.exists()
    assert storage_path.is_dir()


def test_load_returns_saved_operation(tmp_path) -> None:
    store = ImportOperationStore(tmp_path)
    operation = make_operation()

    store.save(operation)

    loaded = store.load("import-001")

    assert loaded == operation


def test_save_and_load_preserve_transaction_account_and_dates(
    tmp_path,
) -> None:
    store = ImportOperationStore(tmp_path)

    operation = make_operation(
        source_file="transactions.csv",
        file_type=ImportFileType.TRANSACTIONS,
        file_hash=SECOND_HASH,
        account="Contributory-111",
        reporting_start_date=date(2026, 7, 1),
        reporting_end_date=date(2026, 7, 31),
    )

    store.save(operation)

    loaded = store.load("import-001")

    assert loaded.file_type == ImportFileType.TRANSACTIONS
    assert loaded.file_hash == SECOND_HASH
    assert loaded.account == "Contributory-111"
    assert loaded.reporting_start_date == date(2026, 7, 1)
    assert loaded.reporting_end_date == date(2026, 7, 31)


def test_save_protects_existing_operation(tmp_path) -> None:
    store = ImportOperationStore(tmp_path)
    operation = make_operation()

    store.save(operation)

    with pytest.raises(FileExistsError):
        store.save(operation)


def test_save_allows_explicit_overwrite(tmp_path) -> None:
    store = ImportOperationStore(tmp_path)

    original = make_operation()
    replacement = make_operation(
        source_file="replacement.csv",
        status=ImportStatus.CONFIRMED,
    )

    store.save(original)
    store.save(replacement, overwrite=True)

    loaded = store.load("import-001")

    assert loaded.source_file == "replacement.csv"
    assert loaded.status == ImportStatus.CONFIRMED


def test_load_missing_operation_raises_file_not_found(tmp_path) -> None:
    store = ImportOperationStore(tmp_path)

    with pytest.raises(FileNotFoundError):
        store.load("missing-import")


def test_load_blank_import_id_raises_value_error(tmp_path) -> None:
    store = ImportOperationStore(tmp_path)

    with pytest.raises(ValueError):
        store.load("   ")


def test_list_operations_returns_operations_in_import_id_order(
    tmp_path,
) -> None:
    store = ImportOperationStore(tmp_path)

    store.save(make_operation(import_id="import-003"))
    store.save(
        make_operation(
            import_id="import-001",
            file_hash=SECOND_HASH,
        )
    )
    store.save(
        make_operation(
            import_id="import-002",
            source_file="transactions.csv",
        )
    )

    operations = store.list_operations()

    assert [operation.import_id for operation in operations] == [
        "import-001",
        "import-002",
        "import-003",
    ]


def test_find_by_file_hash_returns_matching_operation(tmp_path) -> None:
    store = ImportOperationStore(tmp_path)
    operation = make_operation()

    store.save(operation)

    found = store.find_by_file_hash(VALID_HASH)

    assert found == operation


def test_find_by_file_hash_is_case_insensitive(tmp_path) -> None:
    store = ImportOperationStore(tmp_path)
    operation = make_operation()

    store.save(operation)

    found = store.find_by_file_hash(VALID_HASH.upper())

    assert found == operation


def test_find_by_file_hash_returns_none_when_not_found(tmp_path) -> None:
    store = ImportOperationStore(tmp_path)
    store.save(make_operation())

    assert store.find_by_file_hash(SECOND_HASH) is None


def test_find_by_file_hash_rejects_blank_hash(tmp_path) -> None:
    store = ImportOperationStore(tmp_path)

    with pytest.raises(ValueError):
        store.find_by_file_hash("   ")


def test_save_rejects_wrong_object_type(tmp_path) -> None:
    store = ImportOperationStore(tmp_path)

    with pytest.raises(TypeError):
        store.save("not an import operation")


def test_invalid_persisted_data_raises_value_error(tmp_path) -> None:
    store = ImportOperationStore(tmp_path)

    path = tmp_path / "invalid.json"
    path.write_text(
        '{"import_id": "invalid"}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        store.list_operations()
        