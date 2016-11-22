#coding: utf-8

from collections import defaultdict

# TODO make field readonly
# TODO use nametuple to reduce memory


class Position(object):

    def __init__(self):
        self.quantity = 0.          # int 未平仓部分的总头寸
        self.bought_quantity = 0.   # int 该合约的总的多头头寸
        self.sold_quantity = 0.     # int 该合约的总的空头头寸
        self.bought_premium = 0.      # float 该合约的总的多头占用保证金
        self.sold_premium = 0.        # float 该合约的总的空头占用保证金
        self.long_sellable = 0.          # int 该合约的总的多头可平仓数目
        self.short_sellable = 0.          # int 该合约的总空头的可平仓数目
        self.average_long_cost = 0.      # float 获得多头均价,计算方法为每次买入的数量做加权平均
        self.average_short_cost = 0.     # float 获得空头均价,计算方法为每次买入的数量做加权平均
        self.market_value = 0.      # float 获得该持仓的实时市场价值单手的点数
        self.value_percent = 0.     # float 获得该持仓的实时市场价值在总投资组合价值中所占比例

    def __repr__(self):
        return "Position({%s})" % self.__dict__


def Positions():
    return defaultdict(Position)
