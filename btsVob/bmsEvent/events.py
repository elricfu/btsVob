#coding: utf-8
import datetime
import time
from ..bmsUtils.const import EVENT_TYPE

class SimulatorAStockTradingEventSource(object):
    def __init__(self, trading_param):
        self.trading_param = trading_param
        self.timezone = trading_param.timezone
        self.generator = self.create_generator()

    def create_generator(self):
        for date in self.trading_param.trading_calendar:
            yield date.replace(hour=9, minute=0), EVENT_TYPE.DAY_START
            yield date.replace(hour=15, minute=0), EVENT_TYPE.HANDLE_DAY_BAR
            yield date.replace(hour=16, minute=0), EVENT_TYPE.DAY_END

    def __iter__(self):
        return self

    def __next__(self):
        for date, event in self.generator:
            return date, event

        raise StopIteration

    next = __next__  # Python 2

class SimulatorFutureTradingEventSource(object):
    """添加期货时间事件这里只能支持分钟线"""
    def __init__(self, trading_param):
        self.trading_param = trading_param
        self.timezone = trading_param.timezone
        self.generator = self.create_generator()

    def judge_settle_time(self, date):
        """判断结算时间每天两次结算"""
        settle1 = [datetime.datetime.strptime(date.strftime('%Y-%m-%d')+' 15:00:00', '%Y-%m-%d %H:%M:%S'),
                   datetime.datetime.strptime(date.strftime('%Y-%m-%d')+' 20:00:00', '%Y-%m-%d %H:%M:%S')]
        settle2 = [datetime.datetime.strptime(date.strftime('%Y-%m-%d')+' 03:00:00', '%Y-%m-%d %H:%M:%S'),
                   datetime.datetime.strptime(date.strftime('%Y-%m-%d')+' 08:00:00', '%Y-%m-%d %H:%M:%S')]
        if ((date >= settle1[0] and date < settle1[1]) or
            (date >= settle2[0] and date < settle2[1])):
            return True
        else:
            return False
        
    def create_generator(self):
        for date in self.trading_param.trading_calendar:
            if self.judge_settle_time(date):
                yield date, EVENT_TYPE.DAILY_SETTLE
            else:
                yield date, EVENT_TYPE.HANDLE_MIN_BAR

    def __iter__(self):
        return self

    def __next__(self):
        for date, event in self.generator:
            return date, event

        raise StopIteration

    next = __next__
