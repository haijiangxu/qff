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

from qff.price.cache import get_current_data
from qff.frame.context import context
from qff.tools.date import get_trade_gap


class Position:
    """
    持仓标的信息

    持有的某个标的的信息

    ======================  ==============  ==============================================================
        属性                   类型                说明
    ======================  ==============  ==============================================================
    security                 str             股票代码
    security_name            str             股票名称
    init_time                str             建仓时间
    avg_cost                 float           当前持仓成本，只有在开仓/加仓时会更新
    acc_avg_cost             float           累计的持仓成本,在清仓/减仓时也会更新，该持仓累积的收益都会用于计算成本
    transact_time            str             最后交易时间
    locked_amount            int             挂单冻结仓位
    closeable_amount         int             可卖出的仓位，不包括挂单冻结仓位，建仓当天不能卖出
    today_open_amount        int             今天开仓的仓位
    today_open_price         float           今日开仓价格
    total_amount             int             总仓位, 等于locked_amount+closeable_amount+today_open_amount)
    latest_price             float           最新行情价格
    valuation                float           标的市值，计算方法是: price * total_amount
    income                   float           浮动盈亏
    income_rate              float           浮动盈亏比率
    today_income             float           当日盈亏
    today_income_rate        float           当日盈亏比率
    hold_days                int             持仓天数
    ======================  ==============  ==============================================================
    """
    def __init__(self, security, security_name, init_time, amount, avg_cost):
        self.security = security
        self.security_name = security_name  # 股票名称
        self.init_time = init_time       # 建仓时间
        self.avg_cost = avg_cost         # 是当前持仓成本，只有在开仓/加仓时会更新
        self.acc_avg_cost = avg_cost     # 累计的持仓成本,在清仓/减仓时也会更新，该持仓累积的收益都会用于计算成本
        self.transact_time = init_time   # 最后交易时间
        self.locked_amount = 0           # 挂单冻结仓位
        self.closeable_amount = 0        # 可卖出的仓位，不包括挂单冻结仓位，建仓当天不能卖出
        self.today_open_amount = amount  # 今天开的仓位
        self.today_open_price = avg_cost  # 今日开仓价格，加仓时保存，用于计算当日盈亏
        self.total_amount = amount       # 总仓位, 等于locked_amount+closeable_amount+today_open_amount)
        self.price = None                # 最新行情价格
        self.value = None                # 标的价值，计算方法是: price * total_amount

    @property
    def latest_price(self):
        """ 最新行情价格 """
        return get_current_data(self.security).last_price

    @property
    def valuation(self):
        """ 当前市值 """
        return round(self.total_amount * self.latest_price, 2)

    @property
    def income(self):
        """ 浮动盈亏 """
        return round((self.latest_price - self.acc_avg_cost) * self.total_amount, 2)

    @property
    def income_rate(self):
        """ 浮动利率率 """
        return round(self.latest_price / self.acc_avg_cost - 1, 4)

    @property
    def today_income(self):
        """ 当日盈亏 """
        cur_data = get_current_data(self.security)
        return round((self.total_amount - self.today_open_amount) *
                     (cur_data.last_price - cur_data.pre_close) +
                     (self.today_open_amount * (cur_data.last_price - self.today_open_price)), 2)

    @property
    def today_income_rate(self):
        """ 当日盈亏率 """
        today_income = self.today_income
        return round(today_income / (self.valuation - today_income), 4)

    @property
    def hold_days(self):
        """ 持仓天数 """
        return get_trade_gap(self.init_time[:10], context.current_dt[:10])

    @property
    def message(self):
        """ 当前持仓快照 """
        return {
            '日期': context.current_dt[:10],
            '股票代码' : self.security,
            '股票名称' : self.security_name,
            '持仓数量' : self.total_amount,
            '今开数量' : self.today_open_amount,
            '可用数量' : self.closeable_amount,
            '平均成本' : self.acc_avg_cost,
            '当前价格' : self.latest_price,
            '浮动盈亏' : self.income,
            '浮动盈亏率' : '{:.2%}'.format(self.income_rate),
            '当日盈亏' : self.today_income,
            '当日盈亏率' : '{:.2%}'.format(self.today_income_rate),
            '持仓天数' : self.hold_days,
            '当日市值': self.valuation,
            '仓位占比' : '{:.2%}'.format(self.valuation / context.portfolio.total_assets)
        }
