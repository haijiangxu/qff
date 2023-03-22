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

from datetime import datetime

from qff.frame.const import RUN_TYPE, RUN_STATUS
from qff.tools.date import get_pre_trade_day, get_trade_gap


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


class Context:
    """
    策略上下文

    系统全局变量context保存策略运行信息，包含账户、策略、时间、运行参数等。用户可以直接读取context相关属性,但 **注意不能直接修改**

    ================== =====================  =======================================================================
        属性            类型                      说明
    ================== =====================  =======================================================================
    strategy_name      str                      策略名称
    run_type           :class:`.RUN_TYPE`       当前框架运行模式，回测还是模拟
    status             :class:`.RUN_STATUS`     策略当前运行状态
    run_freq           str                      策略运行频率 包括”day" ,"tick"和 "min"
    start_date         str                      回测开始日期
    end_date           str                      回测结束日期
    current_dt         str                      策略执行的当前时间 "yyyy-mm-dd HH:MM:SS"
    previous_date      str                      策略执行的当前时间的前一天"yyyy-mm-dd”
    benchmark          str                      基准指数代码
    portfolio          :class:`.Portfolio`      交易账户对象
    order_list         Dict                     当日的所有订单列表,key为order_id, value为 :class:`.Order`
    order_hists        List                     历史订单列表,以List保存 :class:`.Order` 对象的message属性
    positions_hists    List                     历史仓位列表,以List保存 :class:`.Position` 对象的message属性
    asset_hists        List                     历史账户资产列表，以List保存 :class:`.Portfolio` 对象的message属性
    strategy_file      str                      策略文件名称及路径
    log_file           str                      日志文件名称及路径
    run_start          str                      回测开始时间，格式"yyyy-mm-dd HH:MM:SS"
    run_end            str                      回测运行结束时间（用于计算回测耗时）
    output_dir         str                      策略运行结果文件输出路径
    ================== =====================  =======================================================================

    """
    status_tb = ['停止', '运行中', '已完成', '失败', '', '取消', '暂停']

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
        self.portfolio = None           # 股票账户信息对象
        self.order_list = {}            # 当日的所有订单列表,key为order_ID
        self.order_hists = []           # 历史订单列表,以List保存order对象的message属性
        self.positions_hists = []       # 历史仓位列表,以List保存Position对象的message属性
        self.asset_hists = []           # 历史账户资产,以List保存Portfolio对象的message属性
        self.pass_today = False         # 分钟运行频率时，设置该值则跳过当天分钟循环
        self.strategy_file = None       # 策略文件名称及路径
        self.log_file = None            # 日志文件名称及路径
        self.run_start = None           # 回测运行开始时间（用于计算回测耗时）
        self.run_end = None             # 回测运行结束时间（用于计算回测耗时）
        self.output_dir = None          # 策略运行结果文件输出路径

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

    @property
    def get_run_type(self):
        return '回测' if self.run_type == RUN_TYPE.BACK_TEST else '实盘'

    @property
    def get_run_status(self):
        return self.status_tb[self.status.value]

    def read_log_file(self):
        ret = []
        for str_line in open(self.log_file):
            if str_line.startswith('qff>>'):
                str_time = str_line[7:26]
                str_level = str_line[29:39].split(' - ')[0]
                str_content = str_line[32+len(str_level):]

                ret.append([str_time, str_level, str_content])
        return ret

    @property
    def run_progress(self):
        if self.run_type == RUN_TYPE.BACK_TEST:
            total = get_trade_gap(self.start_date, self.end_date)
            crt = get_trade_gap(self.start_date, self.current_dt[:10])
            return round(crt / total, 4)
        else:
            return 1

    @property
    def spend_time(self):
        if self.run_type == RUN_TYPE.BACK_TEST and self.status == RUN_STATUS.DONE:
            end = self.run_end
        else:
            end = datetime.now()

        delta = end - self.run_start
        hour = int(delta.seconds / 3600)
        minute = int((delta.seconds % 3600) / 60)
        second = delta.seconds % 60
        return "{}天 {}时 {}分 {}秒".format(delta.days, hour, minute, second)

    @property
    def message(self):

        return {
            "策略名称": self.strategy_name,
            "框架类型": self.get_run_type,
            "当前状态": self.get_run_status,
            "运行频率": self.run_freq,
            "开始日期": self.start_date,
            "结束日期": self.end_date,
            "回测周期": get_trade_gap(self.start_date, self.end_date) if self.run_type == RUN_TYPE.BACK_TEST else None,
            "当前日期": self.current_dt,
            "运行天数": get_trade_gap(self.start_date, self.current_dt[:10]),
            "基准指数": self.benchmark,
            "初始资金": self.portfolio.starting_cash,
        }


class GlobalVar:
    """
    全局对象 g，用来存储用户的各类可被pickle.dumps函数序列化的全局数据

    在模拟盘中，如果中途进程中断，我们会使用[pickle.dumps]序列化所有的g下面的变量内容, 保存到磁盘中，再启动的时候模拟盘就不会
    有任何数据影响。如果没有用g声明，会出现模拟盘重启后，变量数据丢失的问题。

    **如果不想 g 中的某个变量被序列化, 可以让变量以 '__' 开头, 这样, 这个变量在序列化时就会被忽略**

    示例：

    ::

        def initialize(context):
            g.security = "000001"
            g.count = 1
            g.flag = 0

        def process_initialize(context):
            # 保存不能被序列化的对象, 进程每次重启都初始化, 更多信息, 请看 [process_initialize]
            g.__q = ["000001", "000002"]

        def handle_data(context, data):
            log.info(g.security)
            log.info(g.count)
            log.info(g.flag)

    """
    def __init__(self):
        self.type = None


strategy = Strategy()
context = Context()
g = GlobalVar()


def run_strategy_funcs(strategy_funcs):
    # try:
    if isinstance(strategy_funcs, list):
        for func in strategy_funcs:
            if callable(func):
                func()
    elif callable(strategy_funcs):
        strategy_funcs()
    # except Exception as e:
    #     print(e)
