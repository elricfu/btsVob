#coding: utf-8

from __future__ import division
from functools import partial, wraps
from collections import Iterable
import copy
import datetime
import six

from ..bmsUtils import ExecutionContext
from ..bmsUtils.history import HybridDataFrame, missing_handler
from ..bmsUtils.const import *

__all__ = [
]

def export_as_api(func):
    __all__.append(func.__name__)
    return func

@export_as_api
@ExecutionContext.enforce_phase(EXECUTION_PHASE.BEFORE_TRADING,
                                EXECUTION_PHASE.HANDLE_BAR,
                                EXECUTION_PHASE.SCHEDULED)
def history(bar_count, frequency, field):
    executor = get_strategy_executor()
    data_proxy = get_data_proxy()
    results = {}
    dt = ExecutionContext.get_current_dt().to_datetime()
    for order_book_id in list(executor.current_universe):
        hist = data_proxy.history(order_book_id, dt, bar_count, frequency, field)
        results[order_book_id] = hist
    handler = partial(missing_handler, bar_count=bar_count, frequency=frequency, field=field)
    return HybridDataFrame(results, missing_handler=handler)

@export_as_api
def order_shares(id_or_ins, amount, direction, offset):
    """根据合约号和需要买卖的手数落单回测对外接口,后续需要统一
    :direction: long, short
    :offset: open, close
    """
    order_book_id = assure_order_book_id(id_or_ins)
    amount = int(amount)
    bar_dict = ExecutionContext.get_current_bar_dict()
    order = get_simu_exchange().create_order(bar_dict, order_book_id, amount, direction, offset)
    return order.order_id

def assure_order_book_id(id_or_ins):
    """确保合约号是回测系统支持的暂时不做检查"""
    if isinstance(id_or_ins, six.string_types):
        order_book_id = id_or_ins
    return order_book_id

def get_simu_exchange():
    return ExecutionContext.get_exchange()

def get_strategy_executor():
    return ExecutionContext.get_strategy_executor()

def get_strategy_context():
    return ExecutionContext.get_strategy_context()

def get_data_proxy():
    return ExecutionContext.get_strategy_executor().data_proxy
