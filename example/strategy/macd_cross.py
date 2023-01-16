from qff import *
import talib as tl
import numpy as np


def initialize():

    # 设置指数基准
    set_benchmark(security="000300")
    # 定义一个全局变量, 保存要操作的股票
    g.s1 = "000001"
    # 定义运行函数
    run_daily(market_open, run_time='09:50')

    log.info("initialize : 初始化运行")


def market_open():
    log.info("market_open函数，每天运行一次...")
    # 读取历史数据
    close = history(100, '1d', 'close', g.s1).close.values
    # 获取当前价格
    current_price = get_current_data(g.s1).last_price
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



