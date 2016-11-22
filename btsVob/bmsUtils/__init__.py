#coding: utf-8

import datetime
from six import iteritems

from .context import ExecutionContext
from .click_helper import Date
from .trading_params import TradingParams

def memoize(function):
    memo = {}
    function.__memo__ = memo

    def wrapper(*args, **kwargs):
        key = "#".join([str(arg) for arg in args] + ["%s:%s" % (k, v) for k, v in iteritems(kwargs)])
        if key in memo:
            return memo[key]
        else:
            rv = function(*args, **kwargs)
            memo[key] = rv
            return rv

    return wrapper

def dummy_func(*args, **kwargs):
    return None
