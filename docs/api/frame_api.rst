
===========================================
 基础API
===========================================


策略程序接口
==================
.. note::
    用户编写的策略文件需实现以下部分策略程序接口函数，才能被QFF框架识别并正确执行。

.. _api_initialize:

initialize - 策略初始化
---------------------------

..  py:function:: initialize()

初始化函数 - 在回测和实时模拟交易只会在启动的时候触发一次，用于初始一些全局变量。
作为策略文件的入口，**本方法必须实现。**

在初始化函数中，除了初始化全局变量，用户可以设置基准、交易费率、固定滑点等参数。
另外通过调用 :func:`.run_daily` ，还可以配置定时运行的策略函数，用以替代其他的框架函数。

示例:

    ..  code-block:: python

        def initialize():

            # 设置指数基准
            set_benchmark(security="000300")
            # 定义一个全局变量, 保存要操作的股票
            g.security = ['000001', '000002']
            # 定义运行函数
            run_daily(market_open, run_time='09:50')

            log.info("initialize : 初始化运行")



.. _api_handle_data:

handle_data - 盘中策略运行函数(可选)
------------------------------------------

..  py:function:: handle_data()

盘中策略运行函数，该函数每个单位时间会调用一次, 如果按天回测,则每天调用一次,如果按分钟,则每分钟调用一次。
如果在initialize()函数中run_daily设置了盘中策略函数，则本函数可以不实现。

**该函数运行的时间是股票的交易时间，即 9:31 - 15:00。**

该函数在回测中的非交易日是不会触发的（如回测结束日期为2021年1月5日，则程序在2022年1月1日-3日时，handle_data不会运行，4日继续运行）。

对于使用日级回测或模拟， 策略内获取到逻辑时间(context.current_dt)是 9:31。

示例：

 ..  code-block:: python

        def handle_data():
            for i in g.security:
                # 获取当前时间点的股票数据
                data = get_current_data(i)
                last_price = data.last_close
                average_price = data.mavg(20, 'close')
                # 获取账户剩余资金
                cash = context.portfolio.available_cash
                if last_price > average_price:
                    # 下单买入指定金额的股票
                    order_value(i, cash)
                elif last_price < average_price:
                    # 卖出指定股票
                    order_target(i, 0)


        # 在交易时间段内的策略函数中，使用 :func:`get_current_data` 来获取当前时间点的数据，此数据只在这一个时间点有效,请不要存起来到下一个 handle_data 再用。

        # :class:`.Context` 为全局变量，在策略函数中可以访问，但不能对context对象属性进行修改和赋值。



.. _api_before_trading_start:

before_trading_start - 开盘前运行策略(可选)
--------------------------------------------------

..  py:function:: before_trading_start()


开盘前运行函数，该函数会在每天开始交易前被调用一次, 您可以在这里添加一些每天都要初始化的东西。比如根据历史量价数据或基本面数据，
选择符合策略条件的股票加入股票池，再根据当日开盘后的表现，进行买入或卖出。

**该函数依据的时间是股票的交易时间，即该函数启动时间为'09:00'。**

示例:

 ..  code-block:: python

        def before_trading_start():
            log.info(str(context.current_dt))

.. _api_after_trading_end:

after_trading_end - 收盘后运行策略(可选)
--------------------------------------------------

..  py:function:: after_trading_end()

收盘后运行函数，该函数会在每天结束交易后被调用一次, 您可以在这里添加一些每天收盘后要执行的内容。
这个时候所有未完成的订单已经取消。

**该函数依据的时间是股票的交易时间，即该函数启动时间为 15:30。**

示例:

 ..  code-block:: python

        def after_trading_end():
            log.info(str(context.current_dt))

.. _api_on_strategy_end:

on_strategy_end - 策略运行结束时调用函数(可选)
--------------------------------------------------

..  py:function:: on_strategy_end()


策略运行结束时调用函数，在回测、模拟交易正常结束时被调用，失败或取消不会被调用。

示例:

 ..  code-block:: python

        def on_strategy_end():
            print('回测结束')


.. _api_process_initialize:

process_initialize - 策略恢复启动时运行函数(可选)
--------------------------------------------------

..  py:function:: process_initialize()

每次程序启动时运行函数，该函数会在每次模拟盘/回测任务恢复运行时执行, 一般用来初始化一些不能持久化保存的内容。
恢复运行时，函数initialize不再执行。

示例:

 ..  code-block:: python

        def process_initialize():
            print('回测重启运行！')





策略执行函数
==================

run_file - 执行指定的策略文件
--------------------------------------

.. autofunction::  qff.frame.api.run_file

策略设置函数
==================

..  module:: qff.frame.api

.. _api_run_daily:

run_daily - 定时运行策略设置函数(可选)
--------------------------------------

.. autofunction:: run_daily

set_benchmark - 设置指数基准
--------------------------------------

.. autofunction:: set_benchmark

set_order_cost - 设置交易税费
--------------------------------------

