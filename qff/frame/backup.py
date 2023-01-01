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

import os
import pickle
from qff.frame.context import context, g, RUNTYPE
from qff.tools.local import cache_path
from qff.tools.logs import log


def save_context(backup_file=None):
    if backup_file is None:
        file_name = context.strategy_name+'_bt' if context.run_type == RUNTYPE.BACK_TEST\
                else context.strategy_name+'_sim'
        backup_file = '{}{}{}'.format(cache_path, os.sep, file_name+'.pkl')
    try:
        if os.path.exists(backup_file):
            os.remove(backup_file)
        with open(backup_file, 'wb') as pk_file:
            pickle.dump([context.__dict__, g.__dict__], pk_file)
        log.info("save_context():策略环境保存成功！")
    except Exception as e:
        log.error("save_context():策略环境保存失败！")
        log.error(e)


def load_context(backup_file):
    # global context, g
    with open(backup_file, 'rb') as pk_file:
        res = pickle.load(pk_file)
        c_dict: dict = res[0]
        for key, value in c_dict.items():
            setattr(context, key, value)

        g_dict: dict = res[1]
        for key, value in g_dict.items():
            if str(key)[0] != '_':
                setattr(g, key, value)
    log.info("load_context():策略环境转载成功！")


# def save_context():
#     file_name = context.strategy_name+'_bt' if context.run_type == RUNTYPE.BACK_TEST\
#         else context.strategy_name+'_sim'
#     backup_file = '{}{}{}'.format(cache_path, os.sep, file_name+'.pkl')
#     if os.path.exists(backup_file):
#         os.remove(backup_file)
#     with open(backup_file, 'wb') as pk_file:
#         pickle.dump([context, g], pk_file)
#
#
# def load_context(backup_file):
#     global context, g
#     if os.path.exists(backup_file):
#         with open(backup_file, 'rb') as pk_file:
#             res = pickle.load(pk_file)
#             context = res[0]
#             g = res[1]
#             # import copy
#             # context = copy.deepcopy(res[0])
#             # g = copy.deepcopy(res[1])
