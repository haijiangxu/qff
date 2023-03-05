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
# 双均线策略，当五日均线位于十日均线上方则买入，反之卖出。
from qff import *


# 初始化函数，设定要操作的股票、基准等等
def initialize():
    # 定义一个全局变量, 保存要操作的股票
    # 000002(股票:万科A)
    g.security = '000002'
    # 设定沪深300作为基准
    set_benchmark('000300')
    # 运行函数
    run_daily(trade, 'every_bar')


# 交易程序
def trade():
    security = g.security
    # 设定均线窗口长度
    n1 = 5
    n2 = 10
    # 获取股票的收盘价
    close_data = attribute_history(security, n2+2, '1d', ['close'])
    # 取得过去 ma_n1 天的平均价格
    ma_n1 = close_data['close'][-n1:].mean()
    # 取得过去 ma_n2 天的平均价格
    ma_n2 = close_data['close'][-n2:].mean()
    # 取得当前的现金
    cash = context.portfolio.available_cash

    # 如果当前有余额，并且n1日均线大于n2日均线
    if ma_n1 > ma_n2:
        # 用所有 cash 买入股票
        order_value(security, cash)
        # 记录这次买入
        log.info("Buying %s" % security)

    # 如果n1日均线小于n2日均线，并且目前有头寸
    elif ma_n1 < ma_n2 and\
            security in context.portfolio.positions.keys() and\
            context.portfolio.positions[security].closeable_amount > 0:
        # 全部卖出
        order_target(security, 0)
        # 记录这次卖出
        log.info("Selling %s" % security)


if __name__ == '__main__':
    run_file(__file__)
