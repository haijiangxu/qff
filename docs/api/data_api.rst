
===========================================
 数据 API
===========================================


行情
==================

..  module:: qff.price.query

get_price - 获取历史数据,可查询多个标的多个数据字段
----------------------------------------------------

.. autofunction:: get_price

history - 获取历史数据,可查询多个标的单个数据字段
-------------------------------------------------

.. autofunction:: history

attribute_history - 获取历史数据,可查询单个标的多个数据字段
-------------------------------------------------------------------

.. autofunction:: attribute_history

get_bars - 获取历史数据(包含快照数据),可查询多个标的多个数据字段
---------------------------------------------------------------------------

.. autofunction:: get_bars


get_current_data - 获取当前时刻标的数据
---------------------------------------------------------------------------

.. autofunction:: qff.price.cache.get_current_data


fetch_ticks - 获取实时tick数据
---------------------------------------------------------------------------

.. autofunction:: qff.price.fetch.fetch_ticks


fetch_today_transaction -  获取当日实时分笔成交信息
---------------------------------------------------------------------------

.. autofunction:: qff.price.fetch.fetch_today_transaction

fetch_today_min_curve -  实时获取当天的1分钟曲线
---------------------------------------------------------------------------

.. autofunction:: qff.price.fetch.fetch_today_min_curve


股票
==================


get_all_securities- 获取平台支持的所有股票信息
--------------------------------------------------------------

.. autofunction:: get_all_securities

get_security_info- 获取股票的信息
--------------------------------------------------------------

.. autofunction:: get_security_info

get_stock_name- 获取股票名称
--------------------------------------------------------------

.. autofunction:: get_stock_name


get_block_stock- 根据板块名称检索对应的股票代码
--------------------------------------------------------------

.. autofunction:: get_block_stock


get_stock_block- 根据股票代码检索所属的板块名称
--------------------------------------------------------------

.. autofunction:: get_stock_block

get_mtss- 获取股票的融资融券信息
--------------------------------------------------------------

.. autofunction:: get_mtss

get_st_stock- 获取指定日期ST股票代码和名称
--------------------------------------------------------------

.. autofunction:: get_st_stock

get_paused_stock- 获取停牌的股票代码
--------------------------------------------------------------

.. autofunction:: get_paused_stock

指数
==================

get_index_name- 获取指数名称
--------------------------------------------------------------

.. autofunction:: get_index_name

get_index_stocks- 获取一个指数给定日期的成分股列表
--------------------------------------------------------------

.. autofunction:: get_index_stocks


.. _api_finance:

财务
==================

..  module:: qff.price.finance

get_fundamentals- 根据mongodb语法查询财务数据
--------------------------------------------------------------

.. autofunction:: get_fundamentals

get_financial_data- 查询多只股票给定日期的财务数据
--------------------------------------------------------------

.. autofunction:: get_financial_data

get_stock_reports- 获取单个股票多个报告期发布的财务数据
--------------------------------------------------------------

.. autofunction:: get_stock_reports

get_fundamentals_continuously- 查询单个股票连续多日的财务数据
--------------------------------------------------------------

.. autofunction:: get_fundamentals_continuously

get_history_fundamentals- 获取多只股票多个季度（年度）的历史财务数据
----------------------------------------------------------------------------

.. autofunction:: get_history_fundamentals

get_stock_forecast- 获取股票业绩预告数据
--------------------------------------------------------------

.. autofunction:: get_stock_forecast

get_stock_express- 获取股票业绩快报数据
--------------------------------------------------------------

.. autofunction:: get_stock_express


get_valuation- 获取多个股票在指定交易日范围内的市值表数据
--------------------------------------------------------------

.. autofunction:: get_valuation

query_valuation- 查询满足条件的市值信息数据
--------------------------------------------------------------

.. autofunction:: query_valuation

