# coding:utf-8

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

from typing import Optional
from datetime import datetime

from qff.frame.const import RUN_TYPE, RUN_STATUS
from qff.tools.date import get_pre_trade_day


class TradeCost:
    """
    股票交易费用对象
    """
    def __init__(self, open_tax=0,
                 close_tax=0.001,
                 open_commission=0.0002,
                 close_commission=0.0002,
                 min_commission=5):
        self.open_tax = open_tax  # 买入时印花税 (只股票类标的收取，基金与期货不收)
        self.close_tax = close_tax  # 卖出时印花税 (只股票类标的收取，基金与期货不收)
        self.open_commission = open_commission  # 买入时佣金，申购场外基金的手续费
        self.close_commission = close_commission  # 卖出时佣金，赎回场外基金的手续费
        self.min_commission = min_commission  # 最低佣金，不包含印花税


class Strategy:
    """
     策略对象，由run_daily()注册
    """
    def __init__(self):
        self.initialize = None              # 策略初始化函数
        self.handle_data = None             # 运行策略函数，该函数每个单位时间会调用一次, 如果按天回测,则每天调用一次,如果按分钟,则每分钟调用一次。
        self.before_trading_start = None    # 开盘前运行的策略函数
        self.after_trading_end = None       # 收盘后运行的策略函数
        self.on_strategy_end = None         # 策略运行结束时调用(可选)
        self.process_initialize = None      # 程序恢复启动时运行函数(可选)，如果模拟盘每天重启, 所以这个函数会每天都执行.
        self.run_daily = {}             # 每天固定时间点运行的策略函数,由run_daily注册，key为‘HH:MM',value为策略函数


class Position:
    """
    持仓标的信息

    持有的某个标的的信息,注意区分多仓和空仓

    ==================  ==============  ==============================================================
        属性               类型                说明
    ==================  ==============  ==============================================================
    security             str             股票代码
    init_time            str             建仓时间
    avg_cost             float           当前持仓成本，只有在开仓/加仓时会更新
    acc_avg_cost         float           累计的持仓成本,在清仓/减仓时也会更新，该持仓累积的收益都会用于计算成本
    transact_time        str             最后交易时间
    locked_amount        int             挂单冻结仓位
    closeable_amount     int             可卖出的仓位，不包括挂单冻结仓位，建仓当天不能卖出
    today_amount         int             今天开的仓位
    total_amount         int             总仓位, 等于locked_amount+closeable_amount+today_amount)
    price                float           最新行情价格
    value                float           标的价值，计算方法是: price * total_amount
    ==================  ==============  ==============================================================
    """
    def __init__(self, security, init_time, amount, avg_cost):
        self.security = security
        self.init_time = init_time       # 建仓时间
        self.avg_cost = avg_cost         # 是当前持仓成本，只有在开仓/加仓时会更新
        self.acc_avg_cost = avg_cost     # 累计的持仓成本,在清仓/减仓时也会更新，该持仓累积的收益都会用于计算成本
        self.transact_time = init_time   # 最后交易时间
        self.locked_amount = 0           # 挂单冻结仓位
        self.closeable_amount = 0        # 可卖出的仓位，不包括挂单冻结仓位，建仓当天不能卖出
        self.today_amount = amount       # 今天开的仓位
        self.total_amount = amount       # 总仓位, 等于locked_amount+closeable_amount+today_amount)
        self.price = None                # 最新行情价格
        self.value = None                # 标的价值，计算方法是: price * total_amount


