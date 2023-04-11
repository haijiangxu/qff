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
从网络获取数据，包括股票（指数、基金）的上市时间、退市时间、代码、名称等，进行加工和保存至数据库中
初始化：
1、运行init_stock_list()
2、init_stock_name_hist()
3、运行save_index_list()
4、运行save_etf_list()
5、运行save_industry_list()


每日运行：
1、save_stock_list()
2、save_index_stock()

"""

import os
import time
from qff.price.crawl import crawl_index_list, crawl_stock_list, crawl_delist_stock, \
    crawl_index_stock_cons, crawl_industry_stock_cons
from qff.price.fetch import fetch_stock_list
from qff.tools.mongo import DATABASE
from qff.tools.local import cache_path
from qff.tools.date import get_real_trade_date
from qff.tools.utils import util_to_json_from_pandas
from datetime import datetime
import pandas as pd
import akshare as ak
import requests
import json


def save_stock_list():
    """
    每日自动更新stock_list表,同时维护stock_name表数据
    :return: 无
    """
    print('====  开始更新股票列表信息 ====')
    if 'stock_list' not in DATABASE.list_collection_names():
        print('stock_list未初始化，请先运行qff save init_info命令')
        return
    else:
        coll_list = DATABASE.get_collection('stock_list')

    if 'stock_name' not in DATABASE.list_collection_names():
        # print('stock_name 数据集合未初始化，请手动初始化！......')
        coll_name = None
    else:
        coll_name = DATABASE.get_collection('stock_name')

    try:
        # 获取当日网络最新的股票信息 ['code', 'name', 'start']
        new_list = crawl_stock_list().set_index('code')
        new_list.name = new_list.name.apply(lambda x: ''.join(x.split(' ')))

        # 查找数据库中最新的股票信息['code', 'name', 'start', 'end']
        cursor = coll_list.find({'end': '2200-01-01'}, {'_id': 0})
        org_list = pd.DataFrame([item for item in cursor]).set_index('code')

        # 比较new_list 和 org_list
        df = org_list.join(new_list, how='outer', rsuffix='_', sort=True)
        # 1、处理当日新上市的股票列表

        df_new = df[df['name'].isna()].copy()
        print(f'====  更新当日新上市的股票列表:{len(df_new)} ====')
        if len(df_new) > 0:
            df_new = df_new.drop(['name', 'start', 'end'], axis=1).\
                rename(columns={'name_': 'name', 'start_': 'start'}).\
                assign(end='2200-01-01').\
                reset_index()
            df_new = df_new.dropna()

            data_new_stock = util_to_json_from_pandas(df_new)
            coll_list.insert_many(data_new_stock)
            if coll_name:
                coll_name.insert_many(data_new_stock)

        # 2、处理当日退市的股票

        df_tuishi = df[df['name_'].isna()].copy()
        print(f'====  更新当日退市的股票列表:{len(df_tuishi)} ====')
        if len(df_tuishi) > 0:
            df_tuishi = df_tuishi.drop(['name_', 'start_'], axis=1)
            df_crawl = crawl_delist_stock().set_index('code')  # 再次确认是否退市
            df_tuishi = df_tuishi.join(df_crawl, how='inner', lsuffix='_', sort=True)
            df.dropna(inplace=True)
            if len(df_tuishi) > 0:
                # 更新stock_list
                # tuishi_date = get_real_trade_date(datetime.now().strftime('%Y-%m-%d'))
                df_tuishi = df_tuishi.drop(['name_', 'start_', 'end_'], axis=1)\
                    .reset_index()

                data = util_to_json_from_pandas(df_tuishi)
                for d in data:
                    coll_list.update_one({'code': d['code']}, {'$set': d})
                # 更新stock_name
                if coll_name:
                    cursor = coll_name.find({'code': {'$in': df_tuishi.code.tolist()}, 'end': '2200-01-01'}, {'_id': 0})
                    df_name = pd.DataFrame([item for item in cursor]).assign(end=df_tuishi.end)
                    data = util_to_json_from_pandas(df_name)
                    for d in data:
                        coll_name.update_one({'code': d['code'], 'start': d['start']}, {'$set': d}, upsert=True)

        # 3、处理更名的股票

        df.dropna(inplace=True)
        df_change = df[df['name_'] != df['name']]
        print(f'====  更新当日更名的股票列表:{len(df_change)} ====')
        if len(df_change) > 0:
            change_date = get_real_trade_date(datetime.now().strftime('%Y-%m-%d'))
            # 3.1 更新stock_list 否则下次继续更新
            df_change = df_change.assign(name=df_change.name_)
            df_change.drop(['name_', 'start_'], axis=1, inplace=True)
            df_change.reset_index(inplace=True)
            data = util_to_json_from_pandas(df_change)
            for d in data:
                coll_list.update_one({'code': d['code']}, {'$set': d}, upsert=True)

            # 3.2 更新stock_name
            if coll_name:
                cursor = coll_name.find({'code': {'$in': df_change.code.tolist()}, 'end': '2200-01-01'}, {'_id': 0})
                df_name_update = pd.DataFrame([item for item in cursor]).assign(end=change_date)
                data = util_to_json_from_pandas(df_name_update)
                for d in data:
                    coll_name.update_one({'code': d['code'], 'start': d['start']}, {'$set': d}, upsert=True)

                df_change = df_change.assign(start=change_date)
                coll_name.insert_many(util_to_json_from_pandas(df_change))

        print('====  更新股票列表完成！ ====')

    except Exception as err:
        print('====  更新股票列表完成！但出现异常！ ====')
        print(err)


def init_index_list():
    """
    保存index_list表，网络数据来源于静态网站，无需每日更新
    :return: 无
    """
    print('====  开始更新指数列表信息 ====')
    new_df = crawl_index_list()

    DATABASE.drop_collection('index_list')
    coll = DATABASE.get_collection('index_list')
    coll.create_index("code", unique=True)
    coll.create_index("start")
    cursor = coll.find({}, {'_id': 0})
    org_df = pd.DataFrame([item for item in cursor])

    df = pd.concat([org_df, new_df]).reset_index(drop=True)
    df.drop_duplicates(keep=False, inplace=True)
    df.drop_duplicates(subset=['code'], keep='last', inplace=True)
    print(f'====  更新指数列表信息:{len(df)} ====')
    if len(df) > 0:
        data = util_to_json_from_pandas(df)
        for d in data:
            coll.update_one({'code': d['code']}, {'$set': d}, upsert=True)
    print('====  更新指数列表完成！ ====')


def init_etf_list():
    """
    无需每日更新 index_etf表策略
    :return: 无
    """
    print('====  开始更新ETF列表信息 ====')
    new_df = fetch_stock_list('etf').reset_index()
    DATABASE.drop_collection('etf_list')
    coll = DATABASE.get_collection('etf_list')
    coll.create_index("code", unique=True)
    cursor = coll.find({}, {'_id': 0})
    org_df = pd.DataFrame([item for item in cursor])

    df = pd.concat([org_df, new_df]).reset_index(drop=True)
    df.drop_duplicates(keep=False, inplace=True)
    df.drop_duplicates(subset=['code'], keep='last', inplace=True)
    print(f'====  更新ETF列表信息:{len(df)} ====')
    if len(df) > 0:
        data = util_to_json_from_pandas(df)
        for d in data:
            coll.update_one({'code': d['code']}, {'$set': d}, upsert=True)
    print('====  更新ETF列表完成！ ====')


def save_index_stock():
    """
    保存指数对应的成分股股票代码
    :return: None
    """
    index_list = ['000016', '000852', '000905', '000906','000300', '000010', '000688']
    print('====  开始更新指数成分股列表 ====')
    start = time.perf_counter()
    total = len(index_list)
    for item in range(total):
        finsh = "▓" * int(item * 100 / total)
        need_do = "-" * int((total - item) * 100 / total)
        progress = (item / total) * 100
        dur = time.perf_counter() - start
        tt = dur / (item + 1) * total
        code = index_list[item]
        print("\r{:^3.0f}%[{}->{}]{:.2f}s|{:.2f}s ({})".format(progress, finsh, need_do, dur, tt, code), end="")
        _save_one_index_stock(code)
    print('\n====  更新指数成分股列表完成 ====')


def _save_one_index_stock(symbol):
    """
    自动更新指数对应的成分股
    1、查询数据库该指数对应的成分股列表， 如果返回空，则初始化该指数历史成分数据
    2、调用crawl_index_stock_cons(symbol="000300")返回当日成分数据
    3、对比成分股票代码，处理新入和退出规则

    """
    try:
        coll = DATABASE.get_collection('index_stock')
        cursor = coll.find({'index': symbol, 'end': '2200-01-01'}, {'_id': 0, 'index': 0})
        df_db = pd.DataFrame([item for item in cursor])
        if len(df_db) < 1:
            _init_index_stock(symbol)
            return
        df_db.set_index('code', inplace=True)

        df_crawl = crawl_index_stock_cons(symbol=symbol)
        if df_crawl is None or len(df_crawl) < 1:
            print(f"save_index_stock: 指数{symbol}获取最新成分数据为空！")
            return
        df_crawl = df_crawl.drop('品种名称', axis=1)
        df_crawl.columns = pd.Index(['code', 'start'])
        df_crawl.set_index('code', inplace=True)

        s1 = df_crawl.index.tolist()
        s2 = df_db.index.tolist()
        a = [x for x in s1 if x not in s2]  # 新增加的股票代码
        if len(a) > 0:
            start_date = df_crawl.loc[a, 'start'].tolist()
            new = pd.DataFrame({
                'code': a,
                'start': start_date,
                'end': '2200-01-01',
                'index': symbol
            })
            coll.insert_many(util_to_json_from_pandas(new))

            b = [x for x in s2 if x not in s1]  # 取消掉的股票代码,按道理a和b的数量相等
            df_del = df_db.loc[b].copy()

            df_del.assign(end=start_date)
            for d in util_to_json_from_pandas(df_del):
                coll.update_one({
                    'code': d['code'],
                    'index': symbol,
                    'end': '2200-01-01'
                }, {'$set': d}, upsert=True)

    except Exception as error0:
        print(error0)
        print(f"save_index_stock: 指数{symbol}保存最新成分数据错误！")


def _init_index_stock(symbol):
    if symbol[:1] == '0':
        pre_symbol = 'sh'+ symbol
    elif symbol[:1] == '3':
        pre_symbol = 'sz' + symbol
    else:
        print(f"init_index_list:指数{symbol}代码错误！")
        return

    df_hist = ak.index_stock_hist(symbol=pre_symbol)
    if df_hist is None or len(df_hist) == 0:
        print(f"init_index_list:指数{symbol}获取历史成分失败！")
        return
    df_hist.columns = pd.Index(['code', 'start', 'end'])

    df_new = crawl_index_stock_cons(symbol)
    if df_new is None or len(df_new) == 0:
        print(f"init_index_list:指数{symbol}获取当前成分失败！")
        return
    df_new = df_new.drop('品种名称', axis=1)
    df_new.columns = pd.Index(['code', 'start'])
    df_new = df_new.assign(end='2200-01-01')

    df = pd.concat([df_new, df_hist])
    df = df.assign(index=symbol).drop_duplicates()

    coll = DATABASE.get_collection('index_stock')
    coll.create_index([('index', 1), ('end', 1), ('code', 1)], unique=True)
    coll.create_index('code')
    coll.delete_many({'index': symbol})
    coll.insert_many(util_to_json_from_pandas(df))


def save_industry_stock():
    """
    最新股票行业的成份股目录
    'https://www.swsresearch.com/institute-sw/api/index_publish/current/?page=1&page_size=50&indextype=%E4%B8%80%E7%BA%A7%E8%A1%8C%E4%B8%9A'
    保存指数对应的成分股股票代码
    :return: None
    """
    url = 'https://www.swsresearch.com/institute-sw/api/index_publish/current/?page=1&page_size=50&indextype=%E4%B8%80%E7%BA%A7%E8%A1%8C%E4%B8%9A'
    response = requests.get(url)
    code_table = json.loads(response.text)
    code_dict = code_table['data']['results']
    dm = pd.DataFrame.from_dict(code_dict)
    dm.columns = ['swcode', 'swname', 'pre_close', 'open', 'amount', 'high', 'low', 'last_price', 'volume']
    industry_list = dm.swcode.tolist()

    # industry_list = ['801010', '801030', '801040', '801050', '801080', '801110', '801120', '801130',
    #                 '801140', '801150', '801160', '801170', '801180', '801200', '801210', '801230',
    #                 '801710', '801720', '801730', '801740', '801750', '801760', '801770', '801780',
    #                 '801790', '801880', '801890', '801950', '801960', '801970', '801980']

    print('====  开始更新行业成分股列表 ====')
    start = time.perf_counter()
    total = len(industry_list)
    for item in range(total):
        finsh = "▓" * int(item * 100 / total)
        need_do = "-" * int((total - item) * 100 / total)
        progress = (item / total) * 100
        dur = time.perf_counter() - start
        tt = dur / (item + 1) * total
        code = industry_list[item]
        print("\r{:^3.0f}%[{}->{}]{:.2f}s|{:.2f}s ({})".format(progress, finsh, need_do, dur, tt, code), end="")
        _save_one_industry_stock(code)
    print('\n====  更新行业成分股列表完成 ====')


def _save_one_industry_stock(symbol):
    """
    自动更新指数对应的成分股
    1、查询数据库该指数对应的成分股列表， 如果返回空，则初始化该指数历史成分数据
    2、调用crawl_industry_stock_cons(symbol="801010")返回当日成分数据
    3、对比成分股票代码，处理新入和退出规则

    """
    try:
        coll = DATABASE.get_collection('industry_stock')
        cursor = coll.find({'industry': symbol, 'end': '2200-01-01'}, {'_id': 0, 'industry': 0})
        df_db = pd.DataFrame([item for item in cursor])
        if len(df_db) < 1:
            _init_industry_stock(symbol)
            return
        df_db.set_index('code', inplace=True)

        df_crawl = crawl_industry_stock_cons(symbol=symbol)
        if df_crawl is None or len(df_crawl) < 1:
            print(f"save_industry_stock: 行业代码{symbol}获取最新成分数据为空！")
            return
        df_crawl = df_crawl.drop('序号', axis=1)
        df_crawl.columns = pd.Index(['code', 'name', 'weight', 'date'])
        df_crawl.set_index('code', inplace=True)

        s1 = df_crawl.index.tolist()
        s2 = df_db.index.tolist()
        a = [x for x in s1 if x not in s2]  # 新增加的股票代码
        if len(a) > 0:
            start_date = df_crawl.loc[a, 'date'].tolist()
            new = pd.DataFrame({
                'code': a,
                'start': start_date,
                'end': '2200-01-01',
                'industry': symbol
            })
            coll.insert_many(util_to_json_from_pandas(new))

            b = [x for x in s2 if x not in s1]  # 取消掉的股票代码,按道理a和b的数量相等
            df_del = df_db.loc[b].copy()

            df_del.assign(end=start_date)
            for d in util_to_json_from_pandas(df_del):
                coll.update_one({
                    'code': d['code'],
                    'industry': symbol,
                    'end': '2200-01-01'
                }, {'$set': d}, upsert=True)

    except Exception as error0:
        print(error0)
        print(f"save_industry_stock: 行业代码{symbol}保存最新成分数据错误！")


def _init_industry_stock(symbol):
    if symbol[:1] == '8':
        symbol = symbol
    else:
        print(f"init_industry_list:指数{symbol}代码错误！")
        return

    df_new = crawl_industry_stock_cons(symbol)
    if df_new is None or len(df_new) == 0:
        print(f"init_industry_list:行业代码{symbol}获取当前成分失败！")
        return
    df_new = df_new.drop('序号', axis=1)
    df_new.columns = pd.Index(['code', 'name', 'weight', 'date'])
    # temp_df.set_index('code', inplace=True)
    df_new = df_new.assign(end='2200-01-01')

    # df = pd.concat([df_new, df_hist])
    df_new = df_new.assign(industry=symbol).drop_duplicates()

    coll = DATABASE.get_collection('industry_stock')
    coll.create_index([('industry', 1), ('end', 1), ('code', 1)], unique=True)
    coll.create_index('code')
    coll.delete_many({'industry': symbol})
    coll.insert_many(util_to_json_from_pandas(df_new))


def init_stock_list():
    """
    获取股票列表数据及退市股票列表，初始化stock_list表
    """
    table_name = 'stock_list'
    DATABASE.drop_collection(table_name)
    coll = DATABASE.get_collection(table_name)
    coll.create_index([("end", 1), ("start", 1)])
    coll.create_index("code", unique=True)
    print(f'==== Now initialized {table_name} ====')

    stock_list = crawl_stock_list()
    stock_list = stock_list.assign(end='2200-01-01')
    delist = crawl_delist_stock()
    df = pd.concat([stock_list, delist])
    df.drop_duplicates(subset=['code'], keep='last', inplace=True)

    df.sort_values('code', inplace=True)
    df['name'] = df['name'].apply(lambda x: ''.join(x.split(' ')))
    df['start'] = df['start'].apply(lambda x: str(x)[:10])
    df['end'] = df['end'].apply(lambda x: str(x)[:10])

    data = util_to_json_from_pandas(df)
    coll.insert_many(data)
    print(f'==== Save {table_name} Done! ====')


def init_stock_name():
    """
    初始化stock_name表, 必须在init_stock_list后面运行
    """

    try:
        print(f'==== 初始化stock_name表, 必须在init_stock_list后面运行 ====')

        # 读取csv文件
        stock_name_file = '{}{}{}'.format(cache_path, os.sep, 'stock_name_history.csv')
        if not os.path.exists(stock_name_file):
            info = """
                本地未保存股票历史名称csv文件。
                在聚宽研究环境中运行以下代码：
                from jqdata import finance
                import pandas as pd
        
                df = pd.concat([finance.run_query(query(finance.STK_NAME_HISTORY).\r
                               filter(finance.STK_NAME_HISTORY.pub_date < str(year)+'-12-31',\r
                               finance.STK_NAME_HISTORY.pub_date>= str(year)+'-01-01')) for year in range(1980,2023)])
                df.to_csv("stock_name_history.csv")
                
                下载"stock_name_history.csv"文件至".qff/cache" 目录
            """
            print(info)
            return

        df_csv = pd.read_csv(stock_name_file, index_col=0)
        df_csv = df_csv[['code', 'new_name', 'start_date']]
        df_csv.code = df_csv.code.apply(lambda x: str(x)[:6])
        df_csv = df_csv.rename(columns={"new_name": "name", "start_date": "start"})
        df_csv.name = df_csv.name.apply(lambda x: ''.join(x.split(' ')))
        # 从数据库中查询当前股票列表，
        coll = DATABASE.get_collection('stock_list')
        cursor = coll.find({}, {"_id": 0})
        df_list = pd.DataFrame([item for item in cursor])

        # 从stock_name_history中筛选出stock_list里的股票代码，其他如B股数据丢弃
        df_csv = df_csv[df_csv['code'].isin(df_list['code'].to_list())]
        # 从stock_list中筛选出未包含在stock_name_history里的股票代码
        df_omit = df_list[~df_list['code'].isin(df_csv['code'].unique().tolist())]
        # 从stock_list中筛选已未包含在stock_name_history里的股票代码
        df_list = df_list[df_list['code'].isin(df_csv['code'].unique().tolist())]
        # df_list 与df_csv 合并
        df_list = df_list[['code', 'name', 'end']]
        df_list = df_list.rename(columns={"end": "start"})
        df = pd.concat([df_csv, df_list])

        # 生成end字段
        df = df.sort_values(["code", "start"], ascending=True)
        df = df.assign(end=df.groupby('code')['start'].shift(-1))  # 每只股票的最后一条记录的end字段为NAN
        df = df.dropna()

        # 合并df_omit
        df = pd.concat([df, df_omit])
        df = df.reset_index(drop=True)

        # 保存至数据库
        table_name = 'stock_name'
        DATABASE.drop_collection(table_name)
        coll = DATABASE.get_collection(table_name)
        coll.create_index([("end", 1), ("start", 1)])
        coll.create_index("code")

        pandas_data = util_to_json_from_pandas(df)
        coll.insert_many(pandas_data)
        print(f'==== Save {table_name} Done! ====')
    except Exception as e:
        print(" Error init_stock_name exception!")
        print(e)


if __name__ == '__main__':

    # init_stock_list()
    save_stock_list()
    # init_stock_name()
    # init_index_list()
    # init_etf_list()
    # save_index_stock()