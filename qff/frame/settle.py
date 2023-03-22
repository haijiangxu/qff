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

# 结算模块
import os
import pickle
from qff.tools.logs import log
from qff.tools.local import back_test_path, sim_trade_path
from qff.tools.utils import auto_file_name
from qff.frame.context import context
from qff.frame.const import RUN_TYPE, ORDER_STATUS
from qff.frame.order import Order
from qff.frame.portfolio import Portfolio
from qff.price.cache import clear_current_data
from qff.frame.stats import stats_report


def settle_by_day():
    """
    每日收盘后结算处理，执行时间为15：30
    :return:
    """
    """
    一、处理order_list
    1、将其中open状态的订单，执行取消操作。
    2、将其中held状态的订单，复制到deal_list中。
    3、生成交易详情list，每个订单为一个 dict，键的含义为：
       --time: 交易时间
       --action: 开平仓，'open'/'close',
       --amount: 数量,
       --commission: 手续费,
       --filled: 已成交量,
       --gains: 收益,
       --limit_price: 限价单委托价,
       --match_time: 最新成交时间,
       --price: 成交价,
       --security: 标的代码,
       --security_name: 标的名,
       --side: 仓位方向,
       --status: 订单状态,
       --time: 委托时间,
       --type: 委托方式，市价单/限价单
    
    4、清空order_list
    二、账户及仓位信息处理
    1、以当日收盘价格更新账户和仓位信息
    2、生成收益曲线数据，每个交易日是一个 dict，键的含义为：
        --time: 时间
        --returns: 收益，
        --benchmark_returns: 基准收益
        --total_value：市值
        --benchmark_value：基准价值
    3、生成持仓详情. 返回一个 list，默认取所有回测时间段内的数据。每个交易日为一个 dict，键的含义为：
        --time: 时间
        --amount: 持仓数量,
        --avg_cost: 开场均价,
        --closeable_amount: 可平仓数量,
        --daily_gains: 当日收益,
        --gains: 累积收益,
        --hold_cost: 持仓成本（期货）,
        --margin: 保证金,
        --price: 当前价格,
        --security: 标的代码,
        --security_name: 标的名,
        --side: 仓位方向,
        --today_open_amount: 今开仓量
      4、修改Portions对象中的今日开仓数据，及可出售数量，以保障今日买入的股票明日可以卖出
      5、仓位为0的股票，需删除该笔记录
    
    """
    # 一、处理order_list
    _order: Order
    for _order in context.order_list.values():
        if _order.status == ORDER_STATUS.OPEN:
            _order.cancel()
        elif _order.status == ORDER_STATUS.DEAL:
            do = _order.message
            context.order_hists.append(do)

    context.order_list.clear()

    # 二、账户及仓位信息处理
    acc: Portfolio = context.portfolio
    if len(context.asset_hists) == 0:  # 初始化账户资产信息列表
        context.asset_hists.append(acc.init_message)

    context.asset_hists.append(acc.message)

    # 3、生成持仓详情历史记录
    for pst in acc.positions.values():
        context.positions_hists.append(pst.message)

    #  4、修改Portions对象中的今日开仓数据，及可出售数量，以保障今日买入的股票明日可以卖出
    #  5、仓位为0的股票，需删除该笔记录
    for pst in list(acc.positions.values()):
        if pst.today_open_amount > 0:
            pst.closeable_amount += pst.today_open_amount
            pst.today_open_amount = 0
        if pst.total_amount == 0:
            acc.positions.pop(pst.security)

    # 6. 更新portfolio对象中上一日总资产数据
    acc.pre_total_assets = acc.total_assets

    # 清空cache缓存
    clear_current_data()
    log.info("settle_by_day : 当日结算完成")


def profit_analyse():
    """
    收益分析
    """
    if context.output_dir is None:
        out_path = back_test_path if context.run_type == RUN_TYPE.BACK_TEST else sim_trade_path
    else:
        out_path = context.output_dir

    if context.run_type == RUN_TYPE.BACK_TEST:
        pkl_file = '{}{}{}.pkl'.format(out_path, os.sep, context.strategy_name)
        pkl_file = auto_file_name(pkl_file)

        with open(pkl_file, 'wb') as pk_file:
            pickle.dump(context, pk_file)

    report_file = os.path.join(out_path, '策略运行报告({}).html'.format(context.strategy_name))
    report_file = auto_file_name(report_file)
    stats_report(context, report_file)
