"""Persistent baseline state for forward income comparisons."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .forward_income_change import ForwardIncomePositionState


class ForwardIncomeBaseline:
    """Persist the last known forward income position state."""

    FILE_NAME = "forward_income_baseline.json"

    def __init__(self, storage_path: str | Path) -> None:
        self._storage_path = Path(storage_path)

    @property
    def file_path(self) -> Path:
        """Return the path of the persisted baseline file."""

        return self._storage_path / self.FILE_NAME

    def save(
        self,
        states: tuple[ForwardIncomePositionState, ...],
    ) -> None:
        """Save the current position states as the new baseline."""

        if not isinstance(states, tuple):
            raise TypeError("states must be a tuple")

        for state in states:
            if not isinstance(state, ForwardIncomePositionState):
                raise TypeError(
                    "states must contain only "
                    "ForwardIncomePositionState objects"
                )

        self._validate_unique_symbols(states)

        self._storage_path.mkdir(parents=True, exist_ok=True)

        payload = [
            {
                "symbol": state.symbol,
                "shares": str(state.shares),
                "forward_annual_income_per_share": str(
                    state.forward_annual_income_per_share
                ),
            }
            for state in states
        ]

        self.file_path.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )

    def load(self) -> tuple[ForwardIncomePositionState, ...]:
        """Load the last known position states."""

        if not self.file_path.exists():
            return ()

        payload = json.loads(
            self.file_path.read_text(encoding="utf-8")
        )

        if not isinstance(payload, list):
            raise ValueError(
                "forward income baseline must contain a JSON list"
            )

        states = tuple(
            self._state_from_dict(item)
            for item in payload
        )

        self._validate_unique_symbols(states)

        return states

    @staticmethod
    def _state_from_dict(
        item: object,
    ) -> ForwardIncomePositionState:
        """Convert one JSON object to a position state."""

        if not isinstance(item, dict):
            raise ValueError(
                "each forward income baseline record "
                "must be a JSON object"
            )

        required_fields = {
            "symbol",
            "shares",
            "forward_annual_income_per_share",
        }

        if set(item) != required_fields:
            raise ValueError(
                "forward income baseline record has invalid fields"
            )

        try:
            return ForwardIncomePositionState(
                symbol=item["symbol"],
                shares=Decimal(item["shares"]),
                forward_annual_income_per_share=Decimal(
                    item["forward_annual_income_per_share"]
                ),
            )
        except (
            TypeError,
            ValueError,
            KeyError,
            InvalidOperation,
        ) as exc:
            raise ValueError(
                "invalid forward income baseline record"
            ) from exc

    @staticmethod
    def _validate_unique_symbols(
        states: tuple[ForwardIncomePositionState, ...],
    ) -> None:
        """Reject duplicate symbols in baseline data."""

        symbols = [state.symbol for state in states]

        if len(symbols) != len(set(symbols)):
            raise ValueError(
                "forward income baseline must contain "
                "unique symbols"
            )