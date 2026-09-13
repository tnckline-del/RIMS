"""Persistent storage for forward annual income assumptions."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .forward_income import ForwardIncomeAssumption


class ForwardIncomeStore:
    """Persist forward annual income assumptions as JSON."""

    FILE_NAME = "forward_income.json"

    def __init__(self, storage_path: str | Path) -> None:
        self._storage_path = Path(storage_path)

    @property
    def file_path(self) -> Path:
        """Return the path of the persisted assumptions file."""

        return self._storage_path / self.FILE_NAME

    def save(
        self,
        assumptions: tuple[ForwardIncomeAssumption, ...],
    ) -> None:
        """Save forward income assumptions."""

        if not isinstance(assumptions, tuple):
            raise TypeError("assumptions must be a tuple")

        for assumption in assumptions:
            if not isinstance(assumption, ForwardIncomeAssumption):
                raise TypeError(
                    "assumptions must contain only "
                    "ForwardIncomeAssumption objects"
                )

        self._validate_unique_symbols(assumptions)

        self._storage_path.mkdir(parents=True, exist_ok=True)

        payload = [
            {
                "symbol": assumption.symbol,
                "forward_annual_income": str(
                    assumption.forward_annual_income
                ),
                "effective_date": assumption.effective_date.isoformat(),
                "source": assumption.source,
                "notes": assumption.notes,
            }
            for assumption in assumptions
        ]

        self.file_path.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )

    def load(self) -> tuple[ForwardIncomeAssumption, ...]:
        """Load persisted forward income assumptions."""

        if not self.file_path.exists():
            return ()

        payload = json.loads(
            self.file_path.read_text(encoding="utf-8")
        )

        if not isinstance(payload, list):
            raise ValueError(
                "forward income store must contain a JSON list"
            )

        assumptions = tuple(
            self._assumption_from_dict(item)
            for item in payload
        )

        self._validate_unique_symbols(assumptions)

        return assumptions

    @staticmethod
    def _assumption_from_dict(
        item: object,
    ) -> ForwardIncomeAssumption:
        """Convert one JSON object to an income assumption."""

        if not isinstance(item, dict):
            raise ValueError(
                "each forward income record must be a JSON object"
            )

        required_fields = {
            "symbol",
            "forward_annual_income",
            "effective_date",
            "source",
            "notes",
        }

        if set(item) != required_fields:
            raise ValueError(
                "forward income record has invalid fields"
            )

        try:
            return ForwardIncomeAssumption(
                symbol=item["symbol"],
                forward_annual_income=Decimal(
                    item["forward_annual_income"]
                ),
                effective_date=date.fromisoformat(
                    item["effective_date"]
                ),
                source=item["source"],
                notes=item["notes"],
            )
        except (
            TypeError,
            ValueError,
            KeyError,
            InvalidOperation,
        ) as exc:
            raise ValueError(
                "invalid forward income record"
            ) from exc

    @staticmethod
    def _validate_unique_symbols(
        assumptions: tuple[ForwardIncomeAssumption, ...],
    ) -> None:
        """Reject duplicate symbols in persisted data."""

        symbols = [assumption.symbol for assumption in assumptions]

        if len(symbols) != len(set(symbols)):
            raise ValueError(
                "forward income assumptions must contain "
                "unique symbols"
            )