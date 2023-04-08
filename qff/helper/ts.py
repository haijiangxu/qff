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

"""
调整框架接口函数后不能直接使用，需重构修改

--辅助交易系统--

在策略函数中，用户只需关注选股和择时，将交易系统中的其他内容在本模型中实现
包括以下部分：
1、账户总仓位控制（可多个）:
        根据大盘指数判断牛、熊及震荡市，以此决策参与的仓位。当可用仓位小于控制仓位，不强制卖出股票，
        仅限制股票的买入。
2、大盘风险控制（可多个）
        根据大盘走势判断大盘风险级别，并根据风险级别决策下一步动作：
        0：无风险；1：不加仓；2：减仓至50%；3：减仓至20%；4：清仓
3、个股仓位控制
        配置个股仓位控制策略，在买入股票时，根据策略决策买入股票的数量或金额
4、止损策略
        配置股票止损策略，在买入股票时，需根据止损策略计算股票的止损价格，并在
        交易期间实时（或收盘前定时）判断是否达到止损条件，并自动进行股票卖出操作。
5、止盈策略（可多个）
        通过配置股票的止盈策略，将根据股票走势，选择股票的卖出时机。
        如果卖出价格低于成本价，则执行止损策略，忽略止盈策略。

"""

import json
from functools import partial

from qff.frame.context import context, g
from qff.frame.const import RUN_TYPE, ORDER_STATUS
from qff.frame.api import run_daily
from qff.frame.order import order_value, order_target
from qff.price.cache import get_current_data
from qff.price.query import get_price
from qff.tools.date import get_pre_trade_day, get_trade_gap
from qff.tools.logs import log
from qff.helper.indicator import ind_macd, ind_ma, ind_atr


class TsContext:
    def __init__(self):
        self.total_positions_cof = {}   # 策略控制总仓位系数
        # self.total_positions = context.portfolio.total_assets  # 策略控制总仓位
        self.stop_loss_price = {}    # 股票代码:止损价格
        self.calc_stop_loss_price_func = None  # 计算止损价格的函数对象
        self.calc_each_position_func = None  # 计算个股仓位的函数对象
        self.index_data = None  # 指数数据，用于仓位控制

    @property
    def available_positions(self):
        if len(self.total_positions_cof) > 0:
            cof = min(list(self.total_positions_cof.values()))
        else:
            cof = 1

        rtn = context.portfolio.total_assets * cof - (context.portfolio.total_assets
                                                      - context.portfolio.available_cash
                                                      - context.portfolio.locked_cash)
        return round(rtn, 2)

    def get_index_data(self, ref_index):
        if context.run_type == RUN_TYPE.BACK_TEST:
            if self.index_data is None:
                _start = get_pre_trade_day(context.start_date, 200)
                self.index_data = get_price(ref_index, start=_start, end=context.end_date, market='index')
                self.index_data = ind_macd(self.index_data)
                self.index_data = ind_ma(self.index_data)
            return self.index_data.loc[:context.previous_date]

        else:
            self.index_data = get_price(ref_index, end=context.previous_date, count=200, market='index')
            self.index_data = ind_macd(self.index_data)
            self.index_data = ind_ma(self.index_data)
            return self.index_data


#######################################################################################################################
# 交易系统对外接口
def ts_init(json_file=None):
    """
    辅助交易系统初始化
    :param json_file: 交易系统配置文件
    :return: None
    """

    if json_file is not None:
        try:
            with open(json_file, 'r', encoding='utf-8') as fw:
                g.ts_config = json.load(fw)
        except Exception as e:
            log.error('导入的ts配置文件解析错误！')
            log.error(e)

    _register_ts_func('total_position_control', g.ts_config)
    _register_ts_func('market_risk_control', g.ts_config)
    _register_ts_func('stop_win_control', g.ts_config)

    # 初始化个股仓位控制函数
    try:
        g.ts_context.calc_each_position_func = None
        if 'each_position_control' in g.ts_config.keys() and g.ts_config['each_position_control']['enable']:
            for item in g.ts_config['each_position_control']['methods']:
                if item['enable']:
                    g.ts_context.calc_each_position_func = partial(globals()[item['name']], **item['args'])
                    break
    except Exception as e:
        log.error('ts配置文件错误！配置项：each_position_control')
        log.error(e)

    # 初始化止损策略控制函数
    try:
        g.ts_context.calc_stop_loss_price_func = None
        if 'stop_loss_control' in g.ts_config.keys() and g.ts_config['stop_loss_control']['enable']:
            slc_handle_func = globals()[g.ts_config['stop_loss_control']['main_handler']]
            for runtime in g.ts_config['stop_loss_control']['run_time']:
                run_daily(slc_handle_func, runtime, append=False)

            for item in g.ts_config['stop_loss_control']['methods']:
                if item['enable']:
                    g.ts_context.calc_stop_loss_price_func = partial(globals()[item['name']], **item['args'])
                    break
    except Exception as e:
        log.error('ts配置文件错误！配置项：stop_loss_control')
        log.error(e)


