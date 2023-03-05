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

# 海归策略
# 2012-01-01 到 2016-03-10, ￥1000000, 分钟

# 海龟策略

from qff import *
import numpy as np

# ================================================================================
# 总体回测前
# ================================================================================


# 总体回测前要做的事情
def initialize():
    set_params()  # 1设置策参数
    set_variables()  # 2设置中间变量
    set_backtest()  # 3设置回测条件


# 1
# 设置策略参数
def set_params():
    g.security = '000001'
    # 系统1入市的trailing date
    g.short_in_date = 20
    # 系统2入市的trailing date
    g.long_in_date = 55
    # 系统1 exiting market trailing date
    g.short_out_date = 10
    # 系统2 exiting market trailing date
    g.long_out_date = 20
    # g.dollars_per_share是标的股票每波动一个最小单位，1手股票的总价格变化量。
    # 在国内最小变化量是0.01元，所以就是0.01×100=1
    g.dollars_per_share = 1
    # 可承受的最大损失率
    g.loss = 0.1
    # 若超过最大损失率，则调整率为：
    g.adjust = 0.8
    # 计算N值的天数
    g.number_days = 20
    # 最大允许单元
    g.unit_limit = 4
    # 系统1所配金额占总金额比例
    g.ratio = 0.8


# 2
# 设置中间变量
def set_variables():
    # 初始单元
    g.unit = 1000
    # A list storing info of N
    g.N = []
    # Record the number of days for this trading system
    g.days = 0
    # 系统1的突破价格
    g.break_price1 = 0
    # 系统2的突破价格
    g.break_price2 = 0
    # 系统1建的仓数
    g.sys1 = 0
    # 系统2建的仓数
    g.sys2 = 0
    # 系统1执行且系统2不执行
    g.system1 = True


# 3
# 设置回测条件
def set_backtest():
    # 作为判断策略好坏和一系列风险值计算的基准
    set_benchmark(g.security)
    log.set_level('info')  # 设置报错等级


'''
================================================================================
每天开盘前
================================================================================
'''


# 每天开盘前要做的事情
def before_trading_start():
    set_slip_fee()


# 4 根据不同的时间段设置滑点与手续费
def set_slip_fee():
    # 将滑点设置为0
    set_slippage(0)
    # 根据不同的时间段设置手续费
    dt = context.current_dt

    if dt > '2013-01-01':
        set_order_cost(open_commission=0.0003, close_commission=0.0013, min_commission=5)
    elif dt > '2011-01-01':
        set_order_cost(open_commission=0.001, close_commission=0.002, min_commission=5)
    elif dt > '2009-01-01':
        set_order_cost(open_commission=0.002, close_commission=0.003, min_commission=5)
    else:
        set_order_cost(open_commission=0.003, close_commission=0.004, min_commission=5)

# ================================================================================
# 每天交易时
# ================================================================================


# 按分钟回测
def handle_data():
    dt = context.current_dt  # 当前日期
    if dt[:10] == '2020-04-20':
        log.info(dt)
    data = get_current_data(g.security)
    current_price = data.last_price  # 当前价格N
    if dt[11:15] == '09:30':
        g.days += 1
        calculate_N()  # 计算N的值
    if g.days > g.number_days:
        # 当前持有的股票和现金的总价值
        value = context.portfolio.total_assets
        # 可花费的现金
        cash = context.portfolio.available_cash
        if g.sys1 == 0 and g.sys2 == 0:
            # 若损失率大于g.loss，则调整（减小）可持有现金和总价值
            if value < (1 - g.loss) * context.portfolio.starting_cash:
                cash *= g.adjust
                value *= g.adjust

        # 计算美元波动的价格
        dollar_volatility = g.dollars_per_share * g.N[-1]
        # 依本策略，计算买卖的单位
        g.unit = value * 0.01 / dollar_volatility

        # 系统1的操作
        g.system1 = True
        if g.sys1 == 0:
            market_in(current_price, g.ratio * cash, g.short_in_date)
        else:
            stop_loss(current_price)
            market_add(current_price, g.ratio * cash, g.short_in_date)
            market_out(current_price, g.short_out_date)

        # 系统2的操作
        g.system1 = False
        if g.sys2 == 0:
            market_in(current_price, (1 - g.ratio) * cash, g.long_in_date)
        else:
            stop_loss(current_price)
            market_add(current_price, (1 - g.ratio) * cash, g.long_in_date)
            market_out(current_price, g.long_out_date)

        # 5


