# coding :utf-8
#
# The MIT License (MIT)
#
# Copyright (c) 2021-2029 XuHaiJiang/QFF
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


from datetime import datetime, timedelta
from functools import wraps
import time
import math
import pandas as pd
from typing import Optional, Callable


year_end = datetime.today().replace(month=12, day=31).strftime("%Y-%m-%d")
precomputed_shanghai_holidays = [
    "1991-01-01",
    "1991-02-15",
    "1991-02-18",
    "1991-05-01",
    "1991-10-01",
    "1991-10-02",
    "1992-01-01",
    "1992-02-04",
    "1992-02-05",
    "1992-02-06",
    "1992-05-01",
    "1992-10-01",
    "1992-10-02",
    "1993-01-01",
    "1993-01-25",
    "1993-01-26",
    "1993-10-01",
    "1994-02-07",
    "1994-02-08",
    "1994-02-09",
    "1994-02-10",
    "1994-02-11",
    "1994-05-02",
    "1994-10-03",
    "1994-10-04",
    "1995-01-02",
    "1995-01-30",
    "1995-01-31",
    "1995-02-01",
    "1995-02-02",
    "1995-02-03",
    "1995-05-01",
    "1995-10-02",
    "1995-10-03",
    "1996-01-01",
    "1996-02-19",
    "1996-02-20",
    "1996-02-21",
    "1996-02-22",
    "1996-02-23",
    "1996-02-26",
    "1996-02-27",
    "1996-02-28",
    "1996-02-29",
    "1996-03-01",
    "1996-05-01",
    "1996-09-30",
    "1996-10-01",
    "1996-10-02",
    "1997-01-01",
    "1997-02-03",
    "1997-02-04",
    "1997-02-05",
    "1997-02-06",
    "1997-02-07",
    "1997-02-10",
    "1997-02-11",
    "1997-02-12",
    "1997-02-13",
    "1997-02-14",
    "1997-05-01",
    "1997-05-02",
    "1997-06-30",
    "1997-07-01",
    "1997-10-01",
    "1997-10-02",
    "1997-10-03",
    "1998-01-01",
    "1998-01-02",
    "1998-01-26",
    "1998-01-27",
    "1998-01-28",
    "1998-01-29",
    "1998-01-30",
    "1998-02-02",
    "1998-02-03",
    "1998-02-04",
    "1998-02-05",
    "1998-02-06",
    "1998-05-01",
    "1998-10-01",
    "1998-10-02",
    "1999-01-01",
    "1999-02-10",
    "1999-02-11",
    "1999-02-12",
    "1999-02-15",
    "1999-02-16",
    "1999-02-17",
    "1999-02-18",
    "1999-02-19",
    "1999-02-22",
    "1999-02-23",
    "1999-02-24",
    "1999-02-25",
    "1999-02-26",
    "1999-05-03",
    "1999-10-01",
    "1999-10-04",
    "1999-10-05",
    "1999-10-06",
    "1999-10-07",
    "1999-12-20",
    "1999-12-31",
    "2000-01-03",
    "2000-01-31",
    "2000-02-01",
    "2000-02-02",
    "2000-02-03",
    "2000-02-04",
    "2000-02-07",
    "2000-02-08",
    "2000-02-09",
    "2000-02-10",
    "2000-02-11",
    "2000-05-01",
    "2000-05-02",
    "2000-05-03",
    "2000-05-04",
    "2000-05-05",
    "2000-10-02",
    "2000-10-03",
    "2000-10-04",
    "2000-10-05",
    "2000-10-06",
    "2001-01-01",
    "2001-01-22",
    "2001-01-23",
    "2001-01-24",
    "2001-01-25",
    "2001-01-26",
    "2001-01-29",
    "2001-01-30",
    "2001-01-31",
    "2001-02-01",
    "2001-02-02",
    "2001-05-01",
    "2001-05-02",
    "2001-05-03",
    "2001-05-04",
    "2001-05-07",
    "2001-10-01",
    "2001-10-02",
    "2001-10-03",
    "2001-10-04",
    "2001-10-05",
    "2002-01-01",
    "2002-01-02",
    "2002-01-03",
    "2002-02-11",
    "2002-02-12",
    "2002-02-13",
    "2002-02-14",
    "2002-02-15",
    "2002-02-18",
    "2002-02-19",
    "2002-02-20",
    "2002-02-21",
    "2002-02-22",
    "2002-05-01",
    "2002-05-02",
    "2002-05-03",
    "2002-05-06",
    "2002-05-07",
    "2002-09-30",
    "2002-10-01",
    "2002-10-02",
    "2002-10-03",
    "2002-10-04",
    "2002-10-07",
    "2003-01-01",
    "2003-01-30",
    "2003-01-31",
    "2003-02-03",
    "2003-02-04",
    "2003-02-05",
    "2003-02-06",
    "2003-02-07",
    "2003-05-01",
    "2003-05-02",
    "2003-05-05",
    "2003-05-06",
    "2003-05-07",
    "2003-05-08",
    "2003-05-09",
    "2003-10-01",
    "2003-10-02",
    "2003-10-03",
    "2003-10-06",
    "2003-10-07",
    "2004-01-01",
    "2004-01-19",
    "2004-01-20",
    "2004-01-21",
    "2004-01-22",
    "2004-01-23",
    "2004-01-26",
    "2004-01-27",
    "2004-01-28",
    "2004-05-03",
    "2004-05-04",
    "2004-05-05",
    "2004-05-06",
    "2004-05-07",
    "2004-10-01",
    "2004-10-04",
    "2004-10-05",
    "2004-10-06",
    "2004-10-07",
    "2005-01-03",
    "2005-02-07",
    "2005-02-08",
    "2005-02-09",
    "2005-02-10",
    "2005-02-11",
    "2005-02-14",
    "2005-02-15",
    "2005-05-02",
    "2005-05-03",
    "2005-05-04",
    "2005-05-05",
    "2005-05-06",
    "2005-10-03",
    "2005-10-04",
    "2005-10-05",
    "2005-10-06",
    "2005-10-07",
    "2006-01-02",
    "2006-01-03",
    "2006-01-26",
    "2006-01-27",
    "2006-01-30",
    "2006-01-31",
    "2006-02-01",
    "2006-02-02",
    "2006-02-03",
    "2006-05-01",
    "2006-05-02",
    "2006-05-03",
    "2006-05-04",
    "2006-05-05",
    "2006-10-02",
    "2006-10-03",
    "2006-10-04",
    "2006-10-05",
    "2006-10-06",
    "2007-01-01",
    "2007-01-02",
    "2007-01-03",
    "2007-02-19",
    "2007-02-20",
    "2007-02-21",
    "2007-02-22",
    "2007-02-23",
    "2007-05-01",
    "2007-05-02",
    "2007-05-03",
    "2007-05-04",
    "2007-05-07",
    "2007-10-01",
    "2007-10-02",
    "2007-10-03",
    "2007-10-04",
    "2007-10-05",
    "2007-12-31",
    "2008-01-01",
    "2008-02-06",
    "2008-02-07",
    "2008-02-08",
    "2008-02-11",
    "2008-02-12",
    "2008-04-04",
    "2008-05-01",
    "2008-05-02",
    "2008-06-09",
    "2008-09-15",
    "2008-09-29",
    "2008-09-30",
    "2008-10-01",
    "2008-10-02",
    "2008-10-03",
    "2009-01-01",
    "2009-01-02",
    "2009-01-26",
    "2009-01-27",
    "2009-01-28",
    "2009-01-29",
    "2009-01-30",
    "2009-04-06",
    "2009-05-01",
    "2009-05-28",
    "2009-05-29",
    "2009-10-01",
    "2009-10-02",
    "2009-10-05",
    "2009-10-06",
    "2009-10-07",
    "2009-10-08",
    "2010-01-01",
    "2010-02-15",
    "2010-02-16",
    "2010-02-17",
    "2010-02-18",
    "2010-02-19",
    "2010-04-05",
    "2010-05-03",
    "2010-06-14",
    "2010-06-15",
    "2010-06-16",
    "2010-09-22",
    "2010-09-23",
    "2010-09-24",
    "2010-10-01",
    "2010-10-04",
    "2010-10-05",
    "2010-10-06",
    "2010-10-07",
    "2011-01-03",
    "2011-02-02",
    "2011-02-03",
    "2011-02-04",
    "2011-02-07",
    "2011-02-08",
    "2011-04-04",
    "2011-04-05",
    "2011-05-02",
    "2011-06-06",
    "2011-09-12",
    "2011-10-03",
    "2011-10-04",
    "2011-10-05",
    "2011-10-06",
    "2011-10-07",
    "2012-01-02",
    "2012-01-03",
    "2012-01-23",
    "2012-01-24",
    "2012-01-25",
    "2012-01-26",
    "2012-01-27",
    "2012-04-02",
    "2012-04-03",
    "2012-04-04",
    "2012-04-30",
    "2012-05-01",
    "2012-06-22",
    "2012-10-01",
    "2012-10-02",
    "2012-10-03",
    "2012-10-04",
    "2012-10-05",
    "2013-01-01",
    "2013-01-02",
    "2013-01-03",
    "2013-02-11",
    "2013-02-12",
    "2013-02-13",
    "2013-02-14",
    "2013-02-15",
    "2013-04-04",
    "2013-04-05",
    "2013-04-29",
    "2013-04-30",
    "2013-05-01",
    "2013-06-10",
    "2013-06-11",
    "2013-06-12",
    "2013-09-19",
    "2013-09-20",
    "2013-10-01",
    "2013-10-02",
    "2013-10-03",
    "2013-10-04",
    "2013-10-07",
    "2014-01-01",
    "2014-01-31",
    "2014-02-03",
    "2014-02-04",
    "2014-02-05",
    "2014-02-06",
    "2014-04-07",
    "2014-05-01",
    "2014-05-02",
    "2014-06-02",
    "2014-09-08",
    "2014-10-01",
    "2014-10-02",
    "2014-10-03",
    "2014-10-06",
    "2014-10-07",
    "2015-01-01",
    "2015-01-02",
    "2015-02-18",
    "2015-02-19",
    "2015-02-20",
    "2015-02-23",
    "2015-02-24",
    "2015-04-06",
    "2015-05-01",
    "2015-06-22",
    "2015-09-03",
    "2015-09-04",
    "2015-10-01",
    "2015-10-02",
    "2015-10-05",
    "2015-10-06",
    "2015-10-07",
    "2016-01-01",
    "2016-02-08",
    "2016-02-09",
    "2016-02-10",
    "2016-02-11",
    "2016-02-12",
    "2016-04-04",
    "2016-05-02",
    "2016-06-09",
    "2016-06-10",
    "2016-09-15",
    "2016-09-16",
    "2016-10-03",
    "2016-10-04",
    "2016-10-05",
    "2016-10-06",
    "2016-10-07",
    "2017-01-02",
    "2017-01-27",
    "2017-01-30",
    "2017-01-31",
    "2017-02-01",
    "2017-02-02",
    "2017-04-03",
    "2017-04-04",
    "2017-05-01",
    "2017-05-29",
    "2017-05-30",
    "2017-10-02",
    "2017-10-03",
    "2017-10-04",
    "2017-10-05",
    "2017-10-06",
    "2018-01-01",
    "2018-02-15",
    "2018-02-16",
    "2018-02-19",
    "2018-02-20",
    "2018-02-21",
    "2018-04-05",
    "2018-04-06",
    "2018-04-30",
    "2018-05-01",
    "2018-06-18",
    "2018-09-24",
    "2018-10-01",
    "2018-10-02",
    "2018-10-03",
    "2018-10-04",
    "2018-10-05",
    "2018-12-31",
    "2019-01-01",
    "2019-02-04",
    "2019-02-05",
    "2019-02-06",
    "2019-02-07",
    "2019-02-08",
    "2019-04-05",
    "2019-05-01",
    "2019-05-02",
    "2019-05-03",
    "2019-06-07",
    "2019-09-13",
    "2019-10-01",
    "2019-10-02",
    "2019-10-03",
    "2019-10-04",
    "2019-10-07",
    "2020-01-01",
    "2020-01-24",
    "2020-01-27",
    "2020-01-28",
    "2020-01-29",
    "2020-01-30",
    "2020-01-31",  # http://english.sse.com.cn/news/newsrelease/c/4993503.shtml
    "2020-04-06",
    "2020-05-01",
    "2020-05-04",
    "2020-05-05",
    "2020-06-25",
    "2020-06-26",
    "2020-10-01",
    "2020-10-02",
    "2020-10-05",
    "2020-10-06",
    "2020-10-07",
    "2020-10-08",
    "2021-01-01",
    "2021-02-11",
    "2021-02-12",
    "2021-02-15",
    "2021-02-16",
    "2021-02-17",
    "2021-04-05",
    "2021-05-03",
    "2021-05-04",
    "2021-05-05",
    "2021-06-14",
    "2021-09-20",
    "2021-09-21",
    "2021-10-01",
    "2021-10-04",
    "2021-10-05",
    "2021-10-06",
    "2021-10-07",
    "2022-01-03",
    "2022-01-31",
    "2022-02-01",
    "2022-02-02",
    "2022-02-03",
    "2022-02-04",
    "2022-04-04",
    "2022-04-05",
    "2022-05-02",
    "2022-05-03",
    "2022-05-04",
    "2022-06-03",
    "2022-09-12",
    "2022-10-03",
    "2022-10-04",
    "2022-10-05",
    "2022-10-06",
    "2022-10-07",
    "2023-01-02",
    "2023-01-23",
    "2023-01-24",
    "2023-01-25",
    "2023-01-26",
    "2023-01-27",
    "2023-04-05",
    "2023-05-01",
    "2023-06-22",
    "2023-09-29",
    "2023-10-02",
    "2023-10-03",
    "2023-10-04",
    "2023-10-05",
    "2023-10-06",
    "2024-01-01",
    "2024-02-12",
    "2024-02-13",
    "2024-02-14",
    "2024-02-15",
    "2024-04-04",
    "2024-05-01",
    "2024-06-10",
    "2024-09-17",
    "2024-10-01",
    "2024-10-02",
    "2024-10-03",
    "2024-10-04",
    "2025-01-01",
    "2025-01-29",
    "2025-01-30",
    "2025-01-31",
    "2025-02-03",
    "2025-04-04",
    "2025-05-01",
    "2025-10-01",
    "2025-10-02",
    "2025-10-03",
    "2025-10-04",
]

