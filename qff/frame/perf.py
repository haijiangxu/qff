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


from collections import deque
from functools import lru_cache
from typing import Any, Union

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pandas import DataFrame

from qff.tools.date import get_trade_gap
from qff.frame.context import context


class Perf:
    pnl: Union[DataFrame, Any]

    def __init__(self, ctx=None):
        """
        根据历史订单记录,以先进先出法生成配对订单列表
        :param ctx: 框架上下文环境

        生成配对成交记录pnl,包括：
            [
                'code',       股票代码
                'name',       股票名称
                'buy_date',   买入日期
                'buy_price',  买入单价
                'sell_date',  卖出日期
                'sell_price', 卖出单价
                'amount',     成交数量
                'pnl_ratio',    收益率
                'pnl_money',    收益金额
                'hold_gap',     持股周期
            ]


        """
        if ctx is None:
            ctx = context

        order_hists = ctx.order_hists
        keys_name = ['股票代码', '股票名称', '交易方向', '交易日期', '成交单价', '成交数量', '交易费用']
        orders = [{key: value for key, value in x.items() if key in keys_name} for x in order_hists]
        if len(orders) > 0:
            df_order = pd.DataFrame(orders)

            df_order.rename(columns={'股票代码': 'security',
                                     '股票名称': 'security_name',
                                     '交易方向': 'is_buy',
                                     '交易日期': 'trade_date',
                                     '成交单价': 'trade_price',
                                     '成交数量': 'trade_amount',
                                     '交易费用': 'commission'
                                     }, inplace=True)

            self._orders = df_order
            self.pnl = self.pnl_fifo
        else:
            self._orders = None
            self.pnl = None

    @property
    def pnl_fifo(self):
        """
        使用先进先出法配对成交记录
        """
        codes = self._orders["security"].to_list()
        order_que = dict(
            zip(
                codes,
                [
                    {
                        'buy': deque(),
                    } for _ in range(len(codes))
                ]
            )
        )

        pair_table = []
        for _, data in self._orders.iterrows():
            while True:
                if data.is_buy == '买入':
                    order_que[data.security]['buy'].append(
                        (
                            data.trade_date,
                            data.trade_amount,
                            data.trade_price,
                        )
                    )
                    break
                else:
                    tmp = order_que[data.security]['buy'].popleft()
                    if tmp[1] > data.trade_amount:
                        temp = (tmp[0], tmp[1] - data.trade_amount, tmp[2])
                        order_que[data.security]['buy'].appendleft(temp)
                        pair_table.append(
                            [
                                data.security,
                                data.security_name,
                                tmp[0],
                                tmp[2],
                                data.trade_date,
                                data.trade_price,
                                data.trade_amount,
                            ]
                        )
                        break
                    elif tmp[1] < data.trade_amount:
                        data.trade_amount = data.trade_amount - tmp[1]
                        pair_table.append(
                            [
                                data.security,
                                data.security_name,
                                tmp[0],
                                tmp[2],
                                data.trade_date,
                                data.trade_price,
                                tmp[1],
                            ]
                        )
                    else:
                        pair_table.append(
                            [
                                data.security,
                                data.security_name,
                                tmp[0],
                                tmp[2],
                                data.trade_date,
                                data.trade_price,
                                data.trade_amount,
                            ]
                        )
                        break

        pair_title = [
            'code',
            'name',
            'buy_date',
            'buy_price',
            'sell_date',
            'sell_price',
            'amount',
        ]
        pnl = pd.DataFrame(pair_table, columns=pair_title)
        if len(pnl) > 0:
            pnl['pnl_return'] = pnl.apply(lambda x: '{:.2%}'.format((x['sell_price'] / x['buy_price']) - 1), axis=1)
            pnl = pnl.assign(pnl_money=round((pnl.sell_price - pnl.buy_price) * pnl.amount, 2))
            pnl["hold_gap"] = pnl.apply(lambda x: get_trade_gap(x['buy_date'], x['sell_date']), axis=1)
            # return pnl.set_index('code')
            return pnl
        else:
            return None

    @property
    def profit_pnl(self):
        """ 盈利交易列表 """
        return self.pnl.query('pnl_money>0')

    @property
    def loss_pnl(self):
        """ 亏损交易列表 """
        return self.pnl.query('pnl_money<0')

    @property
    def even_pnl(self):
        """ 持平交易列表 """
        return self.pnl.query('pnl_money==0')

    @property
    def net_profit(self):
        """ 交易总利润 """
        return round(self.pnl.pnl_money.sum(), 2)

    @property
    def total_profit(self):
        """ 总盈利金额 """
        if self.profit_pnl is not None and len(self.profit_pnl) > 0:
            return round(self.profit_pnl.pnl_money.sum(), 2)
        else:
            return 0

    @property
    def total_loss(self):
        """ 总亏损金额 """
        if self.loss_pnl is not None and len(self.loss_pnl) > 0:
            return round(self.loss_pnl.pnl_money.sum(), 2)
        else:
            return 0

    @property
    def total_pnl(self):
        """ 盈亏比 """
        if self.total_loss == 0:
            return np.Inf
        else:
            return round(abs(self.total_profit / self.total_loss), 2)

    @property
    def trading_amounts(self):
        """ 总交易次数 """
        return len(self.pnl)

    @property
    def profit_amounts(self):
        """ 盈利次数 """
        if self.profit_pnl is not None and len(self.profit_pnl) > 0:
            return len(self.profit_pnl)
        else:
            return 0

    @property
    def loss_amounts(self):
        """ 亏损次数 """
        if self.loss_pnl is not None and len(self.loss_pnl) > 0:
            return len(self.loss_pnl)
        else:
            return 0

    @property
    def even_amounts(self):
        """ 持平交易次数 """
        return len(self.even_pnl)

    @property
    def profit_percentage(self):
        """ 胜率 """
        try:
            return round(self.profit_amounts / self.trading_amounts, 4)
        except ZeroDivisionError:
            return 0

    @property
    def loss_percentage(self):
        """ 亏损比例 """
        try:
            return round(self.loss_amounts / self.trading_amounts, 4)
        except ZeroDivisionError:
            return 0

    @property
    def even_percentage(self):
        """ 持平交易比例 """
        try:
            return round(self.even_amounts / self.trading_amounts, 4)
        except ZeroDivisionError:
            return 0

    @property
    def average_loss(self):
        """ 单笔平均亏损金额 """
        if self.loss_pnl is not None and len(self.loss_pnl) > 0:
            return round(self.loss_pnl.pnl_money.mean(), 2)
        else:
            return 0

    @property
    def average_profit(self):
        """ 单笔平均盈利金额 """
        if len(self.profit_pnl) > 0:
            return round(self.profit_pnl.pnl_money.mean(), 2)
        else:
            return 0

    @property
    def average_pnl(self):
        """ 单笔平均盈亏比 """
        if len(self.loss_pnl) > 0 and len(self.profit_pnl) > 0:
            try:
                return round(abs(self.average_profit / self.average_loss), 2)
            except ZeroDivisionError:
                return 0
        else:
            return 0

    @property
    def max_profit(self):
        """ 最大单笔盈利金额 """
        if len(self.profit_pnl) > 0:
            return round(self.profit_pnl.pnl_money.max(), 2)
        else:
            return 0

    @property
    def max_loss(self):
        """ 最大单笔亏损金额 """
        if len(self.loss_pnl) > 0:
            return round(self.loss_pnl.pnl_money.min(), 2)
        else:
            return 0

    @property
    def max_pnl(self):
        """ 最大单笔盈亏比例 """
        if self.max_loss == 0:
            return np.Inf
        else:
            return round(abs(self.max_profit / self.max_loss), 2)

    @property
    def netprofit_maxloss_ratio(self):
        """ 净利润与单笔最大亏损额比例 """
        if len(self.loss_pnl) > 0:
            try:
                return round(abs(self.pnl.pnl_money.sum() / self.max_loss), 2)
            except ZeroDivisionError:
                return np.Inf
        else:
            return np.Inf

    @property
    def continue_profit_amount(self):
        """
        最大连续利润单数
        """
        w = []
        w1 = 0
        for _, item in self.pnl.pnl_money.items():
            if item > 0:
                w1 += 1
            elif item < 0:
                w.append(w1)
                w1 = 0
        if len(w) == 0:
            return 0
        else:
            return max(w)

    @property
    def continue_loss_amount(self):
        """
        最大连续亏损单数
        """
        tmp = []
        l1 = 0
        for _, item in self.pnl.pnl_money.items():
            if item > 0:
                tmp.append(l1)
                l1 = 0
            elif item < 0:
                l1 += 1
        if len(tmp) == 0:
            return 0
        else:
            return max(tmp)

    @property
    def average_holdgap(self):
        """ 平均持仓周期 """
        if len(self.pnl.hold_gap) > 0:
            return str(round(self.pnl.hold_gap.mean(), 2))
        else:
            return 'no trade'

    @property
    def average_profitholdgap(self):
        """ 盈利交易平均持仓周期 """
        if len(self.profit_pnl.hold_gap) > 0:
            return str(round(self.profit_pnl.hold_gap.mean(), 2))
        else:
            return 'no trade'

    @property
    def average_losssholdgap(self):
        """ 亏损交易平均持仓周期 """
        if len(self.loss_pnl.hold_gap) > 0:
            return str(round(self.loss_pnl.hold_gap.mean(), 2))
        else:
            return 'no trade'

    @property
    def total_commission(self):
        """ 交易费用总额 """
        # return round(self._orders["commission"].sum(), 2) if self._orders else 0
        return round(self._orders["commission"].sum(), 2)

    @property
    @lru_cache()
    def message(self):
        if self.pnl is not None:
            return {
                '交易净利润': self.net_profit,
                '总盈利金额': self.total_profit,
                '总亏损金额': self.total_loss,
                '总盈亏比': self.total_pnl,

                # '总交易次数': self.trading_amounts,
                '盈利次数': self.profit_amounts,
                '亏损次数': self.loss_amounts,
                # '持平交易次数': self.even_amounts,
                '胜率': '{:.2%}'.format(self.profit_percentage),
                # '亏损率': '{:.2%}'.format(self.loss_percentage),
                # '持平交易比例': '{:.2%}'.format(self.even_percentage),

                '平均盈利金额': self.average_profit,
                '平均亏损金额': self.average_loss,
                '平均盈亏比': self.average_pnl,

                '最大单笔盈利': self.max_profit,
                '最大单笔亏损': self.max_loss,
                '最大盈亏比': self.max_pnl,
                # '净利润与单笔最大亏损额比例': self.netprofit_maxloss_ratio,
                # '最大连续利润单数': self.continue_profit_amount,
                # '最大连续亏损单数': self.continue_loss_amount,

                # '交易标的数量': self.pnl['code'].nunique(),
                '交易标的数量': self.pnl.index.nunique(),
                '平均持仓周期': self.average_holdgap,
                # '盈利平均持仓周期': self.average_profitholdgap,
                # '亏损平均持仓周期': self.average_losssholdgap,

                '交易费用总额': self.total_commission,
                '交易费用占比': '{:.2%}'.format(abs(self.total_commission / self.net_profit))
            }
        else:
            return {
                '成交记录': len(self._orders) if self._orders is not None else 0,
                '配对记录': 0
            }

    def save(self, filename='performance.xlsx'):
        msg = self.message
        df = pd.Series(data=msg)
        df.to_excel(filename)

    def plot_pnlratio(self):
        """
        画出pnl比率散点图
        """
        plt.scatter(x=self.pnl.sell_date.apply(str), y=self.pnl.pnl_ratio)
        plt.gcf().autofmt_xdate()
        plt.show()
        return plt

    def plot_pnlmoney(self):
        """
        画出pnl盈亏额散点图
        """
        plt.scatter(x=self.pnl.sell_date.apply(str), y=self.pnl.pnl_money)
        plt.gcf().autofmt_xdate()
        plt.show()
        return plt
