# coding :utf-8
#
# The MIT License (MIT)
#
# Copyright (c) 2016-2019 XuHaiJiang/QFF
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from qff.tools.logs import log
from qff.price.query import get_price, get_stock_name, get_index_name, get_stock_block
from qff.tools.date import *
from qff.price.fetch import fetch_current_ticks, fetch_today_min_curve, fetch_price

from qff.frame.context import context, RUNTYPE
from typing import Optional


backtest_cache = {}  # CurrentData对象缓存
realtime_cache = {}  # RealtimeData对象缓存
backtest_index_cache = {}  # CurrentData对象缓存
realtime_index_cache = {}  # RealtimeData对象缓存


class CacheData:
    def __init__(self, code, market='stock'):
        self.code = code
        self.market = market
        self._name = None
        self._block = None
        self._high_limit = None
        self._low_limit = None

    @property
    def high_limit(self):
        if self._high_limit is None:
            self._calc_limit()
        return self._high_limit

    @property
    def low_limit(self):
        if self._low_limit is None:
            self._calc_limit()
        return self._low_limit

    @property
    def name(self):
        if self._name is None:
            if self.market == "stock":
                dict_name = get_stock_name(self.code, context.previous_date)
            else:
                dict_name = get_index_name(self.code)
            if dict_name is not None:
                self._name = dict_name[self.code]
            else:
                self._name = 'UNKNOWED'

        return self._name

    @property
    def block(self):
        # 股票所属概念板块
        if self._block is None and self.market == "stock":
            self._block = get_stock_block(self.code)
        return self._block

    def _calc_limit(self):

        if self.code[:3] == '300' and context.previous_date >= '2020-08-24':  # 创业板改动涨停幅度日期
            cof = 0.2
        elif self.code[:3] == '688':
            cof = 0.2
        elif 'st' in self.name:   # 创业板和科创版ST涨跌幅度也是20%
            cof = 0.05
        else:
            cof = 0.1
        self._high_limit = round(self.pre_close * (1+cof), 2)
        self._low_limit = round(self.pre_close * (1-cof), 2)

    @property
    def pre_close(self):
        return 0

    @property
    def day_open(self):
        return 0

    @property
    def paused(self):
        return None

    @property
    def min_data_before(self):
        return None

    @property
    def min_data_after(self):
        return None

    @property
    def last_price(self):
        return 0

    @property
    def last_high(self):
        return 0

    @property
    def last_low(self):
        return 0

    @property
    def high_all_day(self):
        return 0

    @property
    def low_all_day(self):
        return 0

    @property
    def min_data_freq(self):
        return None

    @property
    def high_limit_time(self):
        """ 当天涨停时间 """
        return None

    @property
    def ticks(self):
        return None


class BacktestData(CacheData):
    """
    获取当前单位时间（当天/当前分钟）的涨跌停价, 是否停牌，当天的开盘价等。
    回测时, 通过其他获取数据的API获取到的是前一个单位时间(天/分钟)的数据, 而有些数据, 我们在这个单位时间是知道的,
    比如涨跌停价, 是否停牌, 当天的开盘价. 我们添加了这个API用来获取这些数据.
    :param code: 股票代码
    :return: 一个CurrentData对象, 拥有如下属性：
        high_limit: 涨停价
        low_limit: 跌停价
        paused: 是否停止或者暂停了交易, 当停牌、未上市或者退市后返回 True
        day_open: 当天开盘价
        pre_close: 昨日收盘价
        last_price: 最新的价格
        min_data_before 当日开盘到当前时间点的分钟曲线数据
        min_data_after: 当前时间点到收盘时的分钟曲线数据

    """
    def __init__(self, code, market="stock"):
        super().__init__(code, market)
        self._day_buff = get_price(code, end=context.current_dt[0:10], count=2, market=self.market)
        if len(self._day_buff) < 2:
            log.error("获取BacktestData对象失败！code:{},date:{}".format(code, context.current_dt[0:10]))
        self._pre_close = self._day_buff['close'][0]
        self._day_open = self._day_buff['open'][-1]
        self._min_buff = None
        self._min_buff_freq = None

    def _get_min_buff(self):
        for freq in ["1min", "5min", "15min", "30min"]:
            data = get_price(self.code, end=context.current_dt[0:10], freq=freq, market=self.market)
            if data is not None:
                self._min_buff = data
                self._min_buff_freq = freq
                break
        if data is None:
            log.error("获取BacktestData对象分钟数据失败！：{}-{}".format(context.current_dt[0:10], self.code))

    @property
    def pre_close(self):
        return self._pre_close

    @property
    def day_open(self):
        return self._day_open

    @property
    def paused(self):
        return self._day_buff["vol"][-1] < 1

    @property
    def min_data_before(self):
        if self._min_buff is None:
            self._get_min_buff()
        return self._min_buff.loc[:context.current_dt]

    @property
    def min_data_after(self):
        if self._min_buff is None:
            self._get_min_buff()
        return self._min_buff.loc[context.current_dt:]

    @property
    def last_price(self):
        if context.current_dt[11:16] <= '09:30':
            return self._day_open
        else:
            return self.min_data_before.iloc[-1].close

    @property
    def last_high(self):
        if context.current_dt[11:16] <= '09:30':
            return self._day_open
        else:
            return self.min_data_before.iloc[-1].high

    @property
    def last_low(self):
        if context.current_dt[11:16] <= '09:30':
            return self._day_open
        else:
            return self.min_data_before.iloc[-1].low

    @property
    def high_all_day(self):
        if context.current_dt[11:16] <= '09:30':
            return self._day_open
        else:
            return self.min_data_before.high.max()

    @property
    def low_all_day(self):
        if context.current_dt[11:16] <= '09:30':
            return self._day_open
        else:
            return self.min_data_before.low.min()

    @property
    def min_data_freq(self):
        if self._min_buff_freq is None:
            self._get_min_buff()
        return self._min_buff_freq

    @property
    def high_limit_time(self):
        """ 当天涨停时间 """
        if context.current_dt[11:16] <= '09:30':
            return 0
        else:
            freq = int(self.min_data_freq[:-3])
            df = self.min_data_before
            high_limit_count = (pd.Series(df.close >= self.high_limit).sum() +
                                pd.Series(df.open >= self.high_limit).sum() +
                                pd.Series(df.low >= self.high_limit).sum() +
                                pd.Series(df.high >= self.high_limit).sum()) / 4
            return int(high_limit_count * freq)