trade_date_sse = pd.bdate_range(start="1990-12-19",
                                end=year_end, freq='C',
                                holidays=precomputed_shanghai_holidays
                                ).strftime("%Y-%m-%d").tolist()


def get_real_trade_date(date, towards=-1):
    """
    根据给定日期，获取真实的交易日期

    :param date: 给定日期 [str,date]
    :param towards:  方向， -1 -> 向前, 1 -> 向后 int

    :return: 返回计算后的日期str

    """
    day = str(date)[0:10]
    if towards == 1:
        if pd.to_datetime(day) >= pd.to_datetime(trade_date_sse[-1]):
            return trade_date_sse[-1]
        while day not in trade_date_sse:
            day = str(
                datetime.strptime(day, "%Y-%m-%d")
                + timedelta(days=1)
            )[0:10]
        else:
            return str(day)[0:10]
    elif towards == -1:
        if pd.to_datetime(day) <= pd.to_datetime(trade_date_sse[0]):
            return trade_date_sse[0]
        while day not in trade_date_sse:
            day = str(
                datetime.strptime(day, "%Y-%m-%d")
                - timedelta(days=1)
            )[0:10]
        else:
            return str(day)[0:10]


def is_trade_day(date: str) -> bool:
    """
    判断是否交易日期

    :param date: 需判断的日期

    :return: True：是交易日期
    """
    if date in trade_date_sse:
        return True
    else:
        return False


