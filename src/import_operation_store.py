"""Persistent storage for RIMS import operations."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from .import_operation import (
    ImportFileType,
    ImportOperation,
    ImportStatus,
)


class ImportOperationStore:
    """Persist and retrieve RIMS import operations as JSON files."""

    def __init__(self, storage_path: str | Path) -> None:
        """Create an import-operation store."""
        self.storage_path = Path(storage_path)

    def _operation_path(self, import_id: str) -> Path:
        """Return the filesystem path for an import operation."""
        return self.storage_path / f"{import_id}.json"

    def save(
        self,
        operation: ImportOperation,
        overwrite: bool = False,
    ) -> Path:
        """
        Save an import operation.

        Existing operations are protected unless overwrite=True.
        """
        if not isinstance(operation, ImportOperation):
            raise TypeError(
                "ImportOperationStore requires an ImportOperation."
            )

        self.storage_path.mkdir(parents=True, exist_ok=True)

        path = self._operation_path(operation.import_id)

        if path.exists() and not overwrite:
            raise FileExistsError(
                f"Import operation already exists: {path}"
            )

        with path.open("w", encoding="utf-8") as file:
            json.dump(
                operation.to_dict(),
                file,
                indent=2,
                sort_keys=True,
            )
            file.write("\n")

        return path

    def load(self, import_id: str) -> ImportOperation:
        """Load one import operation by ID."""
        import_id = import_id.strip()

        if not import_id:
            raise ValueError("import_id cannot be blank.")

        path = self._operation_path(import_id)

        if not path.exists():
            raise FileNotFoundError(
                f"Import operation not found: {path}"
            )

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return self._deserialize(data)

    def list_operations(self) -> list[ImportOperation]:
        """
        Return all persisted import operations.

        Operations are returned in deterministic import-ID order.
        """
        if not self.storage_path.exists():
            return []

        operations: list[ImportOperation] = []

        for path in sorted(self.storage_path.glob("*.json")):
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)

            operations.append(self._deserialize(data))

        return operations

    def find_by_file_hash(
        self,
        file_hash: str,
    ) -> ImportOperation | None:
        """
        Return the first import operation matching a file hash.

        Returns None when the exact file hash has not been imported.
        """
        normalized_hash = file_hash.strip().lower()

        if not normalized_hash:
            raise ValueError("file_hash cannot be blank.")

        for operation in self.list_operations():
            if operation.file_hash == normalized_hash:
                return operation

        return None

    @staticmethod
    def _deserialize(data: dict[str, object]) -> ImportOperation:
        """Reconstruct an ImportOperation from persisted JSON data."""
        try:
            return ImportOperation(
                import_id=str(data["import_id"]),
                source_file=str(data["source_file"]),
                file_type=ImportFileType(str(data["file_type"])),
                file_hash=str(data["file_hash"]),
                account=(
                    str(data["account"])
                    if data["account"] is not None
                    else None
                ),
                reporting_start_date=(
                    date.fromisoformat(
                        str(data["reporting_start_date"])
                    )
                    if data["reporting_start_date"] is not None
                    else None
                ),
                reporting_end_date=(
                    date.fromisoformat(
                        str(data["reporting_end_date"])
                    )
                    if data["reporting_end_date"] is not None
                    else None
                ),
                imported_at=datetime.fromisoformat(
                    str(data["imported_at"])
                ),
                status=ImportStatus(str(data["status"])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "Invalid persisted import operation."
            ) from exc
        