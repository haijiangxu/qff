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

# 2.1 查询当前账户资金及持股情况
# 2.2 查询策略启动后收益曲线数据
# 2.3 查看策略风险指标数据
# 2.4 查看策略业绩指标数据
# 2.5 查看历史交易股票列表，按股票代码、日期排序
# 2.6 查看运行多长时间
# 2.7 查看某只股票的K线数据
# 2.8 查看当日下单情况

from cmd import Cmd
import subprocess
import os
import sys
import time
import pandas as pd
import prettytable as pt
from qff.frame.context import context, g
from qff.frame.portfolio import Portfolio
from qff.frame.const import RUN_STATUS
from qff.frame.perf import Perf
from qff.frame.stats import stats_risk, stats_report
from qff.price.query import get_price
from qff.tools.kshow import kshow
from qff.tools.local import temp_path
from qff.tools.date import get_next_trade_day, get_date_gap, util_date_valid
from qff.tools.logs import log


def print_df(df: pd.DataFrame, title=None):
    tb = pt.PrettyTable()
    if title is not None:
        tb.title = title
    # tb.add_column('index', df.index)
    for col in df.columns.values:
        tb.add_column(col, df[col])
    print(tb)


def print_dict(dct, title=None):
    tb = pt.PrettyTable()
    if title is not None:
        tb.title = title
    tb.header = False
    for item in dct.items():
        tb.add_row(item)
    print(tb)


def print_list(list_, title=None):
    tb = pt.PrettyTable()
    if title is not None:
        tb.title = title
    tb.header = False
    for i in range(len(list_)):
        tb.add_row([i] + list_[i])
    print(tb)


