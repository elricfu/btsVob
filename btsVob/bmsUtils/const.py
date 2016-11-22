#coding: utf-8

from enum import Enum
import six

if six.PY2:
    ORDER_STATUS = Enum(
        "OPEN",
        "FILLED",
        "REJECTED",
        "CANCELLED"
    )
    
    
    EVENT_TYPE = Enum(
        "DAY_START",
        "HANDLE_DAY_BAR",
        "DAY_END",
        "HANDLE_MIN_BAR",
        "DAILY_SETTLE"
    )
    
    
    EXECUTION_PHASE = Enum(
        "INIT",
        "HANDLE_BAR",
        "BEFORE_TRADING",
        "SCHEDULED",
        "FINALIZED"
    )

    ORDER_DIRECTION = Enum(
        "OPEN",
        "CLOSE"
    )

    ORDER_OFFSET = Enum(
        "LONG",
        "SHORT"
    )
else:
    ORDER_STATUS = Enum("ORDER_STATUS", [
        "OPEN",
        "FILLED",
        "REJECTED",
        "CANCELLED",
    ])
    
    
    EVENT_TYPE = Enum("EVENT_TYPE", [
        "DAY_START",
        "HANDLE_DAY_BAR",
        "DAY_END",
        "HANDLE_MIN_BAR"
    ])
    
    
    EXECUTION_PHASE = Enum("EXECUTION_PHASE", [
        "INIT",
        "HANDLE_BAR",
        "BEFORE_TRADING",
        "SCHEDULED",
        "FINALIZED",
    ])
    

class DAYS_CNT(object):
    DAYS_A_YEAR = 365
    TRADING_DAYS_A_YEAR = 252