class RealtimeData(CacheData):
    def __init__(self, code, market="stock"):
        super().__init__(code, market)
        self._ticks = None
        self._bar = None
        self._bar_time = None
        self._name = None

    @property
    def day_open(self):
        if self._ticks is None:
            self._ticks = fetch_current_ticks(self.code, self.market)
        return self._ticks['open']

    @property
    def pre_close(self):
        if self._ticks is None:
            self._ticks = fetch_current_ticks(self.code, self.market)
        return self._ticks['pre_close']

    @property
    def last_price(self):
        if context.run_freq == 'tick' or context.current_dt[11:16] == '09:30':
            self._ticks = fetch_current_ticks(self.code, self.market)
            return self._ticks['price']
        elif self._bar_time == context.current_dt[11:16]:
            return self._bar['close']
        else:
            self._bar = fetch_price(self.code, 1, '1m', self.market)
            self._bar_time = context.current_dt[11:16]
            return self._bar['close']

    @property
    def high_all_day(self):
        self._ticks = fetch_current_ticks(self.code, self.market)
        return self._ticks['high']

    @property
    def low_all_day(self):
        self._ticks = fetch_current_ticks(self.code, self.market)
        return self._ticks['low']

    @property
    def ticks(self):
        self._ticks = fetch_current_ticks(self.code, self.market)
        return self._ticks

    @property
    def min_data_before(self):
        return fetch_today_min_curve(self.code, self.market)

    @property
    def last_high(self):
        if context.run_freq == 'tick' or context.current_dt[11:16] == '09:30':
            self._ticks = fetch_current_ticks(self.code, self.market)
            return self._ticks['price']
        elif self._bar_time == context.current_dt[11:16]:
            return self._bar['high']
        else:
            self._bar = fetch_price(self.code, 1, '1m', self.market)
            self._bar_time = context.current_dt[11:16]
            return self._bar['high']

    @property
    def last_low(self):
        if context.run_freq == 'tick' or context.current_dt[11:16] == '09:30':
            self._ticks = fetch_current_ticks(self.code, self.market)
            return self._ticks['price']
        elif self._bar_time == context.current_dt[11:16]:
            return self._bar['low']
        else:
            self._bar = fetch_price(self.code, 1, '1m', self.market)
            self._bar_time = context.current_dt[11:16]
            return self._bar['low']


def get_current_data(code, market='stock') -> Optional[CacheData]:
    if context.run_type == RUNTYPE.BACK_TEST:
        if market == 'stock':
            if code not in backtest_cache.keys():
                backtest_cache[code] = BacktestData(code, market)
            return backtest_cache[code]
        elif market == 'index':
            if code not in backtest_index_cache.keys():
                backtest_index_cache[code] = BacktestData(code, market)
            return backtest_index_cache[code]

    elif context.run_type == RUNTYPE.SIM_TRADE:
        if market == 'stock':
            if code not in realtime_cache.keys():
                realtime_cache[code] = RealtimeData(code, market)
            return realtime_cache[code]
        elif market == 'index':
            if code not in realtime_index_cache.keys():
                realtime_index_cache[code] = RealtimeData(code, market)
            return realtime_index_cache[code]

    log.error("get_current_data()出错，market值错误{}".format(market))
    return None


def clear_current_data():
    if context.run_type == RUNTYPE.BACK_TEST:
        backtest_cache.clear()
        backtest_index_cache.clear()
    elif context.run_type == RUNTYPE.SIM_TRADE:
        realtime_cache.clear()
        realtime_index_cache.clear()
    else:
        pass
