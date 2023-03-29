from collections import defaultdict
from typing import List

from loguru import logger

from domain.currency_exchange_service.currencies import FiatValue
from domain.currency_exchange_service.exchanger import Exchanger
from domain.stock.profit.profit_per_year import ProfitPerYear
from domain.stock.queue import Queue
from domain.transactions import Transaction, Action


class PerStockProfitCalculator:
    EPSILON = 0.00000001

    def __init__(self, exchanger: Exchanger):
        self.exchanger = exchanger

    def _get_company_name(self, transaction: List[Transaction]) -> str:
        # check all transactions are from the same company
        assert (t.asset.asset_name == transaction[0].asset.asset_name for t in transaction), \
            "All transactions should be from the same company"
        return transaction[0].asset.asset_name

    def calculate_cost_and_income(self, transactions: List[Transaction]) -> ProfitPerYear:
        queue = Queue()

        profit = ProfitPerYear()

        logger.info(f"Calculating cost and income for company stock: {self._get_company_name(transactions)}")
        logger.info(f"Number of transactions: {len(transactions)}")

        for transaction in transactions:
            if transaction.action == Action.BUY:
                queue.append(transaction)
                continue

            transaction_cost = self._calculate_cost_for_sell(queue, transaction)
            transaction_income = self.exchanger.exchange(transaction.date, transaction.fiat_value)
            transaction_profit = transaction_income - transaction_cost
            logger.debug(
                f"Calculated cost and income for transaction: {transaction}, "
                f"cost = {transaction_cost}, income = {transaction_income}, profit = {transaction_profit}")

            profit.add_income(transaction.year(), transaction_income)
            profit.add_cost(transaction.year(), transaction_cost)

        return profit

    def _calculate_cost_for_sell(self, buy_queue: Queue, transaction: Transaction) -> FiatValue:
        stock_amount_to_account = transaction.asset.amount
        cost = FiatValue(0)

        while stock_amount_to_account > self.EPSILON:
            oldest_buy = buy_queue.head()
            oldest_buy_stock_amount = oldest_buy.asset.amount

            if oldest_buy_stock_amount <= stock_amount_to_account + self.EPSILON:
                cost += self.exchanger.exchange(oldest_buy.date, oldest_buy.fiat_value)
                stock_amount_to_account -= oldest_buy_stock_amount
                buy_queue.pop_head()
            else:
                ratio_of_oldest_buy_to_include = stock_amount_to_account / oldest_buy_stock_amount
                cost += self.exchanger.exchange(
                    transaction.date, oldest_buy.fiat_value) * ratio_of_oldest_buy_to_include
                stock_amount_to_account = 0
                new_head = buy_queue.head() * (1 - ratio_of_oldest_buy_to_include)
                buy_queue.replace_head(new_head)

        return cost
