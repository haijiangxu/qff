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
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qff.frame.entry import entry

if __name__ == '__main__':
    entry()
