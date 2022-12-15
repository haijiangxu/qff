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
常用技术指标的计算函数,优先使用talib中的函数
"""
import pandas as pd
import numpy as np
import talib as tl
from qff.tools.logs import log
from qff.helper.formula import SMA, LLV, HHV, REF, MAX, ABS, MA, STD


def ind_ma(df, period=None, ma_type=0):
    """
    指标计算，生成均线数据
    MA_Type: 0=SMA, 1=EMA, 2=WMA, 3=DEMA, 4=TEMA, 5=TRIMA, 6=KAMA, 7=MAMA, 8=T3 (Default=SMA)
    :param period: 均线周期，默认 [5, 10, 20, 30, 60, 120, 250]
    :param df: DataFrame  包含OCHLV的股票价格数据
    :param  ma_type: 0=SMA, 1=EMA, 2=WMA, 3=DEMA, 4=TEMA, 5=TRIMA, 6=KAMA, 7=MAMA, 8=T3 (Default=SMA)
    :return:
    """
    if period is None:
        period = [5, 10, 20, 30, 60, 120, 250]
    elif isinstance(period, int):
        period = [period]
    elif not isinstance(period, list):
        log.error('ind_ma函数参数period输入错误！')

    close = df['close'].values
    # 系列均线计算
    for n in period:
        df['ma{}'.format(n)] = np.around(tl.MA(close, timeperiod=n, matype=ma_type), 4)

    return df


def ind_macd(df, short=12, long=26, mid=9, cs=False):
    """
    计算MACD指标
    :param df: DataFrame  包含OCHLV的股票价格数据
    :param short: MACD参数
    :param long: MACD参数
    :param mid: MACD参数
    :param cs: 是否计算金叉和死叉，如果为true,则生成 df['cs']=-1：死叉，df['cs']=1：金叉
    :return: 增加相应字段的dataframe
    """
    def calc_cross(s):  # 计算过零轴位置金叉（死叉），以及每个节点到金叉（或死叉）的距离
        d = pd.Series(index=s.index)
        for i in range(1, len(s)):
            if s[i] > 0 >= s[i - 1]:
                d[i] = 1
            elif s[i] <= 0 < s[i - 1]:
                d[i] = -1
            elif d[i - 1] >= 1:
                d[i] = d[i - 1] + 1
            elif d[i - 1] <= -1:
                d[i] = d[i - 1] - 1
            else:
                d[i] = np.nan
        return d
    # 计算MACD
    df['dif'], df['dea'], df['macd'] = np.around(tl.MACD(df['close'].values, short, long, mid), 4)

    if cs:
        # 计算MACD零轴 df['cs']=-1：死叉），1：（金叉）
        df['cs'] = calc_cross(df['macd'])
        df['cs'] = df['cs'].fillna(0).astype('int')
        # 计算DIF白线过零轴位置
        df['dcs'] = calc_cross(df['dif'])
        df['dcs'] = df['dcs'].fillna(0).astype('int')
    return df


def ind_atr(df, n):
    """
    输出TR:(最高价-最低价)和昨收-最高价的绝对值的较大值和昨收-最低价的绝对值的较大值
    输出真实波幅:TR的N日简单移动平均
    算法：今日振幅、今日最高与昨收差价、今日最低与昨收差价中的最大值，为真实波幅，求真实波幅的N日移动平均

    :param df: DataFrame  包含OCHLV的股票价格数据
    :param n: 天数，一般取14
    :return:
    """
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values

    df['atr'] = np.around(tl.ATR(high, low, close, n), 2)
    return df


def ind_kdj(df, n=9, m1=3, m2=3):
    close = df['close']
    high = df['high']
    low = df['low']

    rsv = (close - LLV(low, n)) / (HHV(high, n) - LLV(low, n)) * 100
    k = SMA(rsv, m1)
    d = SMA(k, m2)
    j = 3 * k - 2 * d
    df['kdj_k'] = k
    df['kdj_d'] = d
    df['kdj_j'] = j
    return df


def ind_rsi(df, n1=12, n2=26, n3=9):
    """
    相对强弱指标：
    是通过比较一段时期内的平均收盘涨数和平均收盘跌数来分析市场买沽盘的意向和实力，
    从而作出未来市场的走势。

    """
    close = df['close']
    lc = REF(close, 1)
    rsi1 = SMA(MAX(close - lc, 0), n1) / SMA(ABS(close - lc), n1) * 100
    rsi2 = SMA(MAX(close - lc, 0), n2) / SMA(ABS(close - lc), n2) * 100
    rsi3 = SMA(MAX(close - lc, 0), n3) / SMA(ABS(close - lc), n3) * 100
    df['rsi1'] = rsi1
    df['rsi2'] = rsi2
    df['rsi3'] = rsi3
    return df


def ind_boll(df, n=20, p=2):
    """布林线"""
    close = df['close']
    boll = MA(close, n)
    ub = boll + p * STD(close, n)
    lb = boll - p * STD(close, n)
    df['boll'] = boll
    df['ub'] = ub
    df['lb'] = lb
    return df
