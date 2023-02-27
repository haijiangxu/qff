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

from qff.frame.context import context, RUN_TYPE
from qff.price.cache import get_current_data


class Portfolio:
    """
    股票账户

    账户当前的资金，标的信息，即所有标的操作仓位的信息汇总。

    ==================  ==============  ==============================================================
        属性               类型                说明
    ==================  ==============  ==============================================================
    starting_cash        float              初始资金
    available_cash       float              当可用资金, 可用来购买证券的资金
    locked_cash          float              挂单锁住资金
    total_assets         float              账户总资产, 包括现金, 仓位(股票)的总价值, 可用来计算收益
    positions_assets     float              持仓资产价值
    benchmark_assets     float              基准市值
    income               float              账户累计收益
    returns              float              账户收益率
    day_income           float              当日盈亏金额
    day_returns          float              当日涨幅
    positions            Dict               当前仓位，key值为股票代码，value是 :class:`.Position` 对象
    benchmark_returns    float              基准收益率
    ==================  ==============  ==============================================================

    """

    def __init__(self, starting_cash):
        self.starting_cash = starting_cash  # 初始资金
        self.available_cash = starting_cash  # 可用资金, 可用来购买证券的资金
        self.locked_cash = 0  # 挂单锁住资金
        self.positions = {}  # key值为股票代码，value是Position对象
        self.pre_total_assets = starting_cash  # 上一个交易日的资产总值，用于计算当日收益。
        self._snapshot_time = None
        self._total_assets = 0
        self._position_assets = 0

    def update(self):
        self._position_assets = sum([pst.valuation for pst in self.positions.values()])
        self._total_assets = round(self.available_cash + self._position_assets + self.locked_cash, 2)
        self._snapshot_time = context.current_dt

    @property
    def positions_assets(self):
        """ 持仓资产市值 """
        if context.current_dt != self._snapshot_time:
            self.update()
        return self._position_assets

    @property
    def total_assets(self):
        """  账户当日总市值

        包括现金, 仓位(股票)的总价值, 可用来计算收益
        """
        if context.current_dt != self._snapshot_time:
            self.update()
        return self._total_assets

    @property
    def benchmark_assets(self):
        """ 基准市值 """
        if context.run_type == RUN_TYPE.BACK_TEST:
            b_assets = round(context.bm_data.loc[context.current_dt[0:10]].close
                             / context.bm_start * self.starting_cash, 2)
        else:
            b_assets = round(get_current_data(context.benchmark, market='index').last_price
                             / context.bm_start * self.starting_cash, 2)

        return b_assets

    @property
    def income(self):
        """ 账户累计收益 """
        return round(self.total_assets - self.starting_cash , 2)

    @property
    def returns(self):
        """ 账户累计收益率 """
        return round(self.total_assets / self.starting_cash - 1, 4)

    @property
    def benchmark_returns(self):
        """ 基准收益率 """
        return round(self.benchmark_assets / self.starting_cash - 1, 4)

    @property
    def day_income(self):
        """ 账户当日盈亏 """
        return round(self.total_assets - self.pre_total_assets, 2)

    @property
    def day_returns(self):
        """ 账户当日涨幅 """
        return round(self.total_assets / self.pre_total_assets - 1, 4)

    @property
    def message(self):
        """ 账户当前资产信息快照 """
        return {
            '日期': context.current_dt[:10],
            '现金资产': round(self.available_cash + self.locked_cash, 2),
            '持仓资产': self.positions_assets,
            '账户总资产': self.total_assets,
            '累计收益额': self.income,
            '累计收益率': self.returns,
            '当日盈亏金额': self.day_income,
            '当日涨幅': self.day_returns,
            '仓位': round(self.positions_assets / self.total_assets, 4),
            '基准总资产': self.benchmark_assets,
            '基准收益率': self.benchmark_returns,
        }

    @property
    def init_message(self):
        return {
            '日期': context.previous_date[:10],
            '现金资产': self.starting_cash,
            '持仓资产': 0,
            '账户总资产': self.starting_cash,
            '累计收益额': 0,
            '累计收益率': 0,
            '当日盈亏金额': 0,
            '当日涨幅': 0,
            '仓位': 0,
            '基准总资产': self.starting_cash,
            '基准收益率': 0,
        }


def get_portfolio():
    """ 获取账户当前时刻信息 """
    return context.portfolio.message, [pst.message for pst in context.portfolio.positions.values()]
