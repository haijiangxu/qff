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
from qff import *

strategy_name = "样例策略文件"


def initialize():
    log.info("{} : 初始化运行".format(strategy_name))
    # 设置回测周期
    set_backtest_period(start="2021-08-27", end="2022-03-25")
    # 设置初始资金
    set_init_cash(1000000)
    # 设置运行频率
    set_run_freq('day')
    # 设置指数基准
    set_benchmark(security="000300")
    # 设置定时运行的策略函数
    run_daily(handle_trade, run_time="09:50")


def before_trading_start():
    log.info("before_trading_start函数运行...")
    pass


def handle_trade():
    pass


def after_trading_end():
    log.info("after_trading_end函数运行...")
    pass


if __name__ == '__main__':
    back_test_run(os.path.abspath(__file__))