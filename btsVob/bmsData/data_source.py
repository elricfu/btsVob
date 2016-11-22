#coding: utf-8

import numpy as np
import six
import pandas as pd
from collections import defaultdict
from functools import partial

from .instruments import Instrument

class LocalDataSource(object):
    TRADING_DATES = 'trading_dates.bcolz'
    DAILY = 'daily.bcolz'
    INSTRUMENTS = 'instruments.pk'

    def __init__(self, root_dir):
        self._root_dir = root_dir
        import bcolz
        bcolz.defaults.out_flavor = "numpy"

        import os
        import pickle
        self._daily_table = bcolz.open(os.path.join(root_dir, LocalDataSource.DAILY))
        self._trading_dates = pd.Index(pd.Timestamp(d) for d in
                                       bcolz.open(os.path.join(root_dir, LocalDataSource.TRADING_DATES)))
        self._instruments = {d['order_book_id']: Instrument(d)
                             for d in pickle.load(open(os.path.join(root_dir, LocalDataSource.INSTRUMENTS), 'rb'))}


    def instruments(self, order_book_ids):
        if isinstance(order_book_ids, six.string_types):
            try:
                return self._instruments[order_book_ids]
            except KeyError:
                print('ERROR: order_book_id {} not exists!'.format(order_book_ids))
                return None

        return [self._instruments[ob] for ob in order_book_ids
                if ob in self._instruments]

    def all_instruments(self, itype='Future'):
        """暂时只考虑期货合约原始数据只包含order_book_id和type类型"""
        if itype is None:
            return pd.DataFrame([[v.order_book_id, v.type]
                                 for v in self._instruments.values()],
                                columns=['order_book_id', 'type'])

        if itype not in ['Future']:
            raise ValueError('Unknown type {}'.format(itype))

        return pd.DataFrame([v.__dict__ for v in self._instruments.values() if v.type == itype])

    def get_trading_dates(self, start_date, end_date):
        left = self._trading_dates.searchsorted(start_date)
        right = self._trading_dates.searchsorted(end_date, side='right')
        return self._trading_dates[left:right]

    def get_all_bars(self, order_book_id):
        try:
            start, end = self._daily_table.attrs[order_book_id]
        except KeyError:
            raise RuntimeError('No data for {}'.format(order_book_id))
        bars = self._daily_table[start:end]
        bars = bars[["time", "open", "high", "low", "close", "volume", "oi"]]
        return bars
