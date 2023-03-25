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
"""
    策略回测环境实现模块
"""

import threading
import os
import datetime

from qff.frame.settle import settle_by_day, profit_analyse
from qff.frame.order import order_broker
from qff.frame.context import context, strategy, run_strategy_funcs
from qff.frame.const import RUN_TYPE, RUN_STATUS
from qff.frame.backup import save_context
from qff.frame.trace import Trace
from qff.tools.date import get_trade_days, get_trade_min_list, get_pre_trade_day
from qff.price.query import get_price
from qff.tools.logs import log
from qff.tools.local import cache_path


def back_test_run(trace=False):
    """
    回测框架运行函数,执行该函数将运行回测过程
    :param trace: 设置策略运行过程中是否进行交互
    :return 无返回值

    """

    context.run_type = RUN_TYPE.BACK_TEST

    if context.status == RUN_STATUS.RUNNING:
        log.error('回测函数已运行！')
        return
    else:
        context.status = RUN_STATUS.RUNNING

    if context.run_freq == 'tick':
        log.error("回测模式不支持tick运行频率!")
        return

    context.bm_data = get_price(context.benchmark,
                                start=get_pre_trade_day(context.start_date),
                                end=context.end_date,
                                market='index')
    if context.bm_data is None:
        log.error(f"基准{context.benchmark}指数数据未成功获取，可能数据未下载!")
        return

    context.bm_start = context.bm_data.iloc[0].close
    if trace:
        bt_thread = threading.Thread(target=_back_test_run)
        bt_thread.setDaemon(True)
        # 运行命令行环境...
        trace = Trace(bt_thread)
        bt_thread.start()
        trace.cmdloop()
        log.warning("命令行交互环境退出...")
        bt_thread.join()
        log.warning("回测框架运行结束！")
    else:
        _back_test_run()


def _back_test_run():
    log.debug('_back_test_run(): 回测线程开始运行...')
    days = get_trade_days(context.current_dt[0:10], context.end_date)  # 回测中断恢复时可继续运行
    for day in days:
        if context.status != RUN_STATUS.RUNNING:
            break
        if strategy.before_trading_start is not None:
            context.current_dt = day + " 09:00:00"
            run_strategy_funcs(strategy.before_trading_start)

        # 判断是否跳过当天
        if context.pass_today:
            context.pass_today = False
        else:
            if context.run_freq == 'day':
                # 执行每日策略函数
                if strategy.handle_data is not None:
                    context.current_dt = day + " 09:30:00"  # 分钟第一条数据时间
                    run_strategy_funcs(strategy.handle_data)

                if len(strategy.run_daily) > 0:
                    run_times = list(strategy.run_daily.keys())
                    run_times.sort()
                    for rt in run_times:                    # 目前还不支持非交易时间的函数
                        context.current_dt = day + " " + rt
                        run_strategy_funcs(strategy.run_daily[rt])

            elif context.run_freq == "min":
                # 生成交易时间分钟列表
                min_list = get_trade_min_list(day)
                for context.current_dt in min_list:
                    # 执行分钟策略函数
                    if strategy.handle_data is not None:
                        run_strategy_funcs(strategy.handle_data)
                    # 查找是否有定时执行的策略
                    if str(context.current_dt)[11:] in strategy.run_daily.keys():
                        run_strategy_funcs(strategy.run_daily[str(context.current_dt)[11:]])

                    # 订单撮合 order_broker
                    order_broker()

                    # 跳过当天
                    if context.pass_today:
                        context.pass_today = False
                        break
        # 每日收盘处理函数
        context.current_dt = day + " 15:30:00"
        settle_by_day()

        if strategy.after_trading_end is not None:
            run_strategy_funcs(strategy.after_trading_end)

        log.info("##################### 一天结束 ######################")
        log.info("")

    if context.status == RUN_STATUS.PAUSED:
        # log.warning("_back_test_run回测运行暂停，保存过程数据...!")

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
        log.warning("_back_test_run回测执行取消...!")
    else:
        context.status = RUN_STATUS.DONE
        if strategy.on_strategy_end is not None:
            strategy.on_strategy_end()

        context.run_end = datetime.datetime.now()
        profit_analyse()

        # log.error("回测运行完成!，执行quit退出交互环境后进行回测数据分析")
        log.info("_back_test_run回测线程运行完成!")
