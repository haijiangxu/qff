
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir)))

from qff import *
from qff.helper.common import select_zt_stock, filter_20pct_stock
import pandas as pd
import numpy as np

strategy_name = "首板抓起势策略"
strategy_desc = """ 该策略的主体思路：选取第一次涨停、倍量、近段时间有上升趋势且近30日未涨过百分之15个点的股票。
取30日涨幅不超15%，且30-360日处于升幅(线性拟合)的票，以120日的拟合升幅作为因子取最大值选股."""


def initialize():

    log.info("{} : 初始化运行".format(strategy_name))
    # 设置指数基准
    set_benchmark(security="000300")

    g.good_stock = []  #
    # 持仓数量
    g.stocknum = 4

    # 开盘前运行
    # run_daily(before_trading_start, run_time='before_open')
    #
    run_daily(handle_trade, run_time="09:50")
    #
    # run_daily(after_trading_end, run_time='after_close')


def before_trading_start():
    log.info("before_trading_start函数运行...")
    yesterday = context.previous_date
    zt = select_zt_stock(date=yesterday)
    stock_list = filter_20pct_stock(zt, date=yesterday)
    res = (None, 0)
    for stock in stock_list:
        data = get_price(stock, end=yesterday, count=360)
        if data.vol[-1] < data.vol[-2] * 2:
            continue
        close_30 = data.close[-31:-1]
        if close_30.max() / close_30.min() > 1.15:
            continue
        if fit_linear(data.close[-30:]) < 0:
            continue
        if fit_linear(data.close[-60:]) < 0:
            continue
        if fit_linear(data.close[-90:]) < 0:
            continue
        if fit_linear(data.close[-360:]) < 0:
            continue
        m = fit_linear(data.close[-120:])
        if m > res[1]:
            res = (stock, m)

    if res[0]:
        g.good_stock.append(res[0])
        log.info("{}满足策略选择条件！".format(res[0]))


def handle_trade():
    # 卖出策略
    # 准备卖出，三种卖：涨幅超5%卖，超19日卖，当日跌幅超4卖？
    if len(context.portfolio.positions) > 0:
        pst: Position
        for pst in list(context.portfolio.positions.values()):
            if pst.closeable_amount > 0:
                data = get_current_data(pst.security)
                if data.last_price > pst.avg_cost * 1.05:
                    order(pst.security, -pst.closeable_amount)
                    log.info("盈利5%，卖出股票{}".format(pst.security))
                elif data.day_open > 1.04 * data.last_price:
                    order(pst.security, -pst.closeable_amount)
                    log.info("当日跌幅4%，卖出股票{}".format(pst.security))
                elif get_trade_gap(pst.transact_time, context.current_dt[:10]) > 19:
                    order(pst.security, -pst.closeable_amount)
                    log.info("持股19天，卖出股票{}".format(pst.security))

    # 买入股票
    if len(g.good_stock) > 0:
        remain = g.stocknum - len(context.portfolio.positions)
        cash = int(context.portfolio.available_cash / remain) if remain > 0 else 0
        for code in g.good_stock:
            if cash > 10000:
                order_value(code, cash)
                log.info("买入股票{}，买入金额{}".format(code, cash))
            else:
                log.info("账户资金不足，中选股票{}丢弃".format(code, cash))
            g.good_stock.remove(code)


def fit_linear(x: pd.Series):
    """
    生成股票价格拟合的斜率,最小二乘法方程 : y = mx + c, 返回m
    """
    from sklearn.linear_model import LinearRegression
    model = LinearRegression()
    x_train = np.arange(0, len(x)).reshape(-1, 1)
    y_train = x.values.reshape(-1, 1)
    model.fit(x_train, y_train)
    m = round(float(model.coef_), 2)
    # c = round(float(model.intercept_), 2)
    return m


if __name__ == '__main__':
    run_file(os.path.abspath(__file__), start="2021-08-27", end="2022-03-25")
