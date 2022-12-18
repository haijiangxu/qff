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
获取股票相关数据，并保存至数据库中。
根据操作系统设置定时任务，执行本文件。
"""

import pandas as pd
import datetime
import time
from qff.price.fetch import fetch_price, fetch_stock_xdxr, fetch_stock_block
from qff.price.query import get_all_securities, get_price
from qff.tools.date import get_real_trade_date, get_next_trade_day
from qff.tools.config import DATABASE
from qff.tools.utils import util_to_json_from_pandas
from pymongo.errors import PyMongoError


def save_security_day(market='stock', security=None):
    """
    从通达信获取交易日数据，并保存到数据库中
    :param market: 市场类型，目前支持“stock/index/etf", 默认“stock".
    :param security: list or None, 证券列表
    """
    try:

        end_date = now_time()[:10]
        # stock_list = fetch_stock_list(market).index.to_list()
        stock_list = get_all_securities(market=market) if security is None else security
        table_name = market + '_day'
        print(f'====  Now Saving {table_name.upper()} ====')
        coll = DATABASE.get_collection(table_name)
        coll.create_index([("code", 1), ("date", 1)], unique=True)
        coll.create_index("date")

        data_num = 0
        data_list = []
        start = time.perf_counter()
        total = len(stock_list)
        for item in range(total):
            finsh = "▓" * int(item * 100 / total)
            need_do = "-" * int((total - item) * 100 / total)
            progress = (item / total) * 100
            dur = time.perf_counter() - start
            tt = dur/(item+1) * total
            code = stock_list[item]
            print("\r{:^3.0f}%[{}->{}]{:.2f}s|{:.2f}s ({})".format(progress, finsh, need_do, dur, tt, code), end="")

            try:
                start_date = coll.find_one({'code': code}, sort=[('date', -1)])['date']
                if start_date is None or start_date == 'nan':
                    raise TypeError
            except TypeError or PyMongoError:
                start_date = '1990-01-01'

            if start_date != end_date:
                try:
                    start_date = get_next_trade_day(start_date)
                    # print('Trying updating {} from {}'.format(code, start_date))
                    data = fetch_price(code, freq='day', market=market, start=start_date)
                    if data is None or len(data) == 0:
                        continue
                    data = data.loc[:end_date]
                    data.reset_index(inplace=True)
                    data_num += len(data)
                    data_list.append(data)
                    if data_num > 2000:
                        data = pd.concat(data_list)
                        data_num = 0
                        data_list.clear()
                        coll.insert_many(util_to_json_from_pandas(data))

                except Exception as e:
                    print(f'updating {code} data error!')
                    print('Exception:' + str(e))

        if data_num > 0:
            data = pd.concat(data_list)
            coll.insert_many(util_to_json_from_pandas(data))

        print(f'\n==== SUCCESS SAVE {table_name.upper()} DATA! ====')
    except EOFError:
        time.sleep(1)
    except Exception as e:
        print(" \nError save_security_day exception!")
        print(str(e))


def save_security_min(market='stock', freq='1min', security=None):
    """
    从通达信获取交易日数据，并保存到数据库中
    :param market: 市场类型，目前支持“stock/index/etf", 默认“stock".
    :param freq: 分钟频率，支持1min/5min/15min/30min/60min.
    :param security: list or None, 证券列表
    """
    if freq not in ["1min", "5min", "15min", "30min", "60min"] or\
       market not in ["stock", "index", "etf"]:
        print("save_security_min: 输入参数错误！")
        return

    try:
        end_date = now_time()
        # stock_list = fetch_stock_list(market).index.to_list()
        # stock_list = get_all_securities(market=market)
        stock_list = get_all_securities(market=market) if security is None else security
        table_name = market + '_min'
        print(f'==== NOW SAVE {market.upper()}_{freq.upper()} DATA =====')
        coll = DATABASE.get_collection(table_name)
        coll.create_index([("type", 1), ("code", 1), ("datetime", 1)], unique=True)

        data_num = 0
        data_list = []
        start = time.perf_counter()
        total = len(stock_list)
        for item in range(total):
            finsh = "▓" * int(item * 100 / total)
            need_do = "-" * int((total - item) * 100 / total)
            progress = (item / total) * 100
            dur = time.perf_counter() - start
            tt = dur/(item+1) * total
            code = stock_list[item]
            print("\r{:^3.0f}%[{}->{}]{:.2f}s|{:.2f}s ({})".format(progress, finsh, need_do, dur, tt, code), end="")
        data_num = 0
        data_list = []
        start = time.perf_counter()
        total = len(stock_list)
        for item in range(total):
            finsh = "▓" * int(item * 100 / total)
            need_do = "-" * int((total - item) * 100 / total)
            progress = (item / total) * 100
            dur = time.perf_counter() - start
            tt = dur/(item+1) * total
            code = stock_list[item]
            print("\r{:^3.0f}%[{}->{}]{:.2f}s|{:.2f}s ({})".format(progress, finsh, need_do, dur, tt, code), end="")

            try:
                start_date = coll.find_one({'type': freq, 'code': code}, sort=[('datetime', -1)])['datetime']
                if start_date is None or start_date == 'nan':
                    raise TypeError
            except TypeError or PyMongoError:
                start_date = '1990-01-01'

            if start_date != end_date:
                try:
                    start_date = get_next_trade_day(start_date)
                    # print('Trying updating {} {} data from {}'.format(code, freq, start_date))
                    data = fetch_price(code, freq=freq, market=market, start=start_date)
                    if data is None or len(data) == 0:
                        continue
                    data = data.loc[:end_date]
                    data.reset_index(inplace=True)
                    data['type'] = freq

                    data_num += len(data)
                    data_list.append(data)
                    if data_num > 2000:
                        data = pd.concat(data_list)
                        data_num = 0
                        data_list.clear()
                        coll.insert_many(util_to_json_from_pandas(data))

                except Exception as e:
                    print(f'\nupdating {code} {freq} data error!')
                    print('Exception:' + str(e))
        if data_num > 0:
            data = pd.concat(data_list)
            coll.insert_many(util_to_json_from_pandas(data))

        print(f'\n==== SUCCESS SAVE {table_name.upper()} {freq} DATA! ====')
    except EOFError:
        time.sleep(1)
    except Exception as e:
        print(f"\nError save_security_min exception!:{market.upper()} {freq.upper()} DATA")
        print(e)


def save_stock_xdxr(security=None):
    """
    从通达信获取除权除息分红数据，并保存到数据库中
    :param security: list or None, 证券列表
    """
    try:
        coll = DATABASE.get_collection('stock_xdxr')
        coll.create_index([('code', 1), ('date', 1), ('category', 1)], unique=True)

        coll_adj = DATABASE.get_collection('stock_adj')
        coll_adj.create_index([('code', 1), ('date', 1)], unique=True)

        print('==== NOW SAVE STOCK_XDXR DATA =====')
        end_date = now_time()[:10]
        # stock_list = get_all_securities()
        stock_list = get_all_securities() if security is None else security

        start = time.perf_counter()
        total = len(stock_list)
        for item in range(total):
            finsh = "▓" * int(item * 100 / total)
            need_do = "-" * int((total - item) * 100 / total)
            progress = (item / total) * 100
            dur = time.perf_counter() - start
            tt = dur/(item+1) * total
            code = stock_list[item]
            print("\r{:^3.0f}%[{}->{}]{:.2f}s|{:.2f}s ({})".format(progress, finsh, need_do, dur, tt, code), end="")

            try:
                xdxr_new = fetch_stock_xdxr(str(code))
                if xdxr_new is None or len(xdxr_new) == 0:
                    continue
                cursor = coll.find({'code': code}, {'_id': 0})
                xdxr_db = pd.DataFrame([item for item in cursor])
                if xdxr_db is not None and len(xdxr_db) > 0:
                    xdxr_db = xdxr_db.set_index('date', drop=False, inplace=False)
                    xdxr = pd.concat([xdxr_new, xdxr_db])
                    xdxr = xdxr.drop_duplicates(subset=['code', 'category', 'date'], keep=False)
                else:
                    xdxr = xdxr_new

                if len(xdxr) > 0:
                    try:
                        coll.insert_many(util_to_json_from_pandas(xdxr))
                    except PyMongoError:
                        pass

                try:
                    start_date = coll_adj.find_one({'code': code}, sort=[('date', -1)])['date']
                    if start_date is None or start_date == 'nan':
                        raise TypeError
                    if start_date >= end_date:
                        continue
                except TypeError or PyMongoError:
                    pass

                # data = fetch_price(code, freq='day', market='stock', start='1990-01-01')
                data = get_price(code, start='1990-01-01', end=end_date, freq='day', market='stock', fq=None)
                if data is None or len(data) == 0:
                    continue
                qfq = _calc_stock_to_fq(data, xdxr_new, 'qfq')
                if qfq is None or len(data) == 0:
                    continue
                qfq = qfq.reset_index()
                qfq = qfq.assign(date=qfq.date.apply(lambda x: str(x)[0:10]), code=code)
                adjdata = util_to_json_from_pandas(qfq.loc[:, ['date', 'code', 'adj']])
                coll_adj.delete_many({'code': code})
                coll_adj.insert_many(adjdata)
            except Exception as e:
                print(e)

        print('\n==== SUCCESS SAVE STOCK_XDXR DATA! ====')

    except Exception as e:
        print("\nError save_stock_xdxr exception!")
        print(e)


def save_security_block():
    """
    从通达信获取股票板块信息，并保存到数据库中
    :return: None
    """
    try:
        table_name = 'stock_block'
        DATABASE.drop_collection(table_name)
        coll = DATABASE.get_collection(table_name)
        coll.create_index('code')
        print(f'==== Now Saving {table_name.upper()} ====')
        data = fetch_stock_block()
        if data is not None:
            coll.insert_many(util_to_json_from_pandas(data))
        print(f'SUCCESS SAVE {table_name.upper()} ^_^')

    except Exception as e:
        print(" Error save_security_info exception!")
        print(e)


##########################################################################################################
def now_time():
    return str(get_real_trade_date(str(datetime.date.today() - datetime.timedelta(days=1)))) + \
           ' 15:00:00' if datetime.datetime.now().hour < 15 \
           else str(get_real_trade_date(str(datetime.date.today()))) + ' 15:00:00'


def _calc_stock_to_fq(bfq_data, xdxr_data, fq_type='qfq'):
    """
    计算复权系数
    :param bfq_data: 原始股票数据
    :param xdxr_data: 除权数据表
    :param fq_type: 复权类型,目前仅支持前复权,即qfq
    :return:
    """

    info = xdxr_data.query('category==1')
    bfq_data = bfq_data.assign(if_trade=1)

    if len(info) > 0:
        data = pd.concat(
            [
                bfq_data,
                info.loc[bfq_data.index[0]:bfq_data.index[-1],
                         ['category']]
            ],
            axis=1
        )

        data['if_trade'].fillna(value=0, inplace=True)
        data = data.fillna(method='ffill')

        data = pd.concat(
            [
                data,
                info.loc[bfq_data.index[0]:bfq_data.index[-1],
                         ['fenhong',
                          'peigu',
                          'peigujia',
                          'songzhuangu']]
            ],
            axis=1
        )
    else:
        data = pd.concat(
            [
                bfq_data,
                info.
                loc[:,
                    ['category',
                     'fenhong',
                     'peigu',
                     'peigujia',
                     'songzhuangu']]
            ],
            axis=1
        )
    data = data.fillna(0)
    data['preclose'] = (
        data['close'].shift(1) * 10 - data['fenhong'] +
        data['peigu'] * data['peigujia']
    ) / (10 + data['peigu'] + data['songzhuangu'])

    if fq_type in ['01', 'qfq']:
        data['adj'] = (data['preclose'].shift(-1) /
                       data['close']).fillna(1)[::-1].cumprod()
    else:
        data['adj'] = (data['close'] /
                       data['preclose'].shift(-1)).cumprod().shift(1).fillna(1)

    for col in ['open', 'high', 'low', 'close', 'preclose']:
        data[col] = data[col] * data['adj']
    data['volume'] = data['volume'] / \
        data['adj'] if 'volume' in data.columns else data['vol']/data['adj']
    try:
        data['high_limit'] = data['high_limit'] * data['adj']
        data['low_limit'] = data['high_limit'] * data['adj']
    except:
        pass
    return data.query('if_trade==1 and open != 0').drop(
        ['fenhong',
         'peigu',
         'peigujia',
         'songzhuangu',
         'if_trade',
         'category'],
        axis=1,
        errors='ignore'
    )


if __name__ == '__main__':

    # for market_ in ['stock', 'index', 'etf']:
    #     save_security_list(market_)
    #     save_security_day(market_)
    #     for freq_ in ["1min", "5min", "15min", "30min", "60min"]:
    #         save_security_min(market=market_, freq=freq_)
    #
    # save_security_info()
    # save_stock_name()
    # save_security_block()
    save_stock_xdxr()
    # save_security_min('stock', "1min")
    # save_security_min('stock', '30min')
    # save_security_min(market='index', freq="5min")
