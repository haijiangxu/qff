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
import datetime
import pandas as pd
import pymongo
import time
from dateutil.relativedelta import relativedelta
from qff.tools.mongo import DATABASE
from qff.tools.date import get_next_trade_day, get_pre_trade_day, int_to_date
from qff.price.finance import get_stock_reports
from qff.tools.utils import util_to_json_from_pandas
from qff.price.query import get_stock_list, get_security_info
from qff.store.save_price import print_progress


def save_valuation_by_code(code, err):
    try:
        # 首选查找数据库 是否 有 这个股票代码的数据
        code = str(code)[:6]

        ref1 = DATABASE.valuation.find({"code": code}, {"_id": 0}, sort=[("date", -1)]).limit(1)
        vdf = [item for item in ref1]
        if len(vdf) > 0:
            start = get_next_trade_day(vdf[-1]["date"], 1)
        else:
            start = '2005-01-04'
            # start = get_security_info(code)['start']  # 使用IPO日期
        # 查询股票日数据，读取开始日期前5天的数据，用于计算量比
        ref2 = DATABASE.stock_day.find(
            {
                "code": code,
                "date":
                    {
                        "$gte": get_pre_trade_day(start, 6)
                    }
            },
            {
                "_id": 0,
                "date": 1,
                "close": 1,
                "vol": 1
            },
            sort=[("date", 1)]
        )
        kdf = pd.DataFrame([item for item in ref2])

        if len(kdf) < 6:
            raise ValueError("查询股票日数据无返回！")
        end = kdf.date.iloc[-1]
        if start > end:
            return
            # raise ValueError("valuation数据已更新！")

        # print('SAVE VALUATION \n Trying updating {} from {} to {}'.format(code, start, end))

        # 从数据库中读取财务数据
        query_start = (datetime.datetime.strptime(start, '%Y-%m-%d') - relativedelta(months=14))\
            .strftime('%Y-%m-%d')
        # 'f238':  总股本, 财报中的股本数据严重滞后，取除权库信息
        # 'f239':  上市流通A股
        # 'f232':  归属于母公司所有者的净利润,季度数据
        # "f004":  每股净资产
        # "f096":  归属于母公司所有者的净利润
        # "f266":  自由流通股
        # "f287":  业绩快报-归属母公司净利润
        # "f294":  业绩快报-每股净资产
        # "f315":  业绩快报公告日期
        fin = get_stock_reports(code, fields=['f232', 'f096', 'f004', 'f238', 'f239', 'f287', 'f294', 'f315'],
                                start=query_start)
        if len(fin) < 1:
            raise ValueError("查询财报数据无返回！")

        fin['ttm'] = fin['f232'].rolling(4).apply(sum)
        # 如已公布当年业绩快报，则在快报发布日期和年报发布日期之间使用快报数据（同花顺）
        new_rows = fin[fin['f315'] > 1].copy()
        new_rows['report_date'] = new_rows['report_date'].apply(lambda y: int(y/10000)*10000+1231)
        new_rows['pub_date'] = new_rows['f315'].apply(int_to_date)
        new_rows['f096'] = new_rows['f287']
        new_rows['f004'] = new_rows['f294']
        fin = pd.concat([fin, new_rows], ignore_index=True)
        fin = fin.sort_values('pub_date').reset_index(drop=True)

        fin['dyn'] = fin['f096'] * 12 / (fin['report_date'] % 2000 / 100).astype('int')

        lyr = None
        for i in range(len(fin)):
            if fin.loc[i, 'report_date'] % 2000 == 1231:
                lyr = fin.loc[i, 'lyr'] = fin.loc[i, 'f096']
            else:
                fin.loc[i, 'lyr'] = lyr

        # 股票日数据开始部分无法匹配到财报日期，因此将start前的财报数据匹配到第一条数据上
        fin_pre = fin[fin['pub_date'] <= kdf.date[0]]
        if len(fin_pre) > 0:
            first = fin_pre.iloc[-1].name
            fin.loc[first, 'pub_date'] = kdf.date[0]

        kdf = kdf.merge(fin, left_on='date', right_on='pub_date', how='left')
        kdf = kdf.drop_duplicates(subset=['date'], keep='last')  # 修订：当年报和一季报同一天发布时，会产生两条记录
        kdf.fillna(method='ffill', inplace=True)

        # 以下为修订部分，考虑总股本和流通股本在财报中的严重滞后，修改为从除权信息库中获取
        ref3 = DATABASE.stock_xdxr.find(
            {
                "code": code,
                'category': {'$in': [2, 3, 5, 7, 8, 9, 10]}
            },
            {
                "_id": 0,
                "date": 1,
                "shares_after": 1,
                "liquidity_after": 1
            }
        )

        xdxr = pd.DataFrame([item for item in ref3])
        if len(xdxr) > 0:
            kdf = kdf.drop(['f238', 'f239'], axis=1)
            xdxr.rename(columns={'shares_after': 'f238', 'liquidity_after': 'f239'}, inplace=True)
            xdxr.sort_values('date', inplace=True)

            xdxr_pre = xdxr[xdxr['date'] <= kdf.date[0]]
            if len(xdxr_pre) > 0:
                first = xdxr_pre.iloc[-1].name
                xdxr.loc[first, 'date'] = kdf.date[0]

            kdf = kdf.merge(xdxr, left_on='date', right_on='date', how='left', suffixes=('', '_y'))
            kdf.fillna(method='ffill', inplace=True)

        # 开始计算
        kdf['quantity_ratio'] = round(kdf.vol / kdf.vol.rolling(5).mean().shift(1), 2)  # 计算量比
        kdf['capitalization'] = kdf['f238']     # 总股本(万股)
        kdf['circulating_cap'] = kdf['f239']    # 流通股本(万股)
        kdf['market_cap'] = round(kdf['f238'] * kdf['close'] * 10000 / 1.0e+8, 2)  # 总市值(亿元)
        kdf['cir_market_cap'] = round(kdf['f239'] * kdf['close'] * 10000 / 1.0e+8, 2)  # 流通市值(亿元)
        kdf['turnover_ratio'] = round(kdf['vol'] * 100 / (kdf['f239'] * 10000), 4)  # 换手率(%)
        kdf['pe_ttm'] = round(kdf['f238'] * kdf['close'] * 10000 / kdf['ttm'], 2)  # 市盈率(PE, TTM)
        kdf['pe_lyr'] = round(kdf['f238'] * kdf['close'] * 10000 / kdf['lyr'], 2)  # 市盈率(PE)s
        kdf['pe_dyn'] = round(kdf['f238'] * kdf['close'] * 10000 / kdf['dyn'], 2)  # 市盈率（动态）
        kdf['pb_ratio'] = round(kdf['close'] / kdf['f004'], 3)  # 市净率(PB)

        kdf = kdf.set_index('date')
        kdf = kdf.loc[start:end, ['code', 'quantity_ratio', 'capitalization', 'circulating_cap',
                                  'market_cap', 'cir_market_cap', 'turnover_ratio',
                                  'pe_ttm', 'pe_lyr', 'pe_dyn', 'pb_ratio']]

        DATABASE.valuation.insert_many(util_to_json_from_pandas(kdf.reset_index()))

    except Exception as error0:
        print(error0)
        print(code)
        err.append(str(code))

    return


