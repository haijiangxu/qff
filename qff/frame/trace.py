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
from qff.frame.context import context, Portfolio, Position, g
from qff.frame.const import RUN_TYPE, RUN_STATUS
from qff.price.cache import get_current_data
from qff.frame.risk import Risk
from qff.frame.perf import Perf
from qff.price.fetch import fetch_current_ticks
from qff.price.query import get_price
from qff.tools.kshow import kshow
from qff.tools.date import get_next_trade_day, get_trade_gap, get_date_gap, util_date_valid
from zenlog import logging


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

    def __init__(self):
        Cmd.__init__(self)
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
        status_tb = ['停止','运行中','已完成','失败','','取消','暂停']
        msg = {
            "策略名称": context.strategy_name,
            "框架类型": '回测运行' if context.run_type == RUN_TYPE.BACK_TEST else '模拟实盘',
            "当前状态": status_tb[context.status],
            "运行频率": context.run_freq,
            "开始日期": context.start_date,
            "结束日期": context.end_date,
            "回测周期": get_trade_gap(context.start_date,context.end_date),
            "当前日期": context.current_dt,
            "运行天数": get_trade_gap(context.start_date,context.current_dt[:10]),
            "基准指数": context.benchmark,
            "初始资金": context.portfolio.starting_cash,
        }
        print_dict(msg, title='回测框架/模拟实盘运行基本参数')

    # info 1 查询当前账户资金及持股情况
    @staticmethod
    def info_acc():
        acc: Portfolio = context.portfolio
        acc.positions_assets = 0
        pst: Position
        for pst in acc.positions.values():
            pst.price = get_current_data(pst.security).last_price  # 更新每日的收盘价
            pst.value = round(pst.price * pst.total_amount, 2)  # 股票当日价值
            acc.positions_assets += pst.value  # 账户持仓价值

        acc.total_assets = round(acc.available_cash + acc.positions_assets + acc.locked_cash, 2)  # 账户当日总价值
        # 基准指数当日价值
        if context.run_type == RUN_TYPE.BACK_TEST:
            acc.benchmark_assets = round(context.bm_data.loc[context.current_dt[0:10]].close
                                         / context.bm_start * acc.starting_cash, 2)
        elif context.run_type == RUN_TYPE.SIM_TRADE:
            acc.benchmark_assets = round(fetch_current_ticks(context.benchmark, market='index')['price']
                                         / context.bm_start * acc.starting_cash, 2)
        print("当前日期:{}".format(context.current_dt))
        msg = {
            "初始资金": acc.starting_cash,
            "可用资金": '{:.2f}'.format(acc.available_cash),
            "锁单资金": '{:.2f}'.format(acc.locked_cash),
            "股票市值": '{:.2f}'.format(acc.positions_assets),
            "账户总资产": '{:.2f}'.format(acc.total_assets),
            "浮动盈亏": round(acc.total_assets - acc.starting_cash, 2),
            "仓位": '{:.2%}'.format(acc.positions_assets / acc.total_assets),
            "基准总价值": '{:.2f}'.format(acc.benchmark_assets)
        }
        print_dict(msg, title='账户当前资金情况')

        table = []
        for pst in acc.positions.values():
            dp = list(pst.__dict__.values())
            table.append(dp)
        df = pd.DataFrame(data=table, columns=["股票代码", "建仓时间", "当前成本", "累计成本", "最后交易时间",
                                               "挂单冻结仓位", "可交易仓位", "今开仓位", "总仓位", "当前单价", "股票价值"])

        print_df(df, '账户当前持仓情况')

    @staticmethod
    def info_asset():
        if context.df_asset is not None:
            df: pd.DataFrame = context.df_asset.copy().reset_index(drop=True)
            df.columns = ['日期', '账户总资产', '基准总资产', '持仓总价值']
            print_df(df, '收益曲线数据')
        else:
            print("还未生成交易曲线数据")

    @staticmethod
    def info_risk():
        print("当前日期:{}".format(context.current_dt))
        if context.df_asset is not None:
            risk = Risk(asset=context.df_asset.copy())
            print_dict(risk.message, '策略风险系数风险')

        else:
            print("还未生成交易曲线数据")

    @staticmethod
    def info_chart():
        if context.df_asset is not None:
            risk = Risk(asset=context.df_asset.copy())
            risk.show_chart()
        else:
            print("还未生成交易曲线数据")

    @staticmethod
    def info_perf():
        print("当前日期:{}".format(context.current_dt))

        if context.df_orders is not None:
            perf = Perf(df_order=context.df_orders)
            if perf.pnl is not None:
                print_dict(perf.message, '策略绩效分析')
                df = perf.pnl.reset_index().reset_index()
                print_df(df, '账户交易配对情况')
            else:
                print("策略还没有出现成对交易数据")
        else:
            print("没有股票交易数据！")

    @staticmethod
    def info_hist_order():
        if context.df_orders is not None:
            df: pd.DataFrame = context.df_orders.copy().reset_index(drop=True)
            df = df.drop(['id', 'status', 'add_time', 'cancel_time', '_callback'], axis=1, inplace=False)
            df['is_buy'] = df['is_buy'].apply(lambda x: '买入' if x else '卖出')
            df = df.sort_values('security', )
            df.columns = ['股票代码', '交易方向', '下单数量', '交易时间', '订单类型', '下单单价', '成交数量', '成交金额',
                          '成交单价', '手续费', '订单盈亏']
            print_df(df, '历史交易记录')
        else:
            print("没有股票交易数据！")

    @staticmethod
    def info_current_order():
        # 打印当日委托订单数据

        # for order in context.order_list.values():
        #     df = df.append(pd.Series(order.message), ignore_index=True)
        order_list = [order.message for order in context.order_list.values()]
        if len(order_list) == 0:
            df = pd.DataFrame(columns=['订单编号', '股票代码', '交易方向', '下单时间', '成交状态', '委托数量',
                                       '委托价格', '订单类型', '成交时间', '成交单价', '成交数量', '成交金额', '交易费用'])
        else:
            df = pd.DataFrame(order_list)

        print_df(df, '当日委托订单')

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
        logger = logging.getLogger('')
        if arg is None or arg == '':
            if logging.root.level == logging.ERROR:
                logger.setLevel(logging.INFO)
            else:
                logger.setLevel(logging.ERROR)
        elif arg == 'info':
            logger.setLevel(logging.INFO)
        elif arg == 'warn':
            logger.setLevel(logging.WARN)
        elif arg == 'debug':
            logger.setLevel(logging.DEBUG)

        elif arg == 'error':
            logger.setLevel(logging.ERROR)
        else:
            print("设置日志级别：debug,info,warn,error ")

    def do_pause(self, arg):
        context.status = RUN_STATUS.PAUSED
        time.sleep(1)
        print("暂停回测任务，执行quit命令退出交互环境！")

    def do_resume(self, arg):
        print("恢复策略运行需通过退出本交互环境\n")
        print("在终端环境下运行 python qff 策略文件名 -r")

    def do_cancel(self, arg):
        context.status = RUN_STATUS.CANCELED
        return True

    def do_quit(self, arg):  # 定义quit命令所执行的操作
        return True

    def do_exit(self, arg):  # 定义quit命令所执行的操作
        sys.exit(1)

    def do_ls(self, arg):
        print(os.path.dirname(os.path.abspath(__file__)))

    def do_ks(self, arg):
        if arg == "":
            print("当前日期:{}".format(context.current_dt))

            if context.df_orders is not None:
                perf = Perf(df_order=context.df_orders)
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
            if context.df_orders is not None:
                perf = Perf(df_order=context.df_orders)
                if perf.pnl is not None and len(perf.pnl) > ind:
                    pair = perf.pnl.iloc[ind]
                    code = pair.name
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
                        start = get_date_gap(item[1], 300, "lt")
                        end = get_date_gap(item[1], 200, "gt")
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
            ⌨️命令格式：info 2   : 输出策略运行每日收益曲线数据                                                   \n\
            ⌨️命令格式：info 3   : 输出策略运行历史订单交易数据                                                   \n\
            ⌨️命令格式：info 4   : 输出策略运行当日订单委托信息                                                   \n\
            ----------------------------------------------------------------------------------------------------------------------\n\
            ⌨️命令格式：info 5   : 输出策略运行收益曲线图表                                                      \n\
            ⌨️命令格式：info 6   : 输出策略风险分析指标数据                                                      \n\
            ⌨️命令格式：info 7   : 输出策略绩效分析指标数据                                                      \n\
            ----------------------------------------------------------------------------------------------------------------------\n\
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
            print("pause ----暂停回测任务")
            print("resume----恢复回测任务")
            print("cancel ---回测任务取消，退出交互环境")
            print("quit ---- 退出交互环境，回测仍在运行")
            print("exit ---- 程序完全退出")
            print("ls -- 列出当前路径 ")


if __name__ == '__main__':
    cli = Trace()
    cli.cmdloop()
