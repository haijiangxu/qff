# 实盘操作指南

QFF实盘操作基于通用同花顺下单软件，通过pywinauto库自动化接管客户端，实现股票实际账号的买入、卖出、撤单、账户查询、委托以及成交查询等功能。

```{note} 
 QFF实盘交易仅支持Windows系统，其功能在0.5.15版本后开始支持。
```


## 安装和设置
### 客户端安装
登录 [同花顺官网](http://download.10jqka.com.cn/) ，选择同花顺免费版下载并安装。
如果最新版本操作出现错误，可从网盘下载兼容的历史版本 [THS_9.20.40_20230613.exe](https://pan.baidu.com/s/1JIm9RemOVPC1jgyq33EIYA) ，提取码qff0。

### 客户端设置
* 添加客户端快捷方式。软件位置在同花顺安装目录下 `xiadan.exe` ，找到该文件后鼠标右键点击，选择发送到->桌面快捷方式。在运行qff实盘操作前，一般需先启动下单软件。

* 执行qff命令行指令，将下单软件路径保存在qff配置文件中。如何 `xiadan.exe` 程序已运行，qff实盘可直接接管，否则，将通过qff配置文件信息，自动启动下单软件。
    ```bash
    $ qff config set THS.path c:\ths\xiadan.exe
    ```
* 需要先手动登录一次下单软件。添加券商，填入账户号、密码、验证码，勾选“保存密码”。第一次登录后，上述信息被缓存。
  ```{image} ../_static/ths_login.webp
    :class: bg-primary
    :width: 500px
    :align: center
  ```


* 需要对客户端按以下设置，不然会导致客户端超时锁定。 系统设置 > 界面设置: 界面不操作超时时间设为 0。
    ```{image} ../_static/ths_config.webp
    :class: bg-primary
    :width: 400px
    :align: center
  ``` 



## 命令行指令
QFF提供了用于操作同花顺客户端的命令行指令。在进行实盘交易前，可通过这些命令行指令进行测试验证。您可以执行 `qff trader -h` 查询trader命令用法：

```bash
    $ qff trader -h
 
    usage:
        qff trader <subcommand> [options]
        eg:
        qff trader connect
        qff trader balance
        qff trader position
        qff trader entrust
        qff trader deal
        qff trader buy stock_code  amount price
        qff trader sell stock_code amount price
        qff trader buy stock_code  amount
        qff trader sell stock_code amount
        qff trader cancel entrust_no


    操作同花顺下单软件客户端,用于策略实盘运行前,测试能否正确对交易软件进行操作.

    子命令:
    - connect:                      连接交易软件客户端
    - balance:                      获取账户资金股票信息
    - position:                     获取账户持仓股票列表
    - entrust:                      获取当日委托订单列表
    - deal:                         获取当日成交订单列表
    - buy stock amount price:       买入指定股票, eg: qff trader buy 000001 100 10.5
    - sell stock amount price:      卖出指定股票. eg: qff trader sell 000001 100 10.9
    - buy stock amount:             市价买入指定股票, eg: qff trader buy 000001 100
    - sell stock amount:            市价卖出指定股票. eg: qff trader sell 000001 100
    - cancel entrust_no:            撤销委托订单, entrust_no为委托订单编号,如果不输入,则撤销所有委托订单

    positional arguments:
      subcommand  实盘操作子命令
      options     子命令所需参数
    
    optional arguments:
      -h, --help  显示当前帮助信息
```

示例：

* 执行qff trader connect 进行连接同花顺客户端测试

```bash
    $ qff trader connect
    qff>> ------------------- - INFO - 同花顺交易接口: 下单程序未启动，正在自动加载...
    qff>> ------------------- - INFO - 同花顺交易接口: 连接下单程序成功!
```

* 执行qff trader balance 获取账户资金股票信息

```bash
    $ qff trader balance
    qff>> ------------------- - INFO - 同花顺交易接口: 连接下单程序成功!
    +-----------------------+
    |      账户资金股票     |
    +----------+------------+
    | 资金余额 |   358.64   |
    | 冻结金额 |   13.78    |
    | 可用金额 |   372.42   |
    | 可取金额 |   358.64   |
    | 股票市值 |  123456.0  |
    |  总资产  |  123456.0  |
    | 持仓盈亏 |   10000.0  |
    +----------+------------+
```

## 实盘交易函数

QFF提供了以下函数接口，用于在用户策略中直接进行实盘交易。目前QFF还未提供实盘运行框架，您可以在模拟运行的策略中，直接调用实盘交易函数，以实现实盘交易功能。


```{eval-rst} 

.. currentmodule:: qff.trader.ths

.. autosummary::
   :nosignatures:

   trader_connect
   trader_balance
   trader_position
   trader_today_entrusts
   trader_today_deal
   trader_order
   trader_cancel
     
    
```

## trace交互接口
QFF人机交互功能接口trace中增加了实盘操作接口命令，运行 `trader` 命令可获取使用帮助，其用法和命令行接口一致。
用户也可在策略模拟运行中，通过trace命令手工进行股票实盘交易。
```
QFF> trader
Usage:
             以下命令仅支持windows系统下运行
            ----------------------------------------------------------------------------------------------------------------------
            ⌨️命令格式： trader connect                 :  连接交易软件客户端
            ⌨️命令格式： trader balance                 :  获取账户资金股票信息
            ⌨️命令格式： trader position                :  获取账户持仓股票列表
            ⌨️命令格式： trader entrust                 :  获取当日委托订单列表
            ⌨️命令格式： trader deal                    :  获取当日成交订单列表
            ⌨️命令格式： trader buy stock  amount price :  买入指定股票, eg: qff trader buy 000001 100 10.5
            ⌨️命令格式： trader sell stock amount price :  卖出指定股票. eg: qff trader sell 000001 100 10.9
            ⌨️命令格式： trader buy stock  amount       :  市价买入指定股票, eg: qff trader buy 000001 100
            ⌨️命令格式： trader sell stock amount       :  市价卖出指定股票. eg: qff trader sell 000001 100
            ⌨️命令格式： trader cancel entrust_no       :  撤销委托订单, entrust_no为委托订单编号，如果不输入，则撤销所有委托订单
            -----------------------------------------------------------------------------------------------------------------------
```

示例：执行 `trader balance` 获取实盘账户资金股票信息
```
QFF> trader balance
+-----------------------+
|      账户资金股票     |
+----------+------------+
| 资金余额 |   372.42   |
| 冻结金额 | 296015.89  |
| 可用金额 | 296388.31  |
| 可取金额 |   372.42   |
| 股票市值 | 1095553.0  |
|  总资产  | 1391941.31 |
| 持仓盈亏 | 3928391.25 |
+----------+------------+
```

## 实盘交易注意事项

### 实盘与模拟交易的区别
* 市价单冻结资金规则上不同：实盘按照“涨停价+千分之五手续费”计算可买数量，并冻结资金，这个可能引起实盘下单量偏小；模拟交易的市价单也没有这个规则；
* 手续费不同：模拟交易可以自己设置手续费，实盘下单时没有计算手续费；
* 滑点的影响：模拟交易可以自己设置滑点，实盘成交结果以交易所成交结果为准；
* 对手影响：实盘的话得有对手方才会成交，如果下市价单会减少部分的影响，但是也有缺点就是成交价格会劣于限价单；
* 下单数量的影响：实盘一次下单数量太大可能会引起市场冲击，模拟交易不会引起市场冲击；
* 权限的影响：模拟交易没有这个限制，实盘时需要开通一定的权限才能交易，例如股票的市价单、创业板，期货一些品种也需要单独开通（例如股指期货）；

### 股票实盘下单失败的可能原因
* 同花顺客户端版本错误或未成功登录下单软件；
* 没有开通市价单，但使用市价单下单；
* 购买了创业板或科创板标的，但是没有开通相应权限；
* 资金不足；
* 涨停时购买股票，或者跌停时卖出-->委托废单；
* 五档成交，剩余部分被撤单-->内部取消；
* 集合竞价不能进行市价委托-->委托废单;
* 在非交易时间下单；
* 下单数量太大了：股票、基金交易单笔申报最大数量应当不超过100万股（份）