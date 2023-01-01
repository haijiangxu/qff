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

import argparse
import textwrap
import os
from datetime import datetime
from qff.frame.interface import set_run_freq, set_init_cash, set_backtest_period, set_strategy_name
from qff.frame.backtest import back_test_run
from qff.frame.simtrade import sim_trade_run
from qff.frame.backup import load_context
from qff.frame.context import context, RUNTYPE
from qff.tools.local import cache_path
from qff.tools.config import *
from qff.price.query import get_price
from qff.tools.kshow import kshow

# subprocess.Popen

__all__ = ['Command', 'BackTestCommand', 'SimTradeCommand', 'ResumeCommand', 'CreateCommand',
           'ConfigCommand', 'SaveCommand', 'DbinfoCommand', 'KshowCommand']


class Command:
    usage: str = ""
    summary: str = ""

    def __init__(self, name, sub_parser):
        self.parser = sub_parser.add_parser(name,
                                            prog=f'qff {name}',
                                            usage=self.usage,
                                            description=textwrap.dedent(self.__doc__),
                                            formatter_class=argparse.RawDescriptionHelpFormatter,
                                            help=self.summary,
                                            add_help=False
                                            )
        self.parser.add_argument('-h', '--help', help='显示当前帮助信息', action='help')
        self.add_options()

    def add_options(self):
        pass

    def main(self, args):
        pass


class BackTestCommand(Command):
    """
    使用qff框架对指定策略文件运行回测，以评价交易策略的效果。
    1. 按qff框架规范编写的策略文件，可以通过本接口在终端窗口运行回测，
    2. 接口可设置策略回测涉及历史数据的开始日期、结束日期、初始资金以及运行频率等参数。
    3. 运行参数可在策略文件中设置，但通过本接口设置的参数会替代策略文件中的相同参数。
    """
    usage = f"\nqff run <strategy_file> [options]"
    summary = "对策略文件运行回测"

    def __init__(self, sub_parser):
        super().__init__('run', sub_parser)

    def add_options(self) -> None:
        self.parser.add_argument("strategy_file", help="策略文件名称路径", nargs='?')
        self.parser.add_argument("--name", help="策略名称,默认文件名", metavar="<name>")
        self.parser.add_argument("--freq", choices=['day', 'min'],
                                 help="设置回测执行频率,可选('day', 'min')", metavar="<freq>")
        self.parser.add_argument("--cash", type=int, help="设置账户初始资金", metavar="<money>")
        self.parser.add_argument("--start", type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
                                 help="设置回测开始日期", metavar="<YYYY-MM-DD>")
        self.parser.add_argument("--end", type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
                                 help="设置回测结束日期", metavar="<YYYY-MM-DD>")

    def main(self, args):
        if args.strategy_file is None:
            print('Error:参数strategy_file必须指定！\n')
            self.parser.print_help()
            return

        strategy_file = args.strategy_file
        if not os.path.exists(strategy_file):
            print(f'输入的策略文件不存在!{strategy_file}')
            return

        if args.name:
            set_strategy_name(args.name)
        else:
            set_strategy_name(os.path.basename(strategy_file).split('.')[0])
        if args.freq:
            set_run_freq(args.freq)
        if args.cash is not None:
            set_init_cash(int(args.cash))
        if args.start and args.end:
            set_backtest_period(args.start, args.end)
        elif args.start:
            set_backtest_period(start=args.start)
        elif args.end:
            set_backtest_period(end=args.end)

        back_test_run(strategy_file)


class SimTradeCommand(Command):
    """
    使用qff框架对指定策略文件运行模拟交易，以验证交易策略的效果。
    """
    usage = f"\nqff sim <strategy_file> [options]"
    summary = "对策略文件运行模拟交易"

    def __init__(self, sub_parser):
        super().__init__('sim', sub_parser)

    def add_options(self) -> None:
        self.parser.add_argument("strategy_file", help="策略文件名称路径", nargs='?')
        self.parser.add_argument("--name", help="策略名称,默认文件名", metavar="<name>")
        self.parser.add_argument("--freq", choices=['day', 'min', 'tick'],
                                 help="设置回测执行频率,可选('day', 'min', 'tick')", metavar="<freq>")
        self.parser.add_argument("--cash", type=int, help="设置账户初始资金", metavar="<money>")

    def main(self, args):
        if args.strategy_file is None:
            print('Error:参数strategy_file必须指定！\n')
            self.parser.print_help()
            return
        strategy_file = args.strategy_file
        if not os.path.exists(strategy_file):
            print(f'输入的策略文件不存在!{strategy_file}')
            return

        if args.name:
            set_strategy_name(args.name)
        else:
            set_strategy_name(os.path.basename(strategy_file).split('.')[0])
        if args.freq:
            set_run_freq(args.freq)
        if args.cash is not None:
            set_init_cash(int(args.cash))

        sim_trade_run(strategy_file)