def open_position(security, amount=None, price=None, stop_loss_price=None):
    """
    根据交易系统规则开仓，如何使用辅助交易系统，需使用此函数进行股票买入操作
    :param security: 股票代码
    :param amount:   买入数量,如果为空则采用个股仓位控制策略决定买入数量
    :param price:    买入价格,如果为空则取当前最新价格
    :param stop_loss_price:  止损价格，如果为空，则根据止损策略计算止损价格
    :return: 成功返回order对象，失败返回None
    """
    # 1、根据总仓位控制策略计算当前可用仓位
    if g.ts_context.available_positions < 2000:
        log.debug('open_position：当前可用仓位金额不足'.format(security))
        return None

    # 2、根据止损策略计算止损价格
    if price is None:
        price = get_current_data(security).last_price
    if stop_loss_price is None:
        stop_loss_price = get_stop_loss_price(security, price)

    # 3、根据个股仓位控制策略计算可开仓数量
    if amount is None:
        if g.ts_context.calc_each_position_func:
            need_cash = g.ts_context.calc_each_position_func(price, stop_loss_price)
        else:
            need_cash = context.portfolio.available_cash
    else:
        need_cash = price * amount

    need_cash = min(need_cash, g.ts_context.available_positions)

    # 4、调用order进行下单操作
    def slp_callback(status, code, loss_price):  # 定义回调函数
        if status == ORDER_STATUS.DEAL:
            g.ts_context.stop_loss_price[code] = loss_price
            log.info('设置止损价格成功{}：{}'.format(code, loss_price))

    if stop_loss_price:
        _callback = partial(slp_callback, code=security, loss_price=stop_loss_price)
    else:
        _callback = None
    return order_value(security, need_cash, price, _callback)


def get_stop_loss_price(security, price=None):
    """
    获取计算的股票止损价格
    :param security:股票代码
    :param price:当前价格
    :return: 止损价
    """
    if g.ts_context.calc_stop_loss_price_func:
        return g.ts_context.calc_stop_loss_price_func(security, price)
    else:
        log.error('open_position：未获取股票{}的止损价格！'.format(security))
        return None


def can_open_position():
    """
    根据仓位控制策略，以及当前仓位情况，判断当前能否进行开仓操作
    :return: bool True-可以 False-不可以
    """
    return g.ts_context.available_positions >= 2000


#######################################################################################################################
# 总仓位控制策略
def tpc_by_macd(ref_index='000001'):
    """
    根据MACD位置，判断当前趋势，以决策当前仓位
    MACD>0 50%； 同时dif>0 100%
    """
    data = g.ts_context.get_index_data(ref_index)
    if data.macd[-1] > 0 and data.dif[-1] > 0:
        cof = 1
    elif data.macd[-1] > 0:
        cof = 0.5
    elif data.dif[-1] > 0:
        cof = 0.5
    else:
        cof = 0.2
    g.ts_context.total_positions_cof['macd'] = cof
    # g.ts_context.total_positions = round(context.portfolio.total_assets * cof, 2)


