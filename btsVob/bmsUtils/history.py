#coding: utf-8

import pandas as pd

from . import ExecutionContext

class HybridDataFrame(pd.DataFrame):
    def __init__(self, *args, **kwargs):
        missing_handler = kwargs.pop("missing_handler")
        super(HybridDataFrame, self).__init__(*args, **kwargs)
        self.missing_handler = missing_handler
        self._cache = {}

    def __getitem__(self, key):
        try:
            # return self._cache[key]
            return super(HybridDataFrame, self).__getitem__(key)
        except KeyError as e:
            if not isinstance(key, str) or self.missing_handler is None:
                raise
            try:
                rv = self.missing_handler(key)
            except KeyError:
                raise e
            self[key] = rv
            return rv


def missing_handler(key, bar_count, frequency, field):
    order_book_id = key
    data_proxy = ExecutionContext.get_strategy_executor().data_proxy
    dt = ExecutionContext.get_current_dt().to_datetime()
    hist = data_proxy.history(order_book_id, dt, bar_count, frequency, field)
    series = hist
    executor = ExecutionContext.get_strategy_executor()
    executor.current_universe.add(key)
    return series
