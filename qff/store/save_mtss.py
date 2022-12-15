#!/opt/conda/bin/python

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
存储融资融券信息
"""
import pandas as pd
import numpy as np
import pymongo
import random
from qff.tools.config import DATABASE
from qff.tools.date import date_to_int, get_next_trade_day, get_trade_days, get_pre_trade_day
from qff.tools.utils import util_to_json_from_pandas


_sh_url = 'http://www.sse.com.cn/market/dealingdata/overview/margin/a/rzrqjygk{}.xls'
_sz_url = 'http://www.szse.cn/api/report/ShowReport?SHOWTYPE=xlsx&CATALOGID=1837_xxpl&txtDate={}&tab2PAGENO=1&random={}&TABKEY=tab2'


def save_mtss_by_day(date, err):
    try:
        # 获取上交所数据
        sh_data = pd.read_excel(_sh_url.format(date_to_int(date)), 1).assign(date=date).assign(sse='sh')
        sh_data.columns = ['code', 'name', 'fin_value', 'fin_buy_value', 'fin_refund_value',
                           'sec_value', 'sec_sell_value', 'sec_refund_value', 'date', 'sse']
        sh_data.code = sh_data.code.apply(lambda x: str(x)[0:6])
        sh_data = sh_data[["date", "code", "name", 'fin_value', 'fin_buy_value', 'fin_refund_value',
                           'sec_value', 'sec_sell_value', 'sec_refund_value', 'sse']]

        # 获取深交所数据
        sz_url = _sz_url.format(date, random.random())
        sz_data = pd.read_excel(sz_url)
        sz_data.columns = ['code', 'name', 'fin_buy_value', 'fin_value', 'sec_sell_value',
                           'sec_value', 'sec_money', 'fin_sec_value']
        sz_data['fin_value'] = sz_data['fin_value'].apply(lambda x: int(str(x).replace(',', '')))
        sz_data['fin_buy_value'] = sz_data['fin_buy_value'].apply(lambda x: int(str(x).replace(',', '')))
        sz_data['sec_value'] = sz_data['sec_value'].apply(lambda x: int(str(x).replace(',', '')))
        sz_data['sec_sell_value'] = sz_data['sec_sell_value'].apply(lambda x: int(str(x).replace(',', '')))
        sz_data.code = sz_data.code.apply(lambda x: ('00000' + str(x))[-6:])
        sz_data = sz_data.assign(date=date, sse='sz', fin_refund_value=np.NAN, sec_refund_value=np.NAN)
        sz_data = sz_data[["date", "code", "name", 'fin_value', 'fin_buy_value', 'fin_refund_value',
                           'sec_value', 'sec_sell_value', 'sec_refund_value', 'sse']]

        df = pd.concat([sh_data, sz_data])
        df = df.reset_index(drop=True)

        DATABASE.stock_mtss.insert_many(util_to_json_from_pandas(df))

    except Exception as error0:
        print(error0)
        print(date)
        err.append(str(date))
    return


def patch_mtss_data(code, start):
    """
    补充融资融券缺失数据
    :return:
    """
    coll = DATABASE.stock_mtss
    start = get_pre_trade_day(start)
    if code[0] in ['0', '3']:
        ref = coll.find({'code': code, 'date': {'$gte': start}}, {'_id': 0})
        mtss = pd.DataFrame([item for item in ref])
        if len(mtss) >= 2:
            mtss.sort_values('date', inplace=True)

            mtss['fin_refund_value'] = mtss['fin_value'].shift(1) + mtss['fin_buy_value'] - mtss['fin_value']
            mtss['sec_refund_value'] = mtss['sec_value'].shift(1) + mtss['sec_sell_value'] - mtss['sec_value']
            mtss = mtss.iloc[1:]
        elif len(mtss) == 1:
            mtss['fin_refund_value'] = mtss['fin_buy_value'] - mtss['fin_value']
            mtss['sec_refund_value'] = mtss['sec_sell_value'] - mtss['sec_value']
        else:
            return

        upd_data = util_to_json_from_pandas(mtss)
        try:
            for d in upd_data:
                coll.update_one({'date': d['date'], 'code': d['code']}, {'$set': d})
        except Exception as e:
            print('更新失败，错误：{}，code:{}'.format(e, code))


def save_mtss_data():
    import warnings
    warnings.filterwarnings('ignore')
    print('==== NOW SAVE STOCK MTSS DATA =====')

    coll = DATABASE.stock_mtss
    coll.create_index(
        [("date",
          pymongo.ASCENDING),
         ("code",
          pymongo.ASCENDING)],
        unique=True
    )
    err = []

    ref1 = DATABASE.stock_mtss.find({"code": '000001'}, {"_id": 0, "date": 1}, sort=[("date", -1)]).limit(1)
    vdf = [item for item in ref1]
    if len(vdf) > 0:
        start = get_next_trade_day(vdf[-1]["date"], 1)
    else:
        start = '2010-03-31'

    ref2 = DATABASE.stock_day.find({"code": '000001'}, {"_id": 0, "date": 1}, sort=[("date", -1)]).limit(1)
    vdf = [item for item in ref2]
    end = vdf[-1]["date"]

    if end > start:
        date_list = get_trade_days(start, end)
        for item in range(len(date_list)):
            print('The {} of Total {}'.format(item, len(date_list)))
            save_mtss_by_day(date_list[item], err)

    print('patch mtss data...')
    if start == '2010-03-31':
        ref3 = DATABASE.stock_mtss.distinct('code')   # 首次运行
    else:
        ref3 = DATABASE.stock_mtss.distinct('code', {'date': start})

    code_list = [item for item in ref3]
    for item in range(len(code_list)):
        print('The {} of Total {}'.format(item, len(code_list)))
        patch_mtss_data(code_list[item], start)

    print('==== FINISH SAVE STOCK MTSS DATA =====')

    if len(err) > 0:
        print('ERROR CODE \n ')
        print(err)
    return


if __name__ == '__main__':

    save_mtss_data()
    # err = []
    # save_mtss_by_day('2022-05-17', err)

    # print('patch mtss data...')
    # start = '2010-03-31'
    # ref3 = DATABASE.stock_mtss.distinct('code')
    # code_list = [item for item in ref3]
    # for item in range(len(code_list)):
    #     print('The {} of Total {}'.format(item, len(code_list)))
    #     patch_mtss_data(code_list[item], start)
    # print('SUCCESS patch stock mtss data full ^_^')