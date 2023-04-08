# 策略示例

在下面我们列举一些常用的算法范例，您可以通过QFF运行，方便您快速学习和掌握QFF框架。

## 双均线策略

金叉死叉策略其实就是双均线策略。策略思想是：当短期均线上穿长期均线时，形成金叉，此时买入股票。
当短期均线下穿长期均线时，形成死叉，此时卖出股票。研究表明，双均线系统虽然简单，但只要严格执行，也能长期盈利。

```python

# 双均线策略，当五日均线位于十日均线上方则买入，反之卖出。
from qff import *


# 初始化函数，设定要操作的股票、基准等等
def initialize(context):
    # 定义一个全局变量, 保存要操作的股票
    # 000002(股票:万科A)
    g.security = '000002'
    # 设定沪深300作为基准
    set_benchmark('000300')
    # 运行函数
    run_daily(trade, 'every_bar')


# 交易程序
def trade(context, data):
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



```

## MACD策略
以下是一个我们使用TALib编写的单股票MACD算法示例。
1. macd 是长短均线的差值，signal是macd的均线，使用macd策略有几种不同的方法，我们这里采用macd线突破signal线的判断方法。
2. talib是python的技术指标库，其中包含了很多150多种量化指标，所以talib是非常值得我们学习和使用的。
talib使用C语言实现，执行速度非常快，其安装方法也比较特殊，请自行搜索安装方法。
   
```python
from qff import *
import talib as tl
import numpy as np


def initialize(context):

    # 设置指数基准
    set_benchmark(security="000300")
    # 定义一个全局变量, 保存要操作的股票
    g.s1 = "000001"
    # 定义运行函数，每日9点50分运行
    run_daily(market_open, run_time='09:50')

    log.info("initialize : 初始化运行")


def market_open(context):
    log.info("market_open函数，每天运行一次...")
    # 读取历史数据，前100天的收盘价
    close = history(100, '1d', 'close', g.s1).values
    # 获取当前价格
    current_price = get_current_data(g.s1).last_price
    # 将当前价格与历史价格合并
    close = np.append(close, current_price)

    # 用Talib计算MACD取值，得到三个时间序列数组，
    macd, signal, hist = tl.MACD(close, 12, 26, 9)

    # 如果macd从上往下跌破macd_signal
    if macd[-1] < signal[-1] and macd[-2] > signal[-2]:
        # 进行清仓
        if g.s1 in context.portfolio.positions.keys():
            order_target(g.s1, 0)

    # 如果短均线从下往上突破长均线，为入场信号
    if macd[-1] > signal[-1] and macd[-2] < signal[-2]:
        # 满仓买入
        order_value(g.s1, context.portfolio.available_cash)


if __name__ == '__main__':
    run_file(__file__, start="2021-08-27", end="2022-03-25")


```

## 小市值策略

筛选出市值介于20-30亿的股票，选取其中市值最小的三只股票，每天开盘买入，持有五个交易日，然后调仓。
等权重买入，无单只股票仓位上限控制、无止盈止损。小市值策略曾经在15年期间有非常好的收益，未来有可能还能重现。

```python
from qff import *


# 初始化函数，设定要操作的股票、基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300')
    # 持仓数量
    g.stock_num = 3
    # 交易日计时器
    g.days = 0
    # 调仓频率
    g.refresh_rate = 5


def before_trading_start(context):
    log.info("before_trading_start函数运行...")


def check_stocks(context):
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
def handle_data(context, data):
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
        stock_list = check_stocks(context)

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

```

## 海龟策略
海龟交易系统是非常经典的一种策略，类似的成熟策略体系还有很多种，例如羊驼，鳄鱼等等。
关于海龟策略的原理介绍可以参照 [这篇帖子](https://www.joinquant.com/view/community/detail/b061c8738b509ec318c03e7af040bb9b) 。

```python

# 海归策略
# 2012-01-01 到 2016-03-10, ￥1000000, 分钟

# 海龟策略

from qff import *
import numpy as np

# ================================================================================
# 总体回测前
# ================================================================================


# 总体回测前要做的事情
def initialize(context):
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
def before_trading_start(context):
    set_slip_fee(context)


# 4 根据不同的时间段设置滑点与手续费
def set_slip_fee(context):
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
def handle_data(context, data):
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
def after_trading_end(context):
    return


```