class ResumeCommand(Command):
    """
    恢复前期暂停的策略运行,可以调整策略文件，一般用于模拟交易中。
    在回测或模拟交易过程的交互环境中，输入pause命令，可备份当前运行环境变量，并退出回测/模拟交易过程。
    通过设置backup_file参数，指定备份文件恢复前期暂停的回测/模拟交易过程。
    backup_file参数可输入备份文件的完整路径，也可只输入文件名称，系统将在默认保存备份文件目录中查找并载入。
    本命令默认会调取原有策略文件执行，如果策略文件改名或移动,可通过--strategy参数指定新的策略文件运行。

    """
    usage = f"\nqff resume <backup_file> [options]"
    summary = "恢复前期暂停的策略运行"

    def __init__(self, sub_parser):
        super().__init__('resume', sub_parser)

    def add_options(self) -> None:
        self.parser.add_argument("backup_file", help="策略备份文件名称", nargs='?')
        self.parser.add_argument("--strategy", help="可选重新指定策略文件名称", metavar='<file>')

    def main(self, args):
        if args.backup_file is None:
            print('Error:参数backup_file必须指定！\n')
            self.parser.print_help()
            return
        backup_file = args.backup_file
        if not os.path.exists(backup_file):
            backup_file = '{}{}{}'.format(cache_path, os.sep, os.path.basename(backup_file))
            if not os.path.exists(backup_file):
                print(f'输入的策略文件不存在!{backup_file}')
                return
        try:
            load_context(backup_file)
        except Exception as e:
            print("导入context备份文件失败:{}".format(e))
            return

        if args.strategy and os.path.exists(args.strategy):
            strategy_file = args.strategy
        else:
            strategy_file = context.strategy_file

        if context.run_type == RUNTYPE.SIM_TRADE:
            sim_trade_run(strategy_file, resume=True)
        else:
            back_test_run(strategy_file, resume=True)


class CreateCommand(Command):
    """
    在当前目录创建一个模板策略文件，方便快速入手策略编写。
    """
    usage = f"\nqff create"
    summary = "创建一个简单的策略文件样例"

    def __init__(self, sub_parser):
        super().__init__('create', sub_parser)

    def main(self, args):
        name = input("请输入待创建的策略文件名称[默认：example.py]:")
        if name == '':
            name = 'example.py'
        if name[-3:] != '.py':
            name += '.py'
        file_name = '{}{}{}'.format(os.getcwd(), os.sep, name)

        import requests
        resp = requests.get(
            'https://github.com/haijiangxu/qff/blob/master/example/example.py'
        )

        if resp.ok:
            with open(file_name, "wb") as code:
                code.write(resp.content)
            print(f'策略文件{name}创建成功！')
        else:
            print("获取样例代码失败！")


class ConfigCommand(Command):
    """
    管理qff全局参数配置。

    子命令：
    - list： 列出所有配置参数
    - edit： 利用默认编辑器编辑配置文件
    - get:   读取某个配置项的值
    - set:   设置某个配置项的值 section.option = value
    - unset: 取消某个配置项的设置

    qff 配置项设置
    """
    usage = """
    qff config <subcommand> [options]
    eg:
    qff config list
    qff config edit
    qff config get section.option
    qff config set section.option value
    qff config unset section.option
    """
    summary = "配置qff全局参数"

    def __init__(self, sub_parser):
        super().__init__('config', sub_parser)

    def add_options(self) -> None:
        self.parser.add_argument("subcommand", help="配置子命令", nargs='?')

        self.parser.add_argument("options", help="子命令所需参数", nargs='*')

    def main(self, args):
        # if args.subcommand is None:
        #     self.parser.print_help()

        try:
            if args.subcommand == 'list':
                list_config()
            elif args.subcommand == 'edit':
                edit_config()
            else:
                params = str(args.options[0]).split('.')
                if len(params) != 2:
                    raise ValueError
                section = params[0]
                option = params[1]
                if args.subcommand == 'get':
                    print(get_config(section, option))
                elif args.subcommand == 'unset':
                    unset_config(section, option)
                elif args.subcommand == 'set':
                    value = args.options[1]
                    set_config(section, option, value)
                else:
                    raise ValueError()
        except:
            print('Error:qff config命令参数错误！\n')
            self.parser.print_help()