def tpc_by_ma(ref_index='000001'):
    """
    根据短中长期均线多头/空头排列，判断当前趋势，以决策当前仓位
    指数短中长期均线多头排列80-100%；指数短中期均线多头排列：50-80%；
    指数中长期均线空头排列20-50%，熊市0-20%
    """
    data = g.ts_context.get_index_data(ref_index)
    if data.ma10[-1] > data.ma60[-1] > data.ma120[-1] and \
            data.ma10[-1] > data.ma10[-2] > data.ma10[-3] and \
            data.ma60[-1] > data.ma60[-2] > data.ma60[-3] and \
            data.ma120[-1] > data.ma120[-2] > data.ma120[-3]:
        cof = 1
    elif data.ma10[-1] > data.ma60[-1] > data.ma120[-1]:
        cof = 0.8
    elif data.ma10[-1] > data.ma60[-1] > data.ma60[-2] > data.ma60[-3] and \
            data.ma10[-1] > data.ma10[-2] > data.ma10[-3]:
        cof = 0.8
    elif data.ma10[-1] > data.ma60[-1]:
        cof = 0.5
    elif data.ma10[-1] < data.ma60[-1] < data.ma120[-1] and \
            data.ma10[-1] < data.ma10[-2] < data.ma10[-3] and \
            data.ma60[-1] < data.ma60[-2] < data.ma60[-3] and \
            data.ma120[-1] < data.ma120[-2] < data.ma120[-3]:
        cof = 0
    else:
        cof = 0.2
    g.ts_context.total_positions_cof['ma'] = cof
    # g.ts_context.total_positions = round(context.portfolio.total_assets * cof, 2)


#######################################################################################################################
# 个股仓位控制策略
# 个股仓位控制1-通过最大损失比例决策
def epc_by_max_loss(buy_price, stop_loss_price, loss_ctrl=0.01):
    """
    个股止损后不损失不超过总资产1%,倒推可以购买的股票数量
    :param buy_price: 买入价格
    :param stop_loss_price: 止损价格
    :param loss_ctrl: 单次交易能够承担最大的损失比例，默认0.01
    :return:
    """
    loss_ratio = stop_loss_price/buy_price
    funds = context.portfolio.total_assets * loss_ctrl / loss_ratio
    return min(funds, context.portfolio.available_cash)


# 个股仓位控制2-固定比例
def epc_by_fix_ratio(buy_price, stop_loss_price, ratio=0.1):
    """
    根据固定比例决策可购买的股票数量, 50万以下20%， 50万以上10%
    :param buy_price: 买入价格
    :param stop_loss_price: 止损价格
    :param ratio: 单次交易能够承担最大的损失比例，默认0.1
    :return: 可购买股票数量
    """
    funds = context.portfolio.total_assets * ratio
    return min(funds, context.portfolio.available_cash)


#######################################################################################################################
# 大盘风险控制策略
# 风险控制0 - 大盘上证指数最近10日下跌10%时全部清仓，当日不买入。

# 风险控制1-形态判断（三只乌鸦等）
def mrc_by_form(ref_index, form_type):
    pass


# 风险控制2-日内分时图实时判断，应对大盘暴跌的风险
def mrc_realtime(ref_index, form_type):
    pass


# 风险控制3-根据风险时间窗口
def mrc_window_period(ref_index, form_type):
    pass


# 风险控制4-整体仓位最高下跌幅度
def mrc_dropback(ref_index, form_type):
    pass


#######################################################################################################################
# 止损策略
# 止损操作函数
def slc_main_handler():
    # 判断持仓股票当前价格是否低于止损价，
    for security in list(g.ts_context.stop_loss_price.keys()):
        if security not in context.portfolio.positions.keys():
            g.ts_context.stop_loss_price.pop(security)
        else:
            if context.portfolio.positions[security].closeable_amount > 0 and \
                    get_current_data(security).last_price < g.ts_context.stop_loss_price[security]:
                order_target(security, 0)
                log.info("止损操作：股票代码：{}".format(security))


# 止损价计算
# 1、固定亏损率，当买入个股的浮动亏损幅度达到某个百分点时进行止损，短线5%，中长线10%
def slc_fix_ratio(security, buy_price, ratio):
    if buy_price is None:
        buy_price = get_current_data(security).last_price
    sl_price = round(buy_price * (1 - ratio), 2)
    return sl_price


# 2、ATR倍数, 买入价减去三倍20日平均日波动（ATR)作为止损价'
def slc_atr_multiple(security, buy_price, multiple=3, period=20):
    df = get_price(security, end=context.previous_date, count=period + 1,
                   skip_paused=True)
    n = period if len(df) >= period else len(df) - 1
    sl_price = round(buy_price - ind_atr(df, n)['atr'][-1] * multiple, 2)
    return sl_price


