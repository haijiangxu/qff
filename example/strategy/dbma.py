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

from math import isnan

from qff import *


def initialize():
    # 设置回测周期
    set_backtest_period(start="2021-05-13", end="2021-05-25")
    # 设置初始资金
    set_init_cash(1000000)
    # 设置固定滑点
    set_slippage(slippage=0.00246)
    # 设置交易费用
    set_order_cost(open_tax=0,
                   close_tax=0.001,
                   open_commission=0.0002,
                   close_commission=0.0002,
                   min_commission=5)
    # 设置指数基准
    set_benchmark(security="000300")

    g.tc = 15  # 调仓频率
    g.N = 4  # 持仓数目
    g.security = ["000001", "000002", "000006", "000007", "000009"]  # 设置股票池

    # 开盘前运行
    run_daily(before_trading_start, run_time='before_open')

    run_daily(market_open, run_time="09:30")

    run_daily(after_trading_end, run_time='after_close')


# 每天开盘前要做的事情
def before_trading_start():
    log.info("{} : before_trading_start".format(context.current_dt[0:10]))


# 每天开盘时执行
def market_open():
    # 将总资金等分为g.N份，为每只股票配资
    capital_unit = context.portfolio.total_assets / g.N
    toSell = signal_stock_sell()
    toBuy = signal_stock_buy()
    # 执行卖出操作以腾出资金
    for i in range(len(g.security)):
        if toSell[i] == 1:
            order_target_value(g.security[i], 0)
    # 执行买入操作
    for i in range(len(g.security)):
        if toBuy[i] == 1:
            order_target_value(g.security[i], capital_unit)
    if not (1 in toBuy) or (1 in toSell):
        log.info("今日无操作")


# 每日收盘后要做的事情（本策略中不需要）
def after_trading_end():
    log.info("after_trading_end:{}".format(context.current_dt[0:10]))


# 5
# 获得卖出信号
# 输入：context, data
# 输出：sell - list
def signal_stock_sell():
    sell = [0] * len(g.security)
    for i in range(len(g.security)):
        # 算出今天和昨天的两个指数移动均线的值，我们这里假设长线是60天，短线是1天(前一天的收盘价)
        (ema_long_pre, ema_long_now) = get_EMA(g.security[i], 60)
        (ema_short_pre, ema_short_now) = get_EMA(g.security[i], 1)
        # 如果短均线从上往下穿越长均线，则为死叉信号，标记卖出
        if ema_short_now < ema_long_now and ema_short_pre > ema_long_pre:
            # if g.security[i] in context.portfolio.positions.keys() and \
            #         context.portfolio.positions[g.security[i]].closeable_amount > 0:
            sell[i] = 1
    return sell


# 6
# 获得买入信号
# 输入：context, data
# 输出：buy - list
def signal_stock_buy():
    buy = [0] * len(g.security)
    for i in range(len(g.security)):
        # 算出今天和昨天的两个指数移动均线的值，我们这里假设长线是60天，短线是1天(前一天的收盘价)
        (ema_long_pre, ema_long_now) = get_EMA(g.security[i], 60)
        (ema_short_pre, ema_short_now) = get_EMA(g.security[i], 1)
        # 如果短均线从下往上穿越长均线，则为金叉信号，标记买入
        if ema_short_now > ema_long_now and ema_short_pre < ema_long_pre:
            buy[i] = 1
    return buy


# 7
# 计算移动平均线数据
# 输入：股票代码-字符串，移动平均线天数-整数
# 输出：算术平均值-浮点数
def get_MA(security_code, days):
    # 获得前days天的数据，详见API
    a = history(days, security_list=security_code, field='close')
    # 定义一个局部变量sum，用于求和
    sum = a.sum()
    # # 对前days天的收盘价进行求和
    # for i in range(1, days + 1):
    #     sum += a[-i]
    # 求和之后除以天数就可以的得到算术平均值啦
    return sum / days


# 计算指数移动平均线数据
# 输入：股票代码-字符串，移动指数平均线天数-整数，data
# 输出：今天和昨天的移动指数平均数-浮点数
def get_EMA(security_code, days):
    # 如果只有一天的话,前一天的收盘价就是移动平均
    if days == 1:
        # 获得前两天的收盘价数据，一个作为上一期的移动平均值，后一个作为当期的移动平均值
        t = history(2, security_list=security_code, field='close')
        if len(t) >= 2:
            return t[-2], t[-1]
        else:
            return float("nan"), float("nan")
    else:
        # 如果全局变量g.EMAs不存在的话，创建一个字典类型的变量，用来记录已经计算出来的EMA值
        if 'EMAs' not in dir(g):
            g.EMAs = {}
        # 字典的关键字用股票编码和天数连接起来唯一确定，以免不同股票或者不同天数的指数移动平均弄在一起了
        key = "%s%d" % (security_code, days)
        # 如果关键字存在，说明之前已经计算过EMA了，直接迭代即可
        if key in g.EMAs:
            # 计算alpha值
            alpha = (days - 1.0) / (days + 1.0)
            # 获得前一天的EMA（这个是保存下来的了）
            EMA_pre = g.EMAs[key]
            # EMA迭代计算
            last_close = get_current_data(security_code).last_price
            EMA_now = EMA_pre * alpha + last_close * (1.0 - alpha)
            # 写入新的EMA值
            g.EMAs[key] = EMA_now
            # 给用户返回昨天和今天的两个EMA值
            return (EMA_pre, EMA_now)
        # 如果关键字不存在，说明之前没有计算过这个EMA，因此要初始化
        else:
            # 获得days天的移动平均
            ma = get_MA(security_code, days)
            # 如果滑动平均存在（不返回NaN）的话，那么我们已经有足够数据可以对这个EMA初始化了
            if not (isnan(ma)):
                g.EMAs[key] = ma
                # 因为刚刚初始化，所以前一期的EMA还不存在
                return (float("nan"), ma)
            else:
                # 移动平均数据不足days天，只好返回NaN值
                return (float("nan"), float("nan"))


if __name__ == '__main__':
    back_test_run(__file__)
