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

import os
import importlib.util
import inspect
from functools import partial
from datetime import datetime
from typing import Optional, Callable
from qff.tools.logs import log
from qff.tools.date import is_trade_day, get_real_trade_date, util_date_valid, get_pre_trade_day
from qff.frame.context import context, strategy
from qff.frame.portfolio import Portfolio
from qff.frame.const import RUN_TYPE
from qff.frame.backtest import back_test_run
from qff.frame.simtrade import sim_trade_run
from qff.price.cache import ContextData

__all__ = ['set_benchmark', 'set_order_cost', 'set_slippage', 'run_daily', 'run_file',
           'set_universe', 'pass_today']


context_data = ContextData()


def _getattr(m, func_name):
    try:
        func = getattr(m, func_name)
    except AttributeError:
        func = None
    return func


def _wrap_strategy_func(func_obj, include_data=False):
    if func_obj is not None:
        spec = inspect.getfullargspec(func_obj).args
        if include_data:
            if len(spec) != 2 or spec[0] != 'context' or spec[1] != 'data':
                raise ValueError(f'策略函数定义的参数不正确！')
            return partial(func_obj, context, context_data)
        else:
            if len(spec) != 1 or spec[0] != 'context':
                raise ValueError(f'策略函数定义的参数不正确！')
            return partial(func_obj, context)
    else:
        return None


def _load_strategy_file(path):
    """
    装载策略文件
    :param path: 策略文件的路径
    :return (boolean): 返回加载是否成功
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

    strategy.initialize = _wrap_strategy_func(_getattr(module, 'initialize'))
    strategy.before_trading_start = _wrap_strategy_func(_getattr(module, 'before_trading_start'))
    strategy.handle_data = _wrap_strategy_func(_getattr(module, 'handle_data'), include_data=True)
    strategy.after_trading_end = _wrap_strategy_func(_getattr(module, 'after_trading_end'))
    strategy.on_strategy_end = _wrap_strategy_func(_getattr(module, 'on_strategy_end'))
    strategy.process_initialize = _wrap_strategy_func(_getattr(module, 'process_initialize'))
    if strategy.initialize is None:
        log.error("***策略文件缺少初始化函数initialize！***")
        return False
    return True


def run_daily(func, run_time="every_bar", append=True):
    # type: (Callable, str,bool) -> None
    """
    设置定时运行的策略函数。**回测环境/模拟专用API**

    指定每天要运行的函数, 可以在具体交易日的某一分钟执行。

    :param func: 一个自定义的函数，此函数必须接受context参数。例如自定义函数名 :code:`market_open(context)`。
    :param run_time: 具体执行时间,一个字符串格式的时间:

        - 交易时间内的任意时间点，上午“09:30-11:30”， 下午“13:01-15:00”，例如"10:00", "14:00"；
        - **every_bar**，运行时间和您设置的运行频率一致，按天会在交易日的开盘时调用一次，按分钟会在交易时间每分钟运行。执行后将替代handle_data()策略框架函数.
        - **before_open**,设置func在开盘前运行，执行后将替代before_trading_start()策略框架函数.
        - **after_close**,设置func在收盘后运行，执行后将替代after_trading_end()策略框架函数.
    :param append: 如果run_time已注册运行函数，新函数是在原函数前面运行还是后面运行。append=True: 则新函数是在原函数后面运行。

    .. note::
        一个策略中尽量不要同时使用run_daily和handle_data，更不能使用run_daily(handle_data, "xx:xx")
        run_daily中的函数只能有一个参数context，具体示例如下：

    :example:

        ::

            def initialize(context):
                run_daily(func, run_time='10:00')

            def func(context):
                print(context.current_dt)
                print('-'*50)

            # 参数 func 必须是一个全局的函数, 不能是类的成员函数, 并且func是可重入函数，即可重复调用。

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

    log.debug('调用run_daily' + str(locals()).replace('{', '(').replace('}', ')'))
    if not callable(func):
        raise ValueError("run_daily函数输入的func参数不是函数对象")

    func = _wrap_strategy_func(func,  run_time == "every_bar")

    if run_time == "before_open":
        strategy.before_trading_start = register_strategy_func(strategy.before_trading_start, func, append)

    elif run_time == "after_close":
        strategy.after_trading_end = register_strategy_func(strategy.after_trading_end, func, append)

    elif run_time == "every_bar":
        strategy.handle_data = register_strategy_func(strategy.handle_data, func, append)

    else:
        try:
            datetime.strptime(run_time, '%H:%M')
            if run_time < '09:30' or run_time > '15:00' or ('11:30' < run_time < '13:30'):
                raise ValueError

            if run_time + ':00' not in strategy.run_daily.keys():
                strategy.run_daily[run_time + ':00'] = func  # 加上秒是为了防止在tick策略中多次执行
            else:
                strategy.run_daily[run_time + ':00'] = \
                    register_strategy_func(strategy.run_daily[run_time + ':00'], func, append)

        except ValueError:
            log.error("run_daily函数输入的run_time参数不合法")
            return
    return


def _set_backtest_period(start=None, end=None):
    """
    设置回测周期开始时间和结束时间,默认最近60天数据
    :param start: 回测开始日期
    :param end:   回测结束日期
    :return: None
    """
    if end is None:
        end = datetime.now().strftime('%Y-%m-%d')
        if not is_trade_day(end):
            end = get_real_trade_date(end)
        context.end_date = get_pre_trade_day(end, 1)
    elif util_date_valid(end):
        context.end_date = end if is_trade_day(end) \
            else get_real_trade_date(end, towards=-1)
    else:
        print('set_backtest_period函数参数日期格式设置错误！')
        return ValueError

    if start is None:
        context.start_date = get_pre_trade_day(end, 60)

    elif util_date_valid(start):
        context.start_date = start if is_trade_day(start) \
            else get_real_trade_date(start, towards=1)
    else:
        print('set_backtest_period函数参数日期格式设置错误！')
        raise ValueError

    if context.start_date >= context.end_date:
        print("回测日期参数设置错误！")
        raise ValueError

    context.current_dt = context.start_date + " 09:00:00"    # 必需要设置，回测以该时间作为启动日期


