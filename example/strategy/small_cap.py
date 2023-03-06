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
from qff import *


# 初始化函数，设定要操作的股票、基准等等
def initialize():
    # 设定沪深300作为基准
    set_benchmark('000300')
    # 持仓数量
    g.stock_num = 3
    # 交易日计时器
    g.days = 0
    # 调仓频率
    g.refresh_rate = 5


def before_trading_start():
    log.info("before_trading_start函数运行...")


def check_stocks():
    # 选出小市值股票

    filter = {'date': context.previous_date, 'market_cap': {'$gt': 20, '$lt': 30}}
    projection = {'market_cap': 1}
    df = query_valuation(filter, projection)
    df = df.sort_values('market_cap').reset_index()
    buy_list = list(df['code'])[:g.stock_num*2]

    # 过滤停牌股票
    paused_code = get_paused_stock(buy_list, context.previous_date)
    filter_paused = [x for x in buy_list if x not in paused_code]

    return filter_paused[:g.stock_num]


# 交易函数
def handle_data():
    if g.days % g.refresh_rate == 0:

        # 获取持仓列表
        sell_list = list(context.portfolio.positions.keys())
        # 如果有持仓，则卖出
        if len(sell_list) > 0:
            for stock in sell_list:
                order_target_value(stock, 0)

        # 分配资金
        if len(context.portfolio.positions) < g.stock_num:
            Num = g.stock_num - len(context.portfolio.positions)
            Cash = context.portfolio.available_cash / Num
        else:
            Cash = 0

        # 选股
        stock_list = check_stocks()

        # 买入股票
        for stock in stock_list:
            if len(context.portfolio.positions.keys()) < g.stock_num:
                order_value(stock, Cash)

        # 天计数加一
        g.days = 1
    else:
        g.days += 1


if __name__ == '__main__':
    run_file(__file__, start="2021-08-27", end="2022-03-25")
