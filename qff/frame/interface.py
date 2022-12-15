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

import importlib.util
from datetime import datetime
from qff.tools.logs import log
from qff.tools.date import is_trade_day, get_real_trade_date, util_date_valid
from qff.frame.context import context, strategy, RUNTYPE, Portfolio


def _getattr(m, func_name):
    try:
        func = getattr(m, func_name)
    except AttributeError:
        func = None
    return func


def load_strategy_file(path):
    """
    装载策略文件
    :param path: 策略文件的路径
    :return:
    """
    # 1、导入策略文件
    try:
        spec = importlib.util.spec_from_file_location('strategy', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        log.error('策略文件导入失败！{}'.format(e))
        log.error('策略文件路径！{}'.format(path))
        return False

    # 2、给strategy策略对象赋函数指针
    strategy.initialize = _getattr(module, 'initialize')
    strategy.before_trading_start = _getattr(module, 'before_trading_start')
    strategy.handle_data = _getattr(module, 'handle_data')
    strategy.after_trading_end = _getattr(module, 'after_trading_end')
    strategy.on_strategy_end = _getattr(module, 'on_strategy_end')
    strategy.process_initialize = _getattr(module, 'process_initialize')
    if strategy.initialize is None:
        log.error("***策略文件缺少初始化函数initialize！***")
        return False
    return True


def run_daily(func, run_time="every_bar", append=True):
    """
     定时运行的策略函数
    :param func: 一个自定义的策略函数, 此函数必须接受context参数;例如自定义函数名market_open(context)
    :param run_time: 具体执行时间,一个字符串格式的时间,有两种方式：
        (1) 24小时内的任意时间，例如"10:00", "01:00"；
        (2) time="every_bar",只能在 run_daily 中调用,运行时间和您设置的频率一致，按天会
        在交易日的开盘时调用一次，按分钟会在交易时间每分钟运行。
    :param append: 如何run_time已注册运行函数，新函数是在原函数前面运行还是后面运行
    :return: None
    一个策略中尽量不要同时使用run_daily和handle_data，更不能使用run_daily(handle_data, "xx:xx")
    建议使用run_daily；
    """
    def register_strategy_func(strategy_func, _func, _append=True):
        obj = strategy_func
        if obj is None:
            obj = _func
        elif callable(obj):
            obj = [obj, _func] if _append else [_func, obj]
        elif isinstance(obj, list):
            if _append:
                obj.append(_func)
            else:
                obj.insert(0, _func)
        return obj

    if not callable(func):
        log.error("run_daily函数输入的func参数不是函数对象")
        return

    if run_time == "before_open":
        register_strategy_func(strategy.before_trading_start, func, append)

    elif run_time == "after_close":
        register_strategy_func(strategy.after_trading_end, func, append)

    elif run_time == "every_bar":
        register_strategy_func(strategy.handle_data, func, append)

    else:
        try:
            datetime.strptime(run_time, '%H:%M')
            if run_time < '09:30' or run_time > '15:00' or ('11:30' < run_time < '13:30'):
                raise ValueError

            if run_time + ':00' not in strategy.run_daily.keys():
                strategy.run_daily[run_time + ':00'] = func  # 加上秒是为了防止在tick策略中多次执行
            else:
                register_strategy_func(strategy.run_daily[run_time + ':00'], func, append)

        except ValueError:
            log.error("run_daily函数输入的run_time参数不合法")
            return
    return


def set_run_freq(freq='day'):
    """
    设置回测和模拟运行时的执行频率，当前回测不支持tick
    :param freq: 设置的频率，目前仅支持['day', 'min', 'tick']
    :return: None
    """
    if context.run_freq is None:  # 避免通过__main.py__运行时重复设置
        if freq in ['day', 'min', 'tick']:
            context.run_freq = freq
        else:
            log.error('set_run_freq函数参数运行频率设置错误！')
            raise ValueError


def set_backtest_period(start="2021-03-01", end="2022-07-29"):
    """
    设置回测周期开始时间和结束时间,须在以下策略设置函数之前运行
    :param start: 回测开始日期
    :param end:   回测结束日期
    :return: None
    """
    if context.start_date is None or context.end_date is None:  # 避免通过__main.py__运行时重复设置
        if util_date_valid(start) and util_date_valid(end):
            context.start_date = start if is_trade_day(start) \
                else get_real_trade_date(start, towards=1)
            context.end_date = end if is_trade_day(end) \
                else get_real_trade_date(end, towards=-1)
            context.current_dt = context.start_date + " 09:00:00"    # 必需要设置，回测以该时间作为启动日期
        else:
            log.error('set_backtest_period函数参数日期格式设置错误！')
            raise ValueError


def set_init_cash(cash=1000000):
    """
    设置账户初始资金
    :param cash: 初始资金
    :return: None
    """
    if context.portfolio is None:  # 避免通过__main.py__运行时重复设置
        context.portfolio = Portfolio(cash)


def set_order_cost(open_tax=0,
                   close_tax=0.001,
                   open_commission=0.0002,
                   close_commission=0.0002,
                   min_commission=5):
    """
    设置佣金/印花税
    :param open_tax: 买入时印花税
    :param close_tax: 卖出时印花税
    :param open_commission: 买入时佣金，
    :param close_commission: 卖出时佣金
    :param min_commission: 最低佣金，不包含印花税
    :return: None
    """

    context.trade_cost.open_tax = open_tax
    context.trade_cost.close_tax = close_tax
    context.trade_cost.open_commission = open_commission
    context.trade_cost.close_commission = close_commission
    context.trade_cost.min_commission = min_commission


def set_benchmark(security):
    """
    设置指数基准
    默认我们选定了沪深300指数的每日价格作为判断您策略好坏和一系列风险值计算的基准.
    您也可以使用set_benchmark指定其他指数
    :param security:  指数基准
    :return: None
    """
    # if context.status != RUNSTATUS.NONE:
    #     log.error("框架运行中，不能设置基础参数")
    #     return
    context.benchmark = security
    return


def set_strategy_name(name: str):
    """
    设置策略名称
    :param name: 策略名称
    :return:
    """
    context.strategy_name = name
    return


def set_slippage(slippage=0.00246):
    """
    设置固定滑点
    :param slippage: 固定滑点值，默认0.00246
    :return: None
    """
    # if context.status != RUNSTATUS.NONE:
    #     log.error("框架运行中，不能设置基础参数")
    #     return

    context.slippage = slippage
    return


# context.universe = ['000001', '601567', '000166', '601636'] 测试使用
def set_universe(security_list):
    """
    设置或者更新此策略要操作的股票池 context.universe. 请注意:
    该函数现在只用于设定history函数的默认security_list, 以及缓存回测期间的数据。
    参数
    :param security_list: 股票列表
    :return: None
    """
    if isinstance(security_list, str):
        security_list = [security_list]
    for code in security_list:
        if code not in context.universe:
            context.universe.append(code)
    return


def del_universe(security_list):
    """
    删除股票池 context.universe中的股票
    :param security_list: 股票列表
    :return:
    """
    if isinstance(security_list, str):
        security_list = [security_list]
    for code in security_list:
        if code not in context.universe:
            context.universe.remove(code)
    return


def pass_today():
    """
    在分钟执行策略中，调用此函数可用跳过当日剩余的每分钟策略运行，以提高回测效率
    """
    if context.run_type == RUNTYPE.BACK_TEST:
        context.pass_today = True
    return