class Trace(Cmd):
    prompt = "QFF> "  # 定义命令行提示符
    intro = '--------欢迎进入QFF交互环境(log命令可开关日志，help命令获取帮助)------------'

    def __init__(self, thread_id):
        Cmd.__init__(self)
        self.thread_id = thread_id
        pd.set_option('display.unicode.ambiguous_as_wide', True)
        pd.set_option('display.unicode.east_asian_width', True)
        pd.set_option('display.width', 200)  # 设置打印宽度(**重要**)
        pd.set_option('display.precision', 2)
        pd.set_option('expand_frame_repr', False)
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.float_format', lambda x: '%.2f' % x)

    def emptyline(self):
        # 忽略命令行直接回车，会重复执行上一条指令
        pass

    # info 0 查询回测/模拟基本参数
    @staticmethod
    def info_base():
        """
        info 0 查询回测/模拟基本参数
        """
        msg = context.message
        print_dict(msg, title='回测框架/模拟实盘运行基本参数')

    @staticmethod
    def info_acc():
        """
        info 1: 查询当前账户资金及持股情况
        """
        acc: Portfolio = context.portfolio

        print_dict(acc.message, title='账户当前资金情况')
        print("\n")

        table = [pst.message for pst in acc.positions.values()]
        if len(table) > 0:
            df = pd.DataFrame(table)
            print_df(df, '账户当前持仓情况')

    @staticmethod
    def info_asset():
        """
        info2: 查询历史账户资产信息

        """
        if len(context.asset_hists) > 0:
            df = pd.DataFrame(context.asset_hists)
            print_df(df, '账户资产数据列表')
        else:
            print("还未生成交易数据")

    @staticmethod
    def info_hist_order():
        """
        info3: 输出策略运行历史订单交易数据
        """
        if len(context.order_hists) > 0:
            df = pd.DataFrame(context.order_hists)
            print_df(df, '历史交易记录')
        else:
            print("*** 没有股票交易数据！*** \n")

    @staticmethod
    def info_current_order():
        """
        info4: 输出当日委托订单数据
        """
        order_list = [order.message for order in context.order_list.values()]
        if len(order_list) == 0:
            print('*** 当日没有委托订单！*** \n')
        else:
            df = pd.DataFrame(order_list)
            if len(df) > 0:
                print_df(df, '当日委托订单')

    @staticmethod
    def info_chart():
        """
        info5:  输出策略运行收益曲线图表
        """
        if len(context.asset_hists) > 0:
            chart_file = '{}{}{}.html'.format(temp_path, os.sep, 'strategy_chart')
            stats_report(context, chart_file)
        else:
            print("还未生成交易曲线数据")

    @staticmethod
    def info_risk():
        """
        info 6   : 输出策略风险分析指标数据
        """
        print("当前日期:{}".format(context.current_dt))
        if len(context.asset_hists) > 0:
            print_dict(stats_risk(context), '策略风险系数风险')

        else:
            print("还未生成交易曲线数据")

    @staticmethod
    def info_perf():
        """
        info 7   : 输出策略绩效分析指标数据
        """
        print("当前日期:{}".format(context.current_dt))

        if len(context.order_hists) > 0:
            perf = Perf()
            if perf.pnl is not None:
                print_dict(perf.message, '策略绩效分析')
                df = perf.pnl.reset_index()
                print_df(df, '账户交易配对情况')
            else:
                print("策略还没有出现成对交易数据")
        else:
            print("没有股票交易数据！")

    def do_info(self, arg):
        if arg == "" or len(arg) != 1:
            self.print_info_usage()
        else:
            # try:
            if arg[0] == '0':
                self.info_base()
            elif arg[0] == '1':
                self.info_acc()
            elif arg[0] == '2':
                self.info_asset()
            elif arg[0] == '3':
                self.info_hist_order()
            elif arg[0] == '4':
                self.info_current_order()
            elif arg[0] == '5':
                self.info_chart()
            elif arg[0] == '6':
                self.info_risk()
            elif arg[0] == '7':
                self.info_perf()
            # except Exception as e:
            #     print(e)

    @staticmethod
    def print_info_usage():
        print(
            "Usage: \n\
            ----------------------------------------------------------------------------------------------------------------------\n\
            ⌨️命令格式：info 0   : 输出回测框架/模拟实盘运行基本参数                                               \n\
            ⌨️命令格式：info 1   : 输出当前股票账户资金状况及当前账户持仓情况详情                                    \n\
            ⌨️命令格式：info 2   : 输出策略运行历史账户资产数据                                                   \n\
            ⌨️命令格式：info 3   : 输出策略运行历史订单交易数据                                                   \n\
            ⌨️命令格式：info 4   : 输出策略运行当日订单委托信息                                                   \n\
            ----------------------------------------------------------------------------------------------------------------------\n\
            ⌨️命令格式：info 5   : 输出策略运行分析报告                                                      \n\
            ⌨️命令格式：info 6   : 输出策略风险分析指标数据                                                      \n\
            ⌨️命令格式：info 7   : 输出策略绩效分析指标数据                                                      \n\
            ----------------------------------------------------------------------------------------------------------------------\n\
            "
        )

    def do_time(self, arg):
        print("策略当前时间:{}".format(context.current_dt))
        print("策略启动时间:{}".format(context.start_date))

    def do_shell(self, arg):
        """run a shell command"""
        print(">", arg)
        sub_cmd = subprocess.Popen(arg, shell=True, stdout=subprocess.PIPE)
        print(sub_cmd.communicate()[0])

    def do_fn(self, arg):
        """ fn order('000001',1000,5.6) """
        try:
            print(eval(arg))
        except Exception as er:
            print(er)

    def do_log(self, arg):
        """ 开关日志显示及设置日志级别 """
        if arg is None or arg == '':
            log.toggle()
        else:
            log.set_level(arg)

    def do_pause(self, arg):
        print("正在暂停策略运行，请耐心等待运行环境备份...")
        context.status = RUN_STATUS.PAUSED
        time.sleep(1)
        self.thread_id.join()
        return True


    def do_resume(self, arg):
        print("恢复策略运行需通过退出本交互环境\n")
        print("在终端环境下运行 python qff run 策略文件名 -r")

    def do_cancel(self, arg):
        print("正在取消策略运行，请耐心等待策略正常结束...")
        context.status = RUN_STATUS.CANCELED
        self.thread_id.join()
        return True

    def do_quit(self, arg):  # 定义quit命令所执行的操作
        print("注意：回测时策略将继续运行，但无法再进行交互。实盘下将退出策略运行！")
        ack = input(f"请确认是否真的要退出当前交互环境(Y/N)?:")
        if ack.strip().lower() == 'y':
            return True

    def do_exit(self, arg):  # 定义quit命令所执行的操作
        ack = input(f"请确认是否真的要退出当前策略运行(Y/N)?:")
        if ack.strip().lower() == 'y':
            sys.exit(1)


    def do_ls(self, arg):
        print(os.path.dirname(os.path.abspath(__file__)))

    def do_ks(self, arg):
        if arg == "":
            print("当前日期:{}".format(context.current_dt))

            if context.order_hists is not None:
                perf = Perf()
                if perf.pnl is not None:
                    df = perf.pnl.reset_index().reset_index()
                    print_df(df, '账户交易配对情况')
                else:
                    print("没有股票成对交易数据")
            else:
                print("没有股票交易数据！")
            print(
                "Usage: \n\
                ----------------------------------------------------------------------------------------------------------------------\n\
                ⌨️命令格式：ks n                : 显示账户交易股票的日K线，并标注买入和卖出价格,n代表第n条买入股票                     \n\
                -----------------------------------------------------------------------------------------------------------------------\n\
                "
            )
        else:
            arg = arg.split(" ")
            ind = int(arg[0])
            if len(context.order_hists) > 0:
                perf = Perf()
                if perf.pnl is not None and len(perf.pnl) > ind:
                    pair = perf.pnl.iloc[ind]
                    code = pair.code
                    mp = {
                        "买入点": [pair.buy_date, pair.buy_price],
                        "卖出点": [pair.sell_date, pair.sell_price],
                    }
                    start = get_date_gap(pair.buy_date, 300, "lt")
                    end = get_date_gap(pair.sell_date, 200, "gt")
                    df = get_price(code, start=start, end=end)
                    kshow(df, code, mp)
                else:
                    print("策略还没有出现成对交易数据")
            else:
                print("没有股票交易数据！")

    def do_kg(self, arg):
        if arg == "":
            print(
                "Usage: \n\
                ----------------------------------------------------------------------------------------------------------------------\n\
                ⌨️命令格式：kg name                : 显示全局对象g中name属性对应列表中的数据，即g.name: List                    \n\
                                                    : g.name列表中数据项如需进行K线显示，需满足以下格式：                          \n\
                                                    : [股票代码，标注点1日期，标注点1价格，标注点2日期，标注点2价格，其他信息...]     \n\
                ⌨️命令格式：kg name n              : 显示全局对象g中name属性对应列表中股票的日K线，并标注信息点,n代表第n条数据      \n\
                -----------------------------------------------------------------------------------------------------------------------\n\
                "
            )
        else:
            arg = arg.split(" ")
            name = arg[0]
            try:
                g_list = getattr(g, arg[0])
            except AttributeError:
                print("全局对象g没有{}属性！".format(arg[0]))
                return True

            if not isinstance(g_list, list):
                print("全局对象g.{}属性不是list类型！".format(arg[0]))
                return True

            if len(arg) == 1:
                if len(g_list) > 0:
                    print_list(g_list)
                else:
                    print("全局对象g.{}属性无数据！".format(arg[0]))

            else:
                try:
                    item = g_list[int(arg[1])]
                    if len(item) >= 3:
                        code = item[0]
                        mp = {}
                        if util_date_valid(item[1]):
                            mp["标注点1"] = [item[1], float(item[2])]
                        if len(item) >= 5 and util_date_valid(item[3]):
                            mp["标注点2"] = [item[3], float(item[4])]
                        start = get_date_gap(item[1], 200, "lt")
                        end = get_date_gap(item[1], 50, "gt")
                        df = get_price(code, start=start, end=end)
                        if df is not None and len(df) > 1:
                            kshow(df, code, mp)
                except Exception as e:
                    print("输入格式错误或者全局对象g.{}属性格式不正确！".format(arg[0]))
                    print(e)

    def do_kshow(self, arg):
        if arg == "":
            self.print_kshow_usage()
        else:
            arg = arg.split(" ")
            if 'index' not in arg:
                end = context.current_dt
                code = arg[0]
                if len(arg) == 2:
                    count = int(arg[1])
                    if count < 0:
                        end = get_next_trade_day(context.current_dt, abs(count))
                        count = 500 + abs(count)
                else:
                    count = 500
                df = get_price(code, end=end, count=count)
                kshow(df, code)
            elif arg[0] == 'index':
                end = context.current_dt
                code = arg[1]
                if len(arg) == 3:
                    count = int(arg[2])
                    if count < 0:
                        end = get_next_trade_day(context.current_dt, abs(count))
                        count = 500 + abs(count)
                else:
                    count = 500
                df = get_price(code, end=end, count=count, market='index')
                kshow(df, code)
            else:
                self.print_kshow_usage()

    @staticmethod
    def print_kshow_usage():
        print(
            "Usage: \n\
            ----------------------------------------------------------------------------------------------------------------------\n\
            ⌨️命令格式：kshow 000001           : 从当前日期（或回测运行）查询指定股票代码的日K线，默认500条数据                   \n\
            ⌨️命令格式：kshow 000001 200       : 从当前日期（或回测运行）查询指定股票代码的日K线，显示设置的数据条数               \n\
            ⌨️命令格式：kshow 000001 -20       : 在回测状态下，查询当前日期前500条到后20条数据。                               \n\
            -----------------------------------------------------------------------------------------------------------------------\n\
            ⌨️命令格式：kshow index 000001     : 从当前日期（或回测运行）查询指数代码的日K线，默认500条数据                      \n\
            ⌨️命令格式：kshow index 000001 200 : 从当前日期（或回测运行）查询指数代码的日K线，显示设置的数据条数                  \n\
            -----------------------------------------------------------------------------------------------------------------------\n\
            "
        )

    def do_help(self, arg):
        if len(arg) > 0 and arg == 'kshow':
            self.print_kshow_usage()
        elif len(arg) > 0 and arg == 'info':
            self.print_info_usage()
        else:
            print("\n Possible commands are:")
            print("info ---- 查询策略运行数据")
            print("ks   ---- 查询交易股票的K线图")
            print("kg   ---- 显示全局对象g中name属性对应的数据和K线图")
            print("kshow --- 查询股票K线图")
            print("time ---- 查询策略时间")
            print("fn ------ 运行自定义语句")
            print("shell --- 运行外部程序")
            print("log ----- 设置日志输出级别")
            print("pause ----暂停策略运行")
            print("resume----恢复策略运行")
            print("cancel ---策略运行取消，退出交互环境")
            print("quit ---- 退出交互环境，回测仍在运行")
            print("exit ---- 程序完全退出")
            print("ls -- 列出当前路径 ")


if __name__ == '__main__':
    cli = Trace()
    cli.cmdloop()
