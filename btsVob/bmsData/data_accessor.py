#coding: utf-8
import abc
import datetime
import pandas as pd
import numpy as np
from six import with_metaclass, string_types

from .data_bar import BarObject
from ..bmsUtils.context import ExecutionContext
from .data_source import LocalDataSource

class DataProxy(with_metaclass(abc.ABCMeta)):
    @abc.abstractmethod
    def get_bar(self, order_book_id, dt):
        """get stock Bar object

        :param str order_book_id:
        :param datetime.datetime dt:
        :returns: bar object
        :rtype: BarObject

        """
        raise NotImplementedError

    def latest_bar(self, order_book_id):
        """get latest bar of the stock

        :param str order_book_id:
        :returns: bar object
        :rtype: BarObject

        """
        dt = ExecutionContext.get_current_dt()

        return self.get_bar(order_book_id, dt)

    @abc.abstractmethod
    def history(self, order_book_id, dt, bar_count, frequency, field):
        """get history data

        :param str order_book_id:
        :param datetime dt:
        :param int bar_count:
        :param str frequency: '1d' or '1m' (沿用原来的标记1d表示日线,1m表示分钟线)
        :param str field: "open", "close", "high", "low", "volume", "oi"
        :returns:
        :rtype: pandas.DataFrame

        """
        raise NotImplementedError

    def last(self, order_book_id, dt, bar_count, frequency, field):
        """get history data, will not fill empty data

        :param str order_book_id:
        :param datetime dt:
        :param int bar_count:
        :param str frequency: '1d' or '1m'
        :param str field: "open", "close", "high", "low", "volume", "last", "total_turnover"
        :returns:
        :rtype: pandas.DataFrame

        """
        raise NotImplementedError

    @abc.abstractmethod
    def instrument(self, order_book_id):
        """get instrument of order book id

        :param str order_book_id:
        :returns: result instrument
        :rtype: Instrument

        """
        raise NotImplementedError


class LocalDataProxy(DataProxy):

    def __init__(self, root_dir):
        self._data_source = LocalDataSource(root_dir)
        self._cache = {}
        self._origin_cache = {}
        self._dividend_cache = {}

    def get_bar(self, order_book_id, dt):
        try:
            bars = self._cache[order_book_id]
        except KeyError:
            bars = self._data_source.get_all_bars(order_book_id)
            self._cache[order_book_id] = bars

        if isinstance(dt, string_types):
            dt = pd.Timestamp(dt)

        instrument = self._data_source.instruments(order_book_id)
        bar_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        return BarObject(instrument, bars[bars["time"].searchsorted(bar_str)])

    def history(self, order_book_id, dt, bar_count, frequency, field):
        try:
            bars = self._cache[order_book_id]
        except KeyError:
            bars = self._data_source.get_all_bars(order_book_id)
            self._cache[order_book_id] = bars
        bar_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        i = bars['time'].searchsorted(bar_str)
        left = i - bar_count + 1 if i >= bar_count else 0
        bars = bars[left:i + 1]
        series = pd.Series(bars[field], index=[datetime.datetime.strptime(t, '%Y-%m-%d %H:%M:%S') for t in bars["time"]])
        return series

    def last(self, order_book_id, dt, bar_count, frequency, field):
        try:
            bars = self._origin_cache[order_book_id]
        except KeyError:
            bars = self._data_source.get_all_bars(order_book_id)
            bars = bars[bars["volume"] > 0]
            self._origin_cache[order_book_id] = bars

        bar_str = dt.strftime('%Y-%d-%m %H:%M:%S')
        i = bars["time"].searchsorted(bar_str)
        left = i - bar_count + 1 if i >= bar_count else 0
        hist = bars[left:i + 1][field]

        return hist

    def get_trading_dates(self, start_date, end_date):
        return self._data_source.get_trading_dates(start_date, end_date)

    def instrument(self, order_book_id):
        return self._data_source.instruments(order_book_id)