def set_order_cost(open_tax=0,
                   close_tax=0.001,
                   open_commission=0.0002,
                   close_commission=0.0002,
                   min_commission=5):
    # type: (float, float, float, float, float) -> None
    """
    设置佣金和印花税率。

    指定每笔交易要收取的手续费, 系统会根据用户指定的费率计算每笔交易的手续费

    :param open_tax: 买入时印花税，默认值为0
    :param close_tax: 卖出时印花税，默认值为千分之一
    :param open_commission: 买入时佣金，默认值为万分之二
    :param close_commission: 卖出时佣金，默认值为万分之二
    :param min_commission: 最低佣金，不包含印花税，默认值为5

    """

    context.trade_cost.open_tax = open_tax
    context.trade_cost.close_tax = close_tax
    context.trade_cost.open_commission = open_commission
    context.trade_cost.close_commission = close_commission
    context.trade_cost.min_commission = min_commission


def set_benchmark(security: str):
    """
    设置基准

    默认我们选定了沪深300指数的每日价格作为判断您策略好坏和一系列风险值计算的基准.
    您也可以使用set_benchmark指定其他指数

    :param security:  指数基准

    :return: None
    """

    context.benchmark = security
    return


def set_slippage(slippage=0.00246):
    # type: (float) -> None
    """
    设置固定滑点

    当您下单后, 真实的成交价格与下单时预期的价格总会有一定偏差, 因此我们加入了滑点模式来帮您更好的模拟真实市场的表现. 我们暂时只支持固定滑点。同时，我们也支持为交易品种和特定的交易标的设置滑点。

    :param slippage: 固定滑点值，默认0.00246


    """

    context.slippage = slippage
    return


# context.universe = ['000001', '601567', '000166', '601636'] 测试使用
def set_universe(security_list):
    # type: (list) -> None
    """
    设定股票值(history函数专用)

    设置或者更新此策略要操作的股票池 context.universe. 请注意:
    **该函数现在只用于设定history函数的默认security_list, 除此之外并无其他用处。**

    :param security_list: 证券标的列表

    """
    if isinstance(security_list, str):
        security_list = [security_list]

    context.universe = security_list


def pass_today() -> None:
    """
    跳过当日(回测专用)

    在分钟执行策略中，调用此函数可用跳过当日剩余的每分钟策略运行，以提高回测效率。
    """
    if context.run_type == RUN_TYPE.BACK_TEST:
        context.pass_today = True
    return


def run_file(strategy_file: str,
             run_type: str = 'bt',
             resume: bool = False,
             freq: str = 'day',
             cash: int = 1000000,
             start: Optional[str] = None,
             end: Optional[str] = None,
             name: Optional[str] = None,
             output_dir: Optional[str] = None,
             log_level: str = 'info',
             trace: bool = False):
    """
    运行策略文件，并初始化环境参数。

    :param strategy_file: 待运行策略文件路径
    :param run_type: 指定策略运行方式。bt-回测； sim-实盘模拟, 默认值为bt
    :param resume: 是否执行恢复运行， True-恢复以前的策略执行，False-重新开始执行策略，默认False.
    :param freq: 策略执行频率，有效值为 'day','min','tick',默认值为 'day'
    :param cash: 账户初始资金，默认值1000000
    :param start: 回测开始日期，默认为结束日期前60个交易日
    :param end: 回测结束日期, 默认为上一个交易日
    :param name: 策略名称
    :param output_dir: 指定结果数据输出目录
    :param log_level: 控制台日志输出的级别, 有效值为 'debug', 'info', 'warning', 'error'，默认值为‘info’
    :param trace: 策略运行过程中是否进行交互,模拟交易时自动有效

    :return: None

    :example:
        使用方法：一般在策略文件中的尾部加入以下代码

    .. code-block:: python

        if __name__ == '__main__':
            run_file(__file__, 0,  start='2022-06-01', end='2022-08-31')

    """
    log.set_level(log_level)
    log.debug('调用run_file' + str(locals()).replace('{', '(').replace('}', ')'))

    if not _load_strategy_file(strategy_file):
        print("输入的策略文件路径加载失败！")
        return
    context.strategy_file = strategy_file

    if resume:
        if strategy.process_initialize is not None:
            strategy.process_initialize()
        if context.run_type == RUN_TYPE.BACK_TEST:
            back_test_run(trace)
        else:
            sim_trade_run()
    else:
        context.log_file = log.file_name
        strategy.initialize()

        if freq in ['day', 'min', 'tick']:
            context.run_freq = freq
        else:
            print('参数freq运行频率设置错误！')
            return

        context.portfolio = Portfolio(cash)

        if name is None:
            name = os.path.basename(strategy_file).split('.')[0]
        context.strategy_name = name

        if output_dir is not None:
            if os.path.exists(output_dir):
                context.output_dir = output_dir
            else:
                print("output_dir参数指定的目录不存在！")
                return

        context.run_start = datetime.now()

        if run_type == 'bt':
            _set_backtest_period(start, end)
            back_test_run(trace)
        elif run_type == 'sim':
            sim_trade_run()
        else:
            log.error('输入的参数run_type错误！')
