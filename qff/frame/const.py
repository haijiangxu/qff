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

from enum import Enum


# noinspection PyPep8Naming
class RUN_TYPE(Enum):
    """
    策略运行模式

    :BACK_TEST: 历史数据回测
    :SIM_TRADE: 实盘模拟交易
    """
    BACK_TEST = 0   # 历史数据回测
    SIM_TRADE = 1   # 实盘模拟交易


# noinspection PyPep8Naming
class RUN_STATUS(Enum):
    """
    策略运行状态

    :NONE: 未开始
    :RUNNING: 正在进行
    :DONE: 完成
    :FAILED:  失败
    :CANCELED: 取消
    :PAUSED:  暂停


    """
    NONE = 0      # 未开始
    RUNNING = 1   # 正在进行
    DONE = 2      # 完成
    FAILED = 3    # 失败
    CANCELED = 5  # 取消
    PAUSED = 6    # 暂停


# noinspection PyPep8Naming
class ORDER_TYPE(Enum):
    """
    订单类型

    :MARKET:  市价单

    :LIMIT:  限价单
    """
    MARKET = "市价单"
    LIMIT = "限价单"


# noinspection PyPep8Naming
class ORDER_STATUS(Enum):
    """
    订单状态

    :OPEN: 已委托未成交
    :DEAL: 已成交
    :CANCELLED: 已撤单


    """

    PENDING_NEW = "PENDING_NEW"        # 待报
    OPEN = "OPEN"                  # 已报/部成
    DEAL = "DEALT"                     # 已成
    REJECTED = "REJECTED"              # 拒单
    PENDING_CANCEL = "PENDING_CANCEL"  # 待撤
    CANCELLED = "CANCELLED"            # 已撤
