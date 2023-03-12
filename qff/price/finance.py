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
从数据库中查询年报、季报数据
"""

import pandas as pd
import datetime
from typing import Dict, Optional
from dateutil.relativedelta import relativedelta
from qff.tools.mongo import DATABASE
from qff.tools.date import (
    util_date_valid,
    get_pre_trade_day,
    is_trade_day,
    get_real_trade_date,
    get_trade_days,
    date_to_int,
    int_to_date
)
from qff.tools.logs import log
from qff.frame.context import context
from qff.frame.const import RUN_TYPE, RUN_STATUS
from qff.tools.utils import util_code_tolist


def get_fundamentals(filter, projection=None, date=None, report_date=None):
    # type: (Optional[Dict], Optional[Dict], Optional[str], Optional[str]) -> Optional[pd.DataFrame]
    """
    根据mongodb语法查询财务数据
    详细的财务数据表及字段描述请见 :ref:`db_finance`

    * 输入date时, 查询指定日期date收盘后所能看到的最近的数据,我们会查找上市公司在这个日期之前(包括此日期)发布的数据, 不会有未来函数.
    * 输入report_date, 查询 report_date 指定的季度或者年份的财务数。
    * **参数report_date和date二选一，同时输入,则report_date有效。**
    * **注意：不支持2000年之前的查询**

    :param filter: 查询条件字典，按pymongo格式输入
    :param projection:  你需要查询的字段列表，按pymongo格式输入
    :param date: 查询日期, 一个字符串(格式类似'2015-10-15')，可以是None, 使用默认日期. 这个默认日期在回测时，
                等于 context.current_dt 的前一天。在实盘时，为当前最新日期，一般是昨天。
    :param report_date: 财报统计的季度或者年份, 一个字符串, 有两种格式:

                        * 季度: 格式是: 年 + 'q' + 季度序号, 例如: '2015q1', '2013q4'.
                        * 年份: 格式就是年份的数字, 例如: '2015', '2016'.

    :return: 返回一个 [pandas.DataFrame], 每一行对应数据库返回的每一行, 列索引是你查询的所有字段

    :example:

    ::

        # 策略在开盘前选择净利润增长率大于30%的股票
        def before_trading_start():
            filter = {'f184' : {"$gt": 0.3}}
            df = get_fundamentals(filter=filter, projection={'f184': 1}, date=context.previous_date)
            g.security = df['code'].to_list()

    """
    if filter is None:
        filter = {}
    elif not isinstance(filter, dict):
        log.error("参数filter不合法！")
        return None

    if projection is None:
        projection = {"_id": 0}
    elif isinstance(projection, dict):
        prefix = {
            "_id": 0,
            "code": 1,
            "report_date": 1,
            "f314": 1  # 财报公告日期
        }
        projection = dict(**prefix, **projection)
    else:
        log.error("参数projection不合法！")
        return None

    rd_list = ["-03-31", "-06-30", "-09-30", "-12-31"]
    if report_date is not None:
        if isinstance(report_date, str) and len(report_date) == 4 and report_date.isdigit():
            rd = report_date + "-12-31"
        elif isinstance(report_date, str) and len(report_date) == 6 and report_date[:4].isdigit() \
                and report_date[4] == 'q' and report_date[-1] in ["1", "2", "3", "4"]:
            rd = report_date[:4] + rd_list[int(report_date[-1]) - 1]
        else:
            log.error("参数report_date不合法！")
            return None
        filter['report_date'] = date_to_int(rd)
    else:
        if date is None:
            if context.run_type == RUN_TYPE.BACK_TEST and context.status == RUN_STATUS.RUNNING:
                end = context.previous_date
            else:
                today = datetime.date.today()
                end = (today - relativedelta(days=1)).strftime('%Y-%m-%d')
        elif util_date_valid(date) and date > '2000-01-01':
            end = date
        else:
            log.error("参数date不合法！")
            return None
        # 三季报一般在10月中下旬，年报一般在4月下旬，则最长财报间隔在6-7个月。
        start = (datetime.datetime.strptime(end, '%Y-%m-%d') - relativedelta(months=8)).strftime('%Y-%m-%d')
        if start < '2000-01-01':
            start = '2000-01-01'
        filter['f314'] = {
            "$lt": date_to_int(end[2:]),
            "$gte": date_to_int(start[2:])
        }

    coll = DATABASE.report
    cursor = coll.find(filter=filter, projection=projection)

    db_data = pd.DataFrame([item for item in cursor])
    if len(db_data) < 1:
        log.error("get_fundamentals未查询到数据")
        return None
    rtn: pd.DataFrame = db_data.sort_values('report_date', ascending=False).groupby('code', as_index=False).first()
    rtn = rtn.reset_index(drop=True).sort_values(['code', 'report_date'])
    rtn.insert(2, 'pub_date', rtn['f314'].apply(int_to_date))
    rtn.drop(columns=['f314'], inplace=True)
    return rtn


def get_financial_data(code, fields=None, date=None, report_date=None):
    # type: (Optional[list, str], Optional[list], Optional[str], Optional[str]) -> Optional[pd.DataFrame]
    """
    查询多只股票给定日期的财务数据

    * 输入date时, 查询指定日期date收盘后所能看到的最近的数据,我们会查找上市公司在这个日期之前(包括此日期)发布的数据, 不会有未来函数.
    * 输入report_date, 查询 report_date 指定的季度或者年份的财务数。
    * **参数report_date和date二选一，同时输入,则report_date有效。**
    * **注意：不支持2000年之前的查询**

    :param code:  一支股票代码或者一个股票代码的list，None表示所有股票代码
    :param fields: 返回的财务数据字段list，'001'-'580',None表示所有财务指标,详细的财务数据表及字段描述请见 :ref:`db_finance`
    :param date: 查询日期, 一个字符串(格式类似'2015-10-15')，可以是None, 使用默认日期. 这个默认日期在回测时，
                等于 context.current_dt 的前一天。在实盘时，为当前最新日期，一般是昨天。
    :param report_date: 财报统计的季度或者年份, 一个字符串, 有两种格式:

                        * 季度: 格式是: 年 + 'q' + 季度序号, 例如: '2015q1', '2013q4'.
                        * 年份: 格式就是年份的数字, 例如: '2015', '2016'.

    :return:返回一个 [pandas.DataFrame], 每一行对应数据库返回的每一行, 列名是输入的field字段信息

    :example:

    ::

        # 获取股票'000001'和'601567'的每股收益、扣非每股收益及净利润
        df = get_financial_data(['000001', '601567'], ['f001', 'f002', 'f095'],watch_date='2020-04-22')

    """
    _filter = {}
    if code is not None:
        if isinstance(code, str):
            code = [code]
        elif not isinstance(code, list):
            log.error("参数code不合法！,应该为字符串或列表！")
            return None
        _filter['code'] = {'$in': code}

    if fields is not None:
        if isinstance(fields, list):
            if not all(isinstance(field, str) and field.isdigit() for field in fields):
                log.error("参数fields不合法！,应该为字符串列表,范围'001'~'580'！")
                return None
            projection = dict.fromkeys(fields, 1)
        else:
            log.error("参数fields不合法！,应该为字符串列表！")
            return None
    else:
        projection = None
    try:
        return get_fundamentals(_filter, projection, date, report_date)
    except Exception as e:
        log.error("get_fundamentals运行异常：{}".format(e))
        return None


def get_stock_reports(code, fields=None, start=None, end=None):
    # type: (str, Optional[list], Optional[str], Optional[str]) -> Optional[pd.DataFrame]
    """
    获取单个股票多个报告期发布的财务数据

    :param code: 一支股票代码
    :param fields: 返回的财务数据字段list，'001'-'580',None表示所有财务指标,详细的财务数据表及字段描述请见 :ref:`db_finance`
    :param start: 查询期间开始日期，一个字符串(格式类似'2015-10-15')，可以是None, 代表从股票上市开始
    :param end: 查询日期, 一个字符串(格式类似'2015-10-15')，可以是None, 使用默认日期. 这个默认日期在回测时，
                        等于 context.current_dt 的前一天。在实盘时，为当前最新日期，一般是昨天。
    :return: 返回一个 [pandas.DataFrame]

    """
    if code is None:
        log.error("参数code不可为空！")
        return
    elif not isinstance(code, str):
        log.error("参数code不合法！,应该为字符串")
        return None
    _filter: Dict[str, any] = {'code': code}

    if fields is None:
        projection = {"_id": 0}
    elif isinstance(fields, list):
        if not all(isinstance(field, str) and field[1:].isdigit() for field in fields):
            log.error("参数fields不合法！,应该为字符串列表,范围'001'~'580'！")
            return None
        projection = dict.fromkeys(fields, 1)
        prefix = {
            "_id": 0,
            "code": 1,
            "report_date": 1,
            'f314': 1
        }
        projection = dict(**prefix, **projection)
    else:
        log.error("参数fields不合法！,应该为字符串列表！")
        return None

    if end is None:
        if context.run_type == RUN_TYPE.BACK_TEST and context.status == RUN_STATUS.RUNNING:
            end = context.previous_date
        else:
            today = datetime.date.today()
            end = (today - relativedelta(days=1)).strftime('%Y-%m-%d')
    elif util_date_valid(end) and end > '2000-01-01':
        if not is_trade_day(end):
            end = get_real_trade_date(end)
    else:
        log.error("参数end不合法！查询日期需大于2000-01-01")
        return None

    if start is None:
        _filter['f314'] = {
            "$gt": 0,
            "$lte": date_to_int(end[2:]),
        }
    elif end > start > '2000-01-01':
        _filter['f314'] = {
            "$lte": date_to_int(end[2:]),
            "$gte": date_to_int(start[2:])
        }
    else:
        log.error("参数start不合法！查询日期需大于2000-01-01")
        return None

    coll = DATABASE.report
    cursor = coll.find(filter=_filter, projection=projection)
    db_data = pd.DataFrame([item for item in cursor])
    if len(db_data) > 1:
        db_data = db_data.sort_values('report_date')
        db_data.insert(2, 'pub_date', db_data['f314'].apply(int_to_date))
        db_data.drop(columns=['f314'], inplace=True)
        return db_data
    else:
        return None


def get_stock_forecast(code=None, start=None, end=None):
    # type: (Optional[str], Optional[str], Optional[str]) -> Optional[pd.DataFrame]
    """
    获取股票业绩预告数据

    :param code: 一支股票代码或股票列表，可以是None值，代表整个市场
    :param start: 查询期间开始日期，一个字符串(格式类似'2015-10-15')，可以是None, 代表从股票上市开始
    :param end: 查询日期, 一个字符串(格式类似'2015-10-15')，可以是None, 使用默认日期. 这个默认日期在回测时，
                        等于 context.current_dt 的前一天。在实盘时，为当前最新日期，一般是昨天。
    :return: 返回一个 [pandas.DataFrame]，包含以下数据：

                        ==========================  ====================
                         字段名	                        含义
                        ==========================  ====================
                         code                         股票代码
                         pub_date                     业绩预告公告日期
                         report_date                  报告期
                         profit_min                   本期利润下限
                         profit_max                   本期利润上限
                         profit_ratio_min             本期利润同比增幅下限
                         profit_ratio_max             本期利润同比增幅上限
                        ==========================  ====================

    """
    if code is not None:
        code = util_code_tolist(code)
        _filter = {'code': {'$in': code}}
    else:
        _filter = {}

    if end is None:
        if context.run_type == RUN_TYPE.BACK_TEST and context.status == RUN_STATUS.RUNNING:
            end = context.previous_date
        else:
            today = datetime.date.today()
            end = (today - relativedelta(days=1)).strftime('%Y-%m-%d')
    elif not util_date_valid(end):
        log.error("参数end不合法！")
        return None

    if start is None:
        _filter['f313'] = {
            "$gt": 0,
            "$lte": date_to_int(end[2:]),
        }
    elif util_date_valid(start):
        _filter['f313'] = {
            "$lte": date_to_int(end[2:]),
            "$gte": date_to_int(start[2:])
        }
    else:
        log.error("参数start不合法！")
        return None

    projection = {
        "_id": 0,
        "code": 1,
        "report_date": 1,
        'f313': 1,
        'f317': 1,
        'f318': 1,
        'f285': 1,
        'f286': 1,
    }
    coll = DATABASE.report
    cursor = coll.find(filter=_filter, projection=projection)
    db_data = pd.DataFrame([item for item in cursor])
    if len(db_data) >= 1:
        db_data['f313'] = db_data['f313'].apply(int_to_date)
        db_data.rename(columns={
            'f313': 'pub_date',
            'f317': 'profit_min',
            'f318': 'profit_max',
            'f285': 'profit_ratio_min',
            'f286': 'profit_ratio_max',
        }, inplace=True)
        db_data = db_data.sort_values('code')
        db_data.report_date = db_data.report_date.apply(lambda x: get_next_report_date(x))
        return db_data[['code', 'pub_date', 'report_date', 'profit_min', 'profit_max',
                        'profit_ratio_min', 'profit_ratio_max']]
    else:
        return None


def get_stock_express(code=None, start=None, end=None):
    # type: (Optional[str], Optional[str], Optional[str]) -> Optional[pd.DataFrame]
    """
    获取股票业绩快报数据

    :param code: 一支股票代码或股票列表，可以是None值，代表整个市场
    :param start: 查询期间开始日期，一个字符串(格式类似'2015-10-15')，可以是None, 代表从股票上市开始
    :param end: 查询日期结束日期, 一个字符串(格式类似'2015-10-15')，可以是None, 使用默认日期. 这个默认日期在回测时，
                        等于 context.current_dt 的前一天。在实盘时，为当前最新日期，一般是昨天。

    :return: 返回一个 [pandas.DataFrame]，包含以下数据：

                        ==========================  ====================
                         字段名	                        含义
                        ==========================  ====================
                         code                         股票代码
                         pub_date                     业绩快报公告日期
                         report_date                  报告期
                         net_profit                   归母公司净利润
                         adjusted_profit              扣非净利润
                         total_assets                 总资产
                         net_assets                   净资产
                         eps                          每股收益
                         roe_diminish                 摊薄净资产收益率
                         roe_weighting                加权净资产收益率
                         naps                         每股净资产
                        ==========================  ====================

    """
    if code is not None:
        code = util_code_tolist(code)
        _filter = {'code': {'$in': code}}
    else:
        _filter = {}

    if end is None:
        if context.run_type == RUN_TYPE.BACK_TEST and context.status == RUN_STATUS.RUNNING:
            end = context.previous_date
        else:
            today = datetime.date.today()
            end = (today - relativedelta(days=1)).strftime('%Y-%m-%d')
    elif not util_date_valid(end):
        log.error("参数end不合法！")
        return None

    if start is None:
        _filter['f315'] = {
            "$gt": 0,
            "$lte": date_to_int(end[2:]),
        }
    elif util_date_valid(start):
        _filter['f315'] = {
            "$lte": date_to_int(end[2:]),
            "$gte": date_to_int(start[2:])
        }
    else:
        log.error("参数start不合法！")
        return None

    projection = {
        "_id": 0,
        "code": 1,
        "report_date": 1,
        'f315': 1,
        'f287': 1,
        'f288': 1,
        'f289': 1,
        'f290': 1,
        'f291': 1,
        'f292': 1,
        'f293': 1,
        'f294': 1,
    }
    coll = DATABASE.report
    cursor = coll.find(filter=_filter, projection=projection)
    db_data = pd.DataFrame([item for item in cursor])
    if len(db_data) >= 1:
        db_data.insert(2, 'pub_date', db_data['f315'].apply(int_to_date))
        db_data.drop(columns=['f315'], inplace=True)
        db_data.rename(columns={
            'f287': 'net_profit',
            'f288': 'adjusted_profit',
            'f289': 'total_assets',
            'f290': 'net_assets',
            'f291': 'eps',
            'f292': 'roe_diminish',
            'f293': 'roe_weighting',
            'f294': 'naps',
        }, inplace=True)
        db_data.report_date = db_data.report_date.apply(lambda x: get_next_report_date(x))
        db_data = db_data.sort_values('code')
        return db_data
    else:
        return None


def get_fundamentals_continuously(code, fields=None, end_date=None, count=None):
    # type: (str, Optional[list], Optional[str], Optional[int]) -> Optional[pd.DataFrame]
    """
    查询单个股票连续多日的财务数据

    详细的财务数据表及字段描述请见financial_dict

    :param code:  一支股票代码
    :param fields: 返回的财务数据字段list，'001'-'580',None表示所有财务指标,详细的财务数据表及字段描述请见 :ref:`db_finance`
    :param end_date: 查询日期, 一个字符串(格式类似'2015-10-15')，可以是None, 使用默认日期. 这个默认日期在回测时，
                    等于 context.current_dt 的前一天。在实盘时，为当前最新日期，一般是昨天。
    :param count: 获取 end_date 前 count 个日期的数据

    :return: 返回一个 [pandas.DataFrame]

    """
    if code is None:
        log.error("参数code不可为空！")
        return
    elif not isinstance(code, str):
        log.error("参数code不合法！,应该为字符串")
        return None
    _filter = {'code': code}

    if fields is None:
        projection = {"_id": 0}
    elif isinstance(fields, list):
        if not all(isinstance(field, str) and field.isdigit() for field in fields):
            log.error("参数fields不合法！,应该为字符串列表,范围'001'~'580'！")
            return None
        projection = dict.fromkeys(fields, 1)
        prefix = {
            "_id": 0,
            "code": 1,
            "report_date": 1,
            'f314': 1
        }
        projection = dict(**prefix, **projection)
    else:
        log.error("参数fields不合法！,应该为字符串列表！")
        return None

    if end_date is None:
        if context.run_type == RUN_TYPE.BACK_TEST and context.status == RUN_STATUS.RUNNING:
            end = context.previous_date
        else:
            today = datetime.date.today()
            end = (today - relativedelta(days=1)).strftime('%Y-%m-%d')
    elif util_date_valid(end_date) and end_date > '2000-01-01':
        end = end_date
    else:
        log.error("参数end_date不合法！")
        return None
    if not is_trade_day(end):
        end = get_real_trade_date(end)

    if count is None:
        _filter['f314'] = dict({"$lte": date_to_int(end[2:])})
    else:
        start = get_pre_trade_day(end, count)

        # 查询财报日期向前移8个月，避免4月下旬只能查看到去年10月发布的三季报
        query_start = (datetime.datetime.strptime(start, '%Y-%m-%d') - relativedelta(months=8))\
            .strftime('%Y-%m-%d')
        if query_start < '2000-01-01':
            query_start = '2000-01-01'

        _filter['f314'] = {
            "$lte": date_to_int(end[2:]),
            "$gte": date_to_int(query_start[2:])
        }

    coll = DATABASE.report
    cursor = coll.find(filter=_filter, projection=projection)
    db_data = pd.DataFrame([item for item in cursor])
    if len(db_data) > 1:
        db_data = db_data.sort_values('report_date')
        db_data.insert(2, 'pub_date', db_data['f314'].apply(int_to_date))
        db_data.drop(columns=['f314'], inplace=True)
        start = db_data.pub_date[0]
        date_list = get_trade_days(start, end)
        res = pd.DataFrame({'date': date_list})
        res = res.merge(db_data, left_on='date', right_on='pub_date', how='left')
        res = res.fillna(method='ffill')
        res['report_date'] = res['report_date'].round(0).astype(int)
        if count is not None:
            res = res.iloc[-count:]
        return res

    else:
        log.warning("get_fundamentals_continuously未查询到数据")
        return None


def get_history_fundamentals(code, fields, watch_date=None, report_date=None, count=1, interval='1q'):
    # type: (Optional[str], Optional[list], Optional[str], Optional[str], int, str) -> Optional[pd.DataFrame]
    """
    获取多只股票多个季度（年度）的历史财务数据
    可指定单季度数据, 也可以指定年度数据。可以指定观察日期, 也可以指定最后一个报告期的结束日期

    :param code: 股票代码或者股票代码列表
    :param fields: 要查询的财务数据的列表,详细的财务数据表及字段描述请见 :ref:`db_finance`
    :param watch_date: 观察日期, 如果指定, 将返回 watch_date 日期前(包含该日期)发布的报表数据
    :param report_date: 财报日期, 可以是 '2019'/'2019q1'/'2018q4' 格式, 如果指定, 将返回 report_date 对应报告期及之前的历史报告期的报表数据
                        watch_date 和 stat_date 只能指定一个, 而且必须指定一个
    :param count: 查询历史的多个报告期时, 指定的报告期数量. 如果股票历史报告期的数量小于 count, 则该股票返回的数据行数将小于 count
    :param interval: 查询多个报告期数据时, 指定报告期间隔, 可选值: '1q'/'1y', 表示间隔一季度或者一年，举例：
                        report_date='2019q1', interval='1q', count=4, 将返回 2018q2,2018q3,2018q4,2019q1 的数据
                        report_date='2019q1', interval='1y', count=4, 将返回 2016q1,2017q1,2018q1,2019q1 的数据

    :return: pandas.DataFrame, 数据库查询结果. 数据格式同 get_fundamentals. 每个股票每个报告期(一季度或者一年)的数据占用一行.
            推荐用户对结果使用pandas的groupby方法来进行分组分析数据
    """
    _filter = {}
    if code is not None:
        if isinstance(code, str):
            code = [code]
        elif not isinstance(code, list):
            log.error("参数code不合法！,应该为字符串或列表！")
            return None
        _filter['code'] = {'$in': code}

    if fields is not None:
        if isinstance(fields, list):
            if not all(isinstance(field, str) and field.isdigit() for field in fields):
                log.error("参数fields不合法！,应该为字符串列表,范围'001'~'580'！")
                return None
            projection = dict.fromkeys(fields, 1)
        else:
            log.error("参数fields不合法！,应该为字符串列表！")
            return None
    else:
        projection = None
    try:
        if count == 1:
            return get_fundamentals(_filter, projection, watch_date, report_date)

        elif count > 1 and isinstance(count, int):
            if projection is None:
                projection = {"_id": 0}
            else:
                prefix = {
                    "_id": 0,
                    "code": 1,
                    "report_date": 1,
                    "f314": 1
                }
                projection = dict(**prefix, **projection)

            if interval == '1q':
                inter_months = 3 * count
            elif interval == '1y':
                inter_months = 12 * count
            else:
                log.error("参数interval错误，可选值为'1q'/'1y'!")
                return None

            if report_date is not None:
                rd_list = ["-03-31", "-06-30", "-09-30", "-12-31"]
                if isinstance(report_date, str) and len(report_date) == 4 and report_date.isdigit():
                    end = report_date + "-12-31"
                elif isinstance(report_date, str) and len(report_date) == 6 and report_date[:4].isdigit() \
                        and report_date[4] == 'q' and report_date[-1] in ["1", "2", "3", "4"]:
                    end = report_date[:4] + rd_list[int(report_date[-1]) - 1]
                else:
                    log.error("参数report_date不合法！")
                    return None
                start = (datetime.datetime.strptime(end, '%Y-%m-%d')
                         - relativedelta(months=inter_months)).strftime('%Y-%m-%d')
                _filter['report_date'] = {
                    "$lte": date_to_int(end),
                    "$gte": date_to_int(start)
                }

            elif watch_date is not None:
                if util_date_valid(watch_date) and watch_date > '2000-01-01':
                    end = watch_date
                    start = (datetime.datetime.strptime(end, '%Y-%m-%d')
                             - relativedelta(months=8+inter_months)).strftime('%Y-%m-%d')
                    if start < '2000-01-01':
                        start = '2000-01-01'
                    _filter['f314'] = {
                        "$lte": date_to_int(end[2:]),
                        "$gte": date_to_int(start[2:])
                    }

                else:
                    log.error("参数watch_date输入格式不合法！")
                    return None

            else:
                log.error("参数watch_date和report_date必须指定一个!")
                return None

            coll = DATABASE.report
            cursor = coll.find(filter=_filter, projection=projection)

            db_data = pd.DataFrame([item for item in cursor])
            if len(db_data) < 1:
                log.warning("get_history_fundamentals未查询到数据")
                return None

            # 原先考虑财报数据的更新在数据库中新增一条记录，后来还是在原来数据上update
            # db_data = db_data.sort_values('pub_date', ascending=False)\
            #     .groupby(['code', 'report_date'], as_index=False).first()

            if interval == '1q':
                rtn = db_data.sort_values('report_date', ascending=False)\
                      .groupby(['code'], as_index=False).head(count)
            else:
                rtn = db_data.sort_values('report_date', ascending=False)\
                      .groupby(['code'], as_index=False)\
                      .apply(lambda x: x[[i % 4 == 0 for i in range(len(x))]].head(count))

            rtn = rtn.reset_index(drop=True).sort_values(['code', 'report_date'])
            rtn.insert(2, 'pub_date', rtn['f314'].apply(int_to_date))
            rtn.drop(columns=['f314'], inplace=True)

            return rtn

        else:
            log.error("参数count必须为大于零的整数!")
            return None

    except Exception as e:
        log.error("get_fundamentals运行异常：{}".format(e))
        return None


def get_valuation(code, start=None, end=None, fields=None, count=None):
    # type: (str, Optional[str], Optional[str], Optional[list], Optional[int]) -> Optional[pd.DataFrame]
    """
    获取多个股票在指定交易日范围内的市值表数据

    :param code: 一支股票代码或者一个股票代码的list，None表示所有股票代码
    :param start: 查询开始时间，不能与count共用
    :param end: 查询结束时间
    :param count: 表示往前查询每一个标的count个交易日的数据，如果期间标的停牌，则该标的返回的市值数据数量小于count
    :param fields: 财务数据中市值表的字段，为None返回所有字段，可用字段如下：

    :return: 返回一个dataframe，索引默认是pandas的整数索引，返回的结果字段描述如下：

                        ==========================  ====================
                         字段名	                        含义
                        ==========================  ====================
                         code                         股票代码
                         date                         日期
                         quantity_ratio               量比
                         capitalization               总股本(万股)
                         circulating_cap              流通股本(万股)
                         market_cap                   总市值(亿元)
                         circulating_market_cap       流通市值(亿元)
                         turnover_ratio               换手率(%)
                         pe_ratio                     市盈率(PE, TTM)
                         pe_ratio_lyr                 市盈率(PE)s
                         pe_ratio_dyn                 市盈率（动态）
                         pb_ratio                     市净率(PB)
                        ==========================  ====================
    """

    filter = {}
    if code is not None:
        if isinstance(code, str):
            code = [code]
        elif not isinstance(code, list):
            log.error("参数code不合法！,应该为字符串或列表！")
            return None
        filter['code'] = {'$in': code}

    if end is None:
        end = datetime.datetime.now().strftime('%Y-%m-%d')
        if not is_trade_day(end):
            end = get_real_trade_date(end)
    elif util_date_valid(end):
        if not is_trade_day(end):
            end = get_real_trade_date(end)
    else:
        log.error("参数end不合法！")
        return None

    if start is None:
        if count is None:
            start = end
        else:
            start = get_pre_trade_day(end, count - 1)
    elif not util_date_valid(end):
        log.error("参数end不合法！")
        return None

    filter['date'] = {
        '$gte': str(start)[0:10],
        '$lte': str(end)[0:10]
    }

    if fields is None:
        projection = {"_id": 0}
    elif isinstance(fields, list):
        projection = dict.fromkeys(fields, 1)
        prefix = {
            "_id": 0,
            "code": 1,
            "date": 1,
        }
        projection = dict(**prefix, **projection)
    else:
        log.error("参数fields不合法！,参考函数说明文件！")
        return None

    coll = DATABASE.valuation
    cursor = coll.find(filter=filter, projection=projection)
    return pd.DataFrame([item for item in cursor])


def query_valuation(filter, projection=None):
    # type: (Dict, Optional[Dict]) -> Optional[pd.DataFrame]
    """
    查询满足条件的市值信息数据
    可用查询条件字段如下：

            ==========================  ====================
             字段名	                        含义
            ==========================  ====================
             code                         股票代码
             date                         日期
             quantity_ratio               量比
             capitalization               总股本(万股)
             circulating_cap              流通股本(万股)
             market_cap                   总市值(亿元)
             cir_market_cap               流通市值(亿元)
             turnover_ratio               换手率(%)
             pe_ttm                       市盈率(PE, TTM)
             pe_lyr                       市盈率(PE)s
             pe_dyn                       市盈率（动态）
             pb_ratio                     市净率(PB)
            ==========================  ====================

    :param filter: dict 查询条件字典，按pymongo格式输入
    :param projection:  你需要查询的字段列表，按pymongo格式输入，返回结果中总会包含code、date字段，无需输入

    :return: 返回一个 [pandas.DataFrame], 每一行对应数据库返回的每一行, 列索引是你查询的所有字段

    :example:

        ::

            # 查询上一个交易日量比大于2，换手率小于2%的股票
            yesterday = context.previous_date
            filter = {'date': yesterday, 'quantity_ratio': {'$gt': 2}, 'turnover_ratio': {'$lt': 0.02}}
            projection = {'quantity_ratio' : 1, 'turnover_ratio': 1}
            signal = query_valuation(filter, projection)

    """
    if filter is None:
        filter = {}
    elif not isinstance(filter, dict):
        log.error("参数filter不合法！")
        return None

    if projection is None:
        projection = {"_id": 0}
    elif isinstance(projection, dict):
        prefix = {
            "_id": 0,
            "code": 1,
            "date": 1,
        }
        projection = dict(**prefix, **projection)
    else:
        log.error("参数projection不合法！")
        return None

    coll = DATABASE.valuation
    cursor = coll.find(filter=filter, projection=projection)
    return pd.DataFrame([item for item in cursor])


def get_next_report_date(report_date: int) -> int :
    periods = [331, 630, 930, 1231]
    year = int(report_date / 10000)
    md = report_date % 10000
    if periods.index(md) < 3:
        next_index = periods.index(md) + 1
    else:
        next_index = 0
        year += 1
    return year * 10000 + periods[next_index]





financial_dict = {

    # 1.每股指标
    'f001': '基本每股收益',  # 'EPS',
    'f002': '扣除非经常性损益每股收益',  # 'deductEPS',
    'f003': '每股未分配利润',  # 'undistributedProfitPerShare',
    'f004': '每股净资产',  # 'netAssetsPerShare',
    'f005': '每股资本公积金',  # 'capitalReservePerShare',
    'f006': '净资产收益率',  # 'ROE',
    'f007': '每股经营现金流量',  # 'operatingCashFlowPerShare',
    # 2. 资产负债表 BALANCE SHEET
    # 2.1 资产
    # 2.1.1 流动资产
    'f008': '货币资金',  # 'moneyFunds',
    'f009': '交易性金融资产',  # 'tradingFinancialAssets',
    'f010': '应收票据',  # 'billsReceivables',
    'f011': '应收账款',  # 'accountsReceivables',
    'f012': '预付款项',  # 'prepayments',
    'f013': '其他应收款',  # 'otherReceivables',
    'f014': '应收关联公司款',  # 'interCompanyReceivables',
    'f015': '应收利息',  # 'interestReceivables',
    'f016': '应收股利',  # 'dividendsReceivables',
    'f017': '存货',  # 'inventory',
    'f018': '其中：消耗性生物资产',  # 'expendableBiologicalAssets',
    'f019': '一年内到期的非流动资产',  # 'noncurrentAssetsDueWithinOneYear',
    'f020': '其他流动资产',  # 'otherLiquidAssets',
    'f021': '流动资产合计',  # 'totalLiquidAssets',
    # 2.1.2 非流动资产
    'f022': '可供出售金融资产',  # 'availableForSaleSecurities',
    'f023': '持有至到期投资',  # 'heldToMaturityInvestments',
    'f024': '长期应收款',  # 'longTermReceivables',
    'f025': '长期股权投资',  # 'longTermEquityInvestment',
    'f026': '投资性房地产',  # 'investmentRealEstate',
    'f027': '固定资产',  # 'fixedAssets',
    'f028': '在建工程',  # 'constructionInProgress',
    'f029': '工程物资',  # 'engineerMaterial',
    'f030': '固定资产清理',  # 'fixedAssetsCleanUp',
    'f031': '生产性生物资产',  # 'productiveBiologicalAssets',
    'f032': '油气资产',  # 'oilAndGasAssets',
    'f033': '无形资产',  # 'intangibleAssets',
    'f034': '开发支出',  # 'developmentExpenditure',
    'f035': '商誉',  # 'goodwill',
    'f036': '长期待摊费用',  # 'longTermDeferredExpenses',
    'f037': '递延所得税资产',  # 'deferredIncomeTaxAssets',
    'f038': '其他非流动资产',  # 'otherNonCurrentAssets',
    'f039': '非流动资产合计',  # 'totalNonCurrentAssets',
    'f040': '资产总计',  # 'totalAssets',
    # 2.2 负债
    # 2.2.1 流动负债
    'f041': '短期借款',  # 'shortTermLoan',
    'f042': '交易性金融负债',  # 'tradingFinancialLiabilities',
    'f043': '应付票据',  # 'billsPayable',
    'f044': '应付账款',  # 'accountsPayable',
    'f045': '预收款项',  # 'advancedReceivable',
    'f046': '应付职工薪酬',  # 'employeesPayable',
    'f047': '应交税费',  # 'taxPayable',
    'f048': '应付利息',  # 'interestPayable',
    'f049': '应付股利',  # 'dividendPayable',
    'f050': '其他应付款',  # 'otherPayable',
    'f051': '应付关联公司款',  # 'interCompanyPayable',
    'f052': '一年内到期的非流动负债',  # 'noncurrentLiabilitiesDueWithinOneYear',
    'f053': '其他流动负债',  # 'otherCurrentLiabilities',
    'f054': '流动负债合计',  # 'totalCurrentLiabilities',
    # 2.2.2 非流动负债
    'f055': '长期借款',  # 'longTermLoans',
    'f056': '应付债券',  # 'bondsPayable',
    'f057': '长期应付款',  # 'longTermPayable',
    'f058': '专项应付款',  # 'specialPayable',
    'f059': '预计负债',  # 'estimatedLiabilities',
    'f060': '递延所得税负债',  # 'defferredIncomeTaxLiabilities',
    'f061': '其他非流动负债',  # 'otherNonCurrentLiabilities',
    'f062': '非流动负债合计',  # 'totalNonCurrentLiabilities',
    'f063': '负债合计',  # 'totalLiabilities',
    # 2.3 所有者权益
    'f064': '实收资本（或股本）',  # 'totalShare',
    'f065': '资本公积',  # 'capitalReserve',
    'f066': '盈余公积',  # 'surplusReserve',
    'f067': '减：库存股',  # 'treasuryStock',
    'f068': '未分配利润',  # 'undistributedProfits',
    'f069': '少数股东权益',  # 'minorityEquity',
    'f070': '外币报表折算价差',  # 'foreignCurrencyReportTranslationSpread',
    'f071': '非正常经营项目收益调整',  # 'abnormalBusinessProjectEarningsAdjustment',
    'f072': '所有者权益（或股东权益）合计',  # 'totalOwnersEquity',
    'f073': '负债和所有者（或股东权益）合计',  # 'totalLiabilitiesAndOwnersEquity',
    # 3.利润表
    'f074': '其中：营业收入',  # 'operatingRevenue',
    'f075': '其中：营业成本',  # 'operatingCosts',
    'f076': '营业税金及附加',  # 'taxAndSurcharges',
    'f077': '销售费用',  # 'salesCosts',
    'f078': '管理费用',  # 'managementCosts',
    'f079': '堪探费用',  # 'explorationCosts',
    'f080': '财务费用',  # 'financialCosts',
    'f081': '资产减值损失',  # 'assestsDevaluation',
    'f082': '加：公允价值变动净收益',  # 'profitAndLossFromFairValueChanges',
    'f083': '投资收益',  # 'investmentIncome',
    'f084': '其中：对联营企业和合营企业的投资收益',  # 'investmentIncomeFromAffiliatedBusinessAndCooperativeEnterprise',
    'f085': '影响营业利润的其他科目',  # 'otherSubjectsAffectingOperatingProfit',
    'f086': '三、营业利润',  # 'operatingProfit',
    'f087': '加：补贴收入',  # 'subsidyIncome',
    'f088': '营业外收入',  # 'nonOperatingIncome',
    'f089': '减：营业外支出',  # 'nonOperatingExpenses',
    'f090': '其中：非流动资产处置净损失',  # 'netLossFromDisposalOfNonCurrentAssets',
    'f091': '加：影响利润总额的其他科目',  # 'otherSubjectsAffectTotalProfit',
    'f092': '四、利润总额',  # 'totalProfit',
    'f093': '减：所得税',  # 'incomeTax',
    'f094': '加：影响净利润的其他科目',  # 'otherSubjectsAffectNetProfit',
    'f095': '五、净利润',  # 'netProfit',
    'f096': '归属于母公司所有者的净利润',  # 'netProfitsBelongToParentCompanyOwner',
    'f097': '少数股东损益',  # 'minorityProfitAndLoss',
    # 4.现金流量表
    # 4.1 经营活动 Operating
    'f098': '销售商品、提供劳务收到的现金',  # 'cashFromGoodsSalesorOrRenderingOfServices',
    'f099': '收到的税费返还',  # 'refundOfTaxAndFeeReceived',
    'f100': '收到其他与经营活动有关的现金',  # 'otherCashRelatedBusinessActivitiesReceived',
    'f101': '经营活动现金流入小计',  # 'cashInflowsFromOperatingActivities',
    'f102': '购买商品、接受劳务支付的现金',  # 'buyingGoodsReceivingCashPaidForLabor',
    'f103': '支付给职工以及为职工支付的现金',  # 'paymentToEmployeesAndCashPaidForEmployees',
    'f104': '支付的各项税费',  # 'paymentsOfVariousTaxes',
    'f105': '支付其他与经营活动有关的现金',  # 'paymentOfOtherCashRelatedToBusinessActivities',
    'f106': '经营活动现金流出小计',  # 'cashOutflowsFromOperatingActivities',
    'f107': '经营活动产生的现金流量净额',  # 'netCashFlowsFromOperatingActivities',
    # 4.2 投资活动 Investment
    'f108': '收回投资收到的现金',  # 'cashReceivedFromInvestmentReceived',
    'f109': '取得投资收益收到的现金',  # 'cashReceivedFromInvestmentIncome',
    'f110': '处置固定资产、无形资产和其他长期资产收回的现金净额',
    'f111': '处置子公司及其他营业单位收到的现金净额',  # 'disposalOfNetCashReceivedFromSubsidiariesAndOtherBusinessUnits',
    'f112': '收到其他与投资活动有关的现金',  # 'otherCashReceivedRelatingToInvestingActivities',
    'f113': '投资活动现金流入小计',  # 'cashinFlowsFromInvestmentActivities',
    'f114': '购建固定资产、无形资产和其他长期资产支付的现金',
    'f115': '投资支付的现金',  # 'cashInvestment',
    'f116': '取得子公司及其他营业单位支付的现金净额',  # 'acquisitionOfNetCashPaidBySubsidiariesAndOtherBusinessUnits',
    'f117': '支付其他与投资活动有关的现金',  # 'otherCashPaidRelatingToInvestingActivities',
    'f118': '投资活动现金流出小计',  # 'cashOutflowsFromInvestmentActivities',
    'f119': '投资活动产生的现金流量净额',  # 'netCashFlowsFromInvestingActivities',
    # 4.3 筹资活动 Financing
    'f120': '吸收投资收到的现金',  # 'cashReceivedFromInvestors',
    'f121': '取得借款收到的现金',  # 'cashFromBorrowings',
    'f122': '收到其他与筹资活动有关的现金',  # 'otherCashReceivedRelatingToFinancingActivities',
    'f123': '筹资活动现金流入小计',  # 'cashInflowsFromFinancingActivities',
    'f124': '偿还债务支付的现金',  # 'cashPaymentsOfAmountBorrowed',
    'f125': '分配股利、利润或偿付利息支付的现金',  # 'cashPaymentsForDistrbutionOfDividendsOrProfits',
    'f126': '支付其他与筹资活动有关的现金',  # 'otherCashPaymentRelatingToFinancingActivities',
    'f127': '筹资活动现金流出小计',  # 'cashOutflowsFromFinancingActivities',
    'f128': '筹资活动产生的现金流量净额',  # 'netCashFlowsFromFinancingActivities',
    # 4.4 汇率变动
    'f129': '四、汇率变动对现金的影响',  # 'effectOfForeignExchangRateChangesOnCash',
    'f130': '四(2)、其他原因对现金的影响',  # 'effectOfOtherReasonOnCash',
    # 4.5 现金及现金等价物净增加
    'f131': '五、现金及现金等价物净增加额',  # 'netIncreaseInCashAndCashEquivalents',
    'f132': '期初现金及现金等价物余额',  # 'initialCashAndCashEquivalentsBalance',
    # 4.6 期末现金及现金等价物余额
    'f133': '期末现金及现金等价物余额',  # 'theFinalCashAndCashEquivalentsBalance',
    # 4.x 补充项目 Supplementary Schedule：
    # 现金流量附表项目    Indirect Method
    # 4.x.1 将净利润调节为经营活动现金流量 Convert net profit to cash flow from operating activities
    'f134': '净利润',  # 'netProfitFromOperatingActivities',
    'f135': '资产减值准备',  # 'provisionForAssetsLosses',
    'f136': '固定资产折旧、油气资产折耗、生产性生物资产折旧',  # 'depreciationForFixedAssets',
    'f137': '无形资产摊销',  # 'amortizationOfIntangibleAssets',
    'f138': '长期待摊费用摊销',  # 'amortizationOfLong-termDeferredExpenses',
    'f139': '处置固定资产、无形资产和其他长期资产的损失',  # 'lossOfDisposingFixedAssetsIntangibleAssetsAndOtherLong-termAssets',
    'f140': '固定资产报废损失',  # 'scrapLossOfFixedAssets',
    'f141': '公允价值变动损失',  # 'lossFromFairValueChange',
    'f142': '财务费用',  # 'financialExpenses',
    'f143': '投资损失',  # 'investmentLosses',
    'f144': '递延所得税资产减少',  # 'decreaseOfDeferredTaxAssets',
    'f145': '递延所得税负债增加',  # 'increaseOfDeferredTaxLiabilities',
    'f146': '存货的减少',  # 'decreaseOfInventory',
    'f147': '经营性应收项目的减少',  # 'decreaseOfOperationReceivables',
    'f148': '经营性应付项目的增加',  # 'increaseOfOperationPayables',
    'f149': '其他',  # 'others',
    'f150': '经营活动产生的现金流量净额2',  # 'netCashFromOperatingActivities2',
    # 4.x.2 不涉及现金收支的投资和筹资活动 Investing and financing activities not involved in cash
    'f151': '债务转为资本',  # 'debtConvertedToCSapital',
    'f152': '一年内到期的可转换公司债券',  # 'convertibleBondMaturityWithinOneYear',
    'f153': '融资租入固定资产',  # 'leaseholdImprovements',
    # 4.x.3 现金及现金等价物净增加情况 Net increase of cash and cash equivalents
    'f154': '现金的期末余额',  # 'cashEndingBal',
    'f155': '现金的期初余额',  # 'cashBeginingBal',
    'f156': '现金等价物的期末余额',  # 'cashEquivalentsEndingBal',
    'f157': '现金等价物的期初余额',  # 'cashEquivalentsBeginningBal',
    'f158': '现金及现金等价物净增加额',  # 'netIncreaseOfCashAndCashEquivalents',
    # 5.偿债能力分析
    'f159': '流动比率',  # 'currentRatio',  # 流动资产/流动负债
    'f160': '速动比率',  # 'acidTestRatio',  # (流动资产-存货）/流动负债
    'f161': '现金比率(%)',  # 'cashRatio',  # (货币资金+有价证券)÷流动负债
    'f162': '利息保障倍数',  # 'interestCoverageRatio',  # (利润总额+财务费用（仅指利息费用部份）)/利息费用
    'f163': '非流动负债比率(%)',  # 'noncurrentLiabilitiesRatio',
    'f164': '流动负债比率(%)',  # 'currentLiabilitiesRatio',
    'f165': '现金到期债务比率(%)',  # 'cashDebtRatio',  # 企业经营现金净流入/(本期到期长期负债+本期应付票据)
    'f166': '有形资产净值债务率(%)',  # 'debtToTangibleAssetsRatio',
    'f167': '权益乘数(%)',  # 'equityMultiplier',  # 资产总额/股东权益总额
    'f168': '股东的权益/负债合计(%)',  # 'equityDebtRatio',  # 权益负债率
    'f169': '有形资产/负债合计(%)',  # 'tangibleAssetDebtRatio ',  # 有形资产负债率
    'f170': '经营活动产生的现金流量净额/负债合计(%)',  # 'netCashFlowsFromOperatingActivitiesDebtRatio',
    'f171': 'EBITDA/负债合计(%)',  # 'EBITDA/Liabilities',
    # 6.经营效率分析
    # 销售收入÷平均应收账款=销售收入\(0.5 x(应收账款期初+期末))
    'f172': '应收帐款周转率',  # 'turnoverRatioOfReceivable;',
    'f173': '存货周转率',  # 'turnoverRatioOfInventory',
    # (存货周转天数+应收帐款周转天数-应付帐款周转天数+预付帐款周转天数-预收帐款周转天数)/365
    'f174': '运营资金周转率',  # 'turnoverRatioOfOperatingAssets',
    'f175': '总资产周转率',  # 'turnoverRatioOfTotalAssets',
    'f176': '固定资产周转率',  # 'turnoverRatioOfFixedAssets',  # 企业销售收入与固定资产净值的比率
    'f177': '应收帐款周转天数',  # 'daysSalesOutstanding',  # 企业从取得应收账款的权利到收回款项、转换为现金所需要的时间
    'f178': '存货周转天数',  # 'daysSalesOfInventory',  # 企业从取得存货开始，至消耗、销售为止所经历的天数
    'f179': '流动资产周转率',  # 'turnoverRatioOfCurrentAssets',  # 流动资产周转率(次)=主营业务收入/平均流动资产总额
    'f180': '流动资产周转天数',  # 'daysSalesofCurrentAssets',
    'f181': '总资产周转天数',  # 'daysSalesofTotalAssets',
    'f182': '股东权益周转率',  # 'equityTurnover',  # 销售收入/平均股东权益
    # 7.发展能力分析
    'f183': '营业收入增长率(%)',  # 'operatingIncomeGrowth',
    'f184': '净利润增长率(%)',  # 'netProfitGrowthRate',  # NPGR  利润总额－所得税
    'f185': '净资产增长率(%)',  # 'netAssetsGrowthRate',
    'f186': '固定资产增长率(%)',  # 'fixedAssetsGrowthRate',
    'f187': '总资产增长率(%)',  # 'totalAssetsGrowthRate',
    'f188': '投资收益增长率(%)',  # 'investmentIncomeGrowthRate',
    'f189': '营业利润增长率(%)',  # 'operatingProfitGrowthRate',
    'f190': '暂无',  # 'None1',
    'f191': '暂无',  # 'None2',
    'f192': '暂无',  # 'None3',
    # 8.获利能力分析
    'f193': '成本费用利润率(%)',  # 'rateOfReturnOnCost',
    'f194': '营业利润率',  # 'rateOfReturnOnOperatingProfit',
    'f195': '营业税金率',  # 'rateOfReturnOnBusinessTax',
    'f196': '营业成本率',  # 'rateOfReturnOnOperatingCost',
    'f197': '净资产收益率',  # 'rateOfReturnOnCommonStockholdersEquity',
    'f198': '投资收益率',  # 'rateOfReturnOnInvestmentIncome',
    'f199': '销售净利率(%)',  # 'rateOfReturnOnNetSalesProfit',
    'f200': '总资产报酬率',  # 'rateOfReturnOnTotalAssets',
    'f201': '净利润率',  # 'netProfitMargin',
    'f202': '销售毛利率(%)',  # 'rateOfReturnOnGrossProfitFromSales',
    'f203': '三费比重',  # 'threeFeeProportion',
    'f204': '管理费用率',  # 'ratioOfChargingExpense',
    'f205': '财务费用率',  # 'ratioOfFinancialExpense',
    'f206': '扣除非经常性损益后的净利润',  # 'adjusted_profit',
    'f207': '息税前利润(EBIT)',  # 'EBIT',
    'f208': '息税折旧摊销前利润(EBITDA)',  # 'EBITDA',
    'f209': 'EBITDA/营业总收入(%)',  # 'EBITDA/GrossRevenueRate',
    # 9.资本结构分析
    'f210': '资产负债率(%)',  # 'assetsLiabilitiesRatio',
    'f211': '流动资产比率',  # 'currentAssetsRatio',  # 期末的流动资产除以所有者权益
    'f212': '货币资金比率',  # 'monetaryFundRatio',
    'f213': '存货比率',  # 'inventoryRatio',
    'f214': '固定资产比率',  # 'fixedAssetsRatio',
    'f215': '负债结构比',  # 'liabilitiesStructureRatio',
    'f216': '归属于母公司股东权益/全部投入资本(%)',  # 'shareholdersOwnershipOfAParentCompany/TotalCapital',
    'f217': '股东的权益/带息债务(%)',  # 'shareholdersInterest/InterestRateDebtRatio',
    'f218': '有形资产/净债务(%)',  # 'tangibleAssets/NetDebtRatio',
    # 10.现金流量分析
    'f219': '每股经营性现金流(元)',  # 'operatingCashFlowPerShare',
    'f220': '营业收入现金含量(%)',  # 'cashOfOperatingIncome',
    'f221': '经营活动产生的现金流量净额/经营活动净收益(%)',  # 'netOperatingCashFlow/netOperationProfit',
    'f222': '销售商品提供劳务收到的现金/营业收入(%)',  # 'cashFromGoodsSales/OperatingRevenue',
    'f223': '经营活动产生的现金流量净额/营业收入',  # 'netOperatingCashFlow/OperatingRevenue',
    'f224': '资本支出/折旧和摊销',  # 'capitalExpenditure/DepreciationAndAmortization',
    'f225': '每股现金流量净额(元)',  # 'netCashFlowPerShare',
    'f226': '经营净现金比率（短期债务）',  # 'operatingCashFlow/ShortTermDebtRatio',
    'f227': '经营净现金比率（全部债务）',  # 'operatingCashFlow/LongTermDebtRatio',
    'f228': '经营活动现金净流量与净利润比率',  # 'cashFlowRateAndNetProfitRatioOfOperatingActivities',
    'f229': '全部资产现金回收率',  # 'cashRecoveryForAllAssets',
    # 11. 单季度财务指标
    'f230': '营业收入',  # 'operatingRevenueSingle',
    'f231': '营业利润',  # 'operatingProfitSingle',
    'f232': '归属于母公司所有者的净利润',  # 'netProfitBelongingToTheOwnerOfTheParentCompanySingle',
    'f233': '扣除非经常性损益后的净利润',  # 'netProfitAfterExtraordinaryGainsAndLossesSingle',
    'f234': '经营活动产生的现金流量净额',  # 'netCashFlowsFromOperatingActivitiesSingle',
    'f235': '投资活动产生的现金流量净额',  # 'netCashFlowsFromInvestingActivitiesSingle',
    'f236': '筹资活动产生的现金流量净额',  # 'netCashFlowsFromFinancingActivitiesSingle',
    'f237': '现金及现金等价物净增加额',  # 'netIncreaseInCashAndCashEquivalentsSingle',
    # 12.股本股东
    'f238': '总股本',  # 'totalCapital',
    'f239': '已上市流通A股',  # 'listedAShares',
    'f240': '已上市流通B股',  # 'listedBShares',
    'f241': '已上市流通H股',  # 'listedHShares',
    'f242': '股东人数(户)',  # 'numberOfShareholders',
    'f243': '第一大股东的持股数量',  # 'theNumberOfFirstMajorityShareholder',
    'f244': '十大流通股东持股数量合计(股)',  # 'totalNumberOfTopTenCirculationShareholders',
    'f245': '十大股东持股数量合计(股)',  # 'totalNumberOfTopTenMajorShareholders',
    # 13.机构持股
    'f246': '机构总量（家）',  # 'institutionNumber',
    'f247': '机构持股总量(股)',  # 'institutionShareholding',
    'f248': 'QFII机构数',  # 'QFIIInstitutionNumber',
    'f249': 'QFII持股量',  # 'QFIIShareholding',
    'f250': '券商机构数',  # 'brokerNumber',
    'f251': '券商持股量',  # 'brokerShareholding',
    'f252': '保险机构数',  # 'securityNumber',
    'f253': '保险持股量',  # 'securityShareholding',
    'f254': '基金机构数',  # 'fundsNumber',
    'f255': '基金持股量',  # 'fundsShareholding',
    'f256': '社保机构数',  # 'socialSecurityNumber',
    'f257': '社保持股量',  # 'socialSecurityShareholding',
    'f258': '私募机构数',  # 'privateEquityNumber',
    'f259': '私募持股量',  # 'privateEquityShareholding',
    'f260': '财务公司机构数',  # 'financialCompanyNumber',
    'f261': '财务公司持股量',  # 'financialCompanyShareholding',
    'f262': '年金机构数',  # 'pensionInsuranceAgencyNumber',
    'f263': '年金持股量',  # 'pensionInsuranceAgencyShareholfing',
    # 14.新增指标
    # [注：季度报告中，若股东同时持有非流通A股性质的股份(如同时持有流通A股和流通B股），取的是包含同时持有非流通A股性质的流通股数]
    'f264': '十大流通股东中持有A股合计(股)',  # 'totalNumberOfTopTenCirculationShareholders',
    'f265': '第一大流通股东持股量(股)',  # 'firstLargeCirculationShareholdersNumber',
    # [注：1.自由流通股=已流通A股-十大流通股东5%以上的A股；
    #     2.季度报告中，若股东同时持有非流通A股性质的股份(如同时持有流通A股和流通H股）.
    #     ，5%以上的持股取的是不包含同时持有非流通A股性质的流通股数，结果可能偏大；
    #     3.指标按报告期展示，新股在上市日的下个报告期才有数据]
    'f266': '自由流通股(股)',  # 'freeCirculationStock',
    'f267': '受限流通A股(股)',  # 'limitedCirculationAShares',
    'f268': '一般风险准备(金融类)',  # 'generalRiskPreparation',
    'f269': '其他综合收益(利润表)',  # 'otherComprehensiveIncome',
    'f270': '综合收益总额(利润表)',  # 'totalComprehensiveIncome',
    'f271': '归属于母公司股东权益(资产负债表)',  # 'shareholdersOwnershipOfAParentCompany ',
    'f272': '银行机构数(家)(机构持股)',  # 'bankInstutionNumber',
    'f273': '银行持股量(股)(机构持股)',  # 'bankInstutionShareholding',
    'f274': '一般法人机构数(家)(机构持股)',  # 'corporationNumber',
    'f275': '一般法人持股量(股)(机构持股)',  # 'corporationShareholding',
    'f276': '近一年净利润(元)',  # 'netProfitLastYear',
    'f277': '信托机构数(家)(机构持股)',  # 'trustInstitutionNumber',
    'f278': '信托持股量(股)(机构持股)',  # 'trustInstitutionShareholding',
    'f279': '特殊法人机构数(家)(机构持股)',  # 'specialCorporationNumber',
    'f280': '特殊法人持股量(股)(机构持股)',  # 'specialCorporationShareholding',
    'f281': '加权净资产收益率(每股指标)',  # 'weightedROE',
    'f282': '扣非每股收益(单季度财务指标)',  # 'nonEPSSingle',
    'f283': '最近一年营业收入()',  # 'lastYearOperatingIncome',
    'f284': '国家队持股数量(万股)',  # 'nationalTeamShareholding',
    # [注：本指标统计包含汇金公司、证金公司、外汇管理局旗下投资平台、国家队基金、国开、养老金以及中科汇通等国家队机构持股数量]
    'f285': '业绩预告-本期净利润同比增幅下限%',  # 'PF_theLowerLimitoftheYearonyearGrowthofNetProfitForThePeriod',
    # [注：指标285至294展示未来一个报告期的数据。例，3月31日至6月29日这段时间内展示的是中报的数据；如果最新的财务报告后面有多个报告期的业绩预告/快报，只能展示最新的财务报告后面的一个报告期的业绩预告/快报]
    'f286': '业绩预告-本期净利润同比增幅上限%',  # 'PF_theHigherLimitoftheYearonyearGrowthofNetProfitForThePeriod',
    'f287': '业绩快报-归母净利润',  # 'PE_returningtotheMothersNetProfit',
    'f288': '业绩快报-扣非净利润',  # 'PE_Non-netProfit',
    'f289': '业绩快报-总资产',  # 'PE_TotalAssets',
    'f290': '业绩快报-净资产',  # 'PE_NetAssets',
    'f291': '业绩快报-每股收益',  # 'PE_EPS',
    'f292': '业绩快报-摊薄净资产收益率',  # 'PE_DilutedROA',
    'f293': '业绩快报-加权净资产收益率',  # 'PE_WeightedROE',
    'f294': '业绩快报-每股净资产',  # 'PE_NetAssetsperShare',
    'f295': '应付票据及应付账款(资产负债表)',  # 'BS_NotesPayableandAccountsPayable',
    'f296': '应收票据及应收账款(资产负债表)',  # 'BS_NotesReceivableandAccountsReceivable',
    'f297': '递延收益(资产负债表)',  # 'BS_DeferredIncome',
    'f298': '其他综合收益(资产负债表)',  # 'BS_OtherComprehensiveIncome',
    'f299': '其他权益工具(资产负债表)',  # 'BS_OtherEquityInstruments',
    'f300': '其他收益(利润表)',  # 'IS_OtherIncome',
    'f301': '资产处置收益(利润表)',  # 'IS_AssetDisposalIncome',
    'f302': '持续经营净利润(利润表)',  # 'IS_NetProfitforContinuingOperations',
    'f303': '终止经营净利润(利润表)',  # 'IS_NetProfitforTerminationOperations',
    'f304': '研发费用(利润表)',  # 'IS_R&DExpense',
    'f305': '其中,  #利息费用(利润表-财务费用)',  # 'IS_InterestExpense',
    'f306': '其中,  #利息收入(利润表-财务费用)',  # 'IS_InterestIncome',
    'f307': '近一年经营活动现金流净额',  # 'netCashFlowfromOperatingActivitiesinthepastyear',
    'f308': '近一年归母净利润',  # 'Net_profit_attributable to the mother in the recent year',
    'f309': '近一年扣非净利润',  # 'Nearly_one_year_net profit after deduction',
    'f310': '近一年现金净流量',  # 'Net cash flow in the past year',
    'f311': '基本每股收益(单季度)',  # 'Basic earnings per share (single quarter)',
    'f312': '营业总收入(单季度)',  # 'Total operating income (single quarter) ',
    'f313': '业绩预告公告日期',  # 'Announcement date of earnings forecast',
    'f314': '财报公告日期',  # 'earnings announcement date',
    'f315': '业绩快报公告日期',  # 'Earnings Update Announcement Date',
    'f316': '近一年投资活动现金流净额',  # 'Net cash flow from investing activities in the past year ',
    'f317': '业绩预告-本期净利润下限',  # 'Forecast of performance',
    'f318': '业绩预告-本期净利润上限',  # 'Forecast of Results - Current Period Net Income Cap',
    'f319': '营业总收入TTM',  # 'Total Operating Income TTM',
    'f320': '员工总数(人)',  # 'Total number of employees (people)',
    'f321': '每股企业自由现金流',  # 'Corporate Free Cash Flow per Share',
    'f322': '每股股东自由现金流',  # 'Free cash flow per share for shareholders',
    'f323': '备用323',  # 'unknown323',
    'f324': '备用324',  # 'unknown324',
    'f325': '备用325',  # 'unknown325',
    'f326': '备用326',  # 'unknown326',
    'f327': '备用327',  # 'unknown327',
    'f328': '备用328',  # 'unknown328',
    'f329': '备用329',  # 'unknown329',
    'f330': '备用330',  # 'unknown330',
    'f331': '备用331',  # 'unknown331',
    'f332': '备用332',  # 'unknown332',
    'f333': '备用333',  # 'unknown333',
    'f334': '备用334',  # 'unknown334',
    'f335': '备用335',  # 'unknown335',
    'f336': '备用336',  # 'unknown336',
    'f337': '备用337',  # 'unknown337',
    'f338': '备用338',  # 'unknown338',
    'f339': '备用339',  # 'unknown339',
    'f340': '备用340',  # 'unknown340',
    'f341': '备用341',  # 'unknown341',
    'f342': '备用342',  # 'unknown342',
    'f343': '备用343',  # 'unknown343',
    'f344': '备用344',  # 'unknown344',
    'f345': '备用345',  # 'unknown345',
    'f346': '备用346',  # 'unknown346',
    'f347': '备用347',  # 'unknown347',
    'f348': '备用348',  # 'unknown348',
    'f349': '备用349',  # 'unknown349',
    'f350': '备用350',  # 'unknown350',
    'f351': '备用351',  # 'unknown351',
    'f352': '备用352',  # 'unknown352',
    'f353': '备用353',  # 'unknown353',
    'f354': '备用354',  # 'unknown354',
    'f355': '备用355',  # 'unknown355',
    'f356': '备用356',  # 'unknown356',
    'f357': '备用357',  # 'unknown357',
    'f358': '备用358',  # 'unknown358',
    'f359': '备用359',  # 'unknown359',
    'f360': '备用360',  # 'unknown360',
    'f361': '备用361',  # 'unknown361',
    'f362': '备用362',  # 'unknown362',
    'f363': '备用363',  # 'unknown363',
    'f364': '备用364',  # 'unknown364',
    'f365': '备用365',  # 'unknown365',
    'f366': '备用366',  # 'unknown366',
    'f367': '备用367',  # 'unknown367',
    'f368': '备用368',  # 'unknown368',
    'f369': '备用369',  # 'unknown369',
    'f370': '备用370',  # 'unknown370',
    'f371': '备用371',  # 'unknown371',
    'f372': '备用372',  # 'unknown372',
    'f373': '备用373',  # 'unknown373',
    'f374': '备用374',  # 'unknown374',
    'f375': '备用375',  # 'unknown375',
    'f376': '备用376',  # 'unknown376',
    'f377': '备用377',  # 'unknown377',
    'f378': '备用378',  # 'unknown378',
    'f379': '备用379',  # 'unknown379',
    'f380': '备用380',  # 'unknown380',
    'f381': '备用381',  # 'unknown381',
    'f382': '备用382',  # 'unknown382',
    'f383': '备用383',  # 'unknown383',
    'f384': '备用384',  # 'unknown384',
    'f385': '备用385',  # 'unknown385',
    'f386': '备用386',  # 'unknown386',
    'f387': '备用387',  # 'unknown387',
    'f388': '备用388',  # 'unknown388',
    'f389': '备用389',  # 'unknown389',
    'f390': '备用390',  # 'unknown390',
    'f391': '备用391',  # 'unknown391',
    'f392': '备用392',  # 'unknown392',
    'f393': '备用393',  # 'unknown393',
    'f394': '备用394',  # 'unknown394',
    'f395': '备用395',  # 'unknown395',
    'f396': '备用396',  # 'unknown396',
    'f397': '备用397',  # 'unknown397',
    'f398': '备用398',  # 'unknown398',
    'f399': '备用399',  # 'unknown399',
    'f400': '备用400',  # 'unknown400',
    # 资产负债表新增指标---
    'f401': '专项储备',  # 'Special reserve',
    'f402': '结算备付金',  # 'Settlement provision',
    'f403': '拆出资金',  # 'Funds removed',
    'f404': '发放贷款及垫款',  # 'Loans and advances granted',
    'f405': '衍生金融资产',  # 'Derivative financial assets',
    'f406': '应收保费',  # 'Premium receivable',
    'f407': '应收分保账款',  # 'Sub-insurance receivables',
    'f408': '应收分保合同准备金',  # 'Provision for sub-insurance contracts receivable',
    'f409': '买入返售金融资产',  # 'Buy-back financial assets',
    'f410': '划分为持有待售的资产',  # 'Assets classified as held for sale',
    'f411': '发放贷款及垫款',  # 'Loans and advances granted',
    'f412': '向中央银行借款',  # 'Borrowings from central banks',
    'f413': '吸收存款及同业存放',  # 'Absorption of deposits and interbank deposits',
    'f414': '拆入资金',  # 'Funds borrowed',
    'f415': '衍生金融负债',  # 'Derivative financial liabilities',
    'f416': '卖出回购金融资产款',  # 'Sale of repurchase financial assets',
    'f417': '应付手续费及佣金',  # 'Fees and commissions payable',
    'f418': '应付分保账款',  # 'Payables to sub-insurance accounts',
    'f419': '保险合同准备金',  # 'Provision for insurance contracts',
    'f420': '代理买卖证券款',  # 'Agency securities trading',
    'f421': '代理承销证券款',  # 'Agency underwriting of securities',
    'f422': '划分为持有待售的负债',  # 'Liabilities classified as held for sale',
    'f423': '预计负债',  # 'Projected liabilities',
    'f424': '递延收益',  # 'Deferred income',
    'f425': '其中,  #优先股',  # 'Deferred incomeOf which,  #Preferred stock',
    'f426': '永续债非流动负债科目',  # 'Perpetual bonds',
    'f427': '长期应付职工薪酬',  # 'Long-term employee compensation payable',
    'f428': '其中,  #优先股',  # 'Long-term employee compensation payable Of which,  #Preferred shares',
    'f429': '永续债所有者权益科目',  # 'Perpetual debentures Owners equity account',
    'f430': '债权投资',  # 'Debt investments',
    'f431': '其他债权投资',  # 'Other debt investments',
    'f432': '其他权益工具投资',  # 'Investment in other equity instruments',
    'f433': '其他非流动金融资产',  # 'Other non-current financial assets',
    'f434': '合同负债',  # 'Contract liabilities',
    'f435': '合同资产',  # 'Contract assets',
    'f436': '其他资产',  # 'Other assets',
    'f437': '应收款项融资',  # 'Financing of receivables',
    'f438': '使用权资产',  # 'Right-of-use assets',
    'f439': '租赁负债',  # 'Lease liabilities',
    'f440': '备用440',  # 'unknown440',
    'f441': '备用441',  # 'unknown441',
    'f442': '备用442',  # 'unknown442',
    'f443': '备用443',  # 'unknown443',
    'f444': '备用444',  # 'unknown444',
    'f445': '备用445',  # 'unknown445',
    'f446': '备用446',  # 'unknown446',
    'f447': '备用447',  # 'unknown447',
    'f448': '备用448',  # 'unknown448',
    'f449': '备用449',  # 'unknown449',
    'f450': '备用450',  # 'unknown450',
    'f451': '备用451',  # 'unknown451',
    'f452': '备用452',  # 'unknown452',
    'f453': '备用453',  # 'unknown453',
    'f454': '备用454',  # 'unknown454',
    'f455': '备用455',  # 'unknown455',
    'f456': '备用456',  # 'unknown456',
    'f457': '备用457',  # 'unknown457',
    'f458': '备用458',  # 'unknown458',
    'f459': '备用459',  # 'unknown459',
    'f460': '备用460',  # 'unknown460',
    'f461': '备用461',  # 'unknown461',
    'f462': '备用462',  # 'unknown462',
    'f463': '备用463',  # 'unknown463',
    'f464': '备用464',  # 'unknown464',
    'f465': '备用465',  # 'unknown465',
    'f466': '备用466',  # 'unknown466',
    'f467': '备用467',  # 'unknown467',
    'f468': '备用468',  # 'unknown468',
    'f469': '备用469',  # 'unknown469',
    'f470': '备用470',  # 'unknown470',
    'f471': '备用471',  # 'unknown471',
    'f472': '备用472',  # 'unknown472',
    'f473': '备用473',  # 'unknown473',
    'f474': '备用474',  # 'unknown474',
    'f475': '备用475',  # 'unknown475',
    'f476': '备用476',  # 'unknown476',
    'f477': '备用477',  # 'unknown477',
    'f478': '备用478',  # 'unknown478',
    'f479': '备用479',  # 'unknown479',
    'f480': '备用480',  # 'unknown480',
    'f481': '备用481',  # 'unknown481',
    'f482': '备用482',  # 'unknown482',
    'f483': '备用483',  # 'unknown483',
    'f484': '备用484',  # 'unknown484',
    'f485': '备用485',  # 'unknown485',
    'f486': '备用486',  # 'unknown486',
    'f487': '备用487',  # 'unknown487',
    'f488': '备用488',  # 'unknown488',
    'f489': '备用489',  # 'unknown489',
    'f490': '备用490',  # 'unknown490',
    'f491': '备用491',  # 'unknown491',
    'f492': '备用492',  # 'unknown492',
    'f493': '备用493',  # 'unknown493',
    'f494': '备用494',  # 'unknown494',
    'f495': '备用495',  # 'unknown495',
    'f496': '备用496',  # 'unknown496',
    'f497': '备用497',  # 'unknown497',
    'f498': '备用498',  # 'unknown498',
    'f499': '备用499',  # 'unknown499',
    'f500': '备用500',  # 'unknown500',
    'f501': '稀释每股收益',  # 'Diluted earnings per share',
    'f502': '营业总收入',  # "Total operating income",
    'f503': '汇兑收益',  # 'Foreign exchange gain',
    'f504': '其中,  #归属于母公司综合收益',  # 'Comprehensive income attributable to parent company',
    'f505': '其中,  #归属于少数股东综合收益',  # 'Comprehensive income attributable to minority shareholders',
    'f506': '利息收入',  # 'Interest income',
    'f507': '已赚保费',  # 'Premiums earned',
    'f508': '手续费及佣金收入',  # 'Fee and commission income',
    'f509': '利息支出',  # 'Interest expense',
    'f510': '手续费及佣金支出',  # 'Handling and commission expenses',
    'f511': '退保金',  # 'Surrender premiums',
    'f512': '赔付支出净额',  # 'Net payout expenses',
    'f513': '提取保险合同准备金净额',  # 'Net withdrawal of insurance contract reserve',
    'f514': '保单红利支出',  # 'Policy dividend expense',
    'f515': '分保费用',  # 'Ceding expenses',
    'f516': '其中,  #非流动资产处置利得',  # 'Gain on disposal of non-current assets',
    'f517': '信用减值损失',  # 'Credit impairment loss',
    'f518': '净敞口套期收益',  # 'Net exposure hedging gain',
    'f519': '营业总成本',  # 'Total operating costs',
    'f520': '信用减值损失',  # 'Credit impairment loss',
    'f521': '资产减值损失',  # 'Impairment loss on assets',
    'f522': '备用522',  # 'unknown522',
    'f523': '备用523',  # 'unknown523',
    'f524': '备用524',  # 'unknown524',
    'f525': '备用525',  # 'unknown525',
    'f526': '备用526',  # 'unknown526',
    'f527': '备用527',  # 'unknown527',
    'f528': '备用528',  # 'unknown528',
    'f529': '备用529',  # 'unknown529',
    'f530': '备用530',  # 'unknown530',
    'f531': '备用531',  # 'unknown531',
    'f532': '备用532',  # 'unknown532',
    'f533': '备用533',  # 'unknown533',
    'f534': '备用534',  # 'unknown534',
    'f535': '备用535',  # 'unknown535',
    'f536': '备用536',  # 'unknown536',
    'f537': '备用537',  # 'unknown537',
    'f538': '备用538',  # 'unknown538',
    'f539': '备用539',  # 'unknown539',
    'f540': '备用540',  # 'unknown540',
    'f541': '备用541',  # 'unknown541',
    'f542': '备用542',  # 'unknown542',
    'f543': '备用543',  # 'unknown543',
    'f544': '备用544',  # 'unknown544',
    'f545': '备用545',  # 'unknown545',
    'f546': '备用546',  # 'unknown546',
    'f547': '备用547',  # 'unknown547',
    'f548': '备用548',  # 'unknown548',
    'f549': '备用549',  # 'unknown549',
    'f550': '备用550',  # 'unknown550',
    'f551': '备用551',  # 'unknown551',
    'f552': '备用552',  # 'unknown552',
    'f553': '备用553',  # 'unknown553',
    'f554': '备用554',  # 'unknown554',
    'f555': '备用555',  # 'unknown555',
    'f556': '备用556',  # 'unknown556',
    'f557': '备用557',  # 'unknown557',
    'f558': '备用558',  # 'unknown558',
    'f559': '备用559',  # 'unknown559',
    'f560': '备用560',  # 'unknown560',
    'f561': ',  #其他原因对现金的影响2',  # 'Add,  #Effect of other causes on cash2',
    'f562': '客户存款和同业存放款项净增加额',  # 'Net increase in customer deposits and interbank deposits',
    'f563': '向中央银行借款净增加额',  # 'Net increase in borrowings from central banks',
    'f564': '向其他金融机构拆入资金净增加额',  # 'Net increase in funds borrowed from other financial institutions',
    'f565': '收到原保险合同保费取得的现金',  # 'Cash received from premiums on original insurance contracts',
    'f566': '收到再保险业务现金净额',  # 'Net cash received from reinsurance business',
    'f567': '保户储金及投资款净增加额',  # 'Net increase in policyholders deposits and investment funds',
    'f568': '处置以公允价值计量且其变动计入当期损益的金融资产净增加额',
    'f569': '收取利息、手续费及佣金的现金',  # 'Cash received from interest, fees and commissions',
    'f570': '拆入资金净增加额',  # 'Net increase in funds transferred in ',
    'f571': '回购业务资金净增加额',  # 'Net increase in funds from repo business',
    'f572': '客户贷款及垫款净增加额',  # 'Net increase in loans and advances to customers',
    'f573': '存放中央银行和同业款项净增加额',  # 'Net increase in deposits with central banks and interbank',
    'f574': '支付原保险合同赔付款项的现金',  # 'Cash paid for claims on original insurance contracts',
    'f575': '支付利息、手续费及佣金的现金',  # 'Cash paid for interest, fees and commissions',
    'f576': '支付保单红利的现金',  # 'Cash paid for policy dividends',
    'f577': '其中,  #子公司吸收少数股东投资收到的现金',  # 'cash received from minority shareholders investment in subsidiaries',
    'f578': '其中,  #子公司支付给少数股东的股利利润',  # 'Dividends and profits paid by subsidiaries to minority shareholders',
    'f579': '投资性房地产的折旧及摊销',  # 'Depreciation and amortization of investment properties',
    'f580': '信用减值损失',  # 'Credit impairment loss'
}


if __name__ == '__main__':
    # df = get_financial_data(['000001', '601567'], ['001', '002', '095'],
    # watch_date='2020-04-22')
    # df = get_history_fundamentals(['000001', '601567'], ['001', '002', '095'],
    # watch_date='2020-04-22', count=10, interval='1q')
    df = get_fundamentals_continuously('601567', fields=['001', '002', '095'], end_date='2020-04-22', count=300)
    print(df)
