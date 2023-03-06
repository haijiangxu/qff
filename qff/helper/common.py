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

"""
用于编写策略中常用的函数
"""
import pandas as pd
from datetime import datetime
from qff.price.query import get_st_stock, get_paused_stock, get_price, get_stock_list
from qff.price.finance import get_history_fundamentals
from qff.tools.date import  get_real_trade_date


def filter_st_stock(security, date=None):
    """
    过滤股票列表中的st股票

    :param security: 股票列表
    :param date: 查询日期

    :return: 返回剔除ST股票的股票代码列表
    """
    st_code = get_st_stock(security, date).keys()
    return [x for x in security if x not in st_code]


def filter_paused_stock(security, date=None):
    """
    过滤股票列表中当日停牌的股票

    :param security: 股票列表
    :param date: 查询日期

    :return: 返回剔除当日停牌的股票代码列表
    """
    paused_code = get_paused_stock(security, date)
    return [x for x in security if x not in paused_code]


def filter_bj_stock(security):
    """
    过滤股票列表中北交所的股票

    :param security: 股票列表

    :return: 返回剔除当日停牌的股票代码列表
    """
    if isinstance(security, str):
        security = [security]

    return [x for x in security if x[:2] not in ['43', '83', '87', '82', '88']]


def filter_20pct_stock(security, date=None):
    """
    过滤涨停20%的创业板和科创板股票

    :param security: 股票列表
    :param date: 查询日期

    :return: 返回剔除当日停牌的股票代码列表
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    if date >= '2020-08-24':  # 创业板改动涨停幅度日期
        security = [stock for stock in security if stock[0:3] != '300']
    if date >= '2019-07-22':  # 科创板上市日期
        security = [stock for stock in security if stock[0:2] != '68']
    return security


def select_zt_stock(security=None, date=None, n=1, m=1):
    """
    查找最近n天连续涨停,且前面m天未涨停的股票代码

    :param security: 股票代码list
    :param date: 查询日期
    :param n: 连续涨停的天数
    :param m: 涨停前多少天未涨停

    :return: 返回股票代码list
    """
    def zt(d, k):
        a = round(d['close'].shift(1) * 1.1, 2) <= d['close']
        return a[-k:].all() and ~a[:-k].any()

    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
        date = get_real_trade_date(date, -1)

    if security is None:
        security = get_stock_list(date)

    df = get_price(security, end=date, fields=['close'], count=n+m)
    if df is None:
        return []
    df = df.reset_index()
    zt_df = df.groupby('code').apply(zt, n)
    return zt_df[zt_df].index.tolist()


def select_npgr_stock(npgr, date=None, count=1):
    """
    选择净利润增长率大于指定值的股票。
    对于上个季度亏损的股票，会造成净利润增长率很大，不能真实反映股票的成长性.
    可以选择连续三个季报净利润增长率大于指定值的股票。

    :param npgr:净利润增长率阀值,30% 输入30
    :param date:查询日期
    :param count:连续n个报告期,默认最近一个报告期

    :return: 返回满足条件的股票列表
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
        date = get_real_trade_date(date, -1)

    data = get_history_fundamentals(code=None, fields=['f184'], watch_date=date, count=count)
    data = data.rename(columns={'184' : 'npgr'}).drop(['report_date', 'pub_date'], axis=1)
    # data = data[data['npgr'] >= npgr]
    df = data.groupby(['code']).apply(lambda x: (x['npgr'] >= npgr).all())
    return df[df].index.tolist()


def macd_diverge(df):
    """
    判断当前MACD是否顶/底背离
    原理：按MACD金叉分为两个周期，周期类股价最高点对应的dif值进行比较。

    :param df: DataFrame  包含OCHLV的股票价格数据以及生成的MACD、CS数据

    :return: 1：顶背离，-1：底背离，0：其他
    """
    pass


# def fit_linear(x: pd.Series):
#     """
#     生成股票价格拟合的斜率,最小二乘法方程 : y = mx + c, 返回m
#     :param x: 输入数据
#     :return:
#     """
#     from sklearn.linear_model import LinearRegression
#     model = LinearRegression()
#     x_train = np.arange(0, len(x)).reshape(-1, 1)
#     y_train = x.values.reshape(-1, 1)
#     model.fit(x_train, y_train)
#     m = round(float(model.coef_), 2)
#     # c = round(float(model.intercept_), 2)
#     return m


def trend_line(df: pd.DataFrame):
    """
    趋势线（上下轨）
    :param df:
    :return:
    """
    pass


def pressure_line(df: pd.DataFrame):
    """
    压力线/支撑线
    :param df:
    :return:
    """
    pass
