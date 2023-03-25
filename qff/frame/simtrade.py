# coding :utf-8
#
# The MIT License (MIT)
#
# Copyright (c) 2021-2029 XuHaiJiang/QFF
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

# 实盘模拟实现
# 1、设计一个线程对象，1秒钟执行一次，判断时间运行策略函数
# 2、主程序设计成一个命令行，可接受指令，输出实盘过程中的信息和数据分析


import threading
import os
import pandas as pd
from time import sleep
from qff.frame.context import context, strategy, run_strategy_funcs
from qff.frame.const import RUN_TYPE, RUN_STATUS
from qff.frame.backup import save_context
from qff.frame.order import order_broker
from qff.frame.settle import settle_by_day, profit_analyse
from qff.frame.trace import Trace
from qff.tools.date import is_trade_day
from qff.price.fetch import fetch_current_ticks
from qff.tools.logs import log
from qff.tools.local import cache_path


def sim_trade_run():
    """
    实盘模拟框架运行函数,执行该函数将运行策略实盘模拟

    :return: None
    """
    context.run_type = RUN_TYPE.SIM_TRADE

    if context.status == RUN_STATUS.RUNNING:
        log.error('实盘模拟框架函数已运行！')
        return
    else:
        context.status = RUN_STATUS.RUNNING

    # 恢复运行时不能设置
    if context.bm_start is None:
        context.start_date = pd.Timestamp.now().strftime('%Y-%m-%d')
        context.bm_start = fetch_current_ticks(context.benchmark, market='index')['price']

    sim_thread = threading.Thread(target=_sim_trade_run)

    sim_thread.setDaemon(True)   # 主线程A一旦执行结束，不管子线程B是否执行完成，会全部被终止。
    sim_thread.start()
    # 运行命令行环境...
    trace = Trace(sim_thread)
    trace.cmdloop()
    # sim_thread.join()  # 主线程等待子线程执行完成，屏蔽原因：执行quit命令后，结束不了进程
    log.warning("实盘模拟框架运行结束！")


def _sim_trade_run():
    while context.status == RUN_STATUS.RUNNING:
        _time = pd.Timestamp.now()
        stime = _time.strftime('%Y-%m-%d %H:%M:%S')
        if is_trade_day(stime[0:10]):
            # 固定时间点的策略函数
            # 移到此处（1）能够保证sleep后能够匹配到；（2）可以设置任意时间点运行的函数
            if stime[11:] in strategy.run_daily.keys():
                run_strategy_funcs(strategy.run_daily[stime[11:]])

            if stime[11:16] == '09:00':
                if strategy.before_trading_start is not None:
                    run_strategy_funcs(strategy.before_trading_start)

            elif '09:30' <= stime[11:16] <= '11:30' or '13:00' <= stime[11:16] <= '15:00':
                # 按策略频率运行的策略函数
                if context.run_freq == 'day':
                    if stime[11:16] == '09:30' and strategy.handle_data is not None:
                        run_strategy_funcs(strategy.handle_data)

                else:
                    if strategy.handle_data is not None:
                        run_strategy_funcs(strategy.handle_data)

                # 订单撮合 order_broker
                order_broker()

            elif stime[11:16] == '15:30':
                settle_by_day()
                if strategy.after_trading_end is not None:
                    run_strategy_funcs(strategy.after_trading_end)

                profit_analyse()
                save_context()
                log.info("##################### 一天结束 ######################")
                log.info("")

            else:
                pass

            _freq = "3s" if context.run_freq == 'tick' else '1min'     # 3s是为了tick频率运行
            _t = pd.Timestamp.now()
            sleep((_t.ceil(freq=_freq) - _t).total_seconds())         # 考虑前面运行超过_freq，造成sleep负数
        else:
            sleep(60)
    if context.status == RUN_STATUS.PAUSED:
        log.warning("回测运行暂停，保存过程数据...!")
        default_name = context.strategy_name+'.pkl'
        if ' ' in default_name:
            default_name = '_'.join(default_name.split(' '))
        bf_input = input(f"输入备份文件名称[{default_name}]:")
        if bf_input == '':
            bf_input = default_name
        backup_file = '{}{}{}'.format(cache_path, os.sep, bf_input)
        print(f"策略备份文件：{backup_file}")
        save_context(backup_file)
        if bf_input != default_name:
            save_context()
    elif context.status == RUN_STATUS.CANCELED:
        log.warning("回测执行取消...!")