class SaveCommand(Command):
    """
    存储更新qff数据库。

    子命令：
        ----------------------------------------------------------------------------------------------------------------------\n\
        ⌨️命令格式：qff save all               : 保存/更新所有数据                                                        \n\
        ⌨️命令格式：qff save day               : 保存/更新股票日数据、指数日数据、ETF日数据                                   \n\
        ⌨️命令格式：qff save min               : 保存/更新股票分钟数据、指数分钟数据、ETF分钟数据                              \n\
        -----------------------------------------------------------------------------------------------------------------------\n\
        ⌨️命令格式：qff save stock_list        : 保存/更新股票列表数据                                                        \n\
        ⌨️命令格式：qff save stock_day         : 保存/更新股票日线数据                                                        \n\
        ⌨️命令格式：qff save index_day         : 保存/更新指数日线数据                                                        \n\
        ⌨️命令格式：qff save etf_day           : 保存/更新ETF日线数据                                                        \n\
        ⌨️命令格式：qff save stock_min         : 保存/更新股票分钟数据                                                        \n\
        ⌨️命令格式：qff save index_min         : 保存/更新指数分钟数据                                                        \n\
        ⌨️命令格式：qff save etf_min           : 保存/更新ETF分钟数据                                                        \n\
        ⌨️命令格式：qff save stock_xdxr        : 保存/更新日除权除息数据                                                      \n\
        ⌨️命令格式：qff save stock_block       : 保存/更新板块股票数据                                                        \n\
        ⌨️命令格式：qff save report            : 保存/更新股票财务报表                                                        \n\
        ⌨️命令格式：qff save valuation         : 保存/更新股票市值数据                                                        \n\
        ⌨️命令格式：qff save mtss              : 保存/更新融资融券数据                                                        \n\
        ⌨️命令格式：qff save index_stock       : 保存/更新指数成分股信息                                                      \n\
        --------------------------------------------------------------------------------------------------------------------\n\
        ⌨️命令格式：qff save init_info         : 初始化股票列表、指数列表、ETF列表                                        \n\
        ⌨️命令格式：qff save init_name         : 初始化股票历史更名数据                                                        \n\
        ⌨️命令格式：qff save save_delist       : 保存退市股票的日数据和分钟数据                                                 \n\
        ----------------------------------------------------------------------------------------------------------------------\n\

    """
    usage = f"\nqff save <subcommand>"
    summary = "存储更新qff数据库"

    def __init__(self, sub_parser):
        super().__init__('save', sub_parser)

    def add_options(self) -> None:
        self.parser.add_argument("subcommand", help="存储更新数据库子命令", nargs='?')

    def main(self, args):
        from qff.store.update_all import qff_save
        # print(args)
        if args.subcommand is None or \
                args.subcommand not in ['all', 'day', 'min', 'stock_list', 'stock_day', 'index_day', 'etf_day',
                                        'stock_min', 'index_min', 'etf_min', 'stock_xdxr', 'stock_block', 'report',
                                        'valuation', 'mtss', 'index_stock', 'init_info', 'init_name', 'save_delist']:

            self.parser.print_help()
            return
        qff_save(args.subcommand)


class DbinfoCommand(Command):
    """
    显示qff数据库的当前信息
    1.数据库qff有多少个数据集，且每个数据集的记录数量和字段xinx
    2.数据库最后一次数据更新时间
    """
    usage = f"\nqff dbinfo"
    summary = "查询qff数据库信息"

    def __init__(self, sub_parser):
        super().__init__('dbinfo', sub_parser)

    def add_options(self) -> None:
        pass

    def main(self, args):
        from qff.store.update_all import mongo_info
        mongo_info()


class KshowCommand(Command):
    """
    查询股票数据，并以K线图展示。
    """
    usage = f"\nqff kshow <security> [options]"
    summary = "K线图展示股票数据"

    def __init__(self, sub_parser):
        super().__init__('kshow', sub_parser)

    def add_options(self) -> None:
        self.parser.add_argument("security", help="股票或指数代码", nargs='?')
        self.parser.add_argument("--count", type=int, help="返回记录条数", metavar="<500>", default=500)
        self.parser.add_argument("--index", action='store_true', help="是否为指数代码")
        self.parser.add_argument("--start", type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
                                 help="开始日期", metavar="<YYYY-MM-DD>")
        self.parser.add_argument("--end", type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
                                 help="结束日期", metavar="<YYYY-MM-DD>")

    def main(self, args):
        if args.security is None:
            print('Error:security必须指定！\n')
            self.parser.print_help()
            return
        if args.index:
            market = 'index'
        else:
            market = 'stock'

        df = get_price(args.security, start=args.start, end=args.end, count=args.count, market=market)
        kshow(df, args.security, index=args.index)
