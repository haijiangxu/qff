#!/opt/conda/bin/python
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
qff 框架命令行接口函数入口
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import List
import argparse
import textwrap
from typing import Dict, Optional
from qff import __version__
from qff.frame.cli import *


desc = """
QFF是一个量化金融框架Python包，用于为个人提供本地的回测和模拟交易环境，使用户更加专注于交易策略的编写。
框架具有以下特点：
1. 提供数据爬取-数据存储-策略编写-策略分析-策略回测-模拟交易等一站式解决方案；
2. 提供优雅的策略编写接口（类似聚宽），方便用户快速入门；
3. 提供本地的运行环境以提升策略运行效率；
4. 提供丰富的数据接口，以获取免费的股票和市场数据；
5. 提供实用的辅助功能，如：指标计算、交易系统框架等，尽量简化策略编写。

本命令为qff框架命令行接口，本接口可方便执行以下命令.
"""


def main(args: Optional[List[str]] = None) -> int:
    if args is None:
        args = sys.argv[1:]
    if len(args) == 0:
        args = ['-h']

    parser = argparse.ArgumentParser(
        prog="qff",
        usage=f"\nqff <command> [options]",
        description=textwrap.dedent(desc),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False
    )

    parser.add_argument('-v', '--version', help='显示qff当前版本', action='version', version=f'{get_qff_version()}')
    parser.add_argument('-h', '--help', help='显示当前帮助信息', action='help')

    # for key in commands_dict:
    sub_parser = parser.add_subparsers(metavar='命令列表', dest='cmd')

    cmd_dict: Dict[str, Command] = {
        'run': RunCommand(sub_parser),
        'sim': SimTradeCommand(sub_parser),
        'resume': ResumeCommand(sub_parser),
        'config': ConfigCommand(sub_parser),
        'create': CreateCommand(sub_parser),
        'save': SaveCommand(sub_parser),
        'drop': DropCommand(sub_parser),
        'dbinfo': DbinfoCommand(sub_parser),
        'kshow': KshowCommand(sub_parser)
    }

    args = parser.parse_args(args)
    # print(args)
    cmd_dict[args.cmd].main(args)
    return 0


def get_qff_version() -> str:

    return "qff {} from {} (python {})".format(
        __version__,
        os.path.abspath(os.path.dirname(__file__)),
        "{}.{}".format(*sys.version_info),
    )


if __name__ == '__main__':
    main()

