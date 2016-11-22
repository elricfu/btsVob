#coding: utf-8

import copy
import pandas as pd
import time
import datetime

from collections import defaultdict, OrderedDict
from six import iteritems

from ..bmsUtils.const import *
from ..bmsUtils.i18n import gettext as _
from ..bmsAccount import Account
from ..bmsLogger import user_log
from .order import Order
from .order_style import MarketOrder, LimitOrder
from .portfolio import Portfolio
from .risk_cal import RiskCal
from .trade import Trade

class SimuExchange(object):
    def __init__(self, data_proxy, trading_params, **kwargs):
        self.data_proxy = data_proxy
        self.trading_params = trading_params

        self.dt = None          # type: datetime.datetime current simulation datetime

        # TODO move risk cal outside this class
        self.risk_cal = RiskCal(trading_params, data_proxy)

        self.daily_portfolios = OrderedDict()      # type: Dict[str, Portfolio], each day has a portfolio copy
        self.all_orders = {}                       # type: Dict[str, Order], all orders, including cancel orders
        self.open_orders = defaultdict(list)       # type: Dict[str, List[Order]], all open orders

        self.start_date = start_date = self.trading_params.trading_calendar[0].to_datetime()
        self.account = Account(start_date=start_date, init_cash=self.trading_params.init_cash)

        self.last_date = None        # type: datetime.date, last trading date
        self.simu_days_cnt = 0       # type: int, days count since simulation start

    def on_dt_change(self, dt):
        """时间Ticker"""
        if dt.to_datetime() != self.current_date:
            self.last_date = self.current_date
        self.dt = dt.to_datetime()

    @property
    def current_date(self):
        return self.dt if self.dt else None

    def update_position(self, bar_dict):
        """更新仓位的情况"""
        portfolio = self.account.portfolio
        commission_info = self.account.commission_decider.commission_info
        positions = portfolio.positions
        old_premium = 0
        new_premium = 0
        for order_book_id, position in iteritems(positions):
            position.market_value = bar_dict[order_book_id].close 
            #计算权益变动
            symbol = self.get_contract_prefix(order_book_id)
            old_premium += position.bought_premium + position.sold_premium
            position.bought_premium = (position.market_value * position.bought_quantity) * float(commission_info[symbol]['premium']) * float(commission_info[symbol]['multiplier'])
            position.sold_premium = (position.market_value * position.sold_quantity) * float(commission_info[symbol]['premium']) * float(commission_info[symbol]['multiplier'])
            new_premium += position.bought_premium + position.sold_premium
        portfolio.cash += (old_premium - new_premium)
            
    def get_previous_portfolio(self):
        """返回之前的组合收益结构"""
        return self.daily_portfolios.get(self.last_date)
        
    def match_current_orders(self, bar_dict):
        """根据当前数据匹配落单"""
        trades, close_orders = self.match_orders(bar_dict)
        for trade in trades:
            self.account.record_new_trade(self.current_date, trade)
        self.remove_close_orders(close_orders)

        # remove rejected order
        rejected_orders = []
        for order_book_id, order_list in iteritems(self.open_orders):
            for order in order_list:
                if order.status == ORDER_STATUS.REJECTED:
                    rejected_orders.append(order)
        self.remove_close_orders(rejected_orders)

    def settlement_daily_portfolio(self):
        """盯市每日结算Market to Market"""
        previous_portfolio = self.get_previous_portfolio()
        portfolio = self.account.portfolio
        positions = portfolio.positions
        commission_info = self.account.commission_decider.commission_info
        print('euxyacg before settlement:%s' % portfolio.__dict__)

        for order_book_id, position in iteritems(positions):
            #根据平均持仓价格结算盈亏
            symbol = self.get_contract_prefix(order_book_id)
            longprofit = position.bought_quantity * (position.market_value - position.average_long_cost) * float(commission_info[symbol]['multiplier'])
            shortprofit = position.sold_quantity * (position.average_short_cost - position.market_value) * float(commission_info[symbol]['multiplier'])

            portfolio.pnl += (longprofit + shortprofit)

            #多空持仓的平均价格按照结算价格重新计算
            position.average_short_cost = position.market_value
            position.average_long_cost = position.market_value

            #多空持单的保证金需要重新计算
            position.bought_premium = (position.market_value * position.bought_quantity) * float(commission_info[symbol]['premium']) * float(commission_info[symbol]['multiplier'])  
            position.sold_premium = (position.market_value * position.sold_quantity) * float(commission_info[symbol]['premium']) * float(commission_info[symbol]['multiplier'])


        #判断是否需要追加保证金
        if portfolio.cash <= 0:
            print('Compensate premium:%f' % portfolio.cash)

        if previous_portfolio is None:
            previous_portfolio_value = portfolio.starting_cash
            portfolio.portfolio_value = portfolio.portfolio_value + portfolio.pnl - portfolio.total_commission
        else:
            previous_portfolio_value = previous_portfolio.portfolio_value
            settlement_commisstion = (portfolio.total_commission - previous_portfolio.total_commission)
            portfolio.portfolio_value = portfolio.portfolio_value + portfolio.pnl - settlement_commisstion

        #当日结算更新回报率这样便于和日线对接
        portfolio.daily_returns = portfolio.pnl / previous_portfolio_value
        portfolio.total_returns = portfolio.portfolio_value / portfolio.starting_cash - 1
        portfolio.annualized_returns = portfolio.total_returns * (
            DAYS_CNT.DAYS_A_YEAR / float((self.current_date - self.trading_params.start_date).days + 1))
        
        # 保存当前投资组合结构
        self.daily_portfolios[self.current_date] = copy.deepcopy(portfolio)
        # 计算当日风险水平
        self.risk_cal.calculate(self.current_date, portfolio.daily_returns)
        portfolio.pnl = 0

        print('euxyacg after settlement:%s' % portfolio.__dict__)

    def update_portfolio(self, bar_dict):
        #获取佣金对象这里为了拿到最小合约乘数后期需要抽象更新
        commission_info = self.account.commission_decider.commission_info
        portfolio = self.account.portfolio
        positions = portfolio.positions

        for order_book_id, position in iteritems(positions):
            #根据order_book_id获取合约前缀
            symbol = self.get_contract_prefix(order_book_id)
            position.market_value = bar_dict[order_book_id].close

    def create_order(self, bar_dict, order_book_id, amount, direction, offset):
        order = Order(self.dt, order_book_id, amount, direction, offset)
        self.open_orders[order_book_id].append(order)
        self.all_orders[order.order_id] = order

        # match order here because ricequant do this
        self.match_current_orders(bar_dict)
        self.update_portfolio(bar_dict)
        return order

    def cancel_order(self, order_id):
        order = self.get_order(order_id)
        if order in self.open_orders[order.order_book_id]:
            order.cancel()

    def remove_close_orders(self, close_orders):
        for order in close_orders:
            order_list = self.open_orders[order.order_book_id]
            try:
                order_list.remove(order)
            except ValueError:
                pass

    def get_order(self, order_id):
        return self.all_orders[order_id]

    def match_orders(self, bar_dict):
        # TODO abstract Matching Engine
        trades = []
        close_orders = []

        portfolio = self.account.portfolio
        positions = portfolio.positions

        slippage_decider = self.account.slippage_decider
        commission_decider = self.account.commission_decider
        commission_info = commission_decider.commission_info
        tax_decider = self.account.tax_decider
        data_proxy = self.data_proxy

        for order_book_id, order_list in iteritems(self.open_orders):
            # TODO handle limit order
            for order in order_list:

                #计算合约前缀获取保证金比例
                symbol = self.get_contract_prefix(order_book_id)
                premium = float(commission_info[symbol]['premium'])
                multiplier = float(commission_info[symbol]['multiplier'])

                # TODO check whether can match
                is_pass, reason = self.validate_order(bar_dict, order, premium, multiplier)
                if not is_pass:
                    order.mark_rejected(reason)
                    user_log.error(reason)
                    continue

                trade_price = slippage_decider.get_trade_price(data_proxy, order)
                amount = order.quantity

                trade = Trade(
                    date=order.dt,
                    order_book_id=order_book_id,
                    price=trade_price,
                    amount=order.quantity,
                    order_id=order.order_id,
                    commission=0.,
                )

                commission = commission_decider.get_commission(order, trade)
                trade.commission = commission

                # update order
                order.filled_shares = order.quantity
                close_orders.append(order)
                trades.append(trade)

                position = positions[order_book_id]
                #更新仓位
                if order.offset == 'open':
                    #模拟开仓逻辑
                    position.quantity += trade.amount
                    portfolio.cash -= (trade_price * amount * multiplier * premium)
                    portfolio.cash -= commission
                    portfolio.total_commission += commission
                    if order.direction == 'long':
                        position.bought_premium += trade.price * amount * multiplier * premium
                        position.long_sellable += amount
                        position.average_long_cost = trade.price * (amount/(position.bought_quantity + amount)) + position.average_long_cost * (position.bought_quantity/(position.bought_quantity + amount)) 
                        position.bought_quantity += amount
                        position.market_value = trade.price
                    if order.direction == 'short':
                        position.sold_premium += trade.price * amount * multiplier * premium
                        position.short_sellable += amount
                        position.average_short_cost = trade.price * (amount/(position.sold_quantity + amount)) + position.average_short_cost * (position.sold_quantity/(position.sold_quantity + amount)) 
                        position.sold_quantity += amount
                        position.market_value = trade.price
                
                if order.offset == 'close':
                    position.quantity -= trade.amount
                    portfolio.cash -= commission
                    #模拟平仓逻辑
                    if order.direction == 'long':
                        portfolio.cash += (position.average_short_cost * amount * multiplier * premium + (position.average_short_cost - trade.price) * multiplier)
                        portfolio.pnl += (position.average_short_cost - trade.price) * multiplier
                        position.sold_premium -= position.average_short_cost * amount * multiplier * premium
                        position.average_short_cost = 0 if (position.sold_quantity - amount) == 0 else (position.average_short_cost * position.sold_quantity - trade.price * amount) / (position.sold_quantity - amount)
                        position.sold_quantity -= amount
                        position.short_sellable -= amount
                        position.market_value = trade.price
                    elif order.direction == 'short':
                        portfolio.cash += (position.average_long_cost * amount * multiplier * premium + (trade.price - position.average_long_cost) * multiplier)
                        portfolio.pnl += (trade.price - position.average_long_cost) * multiplier
                        position.bought_premium -= position.average_long_cost * amount * multiplier * premium
                        position.average_long_cost = 0 if (position.bought_quantity - amount) == 0 else (position.average_long_cost * position.bought_quantity - trade.price * amount) / (position.bought_quantity - amount)
                        position.bought_quantity -= amount
                        position.long_sellable -= amount
                        position.market_value = trade.price
                    else:
                        print('Error direction')
                print('euxyacg print portfolio after open or close % s' % order.offset)
                print(portfolio.__dict__)
        return trades, close_orders

    def validate_order(self, bar_dict, order, premium, multiplier):
        """判断落单是否合理
        :bar_dict: 历史数据集合
        :order: 落单数据结构
        :premium: 单个合约保证金
        :multiplier: 合约权益乘数
        """
        order_book_id = order.order_book_id
        portfolio = self.account.portfolio 
        positions = portfolio.positions
        position = positions[order_book_id]
        bar = bar_dict[order_book_id]
        amount = order.quantity
        close_price = bar.close
        price = self.account.slippage_decider.get_trade_price(self.data_proxy, order)
        cost_money = price * amount
        is_buy = amount > 0
        
        if order.offset == 'open':
            #计算总体保证金
            total_premium = close_price * amount * multiplier * premium 
            if is_buy and total_premium > self.account.portfolio.cash:
                return False, _("Order Rejected: no enough money to buy {order_book_id}, needs {cost_money:.2f}, cash {cash:.2f}").format(
                    order_book_id=order_book_id,
                    cost_money=cost_money,
                    cash=portfolio.cash,
                )

        if order.offset == 'close':
            #平多
            if order.direction == 'long':
                if order.quantity > position.short_sellable:
                    return False, _("Order Rejected: no enough {order_book_id} to close, you want to close {quantity}, sellable {sellable}").format(
                        order_book_id=order_book_id,
                        quantity=order.quantity,
                        sellable=position.short_sellable,
                    )
            if order.direction == 'short':
               if order.quantity > position.long_sellable:
                    return False, _("Order Rejected: no enough {order_book_id} to close, you want to close {quantity}, sellable {sellable}").format(
                        order_book_id=order_book_id,
                        quantity=order.quantity,
                        sellable=position.long_sellable,
                    )
                
        return True, None

    def get_contract_prefix(self, contract_name):
        """通用函数获取合约前缀号"""
        symbol = contract_name[0:-4] if contract_name[-4].isdigit else contract_name[0:-3]
        return symbol
