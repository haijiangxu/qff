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
从数据库中查询股票价格数据
"""

import pandas as pd
from typing import Dict, Optional
from datetime import datetime
from bson.regex import Regex
from qff.tools.mongo import DATABASE
from qff.tools.date import get_pre_trade_day, is_trade_day, get_real_trade_date, util_date_valid, util_time_valid
from qff.tools.utils import util_code_tolist
from qff.tools.logs import log
from qff.frame.context import context, RUN_STATUS

__all__ = ['get_price', 'get_bars', 'get_stock_list', 'get_stock_name', 'get_index_stocks', 'get_block_stock',
           'get_mtss', 'get_all_securities', 'get_security_info', 'get_st_stock', 'get_paused_stock',
           'get_stock_block', 'history', 'attribute_history', 'get_index_name', 'get_industry_stocks']


def get_price(security, start=None, end=None, freq='daily', fields=None, skip_paused=False, fq='pre', count=None,
              market='stock'):
    """
    获取历史数据，可查询一支或者多个标的的行情数据, 按天或者按分钟，返回数据格式为 DataFrame

    :param security: 单只标的代码或标的代码列表，标的为股票、指数、ETF等，本参数不能为空.

    :param count: 返回的结果集的行数, 即表示获取 end_date 之前几个freq的数据，与 start 二选一，不可同时使用.
    :param start: 查询开始时间,与 count 二选一，不可同时使用.

        1. 如果 count 和 start_date 参数都没有, 则 start 等于 end.
        2. 如果 count 和 start_date 参数都设置, 则 start 生效，返回结果会截取最后count数量的记录。
        3. 当取分钟数据时, 时间可以精确到分钟, 比如: 传入datetime.datetime(2015, 1, 1, 10, 0, 0) 或者 '2015-01-01 10:00:00'
        4. 当取分钟数据时, 如果只传入日期, 则日内时间是当日的 09:30:00 - 15:00:00
        5. 当取天数据时, 传入的日内时间会被忽略

    :param end: 查询结束时间, 默认是当前日期, **注意:** 当取分钟数据时, 如果 end 只有日期,则日内时间等同于 15:00:00.

    :param freq: 单位时间长度, 现在支持['daily', '1d', 'day', '1min', '5min', '15min', '30min', '60min', '1m', '5m',
        '15m', '30m', '60m']，

    :param fields: 选择要获取的行情数据字段, 默认是None,表示['open', 'close', 'high', 'low', 'vol','amount']
        这几个标准字段, 指数另外支持[’up_count', 'down_count']。

    :param skip_paused: 是否跳过不交易日期(包括停牌, 未上市或者退市后的日期). 如果不跳过, 停牌时会使用停牌前收盘价数据填充。

        **关于停牌:** 因为此API可以获取多只股票的数据, 可能有的股票停牌有的没有, 为了保持时间轴的一致,我们默认没有跳过停牌的日期

    :param fq: 复权选项: 'pre', 前复权； None,不复权, 返回实际价格；'post',后复权

    :param market: 市场类型，目前支持[“stock", ”index","ETF"], 默认“stock".

    :type security: str or list
    :type count: int
    :type start: str、datetime.datetime or datetime.date
    :type end: str、datetime.datetime or datetime.date
    :type freq: str
    :type fields: str or list
    :type skip_paused: bool
    :type fq: str or None
    :type market: str

    :return: 请注意, 为了方便比较一只股票的多个属性, 同时也满足对比多只股票的一个属性的需求, 我们在security参数是一只股票和多只股票
        时返回的结构完全不一样.

        * 如果是一支股票, 则返回[pandas.DataFrame]对象, 行索引是date(分钟级别数据为datetime), 列索引是行情字段名字.
        * 如果是多支股票, 则返回[pandas.DataFrame]对象,行索引是['date', 'code'],或['datetime', 'code']

    :rtype: DataFrame or None

    :example:

    ::

        # 获取股票000001当天的日数据
        df = get_price('000001')

        # 获得000001的2020年01月的分钟数据, 只获取open+close字段
        df = get_price('000001', start='2020-01-01', end='2020-01-31 23:00:00', frequency='1m', fields=['open', 'close'])

        # 获取获得000001在2020年01月31日前2个交易日的数据
        df = get_price('000001', count = 2, end='2015-01-31', freq='daily', fields=['open', 'close'])

        # 获得000001的2020年12月1号14:00-2020年12月2日12:00的分钟数据
        df = get_price('000001', start='2020-12-01 14:00:00', end_date='2020-12-02 12:00:00', freq='1m')

        # 获取多只股票
        panel =  get_price(get_index_stocks('000903')) # 获取中证100的所有成分股的当天日数据, 返回一个[pandas.DataFrame]



    """
    log.debug('调用get_price' + str(locals()).replace('{', '(').replace('}', ')'))
    # 1、参数合法性判断
    if market not in ['stock', 'index', 'etf'] or \
            freq not in ['daily', '1d', 'day', '1min', '5min', '15min', '30min', '60min', '1m', '5m', '15m', '30m',
                         '60m'] or fq not in ['pre', 'post', None]:
        log.error('get_price：参数错误！对照API文档检查market、freq、fq等参数的合法性！')
        return None
    if market != 'stock' and skip_paused:
        log.error('get_price：参数错误！对照API文档检查market、skip_paused、fq等参数的合法性！')
        return None

    # 2、开始和结束时间计算
    if end is None:
        end = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if not is_trade_day(end[:10]):
            end = get_real_trade_date(end)
    else:
        if not util_date_valid(end) and not util_time_valid(end):
            log.error('get_price：参数错误！对照API文档检查end参数的合法性！')
            return None

    if start is None:
        if count is None:
            start = end
        else:
            start = get_pre_trade_day(end, count - 1, freq)
    else:
        if not util_date_valid(start) and not util_time_valid(start):
            log.error('get_price：参数错误！对照API文档检查start参数的合法性！')
            return None

    if freq in ['daily', '1d', 'day']:
        start = str(start)[:10]
        end = str(end)[:10]
        freq = 'day'
        date_index = 'date'
    else:
        start = str(start)
        end = str(end)
        if len(start) == 10:
            start = '{} 09:30:00'.format(start)

        if len(end) == 10:
            end = '{} 15:00:00'.format(end)

        if len(freq) < 4:
            freq = freq + 'in'
        date_index = 'datetime'
    # 3、其他参数初始化
    code = util_code_tolist(security)
    coll = DATABASE.get_collection(market + '_' + freq[-3:])
    field_list = ['open', 'close', 'low', 'high', 'vol', 'amount']
    if market == 'index':
        field_list += ['up_count', 'down_count']

    # 4、field参数计算
    if fields is None:
        projection = {"_id": 0, "code": 1, date_index: 1, 'open': 1, 'close': 1, 'low': 1, 'high': 1, 'vol': 1,
                      'amount': 1}
    else:
        if isinstance(fields, str):
            fields = [fields]
        if isinstance(fields, list):
            base_fields = [elem for elem in fields if elem in field_list]
            if len(base_fields) == 0:
                log.error(f"get_price：参数fields不合法！,应该{field_list}为列表！")

            if market == 'stock' and skip_paused and 'vol' not in base_fields:
                base_fields.append('vol')

            projection = dict.fromkeys(base_fields, 1)
            prefix = {
                "_id": 0,
                "code": 1,
                date_index: 1,
            }
            projection = dict(**prefix, **projection)

        else:
            log.error("get_price：参数fields不合法！,应该为字符串或字符串列表！")
            return None

    # 5、数据库查询
    filter = {
        'code': {'$in': code},
        date_index: {
            "$gte": start,
            "$lte": end
        },
    }
    if freq != 'day':
        filter['type'] = freq

    cursor = coll.find(filter, projection=projection, batch_size=10000)

    data = pd.DataFrame([item for item in cursor])
    if len(data) == 0:
        log.debug("get_price未查询到数据")
        return None

    # 5、数据清洗
    data.drop_duplicates([date_index, 'code'], inplace=True)
    if 'vol' in data.columns.values:
        data.vol = data.vol.apply(lambda x: int(x * 100))  # 股票成交数量不能有小数
    if 'amount' in data.columns.values:
        data.amount = data.amount.apply(lambda x: round(x, 2))  # 股票成交额保留两位小数
    # 6、处理skip_paused
    if market == 'stock' and skip_paused:
        data = data.query('vol>1').copy()
        if fields and 'vol' not in fields:
            data = data.drop('vol', axis=1)

    # 7、对股票进行复权计算
    if market == 'stock' and fq in ['pre', 'post']:
        cursor = DATABASE.stock_adj.find(
            {
                'code': {
                    '$in': code
                },
                "date": {
                    "$lte": end[:10],
                    "$gte": start[:10]
                }
            },
            {"_id": 0},
            batch_size=10000
        )
        adj = pd.DataFrame([item for item in cursor])
        if len(adj) > 0:
            if date_index == 'datetime':
                data['date'] = data.datetime.apply(lambda x: str(x)[:10])  # 生成日期
            data.set_index(['date', 'code'], inplace=True)
            adj.set_index(['date', 'code'], inplace=True)
            data = data.join(adj, how='left')
            if fq == 'pre':
                data['qfq'] = data['qfq'].fillna(1)  # 前复权空值填1，倒序
                cof = data['qfq']
            else:
                data['hfq'] = data['hfq'].fillna(method='ffill')  # # 后复权空值填最后一个系数
                cof = data['hfq']
            for col in ['open', 'high', 'low', 'close']:
                if col in data.columns.values:
                    data[col] = round(data[col] * cof, 2)
            data.reset_index(inplace=True)
            data.drop(['qfq', 'hfq'], axis=1, inplace=True)
            if date_index == 'datetime':
                data.drop('date', axis=1, inplace=True)
        else:
            log.debug("get_price获取复权因子失败！返回未复权值")

    if count is not None:
        data = data.groupby(['code'], as_index=False).tail(count)

    if len(code) == 1:
        data = data.drop('code', axis=1).set_index(date_index)
    else:
        data.set_index([date_index, 'code'], inplace=True)
    return data


def history(count, unit='1d', field='close', security_list=None, skip_paused=False, fq='pre'):
    # type: (int, str, str, list, bool, str ) -> Optional[pd.DataFrame]
    """

    回测/模拟专用API
    获取历史数据，可查询多个股票的单个数据字段，返回数据格式为 DataFrame
    当取天数据时, 不包括当天的, 即使是在收盘后；分钟数据不包括当前分钟的数据，没有未来

    :param count: 数量, 返回的结果集的行数

    :param unit: 单位时间长度,现在支持['daily', '1d', 'day', '1min', '5min', '15min', '30min', '60min', '1m', '5m',
        '15m', '30m', '60m']

    :param field:  要获取的数据类型,只能是一个值,包含：['open', ' close', 'low', 'high', 'vol', 'amount']

    :param security_list: 要获取数据的股票列表,None 表示查询 context.universe 中所有股票的数据

    :param skip_paused: 是否跳过不交易日期(包括停牌). 如果不跳过, 停牌时会使用停牌前的数据填充。

    :param fq: 复权选项。'pre'：前复权；'post':后复权；None:不复权

    :return:  [pandas.DataFrame]对象, 行索引是datetime字符串, 列索引是股票代号.

    """
    if context.status != RUN_STATUS.RUNNING:
        print("history为回测模拟专用API函数，只能在策略运行过程中使用！")
        return None

    log.debug('调用history' + str(locals()).replace('{', '(').replace('}', ')'))
    code = security_list if security_list is not None else context.universe
    code = util_code_tolist(code)
    if len(code) == 0:
        log.error("history():参数security_list为空并且context.universe为空!")
        return None

    if field not in ['open', 'close', 'high', 'low', 'vol', 'amount']:
        log.error("history():参数field 错误！")
        return None

    if unit in ['daily', '1d', 'day']:
        end_date = context.previous_date
        data = get_price(code, end=end_date, fields=field, freq=unit, count=count, skip_paused=skip_paused, fq=fq)
        if data is not None:
            if len(code) > 1:
                data = data[field].reset_index().pivot(index='date', columns='code', values=field)
            else:
                data = data[field]

    elif unit in ['1min', '5min', '15min', '30min', '60min', '1m', '5m', '15m', '30m', '60m']:
        end_date = context.current_dt
        data = get_price(code, end=end_date, fields=field, freq=unit, count=count + 1, fq=fq)
        if data is not None:
            if len(code) > 1:
                data = data[field].reset_index.pivot(index='datetime', columns='code', values=field)
            else:
                data = data[field]
            data = data.iloc[:-1]
    else:
        log.error("history():unit 参数错误!")
        return None

    return data


def attribute_history(security, count, unit='1d', fields=None, fq='pre'):
    """
    回测/模拟专用API
    查看某一支股票的历史数据, 可以选这只股票的多个属性, 默认跳过停牌日期.
    当取天数据时, 不包括当天的, 即使是在收盘后；分钟数据不包括当前分钟的数据，没有未来；

    :param security: 股票代码

    :param count: 数量, 返回的结果集的行数

    :param unit: 单位时间长度,现在支持['daily', '1d', 'day', '1min', '5min', '15min', '30min', '60min', '1m', '5m',
        '15m', '30m', '60m']

    :param fields: 包含：['open', ' close', 'low', 'high', 'vol', 'amount']

    :param fq: 复权选项: pre-前复权 None-不复权 post-后复权

    :return: 返回[pandas.DataFrame]对象，行索引是datetime字符串, 列索引是属性名字.


    :type security: str or list
    :type count: int
    :type unit: str
    :type fields: str or list
    :type fq: str or None

    """
    if context.status != RUN_STATUS.RUNNING:
        print("attribute_history为回测模拟专用API函数，只能在策略运行过程中使用！")
        return None

    log.debug('调用attribute_history' + str(locals()).replace('{', '(').replace('}', ')'))
    if fields is None:
        fields = ['open', 'close', 'high', 'low', 'vol', 'amount']
    if unit in ['daily', '1d', 'day']:
        end_date = context.previous_date
        data = get_price(security, end=end_date, fields=fields, freq=unit, count=count, skip_paused=True, fq=fq)
        if data is not None:
            data = data[fields]

    elif unit in ['1m', '5m', '15m', '30m', '60m']:
        end_date = context.current_dt
        data = get_price(security, end=end_date, fields=fields, freq=unit, count=count + 1, skip_paused=True, fq=fq)
        if data is not None:
            data = data[fields].iloc[:-1]
    else:
        log.error("attribute_history(): unit 参数错误!")
        return None
    return data


def get_bars(security, count, unit='1d', fields=None, include_now=False, end_dt=None, fq_ref_date=None, market='stock'):
    # type: (list, int, str, Optional[list], bool, Optional[str], Optional[str], str) -> Optional[pd.DataFrame]
    """
    **函数暂未实现**

    获取各种时间周期的 bar 数据， bar 的分割方式与主流股票软件相同， 而且支持返回当前时刻所在 bar 的数据；
    get_bars 开盘时取的bar高开低收都是当天的开盘价，成交量成交额为0；
    get_bars 没有跳过停牌选项，所获取的数据都是不包含停牌的数据，如果bar个数少于count个，则返回实际个数，并不会填充。

    :param security: 标的代码或列表,支持一个或多个标的
    :param count: 大于0的整数，表示获取bar的个数。如果行情数据的bar不足count个，返回的长度则小于count个数。
    :param unit: bar的时间单位, 支持标准bar,包括['1m', '5m', '15m', '30m', '60m', '1d']
    :param fields: 获取数据的字段， 支持如下值：['date', 'open', 'close', 'high', 'low', 'vol', 'amount']，默认为None,表示全部字段。
    :param include_now: 取值True 或者False。 表示是否包含当前bar, 比如策略时间是9:33，unit参数为5m，如果 include_now=True,则返回9:30-9:33这个分钟 bar。
    :param end_dt: 查询的截止时间，支持的类型为None或str。默认值为None

        * 在回测/模拟环境下默认为context.current_dt
        * 在其他环境下默认为datetime.now()
        * 由于bar的最小单位是一分钟，所以end_dt的秒没有什么意义，会被替换为0，例如："2019-11-22 9:35:23" 和 "2019-11-22 9:35:00" 是一样的。
    :param fq_ref_date: 复权基准日期，支持的类型为str或None,为None时为不复权数据。

        * 回测/模拟环境中默认为 context.current_dt
        * 在投研环境下默认为datetime.now()
        * 如果输入 fq_ref_date = None, 则获取到的是不复权的数据
        * 如果想获取后复权的数据，可以将fq_ref_date 指定为一个股票IPO之前很早的日期，比如 datetime.date(1990, 1, 1)
        * 定点复权，以某一天价格点位为参照物，进行的前复权或后复权。
        * 设置为datetime.datetime.now()即返回前复权数据。
        * 设置为context.current_dt返回动态复权数据，
    :param market: 市场类型，目前支持[“stock", ”index","ETF"], 默认“stock".

    :return:

       * 若security为字符串格式的标的代码时，返回pandas.DataFrame，dataframe 的index是一个日期字符串
       * 若security为list格式的标的代码时，返回pandas.DataFrame，dataframe 的index是一个MultiIndex


    :example:

    ::

        # 获取平安银行最近5天数据,包括context.current_date
        df =  get_bars('000001', 5, unit='1d',fields=['open','close'],include_now=True)

        # 设置复权基准日为 2018-01-05 , 取得的最近5条包括 end_dt 的天数据
        get_bars('600507',5,unit='1d', fields=['date','open', 'high', 'low', 'close'],include_now=True, end_dt='2018-01-05 11:00:00', fq_ref_date='2018-01-05')


    """

    """
    log.debug('调用get_bar' + str(locals()).replace('{', '(').replace('}', ')'))
    # 1、参数合法性判断
    if market not in ['stock', 'index', 'etf'] or \
            unit not in ['daily', '1d', 'day', '1min', '5min', '15min', '30min', '60min', '1m', '5m', '15m', '30m',
                         '60m']:
        log.error('get_bar：参数错误！对照API文档检查market、unit参数的合法性！')
        return None

    # 2. end_dt
    if end_dt is None:
        if context.status == RUN_STATUS.RUNNING:
            end_dt = context.current_dt
        else:
            end_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    else:
        if not isinstance(end_dt, str) or (not util_date_valid(end_dt) and not util_time_valid(end_dt)):
            log.error('get_bar：参数错误！对照API文档检查end_dt参数的合法性！')
            return None


    if context.run_type == RUN_TYPE.BACK_TEST and context.status == RUN_STATUS.RUNNING:
        pass
    elif context.run_type == RUN_TYPE.SIM_TRADE and context.status == RUN_STATUS.RUNNING:
        pass
    else:
        pass

    # 2. 获取当天日期，决定使用历史数据还是实时数据
    today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if is_trade_day(today[:10]) and end_dt[:10]:
        pass
    """
    return None


def get_all_securities(date=None, market='stock', df=False):
    """
    获取平台支持的所有股票信息

    :param date: 查询日期, 用于获取某日期还在上市的股票信息. 默认值为 None, 表示获取当日的股票信息.

        1. 特定参数“all”， 表示获取所有日期的上市股票信息。
        2. 特定参数“delist", 表示获取所有退市股票信息
        3. **建议使用时添加上指定date**
    :param market: 用来过滤securities的类型,目前支持的type仅有['stock', 'index', 'etf]
    :param df: 返回格式，若是True, 返回[pandas.DataFrame], 否则返回一个仅包含标的代码的list, 默认是False.

    :type date: str
    :type market: str
    :type df: bool

    :return:  [pandas.DataFrame or list]返回标的列表

    :example:

    ::

        get_all_securities()[:2]

        返回：
        ['000001', '000002']
        当日市场交易的所有股票列表

        get_all_securities(df=True)[:2]
        返回:
        --- 	name	start	     end	    type
        000001	平安银行	1991-04-03	2200-01-01	stock
        000002	万 科Ａ	1991-01-29	2200-01-01	stock

        name: 中文名称
        start: 上市日期
        end: 退市日期（股票是最后一个交易日，不同于摘牌日期），如果没有退市则为2200-01-01；
        type: 类型，stock(股票)，index(指数)，etf(场内ETF基金)

    """
    if market not in ['stock', 'index', 'etf']:
        log.error('get_all_securities：参数错误！market参数不合法！')
        return None

    coll = DATABASE.get_collection(f'{market}_list')
    # filter = {}
    filter: Dict[str, any] = {}
    if market == 'stock':
        if date is None:
            filter['end'] = '2200-01-01'
        elif util_date_valid(date):
            filter['end'] = {"$gt": date}
            filter['start'] = {"$lte": date}
        elif date == 'delist':
            filter['end'] = {"$lt": '2200-01-01'}
        elif date != 'all':
            log.error('get_all_securities：参数错误！date参数不合法！')
            return None

    elif market == 'index':
        if date is None:
            # date = datetime.date().strftime('%Y-%m-%d')
            pass
        elif util_date_valid(date):
            filter['start'] = {"$lte": date}
        elif date is not None and date != 'all':
            log.error('get_all_securities：参数错误！date参数不合法！')
            return None

    cursor = coll.find(filter, {'_id': 0})
    if df:
        return pd.DataFrame([item for item in cursor]).set_index('code').sort_index()
    else:
        return sorted([item["code"] for item in cursor])


def get_security_info(code, market='stock'):
    """
    获取股票的信息.

    :param code: 证券代码
    :type code: 字符串
    :param market: 用来过滤code的类型,目前支持的type仅有['stock', 'index', 'etf]
    :type market: 字符串
    :return: 一个字典对象, 有如下key值:

        1. code: 股票代码
        2. name: 中文名称
        3. start: 上市日期, 字符串类型
        4. end: 退市日期（股票是最后一个交易日，不同于摘牌日期）, 如果没有退市则为2200-01-01

    :example:

    ::
        # 获取股票000001的上市时间
        start_date = get_security_info('000001').start
        print(start)

    """
    coll = DATABASE.get_collection(market + '_list')
    cursor = coll.find({'code': code}, {'_id': 0})
    try:
        rtn = cursor[0]
    except IndexError:
        rtn = {'code': code, 'name': '代码不存在', 'start': '', 'end': ''}
    return rtn


def get_stock_list(date=None):
    """
    获取股票列表

    :param date: 在该日期上市的股票，如果为空，则取上一个交易日日期

    :return list: 返回股票代码列表

    """
    return get_all_securities(date=date)


def get_index_stocks(index, date=None):
    """
    获取一个指数给定日期的成分股列表.目前仅支持：

    * '000016' ：上证50
    * '000852' ：中证1000
    * '000905' ：中证500
    * '000906' ：中证800
    * '000300' ：沪深300
    * '000010' ：上证180
    * '000688' ： 科创50abc

    :param index: 字符串，一个指数代码，如‘000300’
    :param date: 字符串，查询日期, 如'2015-10-15'.
                默认为None,指当前日期
    :return: 返回股票代码的list
    """
    if index not in ['000016', '000852', '000905', '000906', '000300', '000010', '000688']:
        log.error("get_index_stocks: 参数index仅支持 ['000016', '000852', '000905', '000906','000300', '000010', '000688']")
        return None
    filter: Dict[str, any] = {"index": index}
    if date is None:
        filter["end"] = '2200-01-01'
    elif util_date_valid(date):
        filter['end'] = {"$gt": date}
        filter['start'] = {"$lte": date}
    else:
        log.error('get_index_stocks：参数错误！date参数不合法！')
        return None

    coll = DATABASE.index_stock
    cursor = coll.find(filter, {"_id": 0, "code": 1})
    return [item["code"] for item in cursor]


def get_industry_stocks(industry, date=None):
    """
    获取申万一级行业给定日期的成分股列表.目前仅支持(申万I级)：

    * '801010' ：农林牧渔
    * '801030' ：基础化工
    * '801040' ：钢铁
    * '801050' ：有色金属
    * '801080' ：电子
    * '801110' ：家用电器
    * '801120' ：食品饮料
    * '801130' ：纺织服饰
    * '801140' ：轻工制造
    * '801150' ：医药生物
    * '801160' ：公用事业
    * '801170' ：交通运输
    * '801180' ：房地产
    * '801200' ：商贸零售
    * '801210' ：社会服务
    * '801230' ：综合
    * '801710' ：建筑材料
    * '801720' ：建筑装饰
    * '801730' ：电力设备
    * '801740' ：国防军工
    * '801750' ：计算机
    * '801760' ：传媒
    * '801770' ：通信
    * '801780' ：银行
    * '801790' ：非银金融
    * '801880' ：汽车
    * '801890' ：机械设备
    * '801950' ：煤炭
    * '801960' ：石油石化
    * '801970' ：环保
    * '801980' ：美容护理

    :param industry: 字符串，一个指数代码，如‘801010’
    :param date: 字符串，查询日期, 如'2015-10-15'.
                默认为None,指当前日期
    :return: 返回股票代码的list
    """
    if industry not in ['801010', '801030', '801040', '801050', '801080', '801110', '801120', '801130',
                        '801140', '801150', '801160', '801170', '801180', '801200', '801210', '801230',
                        '801710', '801720', '801730', '801740', '801750', '801760', '801770', '801780',
                        '801790', '801880', '801890', '801950', '801960', '801970', '801980']:
        log.error("get_industry_stocks: 参数industry仅支持(申万I级)")
        return None
    filter: Dict[str, any] = {"index": industry}
    if date is None:
        filter["end"] = '2200-01-01'
    elif util_date_valid(date):
        filter['end'] = {"$gt": date}
        filter['start'] = {"$lte": date}
    else:
        log.error('get_industry_stocks：参数错误！date参数不合法！')
        return None

    coll = DATABASE.industry_stock
    cursor = coll.find(filter, {"_id": 0, "code": 1})
    return [item["code"] for item in cursor]


def get_stock_name(code=None, date=None):
    """
    获取股票名称

    :param code: 股票代码，支持list, 如果为空，则返回所有股票
    :param date: 查询日期，如果为空，则取上一个交易日日期

    :return dict: 返回股票代码与股票名称的字典

    """
    filter: Dict[str, any] = {}
    if code is not None:
        code = util_code_tolist(code)
        filter['code'] = {'$in': code}

    if date is None:
        filter['end'] = "2200-01-01"
    elif util_date_valid(date):
        filter['end'] = {"$gt": date}
        filter['start'] = {"$lte": date}
    else:
        log.error('get_stock_name：参数错误！date参数不合法！')
        return None
    if 'stock_name' in DATABASE.list_collection_names():
        coll = DATABASE.stock_name
    else:
        coll = DATABASE.stock_list
    cursor = coll.find(filter, {"_id": 0, "code": 1, "name": 1})
    rtn = {item["code"]: item["name"] for item in cursor}

    # 修复stock_list和stock_name两个结合数据来源不一致造成的bug
    if code is not None and len(code) > len(rtn):
        diff = {i: "-" for i in code if i not in rtn.keys()}
        rtn = dict(**rtn, **diff)

    return rtn


def get_index_name(code=None):
    """
    获取指数名称

    :param code: 指数代码，支持list, 如果为空，则返回所有指数

    :return dict: 返回股票代码与股票名称的字典

    """
    collections = DATABASE.index_list

    if code is not None:
        code = util_code_tolist(code)
        cursor = collections.find(
            {
                "code": {
                    '$in': code
                },
            },
            {"_id": 0, "code": 1, "name": 1},
        )
    else:
        cursor = collections.find({}, {"_id": 0, "code": 1, "name": 1})
    return {item["code"]: item["name"] for item in cursor}


def get_st_stock(code=None, date=None):
    """
    获取ST股票代码和名称

    :param code: 股票代码，支持list, 如果为空，则查询所有股票
    :param date: 查询日期，如果为空，则取最近交易日日期

    :return dict: 返回股票代码与股票名称的字典

    """
    filter: Dict[str, any] = {}
    if code is not None:
        code = util_code_tolist(code)
        filter['code'] = {'$in': code}

    if date is None:
        filter['end'] = "2200-01-01"
    elif util_date_valid(date):
        filter['end'] = {"$gt": date}
        filter['start'] = {"$lte": date}
    else:
        log.error('get_st_stock：参数错误！date参数不合法！')
        return None

    filter['name'] = Regex(u".*ST.*", "i")
    if 'stock_name' in DATABASE.list_collection_names():
        coll = DATABASE.stock_name
    else:
        coll = DATABASE.stock_list

    cursor = coll.find(filter, {"_id": 0, "code": 1, "name": 1})
    return {item["code"]: item["name"] for item in cursor}


def get_paused_stock(code=None, date=None):
    """
    获取停牌的股票代码

    :param code: 股票代码，支持list, 如果为空，则查询所有股票
    :param date: 查询日期，如果为空，则取最近交易日日期

    :return list: 返回股票代码列表

    """
    filter = {}
    if code is not None:
        if isinstance(code, str):
            code = [code]
        elif not isinstance(code, list):
            log.error("参数code不合法！,应该为字符串或列表！")
            return None
        filter['code'] = {'$in': code}

    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
        if not is_trade_day(date):
            date = get_real_trade_date(date)
    elif util_date_valid(date):
        if not is_trade_day(date):
            date = get_real_trade_date(date)
    else:
        log.error("参数date输入不合法！")
        return None

    filter['date'] = date
    filter['vol'] = {'$lt': 1}

    coll = DATABASE.stock_day
    projection = {"_id": 0, "code": 1}
    cursor = coll.find(filter=filter, projection=projection)
    return [item["code"] for item in cursor]


def get_block_stock(block):
    """
    根据板块名称检索对应的股票代码

    :param block:  板块名称

    :return: 板块对应的股票代码列表

    :type block: str

    :rtype: list

    板块名称汇总::

        blockname =
        [
            300ESG,300周期,300非周,3D打印,5G概念,BIPV概念,C2M概念,CIPS概念,CXO概念,ETC概念
            HJT电池,IP变现,MCU芯片,MSCIA50,MSCI中盘,MSCI成份,MiniLED,NFT概念,NMN概念,OLED概念
            PPP模式,PVDF概念,QFII新进,QFII重仓,RCS概念,ST板块,一带一路,三代半导,上海自贸,上证180
            上证380,上证50,上证中盘,上证创新,上证治理,上证混改,上证红利,上证超大,不活跃股,专精特新
            业绩预升,业绩预增,业绩预降,东数西算,两年新股,个人持股,中俄贸易,中创100,中华A80,中字头
            中小100,中小300,中小银行,中盘价值,中盘成长,中证100,中证200,中证央企,中证红利,中证龙头
            久不分红,乡村振兴,亏损股,云游戏,云科技,云计算,互联金融,人工智能,人脑工程,人造肉
            代糖概念,仿制药,低价股,低市净率,低市盈率,体育概念,保险新进,保险重仓,信创,信息安全
            信托重仓,债转股,储能,元宇宙,充电桩,光伏,光刻机,免疫治疗,免税概念,养老概念
            养老金,内地低碳,军民融合,农业50,农村金融,冷链物流,分拆上市,分散染料,创业300,创业创新
            创业大盘,创业板50,创业板指,创业蓝筹,创医药,创成长,创投概念,创新100,创科技,创质量
            券商重仓,券商金股,化肥,北上重仓,北交所,北京冬奥,区块链,区块链50,医废处理,医美概念
            半导体50,博彩概念,卫星导航,即将解禁,参股新股,参股金融,双创50,发可转债,口罩防护,可燃冰
            台资背景,含B股,含GDR,含H股,含可转债,员工持股,商誉减值,回购计划,固态电池,国产软件
            国信价值,国开持股,国证价值,国证农业,国证基建,国证大宗,国证成长,国证服务,国证治理,国证红利
            国证芯片,国资云,国防军工,土地流转,在线消费,地下管网,地摊经济,地热能,垃圾分类,培育钻石
            基因概念,基金减仓,基金增仓,基金独门,基金重仓,壳资源,外资背景,大数据,大盘价值,大盘成长
            大盘股,大飞机,天然气,央企100,央企改革,央视50,婴童概念,字节跳动,安防服务,定增股
            定增预案,家庭医生,密集调研,富时A50,小盘价值,小盘成长,小米概念,工业互联,工业大麻,工业母机
            工业气体,已高送转,幽门菌,微利股,微盘股,恒大概念,成渝特区,户数减少,户数增加,扣非亏损
            投资时钟,抗癌,拟减持,拟增持,持续增长,换电概念,摘帽,操作系统,数字孪生,数字货币
            数据中心,整体上市,新冠检测,新冠药,新型烟草,新材料,新硬件,新能源车,新进成份,新零售
            无人机,无人驾驶,无线耳机,昨成交20,昨收活跃,昨日上榜,昨日振荡,昨日涨停,昨日跌停,昨日较弱
            昨日较强,昨日连板,昨日首板,昨曾涨停,昨曾跌停,昨高换手,智慧城市,智慧政务,智能交通,智能医疗
            智能家居,智能机器,智能电网,智能电视,智能穿戴,最近复牌,最近多板,最近异动,最近闪拉,最近闪跌
            有机硅,机构吸筹,板块趋势,核污防治,核电核能,次新开板,次新股,次新超跌,次新预增,武汉规划
            民企100,民营医院,民营银行,氟概念,氢能源,氮化镓,水产品,水利建设,污水处理,汽车拆解
            汽车电子,汽车芯片,沪深300,油气改革,泛珠三角,活跃股,海南自贸,海外业务,海峡西岸,消费100
            消费电子,涉矿概念,深次新股,深注册制,深证100,深证300,深证价值,深证创新,深证成指,深证成长
            深证治理,深证红利,烟草概念,燃料电池,物业管理,物联网,特斯拉,特高压,猪肉,环保50
            环渤海,生物疫苗,生物质能,电商概念,电子纸,电子身份,电解液,白酒概念,百元股,百度概念
            皖江区域,盐湖提锂,知识产权,石墨烯,破净资产,破发行价,碳中和,碳纤维,磷概念,社保新进
            社保重仓,种业,科创50,科创信息,科技100,租购同权,稀土永磁,稀缺资源,空气治理,粤港澳
            精选指数,绩优股,维生素,绿色建筑,绿色照明,绿色电力,网红经济,网络游戏,职业教育,聚氨酯
            股东减持,股东增持,股权分散,股权激励,股权转让,股权集中,胎压监测,能源互联,腾讯概念,腾讯济安
            航运概念,节能,芯片,苹果概念,草甘膦,虚拟现实,虫害防治,融资增加,融资融券,行业龙头
            被举牌,装配建筑,装饰园林,要约收购,证金汇金,资源优势,赛马概念,超导概念,超清视频,超级电容
            跨境电商,轮动趋势,辅助生殖,边缘计算,近已解禁,近期弱势,近期强势,近期新低,近期新高,远程办公
            连续亏损,送转潜力,送转超跌,透明工厂,通达信88,配股股,配股预案,重组股,重组预案,量子科技
            金融科技,钛金属,钠电池,钴金属,铁路基建,银河99,锂电池,锂矿,镍金属,长三角
            长株潭,阿里概念,陆股通减,陆股通增,降解塑料,雄安新区,页岩气,预制菜,预计扭亏,预计转亏
            预高送转,风沙治理,风能,风险提示,食品安全,高商誉,高市净率,高市盈率,高校背景,高端装备
            "高股息股","高融资盘","高贝塔值","高负债率","高质押股","鸡肉","鸿蒙概念","黄金概念"
        ]
    """
    collections = DATABASE.stock_block
    cursor = collections.find(
        {"blockname": block, "type": 'zs'},
        {"_id": 0, "code": 1},
    )
    return [item["code"] for item in cursor]


def get_stock_block(code):
    """ 根据股票代码检索对应的block名称 """
    collections = DATABASE.stock_block
    cursor = collections.find(
        {"code": code},
        {"_id": 0, "blockname": 1},
    )
    return [item["blockname"] for item in cursor]


def get_mtss(security_list, start_date, end_date, fields=None):
    """
    获取股票的融资融券信息.

    获取一只或者多只股票在一个时间段内的融资融券信息

    :param security_list: 一只股票代码或者一个股票代码的 list

    :param start_date: 开始日期, 一个字符串

    :param end_date: 结束日期, 一个字符串

    :param fields: 字段名或者 list, 可选. 默认为 None, 表示取全部字段, 各字段含义如下：

        ==================  ====================
        字段名	                含义
        ==================  ====================
        date	            日期
        sec_code	        股票代码
        fin_value	        融资余额(元）
        fin_buy_value     	融资买入额（元）
        fin_refund_value	融资偿还额（元）
        sec_value	        融券余量（股）
        sec_sell_value	    融券卖出量（股）
        sec_refund_value	融券偿还股（股）
        ==================  ====================

    :return: 返回一个 pandas.DataFrame 对象，默认的列索引为取得的全部字段. 如果给定了 fields 参数,
     则列索引与给定的 fields 对应.

    """
    if start_date is None:
        start_date = '2010-03-31'
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if isinstance(security_list, str):
        security_list = [security_list]
    filter = {
        'code': {
            '$in': security_list
        },
        'date': {
            '$gte': start_date,
            '$lte': end_date
        }
    }
    if fields is None:
        projection = {'_id': 0}
    elif isinstance(fields, list):
        projection = dict.fromkeys(fields, 1)
        prefix = {
            "_id": 0,
            "code": 1,
            "date": 1
        }
        projection = dict(**prefix, **projection)
    else:
        projection = None

    cursor = DATABASE.stock_mtss.find(filter, projection)
    return pd.DataFrame([item for item in cursor])
