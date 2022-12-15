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
设计一个框架入口函数，将策略文件作为命令行参数传入，由框架启动并调用策略文件中定义的函数
从而可实现框架运行中的暂停和重启
命令行传入参数：
（1）策略文件路径名称
（2）回测还是实盘模拟
（3）重新启动还是恢复运行
 (4) 初始资金
 (5) 回测频率
 (6) 回测开始日期
 (7) 回测结束日期
框架停止和恢复机制：
1、在cli中运行停止，将保存当前context和g 两个全局变量，并退出运行框架
2、实盘模拟时，每日结算完成将保存全局变量到指定位置，以应对框架异常退出
3、恢复运行时，如果未找到

"""
import os
import argparse
from datetime import datetime
from qff.frame.context import context, strategy
from qff.frame.backup import load_context
from qff.tools.local import cache_path
from qff.frame.interface import set_backtest_period, set_init_cash, set_run_freq
from qff.frame.backtest import back_test_run
from qff.frame.simtrade import sim_trade_run


def _getattr(m, func_name):
    try:
        func = getattr(m, func_name)
    except AttributeError:
        func = None
    return func


def entry():
    parser = argparse.ArgumentParser(
        description="qff框架同时支持运行策略回测及实盘模拟,策略文件作为第一个参数必需输入。"
    )
    parser.add_argument("strategy", help="策略文件路径")
    parser.add_argument("-t", "--trade", action="store_true", help="对策略进行实盘模拟，默认策略回测")
    parser.add_argument("-r", "--resume", action='store_true', help="恢复以前中断的策略，默认全新开始")
    parser.add_argument("-f", "--freq", choices=['day', 'min', 'tick'], help="设置回测执行频率")
    parser.add_argument("-m", "--money", type=int, help="设置账户初始资金")
    parser.add_argument("-s", "--start", type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
                        help="设置回测开始日期，格式: YYYY-MM-DD")
    parser.add_argument("-e", "--end", type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
                        help="设置回测结束日期，格式: YYYY-MM-DD")
    args = parser.parse_args()
    print('strategy_file:{}'.format(args.strategy))
    print('strategy_name:{}'.format(os.path.basename(args.strategy).split('.')[0]))

    # print('trade:{}'.format(args.trade))
    # print('resume:{}'.format(args.resume))
    # print('freq:{}'.format(args.freq))
    # print('money:{}'.format(args.money))
    # print('start:{}'.format(args.start))
    # print('end:{}'.format(args.end))

    # 1、恢复导入context全局变量
    strategy_name = os.path.basename(args.strategy).split('.')[0]
    context.strategy_name = strategy_name
    if args.resume:
        file_name = strategy_name + '_sim' if args.trade else strategy_name + '_bt'
        backup_file = '{}{}{}'.format(cache_path, os.sep, file_name + '.pkl')
        try:
            load_context(backup_file)
        except Exception as e:
            print("导入context备份文件失败:{}".format(e))
            return

    # 2、导入策略文件
    # if not load_strategy_file(args.strategy):
    #     print("策略文件载入失败或缺少初始化函数initialize！***")
    #     return
    # 导入策略文件移至回测/实盘框架运行函数中

    # 3、处理其他命令行参数
    if not args.resume:
        if args.freq is not None:
            set_run_freq(args.freq)
        if args.money is not None:
            set_init_cash(int(args.money))
        if args.start is not None and args.end is not None and not args.trade:
            set_backtest_period(args.start, args.end)

    # 4、调用框架运行函数
    if args.trade:
        sim_trade_run(args.strategy, args.resume)
    else:
        back_test_run(args.strategy, args.resume)

    # 5、框架运行结束
    if strategy.on_strategy_end is not None:
        strategy.on_strategy_end()