# 计算当前N的值
# 输入：none
# 输出：N的值的更新列表-list类型
def calculate_N():
    # 如果交易天数小于等于20天
    if g.days <= g.number_days:
        price = attribute_history(g.security, g.days+1, '1d', ['high', 'low', 'close'])
        price['pre_close'] = price['close'].shift(1)
        lst = []
        for i in range(0, g.days):
            h_l = price['high'][i] - price['low'][i]
            h_c = price['high'][i] - price['pre_close'][i]
            c_l = price['pre_close'][i] - price['low'][i]
            # 计算 True Range
            True_Range = max(h_l, h_c, c_l)
            lst.append(True_Range)
        # 计算前g.days（小于等于20）天的True_Range平均值，即当前N的值：
        current_N = np.mean(np.array(lst))
        g.N.append(current_N)

    # 如果交易天数超过20天
    else:
        price = attribute_history(g.security, 2, '1d', ['high', 'low', 'close'])
        price['pre_close'] = price['close'].shift(1)
        h_l = price['high'][-1] - price['low'][-1]
        h_c = price['high'][-1] - price['pre_close'][-1]
        c_l = price['pre_close'][-1] - price['low'][-1]
        # Calculate the True Range
        True_Range = max(h_l, h_c, c_l)
        # 计算前g.number_days（大于20）天的True_Range平均值，即当前N的值：
        current_N = (True_Range + (g.number_days - 1) * g.N[-1]) / g.number_days
        g.N.append(current_N)


# 6
# 入市：决定系统1、系统2是否应该入市，更新系统1和系统2的突破价格
# 海龟将所有资金分为2部分：一部分资金按系统1执行，一部分资金按系统2执行
# 输入：当前价格-float, 现金-float, 天数-int
# 输出：none
def market_in(current_price, cash, in_date):
    # Get the price for the past "in_date" days
    price = attribute_history(g.security, in_date, '1d', ['close'])
    # Build position if current price is higher than highest in past
    if current_price > max(price['close']):
        # 计算可以买该股票的股数
        num_of_shares = cash / current_price
        if num_of_shares >= g.unit:
            print("买入")
            print(current_price)
            print(max(price['close']))
            if g.system1:
                if g.sys1 < int(g.unit_limit * g.unit):
                    order(g.security, int(g.unit))
                    g.sys1 += int(g.unit)
                    g.break_price1 = current_price
            else:
                if g.sys2 < int(g.unit_limit * g.unit):
                    order(g.security, int(g.unit))
                    g.sys2 += int(g.unit)
                    g.break_price2 = current_price


# 7
# 加仓函数
# 输入：当前价格-float, 现金-float, 天数-int
# 输出：none
def market_add(current_price, cash, in_date):
    if g.system1:
        break_price = g.break_price1
    else:
        break_price = g.break_price2
    # 每上涨0.5N，加仓一个单元
    if current_price >= break_price + 0.5 * g.N[-1]:
        num_of_shares = cash / current_price
        # 加仓
        if num_of_shares >= g.unit:
            print("加仓")
            print(g.sys1)
            print(g.sys2)
            print(current_price)
            print(break_price + 0.5 * g.N[-1])

            if g.system1:
                if g.sys1 < int(g.unit_limit * g.unit):
                    order(g.security, int(g.unit))
                    g.sys1 += int(g.unit)
                    g.break_price1 = current_price
            else:
                if g.sys2 < int(g.unit_limit * g.unit):
                    order(g.security, int(g.unit))
                    g.sys2 += int(g.unit)
                    g.break_price2 = current_price


# 8
# 离场函数
# 输入：当前价格-float, 天数-int
# 输出：none
def market_out(current_price, out_date):
    # Function for leaving the market
    price = attribute_history(g.security, out_date, '1d', ['close'])
    # 若当前价格低于前out_date天的收盘价的最小值, 则卖掉所有持仓
    if current_price < min(price['close']):
        print("离场")
        print(current_price)
        print(min(price['close']))
        if g.system1:
            if g.sys1 > 0:
                order(g.security, -g.sys1)
                g.sys1 = 0
        else:
            if g.sys2 > 0:
                order(g.security, -g.sys2)
                g.sys2 = 0


# 9
# 止损函数
# 输入：当前价格-float
# 输出：none
def stop_loss(current_price):
    # 损失大于2N，卖出股票
    if g.system1:
        break_price = g.break_price1
    else:
        break_price = g.break_price2
    # If the price has decreased by 2N, then clear all position
    if current_price < (break_price - 2 * g.N[-1]):
        print("止损")
        print(current_price)
        print(break_price - 2 * g.N[-1])
        if g.system1:
            order(g.security, -g.sys1)
            g.sys1 = 0
        else:
            order(g.security, -g.sys2)
            g.sys2 = 0


# ================================================================================
# 每天收盘后
# ================================================================================

# 每日收盘后要做的事情（本策略中不需要）
def after_trading_end():
    return


if __name__ == '__main__':
    run_file(__file__, start="2020-01-01", end="2022-12-01")
