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


import math
import numpy as np
import pandas as pd

"""
用于实现同花顺和通达信里公式的基础函数
"""


def EMA(s, n):
    """
    EMA-指数移动平均
    :param s: Series对象
    :param n: 统计周期
    :return: Series对象， EMA值
    """
    return pd.Series.ewm(s, span=n, min_periods=n - 1, adjust=True).mean().round(3)


def MA(s, n):
    return pd.Series.rolling(s, n).mean().round(2)


# 威廉SMA  参考https://www.joinquant.com/post/867


def SMA(s, n, m=1):
    """
    威廉SMA算法

    本次修正主要是对于返回值的优化,现在的返回值会带上原先输入的索引index
    2018/5/3
    @yutiansut
    """
    ret = []
    i = 1
    length = len(s)
    # 跳过X中前面几个 nan 值
    while i < length:
        if np.isnan(s.iloc[i]):
            i += 1
        else:
            break
    pre_y = s.iloc[i]  # Y'
    ret.append(pre_y)
    while i < length:
        y = (m * s.iloc[i] + (n - m) * pre_y) / float(n)
        ret.append(y)
        pre_y = y
        i += 1
    return pd.Series(ret, index=s.tail(len(ret)).index).round(3)


def DIFF(s, n=1):
    return pd.Series(s).diff(n)


def HHV(s, n):
    return pd.Series(s).rolling(n).max()


def LLV(s, n):
    return pd.Series(s).rolling(n).min()


def SUM(s, n):
    return pd.Series.rolling(s, n).sum()


def ABS(s):
    return abs(s)


def MAX(a, b):
    var = IF(pd.Series(a > b), a, b)
    return var


def MIN(a, b):
    var = IF(pd.Series(a < b), a, b)
    return var


def SINGLE_CROSS(a, b):
    if a.iloc[-2] < b.iloc[-2] and a.iloc[-1] > b.iloc[-1]:
        return True
    else:
        return False


def EXIST(s, n=5):
    """
    n日内是否存在某一值，
    输入值为true or false的s
    """
    res = pd.DataFrame(s) + 0
    res = res.rolling(n).sum() > 0
    res = res[res.columns[0]]
    return res


def EVERY(s, n=5):
    """
    n日内是否一直存在某一值，
    输入值为true or false的s
    """
    res = pd.DataFrame(s) + 0
    res = res.rolling(n).sum() > n - 1
    res = res[res.columns[0]]
    return res


def CROSS(a, b):
    """A<B then A>B  A上穿B B下穿A

    Arguments:
        A {[type]} -- [description]
        B {[type]} -- [description]

    Returns:
        [type] -- [description]
    """

    var = np.where(a < b, 1, 0)
    try:
        index = a.index
    except:
        index = b.index
    return (pd.Series(var, index=index).diff() < 0).apply(int)


def CROSS_STATUS(a, b):
    """
    A 穿过 B 产生持续的 1 序列信号
    """
    return np.where(a > b, 1, 0)


def FILTER(cond, n):
    k1 = pd.Series(np.where(cond, 1, 0), index=cond.index)
    idx = k1[k1 == 1].index.codes[0]
    need_filter = pd.Series(idx, index=idx)
    after_filter = need_filter.diff().apply(lambda x: False if x < n else True)
    k1.iloc[after_filter[after_filter].index] = 2
    return k1.apply(lambda x: 1 if x == 2 else 0)


def COUNT(cond, n):
    """
    2018/05/23 修改

    参考https://github.com/QUAnTAXIS/QUAnTAXIS/issues/429

    现在返回的是s
    """
    return pd.Series(np.where(cond, 1, 0), index=cond.index).rolling(n).sum()


def IF(cond, v1, v2):
    var = np.where(cond, v1, v2)
    try:
        try:
            index = v1.index
        except:
            index = cond.index
    except:
        index = v2.index
    return pd.Series(var, index=index)


def IFAND(cond1, cond2, v1, v2):
    var = np.where(np.logical_and(cond1, cond2), v1, v2)
    return pd.Series(var, index=v1.index)


def IFOR(cond1, cond2, v1, v2):
    var = np.where(np.logical_or(cond1, cond2), v1, v2)
    return pd.Series(var, index=v1.index)


def REF(s, n):
    return s.shift(n)


