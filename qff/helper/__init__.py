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
    本helper模块用于定义常用的策略模型对象和函数，包括：
    1、仓位管理
    2、止损模型
    3、止盈模型
    4、选股模型
    5、风险控制模型
    6、择时模型

"""
# from qff.helper.formula import (
#     ABS,
#     AVEDEV,
#     BBI,
#     BBIBOLL,
#     BARLAST,
#     BARLAST_EXIST,
#     COUNT,
#     CROSS,
#     CROSS_STATUS,
#     DIFF,
#     EMA,
#     EVERY,
#     EXIST,
#     FILTER,
#     HHV,
#     IF,
#     IFOR,
#     IFAND,
#     LLV,
#     LAST,
#     MIN,
#     MA,
#     MAX,
#     MACD,
#     REF,
#     RENKO,
#     RENKOP,
#     SMA,
#     SUM,
#     STD,
#     SINGLE_CROSS,
#     XARROUND,
# )
#
# from qff.helper.indicator import ind_ma, ind_macd, ind_atr, ind_kdj, ind_rsi, ind_boll
# from qff.helper.common import filter_st_stock, filter_paused_stock, filter_20pct_stock, select_zt_stock
# from qff.helper.ts import ts_init, open_position, get_stop_loss_price
