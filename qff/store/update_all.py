#！/usr/bin/python

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
    init_stock_list, save_index_stock
from qff.store.save_price import save_security_day, save_security_min, save_stock_xdxr, \
    save_security_block
from qff.store.save_report import save_report
from qff.store.save_valuation import save_valuation_data
from qff.store.save_mtss import save_mtss_data
from qff.tools.config import DATABASE
from qff.tools.date import is_trade_day
import datetime


def update_all():
    op_date = str(datetime.date.today())
    if not is_trade_day(op_date):
        print('======== 当前不是交易日，无需更新数据！ ==========')
        return
    # 判断是否需要初始化

    colls = DATABASE.list_collection_names()
    if 'stock_list' not in colls:
        init_stock_list()
    if 'index_list' not in colls:
        init_index_list()
    if 'etf_list' not in colls:
        init_etf_list()

    print(f'====更新数据日期:{op_date} ==========')
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
    save_security_block()


def init_delist_date():
    from qff.price.query import get_all_securities
    stock_list = get_all_securities('delist')
    save_security_day('stock', stock_list)
    for freq_ in ["1min", "5min", "15min", "30min", "60min"]:
        save_security_min(market='stock', freq=freq_, security=stock_list)

    save_stock_xdxr(stock_list)


if __name__ == '__main__':
    update_all()
    # init_delist_date()