def save_valuation_data():
    """
    根据stock_day和report数据集，生成市值数据集valuation，并自动补全前期数据
    valuation字段如下：
                code: 股票代码
                date: 日期
                date_stamp: 日期时间戳
                quantity_ratio: 量比
                capitalization 总股本(万股)
                circulating_cap 流通股本(万股)
                market_cap 总市值(亿元)
                circulating_market_cap 流通市值(亿元)
                turnover_ratio 换手率(%)
                pe_ratio 市盈率(PE, TTM)
                pe_ratio_lyr 市盈率(PE)s
                pb_ratio 市净率(PB)
    :return: None
    """
    print('==== NOW SAVE VALUATION DATA =====')
    stock_list = get_stock_list()
    coll = DATABASE.valuation
    coll.create_index(
        [("code",
          pymongo.ASCENDING),
         ("date",
          pymongo.ASCENDING)]
    )
    coll.create_index("date")
    err = []

    start = time.perf_counter()
    total = len(stock_list)
    for item in range(total):
        code = stock_list[item]
        print_progress(item, total, start, code)

        save_valuation_by_code(code, err)

    print('\n==== FINISH SAVE VALUATION DATA! ====')
    if len(err) > 0:
        print('\n ERROR CODE:')
        print(err)
    return


if __name__ == '__main__':

    save_valuation_data()
    # err1 = []
    # save_valuation_by_code('603778', err1)