.. autofunction:: set_order_cost

set_slippage - 设置固定滑点
--------------------------------------

.. autofunction:: set_slippage

set_universe - 定股票值(history函数专用)
-------------------------------------------

.. autofunction:: set_universe

pass_today - 跳过当日(回测专用)
--------------------------------------

.. autofunction:: pass_today

股票交易函数
==================

..  module:: qff.frame.order

order -  按股票数量下单
--------------------------------------

.. autofunction:: order

order_value -  按股票价值下单
--------------------------------------

.. autofunction:: order_value

order_target -  按股票目标数量下单
--------------------------------------

.. autofunction:: order_target

order_target_value -  按股票目标价值下单
----------------------------------------

.. autofunction:: order_target_value

order_cancel -  撤回已下的订单
--------------------------------------

.. autofunction:: order_cancel

get_orders -  获取当天的所有订单
--------------------------------------

.. autofunction:: get_orders

get_open_orders -  获得当天的所有未完成的订单
----------------------------------------------

.. autofunction:: get_open_orders


策略分析函数
=====================================================

stats_report - 策略运行结果分析
------------------------------------------------------

..  autoclass:: qff.frame.stats.stats_report


strategy_eval - 择时策略评价
------------------------------------------------------

..  autoclass:: qff.frame.evaluation.strategy_eval



日期时间函数
=====================================================

get_real_trade_date - 获取真实的交易日期
------------------------------------------------------

..  autoclass:: qff.tools.date.get_real_trade_date

is_trade_day - 判断是否交易日期
------------------------------------------------------

..  autoclass:: qff.tools.date.is_trade_day

get_date_gap - 获取向前或向后间隔天数的交易日日期
------------------------------------------------------

..  autoclass:: qff.tools.date.get_date_gap

get_next_trade_day - 获取下一个交易日的日期
------------------------------------------------------

..  autoclass:: qff.tools.date.get_next_trade_day

get_pre_trade_day - 获取前几个交易周期的日期
------------------------------------------------------

..  autoclass:: qff.tools.date.get_pre_trade_day

get_trade_days - 获取指定范围交易日
------------------------------------------------------

..  autoclass:: qff.tools.date.get_trade_days

get_trade_gap - 获取两个交易日之间的交易天数
------------------------------------------------------

..  autoclass:: qff.tools.date.get_trade_gap

run_time - 计算函数运行时间的装饰函数
------------------------------------------------------

..  autoclass:: qff.tools.date.run_time


其他函数
=====================================================
log - 日志log信息
------------------------------------------------------

..  autoclass:: qff.tools.logs.Log

.. autoclass:: qff.tools.logs.Log.set_level

kshow - 生成网页版K线图
------------------------------------------------------

..  autoclass:: qff.tools.kshow.kshow

send_message - 发送消息提醒
------------------------------------------------------

..  autoclass:: qff.tools.email.send_message

.. _api-base-types:

类和对象
======================================================

g - 全局变量对象
------------------------------------------------------

..  autoclass:: qff.frame.context.GlobalVar

context - 策略上下文全局对象
------------------------------------------------------

..  autoclass:: qff.frame.context.Context

Portfolio - 股票账户
------------------------------------------------------

..  autoclass:: qff.frame.portfolio.Portfolio

Position - 持仓
------------------------------------------------------

..  autoclass:: qff.frame.position.Position


Order - 订单对象
------------------------------------------------------
..  autoclass:: qff.frame.order.Order

UnitData - 当前数据对象
------------------------------------------------------
..  autoclass:: qff.price.cache.UnitData


.. _class_tick:

Tick - tick对象
------------------------------------------------------
..  module:: qff

..  py:class:: Tick

一个 tick 所包含的信息。 tick 中的信息是在 tick 事件发生时， 盘面的一个快照。

    ==================  ====================
    字段名	                含义
    ==================  ====================
    price               当前价格
    last_close          昨日收盘价
    open                当日开盘价
    high                截至到当前时刻的日内最高价
    low                 截至到当前时刻的日内最低价
    vol                 截至到当前时刻的日内总手数
    cur_vol             当前tick成交笔数
    amount              截至到当前时刻的日内总成交额
    s_vol               内盘
    b_vol               外盘
    bid1~bid5           买一到买五价格
    ask1~ask5           卖一到卖五价格
    bid_vol1~bid_vol5   买一到买五挂单手数
    ask_vol1~ask_vol5   卖一到卖五挂单手数
    ==================  ====================



枚举常量
======================================================

..  module:: qff.frame.const


RUN_TYPE - 策略运行模式
-------------------------------
.. autoclass:: RUN_TYPE


RUN_STATUS - 策略运行状态
-------------------------------
.. autoclass:: RUN_STATUS


ORDER_TYPE - 订单类型
-------------------------------
.. autoclass:: ORDER_TYPE


ORDER_STATUS - 订单状态
-------------------------------
.. autoclass:: ORDER_STATUS