# 3、根据前期跌幅计算(250天内最大的n(n=3)日跌幅 + 个股250天内平均的n日跌幅)/2
def slc_before_max_loss(security, buy_price, scope=250, short=3):
    df = get_price(security, end=context.previous_date, count=scope, skip_paused=True)
    pct = df['close'].pct_change(short)
    loss_rate = (pct.min() + pct.mean()) / 2
    sl_price = round(buy_price * (1 - abs(loss_rate)), 2)
    return sl_price


#######################################################################################################################
# 止盈策略
# 1、回撤止盈:最高价下跌百分比
def swc_dropback(ratio=0.05):
    if "high_price" not in dir(g.ts_context):
        g.ts_context.high_price = {}
    else:
        for security in list(g.ts_context.high_price.keys()):
            if security not in context.portfolio.positions.keys():
                g.ts_context.high_price.pop(security)

    for stock in list(context.portfolio.positions.keys()):
        data = get_current_data(stock)

        if stock not in g.ts_context.high_price.keys() or \
                data.high_all_day > g.ts_context.high_price[stock]:
            g.ts_context.high_price[stock] = data.high_all_day

        # if self.high_price[stock] * self.threshold > data.last_price > context.portfolio.positions[stock].avg_cost:
        if g.ts_context.high_price[stock] * (1 - ratio) > data.last_price:
            order_target(stock, 0)
            log.info("止盈操作：回撤止盈，股票代码：{}，止盈价格：{}".format(stock, data.last_price))


# 2、重要的均线被跌破
def swc_fall_ma(ma_type=0, period=10):
    """
    重要的均线被跌破
    :param ma_type: 0=SMA, 1=EMA, 2=WMA, 3=DEMA, 4=TEMA, 5=TRIMA, 6=KAMA, 7=MAMA, 8=T3 (Default=SMA)
    :param period: 均线周期，默认 [5, 10, 20, 30, 60, 120, 250]
    :return:
    """
    import numpy as np
    import talib as tl

    for stock in list(context.portfolio.positions.keys()):
        if context.portfolio.positions[stock].closeable_amount > 0:  # 当天买入或已挂单卖出的股票除外
            close = get_price(stock, end=context.previous_date, count=period - 1,
                              fields=['close']).close.values
            new_close = get_current_data(stock).last_price
            close = np.append(close, new_close)
            ma = np.around(tl.MA(close, timeperiod=period, matype=ma_type), 4)[-1]

            if ma > new_close:
                order_target(stock, 0)
                log.info("止盈操作：均线跌破，股票代码：{}，止盈价格：{}".format(stock, new_close))


# 3、横盘止损
def swc_long_time(period=10, pct=0.1):
    """
    横盘止损：将买入之后价格在一定幅度内横盘的时间设为止损目标
    :param period: 横盘的设定时间
    :param pct: ：涨幅参数
    :return:
    """
    for stock in list(context.portfolio.positions.keys()):
        start = context.portfolio.positions[stock].init_time
        if get_trade_gap(start, context.current_dt[:10]) > period:
            data = get_current_data(stock)
            curr_pct = data.last_price / context.portfolio.positions[stock].avg_cost - 1
            if curr_pct < pct:
                order_target(stock, 0)
                log.info("止盈操作：时间止盈，股票代码：{}，止盈价格：{}".format(stock, data.last_price))


#######################################################################################################################
# 本地辅助函数
def _register_ts_func(key_value, ts_config):
    try:
        if key_value in ts_config.keys() and ts_config[key_value]['enable']:
            for item in ts_config[key_value]['methods']:
                if item['enable']:
                    func = partial(globals()[item['name']], **item['args'])
                    for runtime in item['run_time']:
                        run_daily(func, runtime, append=False)
    except Exception as e:
        log.error('ts配置文件错误！配置项：{}'.format(key_value))
        log.error(e)