def get_date_gap(date: str, gap: int, methods: str) -> Optional[str]:
    """
    返回指定日期向前或向后间隔天数的交易日日期

    :param date: 字符串起始日
    :param gap: 间隔多数个交易日
    :param methods: 方向["gt->大于", "gte->大于等于","小于->lt", "小于等于->lte", "等于->==="]

    :return: 返回计算后的日期

    """

    try:
        if methods in [">", "gt"]:
            index = trade_date_sse.index(date) + gap
            return trade_date_sse[index] if index < len(trade_date_sse) else trade_date_sse[-1]
        elif methods in [">=", "gte"]:
            index = trade_date_sse.index(date) + gap - 1
            return trade_date_sse[index] if index < len(trade_date_sse) else trade_date_sse[-1]
        elif methods in ["<", "lt"]:
            index = trade_date_sse.index(date) - gap
            return trade_date_sse[index] if index > 0 else trade_date_sse[0]

        elif methods in ["<=", "lte"]:
            index = trade_date_sse.index(date) - gap + 1
            return trade_date_sse[index] if index > 0 else trade_date_sse[0]
        elif methods in ["==", "=", "eq"]:
            return date

    except Exception as e:
        print("日期格式错误！：{}".format(e))
        return None


def get_next_trade_day(date: str, n: int = 1) -> str:
    """
    获取下一个交易日的日期

    :param date: 字符串起始日
    :param n: 间隔多数个交易日

    :return: 返回计算后的日期

    """
    date = str(date)[0:10]

    if not is_trade_day(date):
        date = get_real_trade_date(date, -1)
    return get_date_gap(date, n, "gt")


