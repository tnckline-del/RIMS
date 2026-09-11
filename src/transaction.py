"""
Purpose:
    Define the foundational RIMS InvestmentTransaction entity.

Responsibilities:
    - Represent a single investment transaction.
    - Preserve the original Schwab transaction action.
    - Classify transactions by transaction type.
    - Classify investment income by income type.
    - Classify income treatment and character.
    - Preserve tax character when available.
    - Support future expansion to purchases, sales, transfers, fees,
      and other investment transactions.
    - Provide dictionary serialization for future storage and analysis.

Dependencies:
    Python standard library only.

Revision History:
    0.2.0 - Initial InvestmentTransaction foundation.

Author:
    RIMS Development Team
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


class TransactionType(str, Enum):
    """Classify the broad economic type of an investment transaction."""

    INCOME = "Income"
    PURCHASE = "Purchase"
    SALE = "Sale"
    TRANSFER = "Transfer"
    FEE = "Fee"
    ADJUSTMENT = "Adjustment"
    OTHER = "Other"


class IncomeType(str, Enum):
    """Classify the economic source of investment income."""

    DIVIDEND = "Dividend"
    INTEREST = "Interest"
    CAPITAL_GAIN_DISTRIBUTION = "Capital Gain Distribution"
    OTHER = "Other"


class IncomeCharacter(str, Enum):
    """Classify how investment income should be treated."""

    RECURRING = "Recurring"
    SPECIAL = "Special"
    REINVESTED = "Reinvested"
    PRIOR_YEAR = "Prior Year"
    ADJUSTMENT = "Adjustment"


class TaxCharacter(str, Enum):
    """Preserve available tax classification information."""

    QUALIFIED = "Qualified"
    NON_QUALIFIED = "Non-Qualified"
    ORDINARY = "Ordinary"
    UNKNOWN = "Unknown"


@dataclass(frozen=True, slots=True)
class InvestmentTransaction:
    """
    Represent one investment transaction.

    The transaction model is intentionally broader than investment income.
    Income-related classifications are optional so that the same entity can
    eventually represent purchases, sales, transfers, fees, and other
    investment activity.

    Financial amounts use Decimal to preserve financial precision.
    """

    account: str
    transaction_date: date
    action: str
    symbol: str
    description: str
    amount: Decimal
    transaction_type: TransactionType
    income_type: IncomeType | None = None
    income_character: IncomeCharacter | None = None
    tax_character: TaxCharacter | None = None
    quantity: Decimal | None = None
    price: Decimal | None = None
    fees_and_commissions: Decimal = Decimal("0")
    source_file: str | None = None

    def __post_init__(self) -> None:
        """Normalize and validate the transaction."""

        account = self.account.strip()
        action = self.action.strip()
        symbol = self.symbol.strip().upper()
        description = self.description.strip()

        if not account:
            raise ValueError("Transaction account cannot be blank.")

        if not action:
            raise ValueError("Transaction action cannot be blank.")

        if not symbol:
            raise ValueError("Transaction symbol cannot be blank.")

        if not description:
            raise ValueError(
                "Transaction description cannot be blank."
            )

        if not isinstance(self.transaction_date, date):
            raise TypeError(
                "transaction_date must be a datetime.date."
            )

        if not isinstance(self.transaction_type, TransactionType):
            raise TypeError(
                "transaction_type must be a TransactionType."
            )

        amount = self._to_decimal(self.amount)
        quantity = (
            None
            if self.quantity is None
            else self._to_decimal(self.quantity)
        )
        price = (
            None
            if self.price is None
            else self._to_decimal(self.price)
        )
        fees = self._to_decimal(self.fees_and_commissions)

        if quantity is not None and quantity < 0:
            raise ValueError("Transaction quantity cannot be negative.")

        if price is not None and price < 0:
            raise ValueError("Transaction price cannot be negative.")

        if fees < 0:
            raise ValueError(
                "Transaction fees and commissions cannot be negative."
            )

        if self.transaction_type == TransactionType.INCOME:
            if self.income_type is None:
                raise ValueError(
                    "Income transactions require an income_type."
                )

            if self.income_character is None:
                raise ValueError(
                    "Income transactions require an income_character."
                )

        if self.transaction_type != TransactionType.INCOME:
            if self.income_type is not None:
                raise ValueError(
                    "income_type is only valid for income transactions."
                )

            if self.income_character is not None:
                raise ValueError(
                    "income_character is only valid for income "
                    "transactions."
                )

            if self.tax_character is not None:
                raise ValueError(
                    "tax_character is only valid for income transactions."
                )

        if self.source_file is not None:
            source_file = self.source_file.strip()

            if not source_file:
                source_file = None
        else:
            source_file = None

        object.__setattr__(self, "account", account)
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "price", price)
        object.__setattr__(
            self,
            "fees_and_commissions",
            fees,
        )
        object.__setattr__(self, "source_file", source_file)

    @staticmethod
    def _to_decimal(
        value: Decimal | float | int,
    ) -> Decimal:
        """Convert a numeric value to Decimal safely."""

        if isinstance(value, Decimal):
            return value

        return Decimal(str(value))

    @property
    def is_income(self) -> bool:
        """Return True when the transaction represents investment income."""

        return self.transaction_type == TransactionType.INCOME

    @property
    def is_dividend(self) -> bool:
        """Return True when the transaction represents dividend income."""

        return (
            self.is_income
            and self.income_type == IncomeType.DIVIDEND
        )

    @property
    def is_interest(self) -> bool:
        """Return True when the transaction represents interest income."""

        return (
            self.is_income
            and self.income_type == IncomeType.INTEREST
        )

    @property
    def is_capital_gain_distribution(self) -> bool:
        """Return True for capital-gain distribution transactions."""

        return (
            self.is_income
            and self.income_type
            == IncomeType.CAPITAL_GAIN_DISTRIBUTION
        )

    @property
    def is_special_income(self) -> bool:
        """Return True when the income is classified as special."""

        return (
            self.is_income
            and self.income_character == IncomeCharacter.SPECIAL
        )

    @property
    def is_reinvested_income(self) -> bool:
        """Return True when income was classified as reinvested."""

        return (
            self.is_income
            and self.income_character == IncomeCharacter.REINVESTED
        )

    @property
    def is_recurring_income(self) -> bool:
        """
        Return True when income is classified as recurring.

        Capital-gain distributions are never considered recurring
        retirement income even if their transaction character is
        otherwise classified as recurring.
        """

        return (
            self.is_income
            and self.income_character == IncomeCharacter.RECURRING
            and self.income_type
            != IncomeType.CAPITAL_GAIN_DISTRIBUTION
        )

    @property
    def is_prior_year_income(self) -> bool:
        """Return True for prior-year income transactions."""

        return (
            self.is_income
            and self.income_character == IncomeCharacter.PRIOR_YEAR
        )

    @property
    def is_income_adjustment(self) -> bool:
        """Return True for income adjustment transactions."""

        return (
            self.is_income
            and self.income_character == IncomeCharacter.ADJUSTMENT
        )

    def to_dict(self) -> dict[str, object]:
        """
        Return the transaction as a dictionary.

        Enum values are serialized as their string values.
        Decimal values remain Decimal objects so that downstream
        financial calculations do not lose precision.
        """

        return {
            "account": self.account,
            "transaction_date": self.transaction_date,
            "action": self.action,
            "symbol": self.symbol,
            "description": self.description,
            "amount": self.amount,
            "transaction_type": self.transaction_type.value,
            "income_type": (
                self.income_type.value
                if self.income_type is not None
                else None
            ),
            "income_character": (
                self.income_character.value
                if self.income_character is not None
                else None
            ),
            "tax_character": (
                self.tax_character.value
                if self.tax_character is not None
                else None
            ),
            "quantity": self.quantity,
            "price": self.price,
            "fees_and_commissions": self.fees_and_commissions,
            "source_file": self.source_file,
        }