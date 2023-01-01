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
import platform
import pandas as pd
from datetime import datetime
from qff.tools.logs import log
from qff.price.fetch import fetch_current_ticks
from qff.tools.local import back_test_path, sim_trade_path
from qff.frame.context import context, Position, RUNTYPE
from qff.frame.order import Order, ORDER_OPEN, ORDER_DEAL
from qff.price.cache import get_current_data, clear_current_data
from qff.frame.risk import Risk
from qff.frame.performance import Performance


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
        --today_amount: 今开仓量
      4、修改Portions对象中的今日开仓数据，及可出售数量，以保障今日买入的股票明日可以卖出
      5、仓位为0的股票，需删除该笔记录
    
    """
    # 一、处理order_list
    order: Order
    for order in context.order_list.values():
        if order.status == ORDER_OPEN:
            order.cancel()
        elif order.status == ORDER_DEAL:
            do = order.__dict__
            if context.df_orders is None:
                context.df_orders = pd.DataFrame([do])
            else:
                # context.history_orders = pd.concat([context.history_orders, pd.DataFrame([dict_order])])
                # context.df_orders = context.df_orders.append(pd.Series(do), ignore_index=True)
                context.df_orders = pd.concat([context.df_orders, pd.DataFrame([do])])
    context.order_list.clear()

    # 二、账户及仓位信息处理
    # 1、以当日收盘价格更新账户和仓位信息
    acc = context.portfolio
    acc.positions_assets = 0
    pst: Position
    for pst in acc.positions.values():
        pst.price = get_current_data(pst.security).last_price  # 更新每日的收盘价
        pst.value = round(pst.price * pst.total_amount, 2)  # 股票当日价值
        acc.positions_assets += pst.value  # 账户持仓价值

    acc.total_assets = round(acc.available_cash + acc.positions_assets + acc.locked_cash, 2)  # 账户当日总价值
    # 基准指数当日价值
    if context.run_type == RUNTYPE.BACK_TEST:
        acc.benchmark_assets = round(context.bm_data.loc[context.current_dt[0:10]].close
                                     / context.bm_start * acc.starting_cash, 2)
    elif context.run_type == RUNTYPE.SIM_TRADE:
        acc.benchmark_assets = round(fetch_current_ticks(context.benchmark, market='index')['price']
                                     / context.bm_start * acc.starting_cash, 2)

    # 2、生成收益曲线
    if context.df_asset is None:  # 初始化收益曲线
        asset_init = {
            "date": context.previous_date[0:10],
            "acc_value": context.portfolio.starting_cash,   # 当日账户总资产
            "bm_value": context.portfolio.starting_cash,    # 基准对应的总资产
            "pos_value": 0                                  # 当日持仓总价值
        }
        context.df_asset = pd.DataFrame([asset_init, ])

    asset_cur = {
        "date": context.current_dt[0:10],
        "acc_value": acc.total_assets,       # 当日账户总资产
        "bm_value": acc.benchmark_assets,    # 基准对应的总资产
        "pos_value": acc.positions_assets    # 当日持仓总价值

    }
    # context.df_asset = context.df_asset.append(pd.Series(asset_cur), ignore_index=True)
    context.df_asset = pd.concat([context.df_asset,  pd.DataFrame([asset_cur, ])])

    # 3、生成持仓详情历史记录
    dp = {"date": context.current_dt[0:10]}
    for pst in acc.positions.values():
        dp = {**dp, **pst.__dict__}
        if context.df_positions is None:
            context.df_positions = pd.DataFrame([dp])
        else:
            # context.df_positions = context.df_positions.append(pd.Series(dp), ignore_index=True)
            context.df_positions = pd.concat([context.df_positions, pd.DataFrame([dp])])
    #  4、修改Portions对象中的今日开仓数据，及可出售数量，以保障今日买入的股票明日可以卖出
    #  5、仓位为0的股票，需删除该笔记录
    for pst in list(acc.positions.values()):
        if pst.today_amount > 0:
            pst.closeable_amount += pst.today_amount
            pst.today_amount = 0
        if pst.total_amount == 0:
            acc.positions.pop(pst.security)

    # 清空cache缓存
    clear_current_data()
    log.info("settle_by_day : 当日结算完成")


def profit_analyse():
    """
    收益分析
    :return:

    用于生成回测结果数据，包括
    1、收益曲线数据文件，excel格式
    2、交易记录数据文件，excel格式
    3、每日仓位记录文件，excel格式
    4、回测收益对比图文件
    5、计算总的风险指标
    """

    out_path = back_test_path if context.run_type == RUNTYPE.BACK_TEST else sim_trade_path
    # strategy_name = os.path.basename(sys.argv[0]).split('.')[0]
    out_path = '{}{}{}'.format(out_path, os.sep, context.strategy_name)
    os.makedirs(out_path, exist_ok=True)
    data_filename = '{}{}{}-{}.xlsx'.format(out_path, os.sep, "strategy_result",
                                            str(datetime.now().strftime('%Y-%m-%d %H-%M-%S')))

    # 1、将仓位中还有的股票，都按最后一天的收盘价卖出成交
    #

    # 2、收益曲线数据文件，excel格式
    # df_profit = pd.DataFrame(data=context.df_asset, columns=context.df_asset[0].keys())

    # 3、交易记录数据文件，excel格式 context.history_orders
    # df_order = None
    # if len(context.df_orders) > 0:
    #     df_order = pd.DataFrame(data=context.df_orders, columns=context.df_orders[0].keys())

    # 4、每日仓位记录文件，excel格式  context.history_positions
    # df_positions = None
    # if len(context.df_positions) > 0:
    #     df_positions = pd.DataFrame(data=context.df_positions, columns=context.df_positions[0].keys())

    writer = pd.ExcelWriter(data_filename)
    context.df_asset.to_excel(writer, sheet_name='每日资产收益表', index=False, header=True)
    if context.df_orders is not None:
        context.df_orders.to_excel(writer, sheet_name='股票订单列表', index=False, header=True)
    if context.df_positions is not None:
        context.df_positions.to_excel(writer, sheet_name='每日持仓数据表', index=False, header=True)

    # 5、计算风险分析指标
    risk = Risk(asset=context.df_asset)
    df_risk = pd.Series(data=risk.message)
    df_risk.to_excel(writer, sheet_name='风险指标')

    if context.df_orders is not None:
        perf = Performance(df_order=context.df_orders)
        df_perf = pd.Series(data=perf.message)
        df_perf.to_excel(writer, sheet_name='绩效指标')
        # perf.plot_pnlratio()
        # perf.plot_pnlmoney()

    writer.save()

    # 4、生成收益曲线图文件
    chart_filename = '{}{}{}-{}.html'.format(out_path, os.sep, 'strategy_chart',
                                             str(datetime.now().strftime('%Y-%m-%d %H-%M-%S')))

    risk.show_chart(chart_filename)

    if platform.system() == 'Windows' and context.run_type == RUNTYPE.BACK_TEST:
        os.startfile(data_filename)
        # os.startfile(chart_filename)


def show_chart(data_excel):
    df = pd.read_excel(data_excel, sheet_name='每日资产收益表')
    risk = Risk(df)
    risk.show_chart()