def get_pre_trade_day(date, n=1, freq='day'):
    # type: (str, int, str) -> str
    """
    获取前几个交易周期的日期

    :param date: 字符串起始日
    :param n: 间隔多数个交易日
    :param freq: 间隔频率，支持['day','1min','5min','15min','30min','60min']

    :return: 返回计算后的日期

    """
    date = str(date)[0:10]

    if freq in ['daily', '1d', 'day']:
        if not is_trade_day(date):
            date = get_real_trade_date(date, -1)
        return get_date_gap(date, n, "lt")
    else:
        _time = str(date)[10:]
        if not is_trade_day(date):
            date = get_real_trade_date(date, -1)
            _time = ' 15:00:00'

        if str(freq) in ['5m', '5min']:
            div = 48
        elif str(freq) in ['15m', '15min']:
            div = 16
        elif str(freq) in ['30m', '30min']:
            div = 8
        elif str(freq) in ['60m', '60min']:
            div = 4
        elif str(freq) in ['1m', '1min']:
            div = 240
        else:
            raise ValueError

        new = get_date_gap(date, math.ceil(n / div), "lt")
        if isinstance(new, str):
            return new + _time
        else:
            raise ValueError


def get_trade_days(start: str, end: str) -> Optional[list]:
    """
    获取指定范围交易日

    :param start: 开始日期
    :param end:   结束日期

    :return:  返回交易日期列表

    """
    real_start = get_real_trade_date(start, 1)
    real_end = get_real_trade_date(end, -1)
    if real_start > real_end:
        return None
    else:
        return trade_date_sse[
               trade_date_sse.index(real_start): trade_date_sse.index(real_end) + 1: 1
               ]


