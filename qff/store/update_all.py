# ！/usr/bin/python

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
数据保存统一接口文件，在定时任务中自动执行
"""

from qff.store.save_info import save_stock_list, init_index_list, init_etf_list, \
    init_stock_list, save_index_stock, save_industry_stock, init_stock_name
from qff.store.save_price import save_security_day, save_security_min, save_stock_xdxr, \
    save_security_block
from qff.store.save_report import save_report
from qff.store.save_valuation import save_valuation_data
from qff.store.save_mtss import save_mtss_data
from qff.tools.mongo import DATABASE
from qff.tools.date import is_trade_day
from qff.tools.logs import log
import prettytable as pt
import datetime
import pandas as pd


def update_all(date=None):
    if date is None:
        date = str(datetime.date.today())
    log.info(f'====更新数据日期:{date} ==========')

    # 判断是否需要初始化
    colls = DATABASE.list_collection_names()
    if 'stock_list' not in colls:
        init_stock_list()
    if 'index_list' not in colls:
        init_index_list()
    if 'etf_list' not in colls:
        init_etf_list()

    save_stock_list()
    for market_ in ['stock', 'index', 'etf']:
        save_security_day(market_)
        for freq_ in ["1min", "5min", "15min", "30min", "60min"]:
            save_security_min(market=market_, freq=freq_)

    save_stock_xdxr()
    save_report()
    save_valuation_data()
    save_mtss_data()
    save_index_stock()
    save_industry_stock()
    save_security_block()

    log.info('==== 更新数据完成 ==========')


def init_delist_date():
    from qff.price.query import get_all_securities
    stock_list = get_all_securities('delist')
    save_security_day('stock', stock_list)
    for freq_ in ["1min", "5min", "15min", "30min", "60min"]:
        save_security_min(market='stock', freq=freq_, security=stock_list)

    save_stock_xdxr(stock_list)


def bytes_to_human(n):
    symbols = ('K', 'M', 'G', 'T', 'P')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)
    return '%sB' % n


def mongo_info():
    colls = sorted(DATABASE.list_collection_names())
    if len(colls) == 0:
        print("数据库qff未创建或数据集为空！")
    else:
        value = []
        for item in colls:
            coll = DATABASE.get_collection(item)
            stats = DATABASE.command("collstats", item)
            if stats['count'] > 0:
                columns = coll.find_one().keys()
                col_num = len(columns)
                count = "{:,}".format(stats['count'])
            else:
                col_num = 0
                count = 0

            data_size = bytes_to_human(stats['size'])
            storage_size = bytes_to_human(stats['storageSize'])
            nindex = stats['nindexes']
            total_index_size = bytes_to_human(stats['totalIndexSize'])
            index = list(stats['indexSizes'].keys())

            value.append([item, count, col_num, data_size, storage_size, nindex, total_index_size, index])
        df = pd.DataFrame(value,
                          columns=['数据集合', '记录数量', '字段数量', '集合大小', '存储空间', '索引数量', '索引大小',
                                   '索引值'])
        # df = pd.DataFrame(value, columns=['table_name', 'count', 'column_num', 'column'])
        # pd.set_option('display.width', 300)
        # pd.set_option('display.max_colwidth', 80)
        # pd.set_option('display.max_columns', 4)

        tb = pt.PrettyTable()
        tb.add_column('序号', df.index)
        for col in df.columns.values:
            tb.add_column(col, df[col])
            tb.align[col] = "r"

        print(tb)

        print("\n")
        last_date = DATABASE.stock_day.find_one({'code': '000001'}, sort=[('date', -1)])['date']
        print(f"数据库最后一次更新日期：{last_date}")


def qff_save(*args):
    if args[0] == 'all':
        update_all()

    elif args[0] == 'day':
        for market_ in ['stock', 'index', 'etf']:
            save_security_day(market_)

    elif args[0] == 'min':
        for market_ in ['stock', 'index', 'etf']:
            for freq_ in ["1min", "5min", "15min", "30min", "60min"]:
                save_security_min(market=market_, freq=freq_)

    elif args[0] == 'stock_list':
        save_stock_list()

    elif args[0] in ['stock_day', 'index_day', 'etf_day']:
        save_security_day(str(args[0]).split('_')[0])

    elif args[0] in ['stock_min', 'index_min', 'etf_min']:
        for freq_ in ["1min", "5min", "15min", "30min", "60min"]:
            save_security_min(market=str(args[0]).split('_')[0], freq=freq_)

    elif args[0] == 'stock_xdxr':
        save_stock_xdxr()

    elif args[0] == 'stock_block':
        save_security_block()

    elif args[0] == 'report':
        save_report(True)

    elif args[0] == 'valuation':
        save_valuation_data()

    elif args[0] == 'mtss':
        save_mtss_data()

    elif args[0] == 'index_stock':
        save_index_stock()

    elif args[0] == 'industry_stock':
        save_industry_stock()

    elif args[0] == 'init_info':
        init_stock_list()
        init_index_list()
        init_etf_list()

    elif args[0] == 'init_name':
        init_stock_name()
    elif args[0] == 'save_delist':
        init_delist_date()
    else:
        print("命令格式不合法！")


def qff_drop(*args):
    table_name = args[0]
    table_list = DATABASE.list_collection_names()
    if table_name not in table_list:
        print("输入的数据库不存在！")
    else:
        ack = input(f"注意：请确认是否真的删除数据表{table_name}(Y/N)?:")
        if ack.strip().lower() == 'y':
            DATABASE.drop_collection(table_name)
            print(f"qff数据表{table_name}删除成功！")
        else:
            print(f"qff数据表{table_name}删除取消！")


if __name__ == '__main__':
    op_date = str(datetime.date.today())
    if not is_trade_day(op_date):
        print('======== 当前不是交易日，无需更新数据！ ==========')
    else:

        update_all(op_date)

    # mongo_info()
