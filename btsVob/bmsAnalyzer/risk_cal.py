#coding: utf-8

from __future__ import division

import copy
import numpy as np
import pandas as pd
import datetime

from collections import OrderedDict

from .risk import Risk
from ..bmsUtils import const


class RiskCal(object):
    def __init__(self, trading_params, data_proxy):
        """计算风险回报需要一些特殊处理,如果是分钟线需要找出那些结算的时间点"""

        self.data_proxy = data_proxy
        self.start_date = trading_params.start_date
        
        if trading_params.frequency == '1m':
            self.trading_index = self.pick_up_settlement_date(trading_params.trading_calendar)
        else:
            self.trading_index = trading_params.trading_calendar

        self.trading_days_cnt = len(self.trading_index)
        self.strategy_total_daily_returns = np.full(self.trading_days_cnt, np.nan)
        self.strategy_current_daily_returns = None

        self.strategy_total_returns = np.full(self.trading_days_cnt, np.nan)
        self.strategy_current_total_returns = None

        self.strategy_annualized_returns = np.full(self.trading_days_cnt, np.nan)
        self.strategy_current_annualized_returns = None

        self.risk = Risk()

        self.daily_risks = OrderedDict()

        self.current_max_returns = -np.inf
        self.current_max_drawdown = 0
        
        #无风险利率暂时设置为0
        self.riskfree_total_returns = 0

    def pick_up_settlement_date(self, trading_calendar):
        """选择结算的时间点"""
        index = []
        for elt in trading_calendar:
            if self.judge_settlement_time(elt.to_datetime()) == True:
                index.append(elt)
        index = pd.tseries.index.DatetimeIndex(index)
        return index

    def judge_settlement_time(self, date):
        settle1 = [datetime.datetime.strptime(date.strftime('%Y-%m-%d')+' 15:00:00', '%Y-%m-%d %H:%M:%S'),
                   datetime.datetime.strptime(date.strftime('%Y-%m-%d')+' 20:00:00', '%Y-%m-%d %H:%M:%S')]
        settle2 = [datetime.datetime.strptime(date.strftime('%Y-%m-%d')+' 03:00:00', '%Y-%m-%d %H:%M:%S'),
                   datetime.datetime.strptime(date.strftime('%Y-%m-%d')+' 08:00:00', '%Y-%m-%d %H:%M:%S')]
        if ((date >= settle1[0] and date < settle1[1]) or
            (date >= settle2[0] and date < settle2[1])):
            return True
        else:
            return False
        
    def calculate(self, date, strategy_daily_returns):

        idx = self.latest_idx = self.trading_index.get_loc(date)
        # daily
        self.strategy_total_daily_returns[idx] = strategy_daily_returns
        self.strategy_current_daily_returns = self.strategy_total_daily_returns[:idx + 1]

        self.days_cnt = len(self.strategy_current_daily_returns)
        days_pass_cnt = (date - self.start_date).days + 1

        # total
        self.strategy_total_returns[idx] = (1. + self.strategy_current_daily_returns).prod() - 1
        self.strategy_current_total_returns = self.strategy_total_returns[:idx + 1]

        # annual
        self.strategy_annualized_returns[idx] = (1 + self.strategy_current_total_returns[-1]) ** (
                    const.DAYS_CNT.DAYS_A_YEAR / days_pass_cnt) - 1
        self.strategy_current_annualized_returns = self.strategy_annualized_returns[:idx + 1]

        if self.strategy_current_total_returns[-1] > self.current_max_returns:
            self.current_max_returns = self.strategy_current_total_returns[-1]

        risk = self.risk
        risk.volatility = self.cal_volatility()
        risk.max_drawdown = self.cal_max_drawdown()
        risk.downside_risk = self.cal_downside_risk()
        risk.sharpe = self.cal_sharpe()
        risk.sortino = self.cal_sortino()
        self.daily_risks[date] = copy.deepcopy(risk)

    def cal_volatility(self):
        daily_returns = self.strategy_current_daily_returns
        if len(daily_returns) <= 1:
            return 0.
        volatility = const.DAYS_CNT.TRADING_DAYS_A_YEAR ** 0.5 * np.std(daily_returns, ddof=1)
        return volatility

    def cal_max_drawdown(self):
        today_return = self.strategy_current_total_returns[-1]
        today_drawdown = (1. + today_return) / (1. + self.current_max_returns) - 1.
        if today_drawdown < self.current_max_drawdown:
            self.current_max_drawdown = today_drawdown
        return self.current_max_drawdown

    def cal_sharpe(self):
        volatility = self.risk.volatility
        strategy_rets = self.strategy_current_daily_returns.sum() / len(self.strategy_current_daily_returns) * const.DAYS_CNT.TRADING_DAYS_A_YEAR

        sharpe = (strategy_rets - self.riskfree_total_returns) / volatility

        return sharpe

    def cal_sortino(self):
        strategy_rets = self.strategy_current_daily_returns.sum() / len(self.strategy_current_daily_returns) * const.DAYS_CNT.TRADING_DAYS_A_YEAR
        downside_risk = self.risk.downside_risk

        sortino = (strategy_rets - self.riskfree_total_returns) / downside_risk
        return sortino

    def cal_downside_risk(self):
        mask = self.strategy_current_daily_returns < 0
        diff = self.strategy_current_daily_returns[mask]
        if len(diff) <= 1:
            return 0.

        return ((diff * diff).sum() / len(diff)) ** 0.5 * const.DAYS_CNT.TRADING_DAYS_A_YEAR ** 0.5

    def __repr__(self):
        return "RiskCal({0})".format(self.__dict__)