def get_trade_gap(start: str, end: str) -> int:
    """
    返回start到end中间有多少个交易天，算首尾

    :param start: 开始日期
    :param end: 结束日期

    :return: 交易日数量

    """
    real_start = get_real_trade_date(start, 1)
    real_end = get_real_trade_date(end, -1)

    if real_start is not None:
        return trade_date_sse.index(real_end) + 1 - trade_date_sse.index(real_start)
    else:
        return 0


def get_trade_min_list(day, period=1):
    """
     获取交易日的分钟列表
    :param day:    日期
    :param period: 间隔时间（分钟）
    :return: list
    """
    min_list = []
    dt = day + " 09:30:00"
    while dt <= day + " 15:00:00":
        min_list.append(dt)
        dt = (datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
              + timedelta(minutes=period)).strftime("%Y-%m-%d %H:%M:%S")
        if day + " 11:30:00" < dt < day + " 13:00:00":
            dt = day + " 13:00:00"
            dt = (datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
                  + timedelta(minutes=period)).strftime("%Y-%m-%d %H:%M:%S")
    return min_list


def util_date_valid(date):
    """
    判断字符串格式(1982-05-11)
    :param date: 日期 Str
    :return: bool
    """
    try:
        datetime.strptime(date, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def util_time_valid(date_time):
    """
    判断字符串格式(1982-05-11 12:00:00)
    :param date_time: 日期 Str
    :return: bool
    """
    try:
        datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False


def util_time_stamp(time_):
    """
    转换日期时间的字符串为浮点数的时间戳
    :param time_: str 日期时间 参数支持: ['2018-01-01 00:00:00']
    :return: 浮点数的时间戳
    """
    if len(str(time_)) == 10:
        # yyyy-mm-dd格式
        return time.mktime(time.strptime(time_, '%Y-%m-%d'))
    elif len(str(time_)) == 16:
        # yyyy-mm-dd hh:mm格式
        return time.mktime(time.strptime(time_, '%Y-%m-%d %H:%M'))
    else:
        return time.mktime(time.strptime(str(time_)[0:19], '%Y-%m-%d %H:%M:%S'))


def util_get_date_gap(date: str, n: int):
    """
    获取前/后n天的日期
    """
    return str(datetime.strptime(date, "%Y-%m-%d") + timedelta(days=n))[0:10]


def run_time(func: Callable) -> float:
    """
    计算函数运行时间的装饰函数

    :param func: 函数名称， 在待计时函数上方输入@run_time即可

    :return: 函数运行的时间

    """

    @wraps(func)                                # <- 这里加 wraps(func) 保留函数的元信息
    def wrapper(*args, **kwargs):
        start = time.time()
        res = func(*args, **kwargs)                  # 函数在这里运行
        end = time.time()
        cost_time = end - start
        print("函数 {} 运行用时： {}".format(func.__name__, cost_time))
        return res
    return wrapper


def date_to_int(date: str):
    return int(''.join(date.split('-')))


def int_to_date(d: int):
    d = int(d)
    if len(str(d)) <= 6:
        s = "{:>06d}".format(d)
        ret = s[:2]+'-'+s[2:4]+'-'+s[4:]
        if d > 800000:
            return '19'+ret
        else:
            return '20'+ret
    else:
        s = str(d)
        return s[:4]+'-'+s[4:6]+'-'+s[6:]
