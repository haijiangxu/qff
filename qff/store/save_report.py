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
爬取股票季报年报数据，数据清洗后保存至数据库中
"""

import hashlib
import os
import requests
import time
import pandas as pd
from pytdx.crawler.history_financial_crawler import HistoryFinancialCrawler
from qff.tools.local import download_path
from qff.tools.mongo import DATABASE
from qff.tools.utils import util_to_json_from_pandas
from qff.store.save_price import print_progress

__all__ = ['save_report']

FINANCIAL_URL = 'http://down.tdx.com.cn:8001/tdxfin/gpcw.txt'
DOWNLOAD_URL = 'http://down.tdx.com.cn:8001/tdxfin/'


# 计算文件的MD5值
def get_file_md5(file_name):
    m = hashlib.md5()
    with open(file_name, mode='rb') as f:
        while True:
            # 128 is smaller than the typical filesystem block
            buf = f.read(4096)
            if not buf:
                break
            m.update(buf)
        return m.hexdigest()


# 解析文件名称, 返回文件名称及MD5码
def get_file_name():
    contents = requests.get(FINANCIAL_URL).text.strip().split('\n')
    line_list = [line.strip().split(",") for line in contents]
    return [(line[0], line[1]) for line in line_list]


# 下载股票季报年报文件
def download_report():
    result = get_file_name()
    res = []
    for item, md5 in result:
        file_name = '{}{}{}'.format(download_path, os.sep, item)
        if item in os.listdir(download_path) and md5 == get_file_md5(file_name):
            pass
            # print(' ==== FILE {} IS ALREADY IN {} ==== '.format(item, download_path))
        else:
            print(' ==== DOWNLOADING {} FILE ==== '.format(item[0:12]))
            req = requests.get(DOWNLOAD_URL + item)
            gpcw_file = '{}{}{}'.format(download_path, os.sep, item)
            with open(gpcw_file, "wb") as df:
                df.write(req.content)
            res.append(item)
    return res


# 解析年报文件，转换成dataframe
def parse_to_df(filename):
    with open(filename, 'rb') as df:
        data = HistoryFinancialCrawler().parse(download_file=df)

    if len(data) == 0:
        return None

    total_len = len(data[0])
    col = ['code', 'report_date']
    length = total_len - 2
    for i in range(0, length):
        col.append('f' + '00{}'.format(str(i + 1))[-3:])
    df = pd.DataFrame(data=data, columns=col)
    return df


def save_report(update_all=False):
    """
    从通达信网站爬取股票季报年报数据，数据清洗后保存至数据库中
    :param update_all: 是否保存所有下载文件，True-只保存新下载的文件
    :return: 无
    """
    file_list = download_report()

    coll = DATABASE.report
    coll.create_index([("code", 1), ("report_date", 1)], unique=True)
    coll.create_index([("f314", 1)])  # 财报公告日期
    coll.create_index([("f315", 1)])  # 业绩快报发布日期
    coll.create_index([("f313", 1)])  # 业绩预告发布日期
    coll.create_index([("report_date", 1)])  # 业绩预告发布日期

    if update_all:
        file_list = os.listdir(download_path)

    start = time.perf_counter()
    total = len(file_list)
    for item in range(total):
        file_name = file_list[item]
        print_progress(item, total, start, file_name)

        if file_name[0:4] != 'gpcw':
            continue
        file_path = '{}{}{}'.format(download_path, os.sep, file_name)

        try:
            new_data = parse_to_df(file_path)
            if new_data is None or len(new_data) < 1:
                continue
            # 将公告日期列移动到第3列,由于df列数量太多，执行以下语句pandas报警效率低下，舍弃
            # pub_date_col = new_data.pop('314')
            # new_data.insert(2, 'pub_date', pub_date_col)

            new_data = new_data.drop_duplicates(subset=['code', 'report_date'], keep='last')

            data = util_to_json_from_pandas(new_data)
            try:
                for d in data:
                    coll.update_one({'code': d['code'], 'report_date': d['report_date']}, {'$set': d}, upsert=True)

            except Exception as e:
                if isinstance(e, MemoryError):
                    coll.insert_many(data, ordered=True)
                else:
                    raise e
        except Exception as e:
            print(f"DATA FILE {file_name} SAVE/UPDATE FAILED!")
            print(e)
            os.remove(file_path)

    print('SUCCESSFULLY SAVE/UPDATE FINANCIAL DATA')


if __name__ == '__main__':
    save_report(True)
