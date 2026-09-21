"""Persistent identity and lifecycle model for RIMS import operations."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path

def calculate_file_hash(file_path: str | Path) -> str:
    """Return the SHA-256 hexadecimal digest of a file."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


class ImportFileType(str, Enum):
    """Identify the type of source file being imported."""

    POSITIONS = "Positions"
    TRANSACTIONS = "Transactions"


class ImportStatus(str, Enum):
    """Represent the lifecycle state of an import operation."""

    VALIDATED = "Validated"
    CONFIRMED = "Confirmed"
    STAGED = "Staged"
    IMPORTED = "Imported"
    RECONCILED = "Reconciled"
    VALIDATION_FAILED = "Validation Failed"
    IMPORT_FAILED = "Import Failed"
    RECONCILIATION_FAILED = "Reconciliation Failed"


@dataclass(frozen=True, slots=True)
class ImportOperation:
    """Represent one RIMS import operation."""

    import_id: str
    source_file: str
    file_type: ImportFileType
    file_hash: str
    account: str | None
    reporting_start_date: date | None
    reporting_end_date: date | None
    imported_at: datetime
    status: ImportStatus

    def __post_init__(self) -> None:
        """Validate and normalize the import operation."""

        import_id = self.import_id.strip()
        source_file = Path(self.source_file).name.strip()
        file_hash = self.file_hash.strip().lower()

        if not import_id:
            raise ValueError("import_id cannot be blank.")

        if not source_file:
            raise ValueError("source_file cannot be blank.")

        if not file_hash:
            raise ValueError("file_hash cannot be blank.")

        if len(file_hash) != 64:
            raise ValueError(
                "file_hash must be a 64-character SHA-256 hexadecimal digest."
            )

        if any(character not in "0123456789abcdef" for character in file_hash):
            raise ValueError(
                "file_hash must contain only hexadecimal characters."
            )

        if not isinstance(self.file_type, ImportFileType):
            raise TypeError("file_type must be an ImportFileType.")

        if self.account is not None:
            account = self.account.strip()
            if not account:
                account = None
        else:
            account = None

        if (
            self.reporting_start_date is not None
            and not isinstance(self.reporting_start_date, date)
        ):
            raise TypeError(
                "reporting_start_date must be a date or None."
            )

        if (
            self.reporting_end_date is not None
            and not isinstance(self.reporting_end_date, date)
        ):
            raise TypeError(
                "reporting_end_date must be a date or None."
            )

        if (
            self.reporting_start_date is not None
            and self.reporting_end_date is not None
            and self.reporting_start_date > self.reporting_end_date
        ):
            raise ValueError(
                "reporting_start_date cannot be later than "
                "reporting_end_date."
            )

        if not isinstance(self.imported_at, datetime):
            raise TypeError("imported_at must be a datetime.")

        if not isinstance(self.status, ImportStatus):
            raise TypeError("status must be an ImportStatus.")

        object.__setattr__(self, "import_id", import_id)
        object.__setattr__(self, "source_file", source_file)
        object.__setattr__(self, "file_hash", file_hash)
        object.__setattr__(self, "account", account)

    def to_dict(self) -> dict[str, object]:
        """Return a dictionary representation suitable for persistence."""

        return {
            "import_id": self.import_id,
            "source_file": self.source_file,
            "file_type": self.file_type.value,
            "file_hash": self.file_hash,
            "account": self.account,
            "reporting_start_date": (
                self.reporting_start_date.isoformat()
                if self.reporting_start_date is not None
                else None
            ),
            "reporting_end_date": (
                self.reporting_end_date.isoformat()
                if self.reporting_end_date is not None
                else None
            ),
            "imported_at": self.imported_at.isoformat(),
            "status": self.status.value,
        }