g.ts_context = TsContext()
g.ts_config = {
    'total_position_control': {
        'enable': True,
        'desc': '根据大盘指数判断牛、熊及震荡市，以此决策参与的仓位',
        'methods': [
            {
                'name': 'tpc_by_macd',
                'enable': True,
                'run_time': ['before_open'],
                'args': {'ref_index': '000001'},
                'comment': '根据指数MACD判断当前趋势，以决策当前仓位，MACD>0 50%； 同时dif>0 100%。'
            },
            {
                'name': 'tpc_by_ma',
                'enable': False,
                'run_time': ['before_open'],
                'args': {'ref_index': '000001'},
                'comment': '根据短中长期均线多头/空头排列，判断当前趋势，以决策当前仓位。'
            }
        ]
    },
    'each_position_control': {
        'enable': True,
        'desc': ' 配置个股仓位控制策略，在买入股票时，根据策略决策买入股票金额',
        'methods': [
            {
                'name': 'epc_by_fix_ratio',
                'enable': True,
                'run_time': None,
                'args': {'ratio': 0.1},
                'comment': '根据固定比例决策可购买的股票金额'
            },
            {
                'name': 'epc_by_max_loss',
                'enable': False,
                'run_time': None,
                'args': {'loss_ctrl': 0.01},
                'comment': '个股止损后不损失不超过总资产1%,倒推可以购买的股票金额'
            }
        ]
    },
    'market_risk_control': {
        'enable': False,
        'desc': '根据大盘走势判断大盘风险级别，并决策下一步动作,0：无风险；1：不加仓；2：减仓至50%；3：减仓至20%；4：清仓。',
        'methods': [
            {
                'name': 'mrc_by_form',
                'enable': False,
                'run_time': ['14:50'],
                'args': {'ref_index': '000001', 'form_type': 'three_crow'},
                'comment': '根据大盘顶部形态如三只乌鸦进行判断'
            },
            {
                'name': 'mrc_realtime',
                'enable': False,
                'run_time': ['every_bar'],
                'args': {'ref_index': '000001', 'fall_ratio': 0.04},
                'comment': '日内分时图实时判断，应对大盘暴跌的风险'
            },
            {
                'name': 'mrc_window_period',
                'enable': False,
                'run_time': ['before_open'],
                'args': {'periods': [['12-20', '12-31'], ['04-15', '04-30']]},
                'comment': '根据风险时间窗口，12月下旬、4月底、7月中旬等'
            },
            {
                'name': 'mrc_dropback',
                'enable': False,
                'run_time': ['every_bar'],
                'args': {'max_dropback': 0.08},
                'comment': '根据整体仓位最高市值的下跌幅度，即最大回撤'
            }
        ]
    },
    'stop_loss_control': {
        'enable': True,
        'desc': '配置股票止损策略,stop_loss_price函数配置为第一个为true的methods',
        'run_time': ['14:50'],
        'main_handler': 'slc_main_handler',
        'methods': [
            {
                'name': 'slc_fix_ratio',
                'enable': True,
                'args': {'ratio': 0.05},
                'comment': '固定亏损率，当买入个股的浮动亏损幅度达到某个百分点时进行止损'
            },
            {
                'name': 'slc_atr_multiple',
                'enable': False,
                'args': {'multiple': 3, 'period': 20},
                'comment': '3倍ATR, 买入价减去三倍20日平均日波动（ATR)作为止损价'
            },
            {
                'name': 'slc_before_max_loss',
                'enable': False,
                'args': {'scope': 250, 'short': 3},
                'comment': '(250天内最大的n(n=3)日跌幅 + 个股250天内平均的n日跌幅)/2'
            }
        ]
    },
    'stop_win_control': {
        'enable': True,
        'desc': '配置股票的止盈策略，根据股票走势，选择卖出时机',
        'methods': [
            {
                'name': 'swc_dropback',
                'enable': True,
                'run_time': ['14:50'],
                'args': {'ratio': 0.08},
                'comment': '回撤止盈:最高价下跌百分比'
            },
            {
                'name': 'swc_fall_ma',
                'enable': True,
                'run_time': ['14:50'],
                'args': {'ma_type': 0, 'period': 10},
                'comment': '重要的均线被跌破'
            },
            {
                'name': 'swc_long_time',
                'enable': False,
                'run_time': ['14:50'],
                'args': {'period': 10, 'pct': 0.1},
                'comment': '横盘止损'
            }
        ]
    }
}
