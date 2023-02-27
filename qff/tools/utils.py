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
import random
import json
import os
import re


def util_gen_id(topic='ORD', lens=8):
    """
    生成随机值
    :param topic: 随机值前缀
    :param lens: 随机值长度
    :return: ORD+4数字id+4位大小写随机
    """
    _list = [chr(i) for i in range(65,
                                   91)] + [chr(i) for i in range(97,
                                                                 123)
                                          ] + [str(i) for i in range(10)]

    num = random.sample(_list, lens)
    return '{}_{}'.format(topic, ''.join(num))


def util_code_tostr(code):
    """
    将所有沪深股票从数字转化到6位的代码,因为有时候在csv等转换的时候,诸如 000001的股票会变成office强制转化成数字1,
    同时支持聚宽股票格式,掘金股票代码格式,Wind股票代码格式,天软股票代码格式
    :param code: 股票代码 str
    :return: 6位标准股票代码
    """
    if isinstance(code, int):
        return "{:>06d}".format(code)
    if isinstance(code, str):
        # 聚宽股票代码格式 '600000.XSHG'
        # 掘金股票代码格式 'SHSE.600000'
        # Wind股票代码格式 '600000.SH'
        # 天软股票代码格式 'SH600000'
        if len(code) == 6:
            return code
        if len(code) == 8:
            # 天软数据
            return code[-6:]
        if len(code) == 9:
            return code[:6]
        if len(code) == 11:
            if code[0] in ["S"]:
                return code.split(".")[1]
            return code.split(".")[0]
        raise ValueError("错误的股票代码格式")
    if isinstance(code, list):
        return code[0]


def util_code_tolist(code, auto_fill=True):
    """
    将转换code转换为list
    :param code: 股票代码，str
    :param auto_fill: 是否自动补全(default: {True})
    :return: 股票列表
    """

    if isinstance(code, str):
        if auto_fill:
            return [util_code_tostr(code)]
        else:
            return [code]

    elif isinstance(code, list):
        if auto_fill:
            return [util_code_tostr(item) for item in code]
        else:
            return [item for item in code]


def util_to_json_from_pandas(data):
    """
    将pandas数据转换成json格式
    :param data: pandas dataframe对象数据
    :return: json格式字符串
    """

    """需要对于datetime 和date 进行转换, 以免直接被变成了时间戳"""
    if 'datetime' in data.columns:
        data.datetime = data.datetime.apply(lambda x: str(x))
    if 'date' in data.columns:
        data.date = data.date.apply(lambda x: str(x)[:10])
    return json.loads(data.to_json(orient='records'))


def auto_file_name(path):
    """
    避免覆盖同名文件，自动在文件名后添加”(0), (1), (2)….“之类的编号。
    :param path: 文件路径及名称
    :return:
    """
    directory, file_name = os.path.split(path)
    while os.path.isfile(path):
        pattern = '(\d+)\)\.'
        if re.search(pattern, file_name) is None:
            file_name = file_name.replace('.', '(0).')
        else:
            current_number = int(re.findall(pattern, file_name)[-1])
            new_number = current_number + 1
            file_name = file_name.replace(f'({current_number}).', f'({new_number}).')
        path = os.path.join(directory + os.sep + file_name)
    return path
