#coding: utf-8
import os
import sys
import pandas as pd
import click
import six
from six import iteritems

from ..bmsUtils import ExecutionContext
from ..bmsUtils import dummy_func
from ..bmsUtils.const import *
from ..bmsAnalyzer import SimuExchange
from ..bmsEvent import SimulatorFutureTradingEventSource
from ..bmsData import BarMap
from ..bmsScheduler import scheduler

class StrategyContext(object):
    def __init__(self):
        self.__last_portfolio_update_dt = None

    @property
    def now(self):
        return ExecutionContext.get_current_dt()

    @property
    def slippage(self):
        return copy.deepcopy(ExecutionContext.get_exchange().account.slippage_decider)

    @slippage.setter
    @ExecutionContext.enforce_phase(EXECUTION_PHASE.INIT)
    def slippage(self, value):
        assert isinstance(value, (int, float))
        ExecutionContext.get_exchange().account.slippage_decider = FixedPercentSlippageDecider(rate=value)

    @property
    def commission(self):
        return copy.deepcopy(ExecutionContext.get_exchange().account.commission_decider)

    @commission.setter
    @ExecutionContext.enforce_phase(EXECUTION_PHASE.INIT)
    def commission(self, value):
        assert isinstance(value, (int, float))
        ExecutionContext.get_exchange().account.commission_decider = AStockCommission(commission_rate=value)

    @property
    def benchmark(self):
        return copy.deepcopy(ExecutionContext.get_trading_params().benchmark)

    @benchmark.setter
    @ExecutionContext.enforce_phase(EXECUTION_PHASE.INIT)
    def benchmark(self, value):
        assert isinstance(value, six.string_types)
        ExecutionContext.get_trading_params().benchmark = value

    @property
    def short_selling_allowed(self):
        raise NotImplementedError

    @short_selling_allowed.setter
    def short_selling_allowed(self):
        raise NotImplementedError

    @property
    def portfolio(self):
        dt = self.now
        if True:
            self.__portfolio = copy.deepcopy(ExecutionContext.get_exchange().account.portfolio)
            self.__last_portfolio_update_dt = dt
        return self.__portfolio

    def __repr__(self):
        items = ("%s = %r" % (k, v)
                 for k, v in self.__dict__.items()
                 if not callable(v) and not k.startswith("_"))
        return "Context({%s})" % (', '.join(items), )

class StrategyExecutor(object):
    """策略执行类
    Description:负责从策略中提取执行函数从而被调度
    将来具体策略中的执行函数需要和ftsVob中的策略函数统一
    """
    def __init__(self, trading_params, data_proxy, **kwargs):
        """策略执行类的构造函数
        :trading_params: 当前交易参数
        :data_proxy: 数据代理用来获取和策略相关的数据
        """
        self.trading_params = trading_params
        self._data_proxy = data_proxy

        self._strategy_context = kwargs.get("strategy_context")
        if self._strategy_context is None:
            self._strategy_context = StrategyContext()

        self._user_init = kwargs.get("init", dummy_func)
        self._user_handle_bar = kwargs.get("handle_bar", dummy_func)

        self._simu_exchange = kwargs.get("simu_exchange")
        if self._simu_exchange is None:
            self._simu_exchange = SimuExchange(data_proxy, trading_params)

        self._event_source = SimulatorFutureTradingEventSource(trading_params)
        self._current_dt = None
        self.current_universe = set()

        self.progress_bar = click.progressbar(length=len(self.trading_params.trading_calendar), show_eta=False)

    def execute(self):
        """运行策略
        :returns: 返回策略执行结果以DataFrame的方式
        """
        data_proxy = self.data_proxy
        strategy_context = self.strategy_context
        simu_exchange = self.exchange

        init = self._user_init
        handle_bar = self._user_handle_bar
        exchange_on_dt_change = simu_exchange.on_dt_change
        is_show_progress_bar = self.trading_params.show_progress

        def on_dt_change(dt):
            self._current_dt = dt
            exchange_on_dt_change(dt)

        with ExecutionContext(self, EXECUTION_PHASE.INIT):
            init(strategy_context)

        try:
            for dt, event in self._event_source:
                on_dt_change(dt)

                bar_dict = BarMap(dt, self.current_universe, data_proxy)

                if event == EVENT_TYPE.HANDLE_MIN_BAR:
                    with ExecutionContext(self, EXECUTION_PHASE.HANDLE_BAR, bar_dict):
                        handle_bar(strategy_context, None)
                        self.exchange.update_position(bar_dict)

                    if is_show_progress_bar:
                        self.progress_bar.update(1)

                if event == EVENT_TYPE.DAILY_SETTLE:
                    self.exchange.settlement_daily_portfolio()
                    
        finally:
            self.progress_bar.render_finish()

        results_df = self.generate_result(simu_exchange)
        return results_df

    def generate_result(self, simu_exchange):
        """生成运行结果
        :simu_exchange: 模拟交易器
        """
        account = simu_exchange.account
        risk_cal = simu_exchange.risk_cal
        columns = [
            "daily_returns",
            "total_returns",
            "annualized_returns",
            "market_value",
            "portfolio_value",
            "total_commission",
            "total_tax",
            "pnl",
            "positions",
            "cash",
        ]
        risk_keys = [
            "volatility",
            "max_drawdown",
            "sharpe",
            "downside_risk",
            "sortino",
        ]

        data = []
        for date, portfolio in iteritems(simu_exchange.daily_portfolios):
            print(date)
            print(portfolio.__dict__)
            # portfolio
            items = {"date": pd.Timestamp(date)}
            for key in columns:
                items[key] = getattr(portfolio, key)

            # trades
            items["trades"] = account.get_all_trades()[date]

            # risk
            risk = risk_cal.daily_risks[date]
            for risk_key in risk_keys:
                items[risk_key] = getattr(risk, risk_key)

            idx = risk_cal.trading_index.get_loc(date)
            data.append(items)

        results_df = pd.DataFrame(data)
        results_df.set_index("date", inplace=True)
        return results_df

    @property
    def strategy_context(self):
        """获取当前策略"""
        return self._strategy_context

    @property
    def exchange(self):
        """获取当前模拟交易器"""
        return self._simu_exchange

    @property
    def data_proxy(self):
        """获取数据代理"""
        return self._data_proxy

    @property
    def current_dt(self):
        """获取当前模拟器的交易时间"""
        return self._current_dt
