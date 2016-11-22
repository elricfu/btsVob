#coding: utf-8
import os
import abc
import json
from six import with_metaclass

class BaseCommission(with_metaclass(abc.ABCMeta)):
    @abc.abstractmethod
    def get_commission(self, order, trade):
        """get commission

        :param order:
        :param trade:
        :returns: commission for current trade
        :rtype: float
        """
        raise NotImplementedError


class AStockCommission(BaseCommission):
    def __init__(self, commission_rate=0.0008, min_commission=5):
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self._commission_info = dict()
        self.read_commision_list()

    def read_commision_list(self):
        """读取合约佣金列表以JSON方式"""
        commission_path = os.path.dirname(__file__) + '/commission.json' 
        with open(commission_path) as f:
            self._commission_info =  json.load(f)
        
    def get_commission(self, order, trade):
        """根据合约号获取佣金,暂时不考虑平今的问题"""
        symbol = trade.order_book_id[0:-4] if trade.order_book_id[-4].isdigit else trade.order_book_id[0:-3]
        oc = self._commission_info[symbol]['oc'] 
        multiplier = float(self._commission_info[symbol]['multiplier'])
        if oc[-1] == '%':
            commission_rate = float(oc[0:-1]) / 100
            cost_money = trade.price * abs(trade.amount) * multiplier * commission_rate
        else:
            commission = float(oc)
            cost_money = abs(trade.amount) * commission
        return cost_money 
    
    @property
    def commission_info(self):
        return self._commission_info