def LAST(cond, n1, n2):
    """表达持续性
    从前n1日到前n2日一直满足COnD条件

    Arguments:
        COnD {[type]} -- [description]
        n1 {[type]} -- [description]
        n2 {[type]} -- [description]
    """
    n2 = 1 if n2 == 0 else n2
    assert n2 > 0
    assert n1 > n2
    return cond.iloc[-n1:-n2].all()


def STD(s, n):
    return pd.Series.rolling(s, n).std()


def AVEDEV(s, n):
    """
    平均绝对偏差 mean absolute deviation
    修正: 2018-05-25 

    之前用mad的计算模式依然返回的是单值
    """
    return s.rolling(n).apply(lambda x: (np.abs(x - x.mean())).mean(), raw=True)


def MACD(s, fast=12, slow=26, mid=9):
    """macd指标 仅适用于s
    """
    ema_fast = EMA(s, fast)
    ema_slow = EMA(s, slow)
    diff = ema_fast - ema_slow
    dea = EMA(diff, mid)
    macd = (diff - dea) * 2
    dict_ = {'DIFF': diff, 'DEA': dea, 'MACD': macd}
    return pd.DataFrame(dict_).round(3)


def BBIBOLL(s, n1, n2, n3, n4, n, m):  # 多空布林线
    biol = BBI(s, n1, n2, n3, n4)
    uper = biol + m * STD(biol, n)
    down = biol - m * STD(biol, n)
    dict_ = {'BBIBOLL': biol, 'UPER': uper, 'DOWn': down}
    var = pd.DataFrame(dict_)
    return var


def BBI(s, n1, n2, n3, n4):
    """多空指标"""

    bbi = (MA(s, n1) + MA(s, n2) +
           MA(s, n3) + MA(s, n4)) / 4
    DICT = {'BBI': bbi}
    VAR = pd.DataFrame(DICT)
    return VAR


def BARLAST(cond, yes=True):
    """支持MultiIndex的cond和DateTimeIndex的cond
    条件成立  yes= True 或者 yes=1 根据不同的指标自己定

    最后一次条件成立  到 当前到周期数

    Arguments:
        cond {[type]} -- [description]
    """
    if isinstance(cond.index, pd.MultiIndex):
        return len(cond) - cond.index.levels[0].tolist().index(cond[cond == yes].index[-1][0]) - 1
    elif isinstance(cond.index, pd.DatetimeIndex):
        return len(cond) - cond.index.tolist().index(cond[cond == yes].index[-1]) - 1


def BARLAST_EXIST(cond, yes=True):
    """
    上一次条件成立   持续到当前到数量


    支持MultiIndex的cond和DateTimeIndex的cond
    条件成立  yes= True 或者 yes=1 根据不同的指标自己定

    Arguments:
        cond {[type]} -- [description]
    """
    if isinstance(cond.index, pd.MultiIndex):
        return len(cond) - cond.index.levels[0].tolist().index(cond[cond != yes].index[-1][0]) - 1
    elif isinstance(cond.index, pd.DatetimeIndex):
        return len(cond) - cond.index.tolist().index(cond[cond != yes].index[-1]) - 1


def XARROUND(x, y): return np.round(
    y * (round(x / y - math.floor(x / y) + 0.00000000001) + math.floor(x / y)), 2)


def RENKO(s, n, condensed=True):
    last_price = s[0]
    chart = [last_price]
    for price in s:
        bricks = math.floor(abs(price - last_price) / n)
        if bricks == 0:
            if condensed:
                chart.append(chart[-1])
            continue
        sign = int(np.sign(price - last_price))
        chart += [sign * (last_price + (sign * n * x)) for x in range(1, bricks + 1)]
        last_price = abs(chart[-1])

    return pd.Series(chart)


def RENKOP(s, n, condensed=True):
    last_price = s[0]
    chart = [last_price]
    for price in s:
        inc = (price - last_price) / last_price
        # log.info(inc)
        if abs(inc) < n:
            # if condensed:
            #     chart.append(chart[-1])
            continue

        sign = int(np.sign(price - last_price))
        bricks = math.floor(inc / n)
        # log.info(bricks)
        # log.info((n * (price-last_price)) / inc)
        step = math.floor((n * (price - last_price)) / inc)
        # log.info(step)
        # log.info(sign)
        chart += [sign * (last_price + (sign * step * x))
                  for x in range(1, abs(int(bricks)) + 1)]
        last_price = abs(chart[-1])
    return pd.Series(chart)
