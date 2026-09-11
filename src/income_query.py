"""
Historical income query service for RIMS.

Sprint 19H provides a convenient query interface over the persisted
transaction repository.

This module answers historical income questions using actual transaction
records. It does not import Schwab files, alter transactions, annualize
partial periods, project future income, or make investment recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .transaction import (
    IncomeCharacter,
    IncomeType,
    InvestmentTransaction,
)
from .transaction_repository import TransactionRepository


@dataclass(frozen=True, slots=True)
class IncomeQuery:
    """
    Query service for persisted historical investment income.

    All returned amounts represent actual historical transaction amounts.
    """

    repository: TransactionRepository

    def income_by_account(
        self,
        account: str,
        *,
        recurring_only: bool = False,
    ) -> Decimal:
        """
        Return historical income for one account.

        Args:
            account: Exact account name.
            recurring_only: If True, include only recurring retirement income.
        """
        transactions = self.repository.transactions_by_account(account)

        return self._sum_income(
            transactions,
            recurring_only=recurring_only,
        )

    def income_by_symbol(
        self,
        symbol: str,
        *,
        recurring_only: bool = False,
    ) -> Decimal:
        """
        Return historical income for one security symbol.

        Symbol matching is case-insensitive.
        """
        transactions = self.repository.transactions_by_symbol(symbol)

        return self._sum_income(
            transactions,
            recurring_only=recurring_only,
        )

    def income_by_income_type(
        self,
        income_type: IncomeType,
        *,
        recurring_only: bool = False,
    ) -> Decimal:
        """
        Return historical income for one income type.
        """
        transactions = self.repository.transactions_by_income_type(
            income_type
        )

        return self._sum_income(
            transactions,
            recurring_only=recurring_only,
        )

    def income_by_date_range(
        self,
        start_date: date,
        end_date: date,
        *,
        recurring_only: bool = False,
    ) -> Decimal:
        """
        Return historical income received within an inclusive date range.
        """
        transactions = self.repository.transactions_by_date_range(
            start_date,
            end_date,
        )

        return self._sum_income(
            transactions,
            recurring_only=recurring_only,
        )

    def income_by_year(
        self,
        year: int,
        *,
        recurring_only: bool = False,
    ) -> Decimal:
        """
        Return historical income for one calendar year.

        The year is based on the transaction date.
        """
        if not isinstance(year, int):
            raise TypeError("year must be an integer.")

        transactions = (
            transaction
            for transaction in self.repository.income_transactions()
            if transaction.transaction_date.year == year
        )

        return self._sum_income(
            transactions,
            recurring_only=recurring_only,
        )

    def special_income_by_year(
        self,
        year: int,
    ) -> Decimal:
        """
        Return special income received during one calendar year.
        """
        return self._income_by_character_and_year(
            year,
            IncomeCharacter.SPECIAL,
        )

    def reinvested_income_by_year(
        self,
        year: int,
    ) -> Decimal:
        """
        Return reinvested income received during one calendar year.

        Reinvested income is still income. The corresponding Reinvest Shares
        transaction is not included and therefore cannot double-count it.
        """
        return self._income_by_character_and_year(
            year,
            IncomeCharacter.REINVESTED,
        )

    def prior_year_income_by_year(
        self,
        year: int,
    ) -> Decimal:
        """
        Return prior-year income recorded during one calendar year.
        """
        return self._income_by_character_and_year(
            year,
            IncomeCharacter.PRIOR_YEAR,
        )

    def income_adjustments_by_year(
        self,
        year: int,
    ) -> Decimal:
        """
        Return income adjustments recorded during one calendar year.
        """
        return self._income_by_character_and_year(
            year,
            IncomeCharacter.ADJUSTMENT,
        )

    def capital_gain_distributions_by_year(
        self,
        year: int,
    ) -> Decimal:
        """
        Return capital-gain distributions received during one calendar year.
        """
        if not isinstance(year, int):
            raise TypeError("year must be an integer.")

        return sum(
            (
                transaction.amount
                for transaction in self.repository.income_transactions()
                if (
                    transaction.transaction_date.year == year
                    and transaction.is_capital_gain_distribution
                )
            ),
            Decimal("0"),
        )

    def total_income(self) -> Decimal:
        """
        Return all historical income in the repository.
        """
        return self.repository.total_income()

    def total_recurring_income(self) -> Decimal:
        """
        Return all historical recurring retirement income.
        """
        return self.repository.total_recurring_income()

    def total_special_income(self) -> Decimal:
        """
        Return all historical special income.
        """
        return self._sum_by_character(IncomeCharacter.SPECIAL)

    def total_reinvested_income(self) -> Decimal:
        """
        Return all historical reinvested income.
        """
        return self._sum_by_character(IncomeCharacter.REINVESTED)

    def total_prior_year_income(self) -> Decimal:
        """
        Return all historical prior-year income.
        """
        return self._sum_by_character(IncomeCharacter.PRIOR_YEAR)

    def total_income_adjustments(self) -> Decimal:
        """
        Return all historical income adjustments.
        """
        return self._sum_by_character(IncomeCharacter.ADJUSTMENT)

    def total_capital_gain_distributions(self) -> Decimal:
        """
        Return all historical capital-gain distributions.
        """
        return sum(
            (
                transaction.amount
                for transaction in self.repository.income_transactions()
                if transaction.is_capital_gain_distribution
            ),
            Decimal("0"),
        )

    @staticmethod
    def _sum_income(
        transactions,
        *,
        recurring_only: bool,
    ) -> Decimal:
        """
        Sum income transactions according to the requested scope.
        """
        if recurring_only:
            return sum(
                (
                    transaction.amount
                    for transaction in transactions
                    if transaction.is_recurring_income
                ),
                Decimal("0"),
            )

        return sum(
            (
                transaction.amount
                for transaction in transactions
                if transaction.is_income
            ),
            Decimal("0"),
        )

    def _sum_by_character(
        self,
        character: IncomeCharacter,
    ) -> Decimal:
        """
        Return all income with a specified income character.
        """
        return sum(
            (
                transaction.amount
                for transaction in self.repository.income_transactions()
                if transaction.income_character == character
            ),
            Decimal("0"),
        )

    def _income_by_character_and_year(
        self,
        year: int,
        character: IncomeCharacter,
    ) -> Decimal:
        """
        Return income with a specified character during one calendar year.
        """
        if not isinstance(year, int):
            raise TypeError("year must be an integer.")

        return sum(
            (
                transaction.amount
                for transaction in self.repository.income_transactions()
                if (
                    transaction.transaction_date.year == year
                    and transaction.income_character == character
                )
            ),
            Decimal("0"),
        )


def query_historical_income(
    repository: TransactionRepository,
) -> IncomeQuery:
    """
    Convenience function for creating an IncomeQuery service.
    """
    return IncomeQuery(repository)