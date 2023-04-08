# CHANGELOG

## 0.5.13

### Features

* 重构框架接口函数，与Ptrade和JoinQuant定义的接口参数一致，所有策略文件都需按新接口进行改写。

| **原接口**   | **新接口** |
| :------- | :-- |
| initialize()   |  initialize(context) |
| handle_data()  |  handle_data(context, data)  |
| before_trading_start() | before_trading_start(context)  |
| after_trading_end() | after_trading_end(context) |
| on_strategy_end() | on_strategy_end(context) |
| process_initialize() | process_initialize(context) |



## 0.5.12

### Features

* 增加dbinfo命令的输出内容

### Bug Fixes

*  修复保存股票日数据停牌时的bug
*  修复运行报告进度中出现的长小数问题

## 0.5.11

### Bug Fixes

* 修复保存除权除息数据出现重复键值的错误
* 修复股票列表数据每日更新时出现的日期格式错误问题
* 修复available_cash出现负数的BUG

## 0.5.10

### Features

* 增加邮件通知功能
* 实现trace暂停和取消策略时，等待子线程运行结束的功能

### Bug Fixes

* 修复获取实时分钟数据时返回空值导致的异常

## 0.5.9

### Bug Fixes

* 修复实盘模拟运行中sleep出现负数的bug
* 修复完善trace中pause命令的执行
* 修复回测恢复时，无法进入交互环境的缺陷
* 修复实盘模拟时，在分钟频率下，UnitData取数错误
* 修复实盘模拟时pre_close数据错误
* 修复查询日期当天发布财报时，不能正确获取的错误
* 修复在实盘模拟时报告中策略开始时间解析产生错误
* 修复在实盘模拟时收盘后保存pkl文件的错误

## 0.5.8

### Bug Fixes

* 修复mongo_info函数对空表发生异常的缺陷
* 修复在实盘模拟时，end_date未设置造成的输出信息缺陷
* 增加run_file函数output_dir目录是否存在的判断

## 0.5.7

### Bug Fixes

* 修复attribute_history返回None值的缺陷
* 修复'st‘为模拟交易的问题，统一改成'sim'
* 修复订单撮合时，撮合成功就退出循环，造成满足条件的情况下只能撮合一笔。
* 修复业绩预告快报报告期日期不对的错误
* 增加基准数据未成功获取的报错信息

## 0.5.6

### Features

* 增加删除数据表命令行功能

### Bug Fixes

* 修改对akshare的版本要求
* 修复获取预告快报数据函数中的缺陷

## 0.5.5

### Features

* 增加查询预告数据和快报数据的功能
* 增加查询快报和预告的日期索引
* 改命令行qff save report的操作，将全部更新年报数据

### Bug Fixes

* 修复历史市盈率不正确的问题
* 修复int_to_date的缺陷
* 修复fetch_price调用get_trade_gap参数类型不匹配的告警
* 修复保存分钟数据时重复循环的问题

## 0.5.4

### Features

* 增加过滤北交所股票的辅助函数

### Bug Fixes

* 修复stock_list和stock_name两个结合数据来源不一致造成的bug
* 修复回测全程无交易记录时输出报告中出现错误的问题
* 修复回测全程单笔交易记录时输出报告中出现错误的问题

## 0.5.3

### Bug Fixes

* 修复未手工初始化股票历史名称时造成的异常
* 修复无成交记录时绩效分析出现的异常
* 修复分钟曲线缺失造成的异常
* 调整执行频率为天时，handle_data的执行时间为09:30

## 0.5.2

### Bug Fixes

* 修复akshare库升级造成的参数不兼容！
* 修复添加--log-level参数时的bug
* 修改select_best_ip日志输出级别


## 0.5.1

### Features

* 完善QFF日志功能
* 添加后复权功能
* 进度条显示优化
* 市值数据加索引

### Bug Fixes

* 优化run_file函数，直接处理resume参数
* 处理pandas1.5升级后的deprecated告警