class Portfolio:
    """
    股票账户

    账户当前的资金，标的信息，即所有标的操作仓位的信息汇总。

    ==================  ==============  ==============================================================
        属性               类型                说明
    ==================  ==============  ==============================================================
    starting_cash        float              初始资金
    available_cash       float              当可用资金, 可用来购买证券的资金
    locked_cash          float              挂单锁住资金
    positions            Dict               当前仓位，key值为股票代码，value是 :class:`.Position` 对象
    total_assets         float              总的资产, 包括现金, 仓位(股票)的总价值, 可用来计算收益
    positions_assets     float              持仓资产价值
    benchmark_assets     float              基准价值
    ==================  ==============  ==============================================================

    """
    def __init__(self, starting_cash):
        self.starting_cash = starting_cash   # 初始资金
        self.available_cash = starting_cash  # 可用资金, 可用来购买证券的资金
        self.locked_cash = 0                 # 挂单锁住资金
        self.positions = {}                  # key值为股票代码，value是Position对象
        self.total_assets = starting_cash     # 总的资产, 包括现金, 仓位(股票)的总价值, 可用来计算收益
        # self.returns = 1                     # 总权益的累计收益；（当前总资产 + 今日出入金 - 昨日总资产） / 昨日总资产；
        self.positions_assets = 0             # 持仓资产价值
        # self.benchmark_returns = 1           # 基准收益
        self.benchmark_assets = 0             # 基准价值


class Context:
    """
    策略上下文

    保存策略运行信息，包含账户、时间等


    ============== =====================  =======================================================================
        属性        类型                      说明
    ============== =====================  =======================================================================
    strategy_name  str                      策略名称
    run_type       :class:`.RUN_TYPE`       当前框架运行模式，回测还是模拟
    status         :class:`.RUN_STATUS`     策略当前运行状态
    run_freq       str                      策略运行频率 包括”day" ,"tick"和 "min"
    start_date     str                      回测开始日期
    end_date       str                      回测结束日期
    current_dt     str                      策略执行的当前时间 "yyyy-mm-dd HH:MM:SS"
    benchmark      str                      基准指数代码
    portfolio      :class:`.Portfolio`      交易账户对象
    order_list     Dict                     当日的所有订单列表,key为order_id, value为 :class:`.Order`
    df_orders      DataFrame                历史的订单列表,以DataFrame保存order对象
    df_positions   DataFrame                历史仓位列表,以DataFrame模式保存Position对象
    df_asset       DataFrame                收益曲线，以DataFrame模式保存：时间、收益、基准收益、持仓资产
    strategy_file  str                      策略文件名称及路径
    ============== =====================  =======================================================================

    """

    def __init__(self):
        self.strategy_name = None       # 策略名称
        self.run_type = RUN_TYPE.BACK_TEST  # 当前框架运行的是回测还是模拟
        self.status = RUN_STATUS.NONE    # 回测框架运行状态
        self.run_freq = None            # 策略运行频率 包括”day" ,"tick"和 "min"
        self.start_date = None  # 回测开始日期
        self.end_date = None    # 回测结束日期
        self._current_dt = None         # 回测时对应的策略执行的当前时间 "yyyy-mm-dd HH:MM:SS"
        self.benchmark = "000300"       # 指数基准
        self.bm_data = None
        self.bm_start = None            # 基准指数回测前一天的收盘点数
        self.slippage = 0.00246         # 固定滑点
        self.universe = []              # 股票池，通过set_universe(stock_list)设定
        self.trade_cost = TradeCost()   # 股票交易费用对象
        self.portfolio: Optional[Portfolio] = None   # 股票账户信息对象
        self.order_list = {}            # 当日的所有订单列表,key为order_ID
        self.df_orders = None           # 历史的订单列表,以DataFrame模式保存order对象
        self.df_positions = None        # 历史仓位列表,以DataFrame模式保存Position对象
        self.df_asset = None            # 收益曲线，以DataFrame模式保存：时间、收益、基准收益、持仓资产
        self.pass_today = False         # 分钟运行频率时，设置该值则跳过当天分钟循环
        self.strategy_file = None       # 策略文件名称及路径

    @property
    def current_dt(self):
        if context.run_type == RUN_TYPE.BACK_TEST:
            return self._current_dt
        else:
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @current_dt.setter
    def current_dt(self, str_datetime):
        if context.run_type == RUN_TYPE.BACK_TEST:
            self._current_dt = str_datetime
        return

    @property
    def previous_date(self):
        return get_pre_trade_day(self.current_dt)[:10]


class GlobalVar:
    def __init__(self):
        self.type = None


strategy = Strategy()
context = Context()
g = GlobalVar()


def run_strategy_funcs(strategy_funcs):
    if isinstance(strategy_funcs, list):
        for func in strategy_funcs:
            if callable(func):
                func()
    elif callable(strategy_funcs):
        strategy_funcs()
