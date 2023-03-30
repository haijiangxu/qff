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

import pandas as pd
from qff.price.cache import get_current_data
from qff.frame.context import context
from qff.frame.position import Position
from qff.frame.const import RUN_TYPE, ORDER_TYPE, ORDER_STATUS
from qff.price.query import get_stock_name
from qff.tools.utils import util_gen_id
from qff.tools.logs import log
from typing import Dict, Callable, Optional


# 订单未完成, 无任何成交
# 订单完成, 已撤销,
# 订单完成, 全部成交


# 订单状态


class Order:
    """
    订单对象

    ============== ======================== =====================================================
        属性        类型                      说明
    ============== ======================== =====================================================
    id             str                       订单编号
    security       str                       股票代码
    is_buy         boolean                   买入还是卖出， True-买入, False-卖出
    amount         int                       委托数量
    status         :class:`.ORDER_STATUS`    订单状态
    add_time       str                       订单委托时间
    deal_time      str                       订单成交时间
    cancel_time    str                       订单取消时间
    style          :class:`.ORDER_TYPE`      订单类型，市价单还是限价单
    order_price    float                     委托价格,当订单为限价单时
    trade_amount   int                       成交数量
    trade_money    float                     成交金额(含交易费用）
    trade_price    float                     成交均价，等于成交金额除以成交数量,包含了交易费用分摊
    commission     float                     交易费用（佣金、税费等）
    gain           float                     订单收益  股票卖出时计算该值
    ============== ======================== =====================================================


    """

    def __init__(self, security, amount, price=None, style=ORDER_TYPE.MARKET, callback=None):
        self.id = util_gen_id()  # 订单ID
        self.security = security  # 股票代码
        self.security_name = get_stock_name(security, context.current_dt[:10])[security]  # 股票名称
        self.is_buy = amount > 0  # 买入 or 卖出
        self.amount = abs(amount)  # 委托数量
        self.status = ORDER_STATUS.OPEN  # 订单状态
        self.add_time = context.current_dt  # 订单添加时间
        self.deal_time = None  # 订单成交时间
        self.cancel_time = None  # 订单取消时间
        self.style = style  # 市价单 or 限价单
        self.order_price = price  # 委托价格,当订单为限价单
        self.trade_amount = 0  # 成交数量
        # self.cancel_amount = 0  # 撤销数量
        self.trade_money = 0  # 成交金额(含交易费用）
        self.trade_price = 0  # 成交均价，等于成交金额除以成交数量,包含了交易费用分摊
        self.commission = 0  # 交易费用（佣金、税费等）
        self.gain = 0  # 订单收益  股票卖出时计算该值
        self._callback = callback

        # 对账户资金或股票进行锁定
        if self.is_buy:  # 买入

            money = round(price * amount, 2)
            commission = round(max(money * context.trade_cost.open_commission, context.trade_cost.min_commission)
                               + money * context.trade_cost.open_tax, 2)
            self.lock_money = money + commission

            context.portfolio.locked_cash += self.lock_money
            context.portfolio.available_cash -= self.lock_money
        else:  # 卖出
            context.portfolio.positions[security].locked_amount += self.amount
            context.portfolio.positions[security].closeable_amount -= self.amount

    @property
    def message(self):
        return {

            '订单编号': self.id,
            '股票代码': self.security,
            '股票名称': self.security_name,
            '交易方向': '买入' if self.is_buy else '卖出',
            '交易日期': self.add_time[:10],
            '委托时间': self.add_time[11:16],
            '成交状态': self.status,
            '委托数量': self.amount,
            '委托价格': self.order_price,
            '订单类型': self.style,
            '成交时间': self.deal_time[11:16],
            '成交单价': self.trade_price,
            '成交数量': self.trade_amount,
            '成交金额': self.trade_money,
            '交易费用': self.commission,
        }

    def __repr__(self):
        return self.message

    def deal(self, deal_time=None):
        """
        订单成交

        :return:
        """

        money = round(self.order_price * self.amount, 2)
        self.trade_amount = self.amount
        if self.is_buy:
            self.commission = round(max(money * context.trade_cost.open_commission,
                                        context.trade_cost.min_commission) + money * context.trade_cost.open_tax, 2)
            self.trade_money = money + self.commission
        else:
            self.commission = round(max(money * context.trade_cost.close_commission,
                                        context.trade_cost.min_commission) + money * context.trade_cost.close_tax, 2)
            self.trade_money = money - self.commission
            # 股票卖出时，计算该订单的收益
            self.gain = round(self.trade_money -
                              context.portfolio.positions[self.security].avg_cost * self.trade_amount, 2)

        self.trade_price = round(self.trade_money / self.trade_amount, 2)
        self.deal_time = deal_time if deal_time is not None else context.current_dt

        # 对账户资金或股票数据进行更新
        if self.is_buy:  # 买入
            context.portfolio.locked_cash -= self.lock_money
            if self.security in context.portfolio.positions.keys():
                # 加仓
                position: Position = context.portfolio.positions[self.security]
                position.today_open_amount += self.trade_amount  # 当日加仓数量
                position.today_open_price = self.trade_price  # 当日买入单价
                position.transact_time = self.deal_time  # 最后交易时间
                position.avg_cost = round((position.avg_cost * position.total_amount + self.trade_money)
                                          / (position.total_amount + self.trade_amount), 2)  # 当前持仓成本
                position.acc_avg_cost = round((position.acc_avg_cost * position.total_amount + self.trade_money)
                                              / (position.total_amount + self.trade_amount), 2)  # 累计持仓成本
                position.total_amount += self.trade_amount  # 总仓位

            else:
                # 生成一个position对象
                position = Position(self.security, self.security_name, self.deal_time, self.trade_amount,
                                    self.trade_price)
                context.portfolio.positions[self.security] = position

            log.info("订单成交：买入，订单编号：{}，股票代码：{}，下单数量：{}， 成交时间：{}.".
                     format(self.id, self.security, self.trade_amount, self.deal_time))

        else:  # 卖出
            context.portfolio.available_cash += self.trade_money
            position: Position = context.portfolio.positions[self.security]
            position.locked_amount -= self.amount  # 挂单冻结仓位
            position.transact_time = self.deal_time  # 最后交易时间
            if position.total_amount > self.trade_amount:
                position.acc_avg_cost = round((position.acc_avg_cost * position.total_amount - self.trade_money)
                                              / (position.total_amount - self.amount), 2)  # 累计持仓成本
            position.total_amount -= self.trade_amount  # 总仓位
            if position.total_amount == 0:
                context.portfolio.positions.pop(position.security)

            log.info("订单成交：卖出，订单编号：{}，股票代码：{}，下单数量：{}， 成交时间：{}.".
                     format(self.id, self.security, self.trade_amount, self.deal_time))

        self.status = ORDER_STATUS.DEAL

        if self._callback is not None:
            self._callback(ORDER_STATUS.DEAL)

    def cancel(self):
        """
        订单取消

        :return: 成功返回True
        """
        if self.status != ORDER_STATUS.OPEN:
            return False
        self.status = ORDER_STATUS.CANCELLED
        self.cancel_time = context.current_dt

        # 对账户资金或股票进行解锁
        if self.is_buy:  # 买入
            context.portfolio.locked_cash -= self.lock_money
            context.portfolio.available_cash += self.lock_money
        else:  # 卖出
            context.portfolio.positions[self.security].locked_amount -= self.amount
            context.portfolio.positions[self.security].closeable_amount += self.amount
        log.info("订单取消：订单编号：{}，股票代码：{}，下单数量：{}, {}."
                 .format(self.id, self.security, self.amount, ('买入' if self.is_buy else '卖出')))
        if self._callback is not None:
            self._callback(ORDER_STATUS.CANCELLED)

    def rejected(self):
        """
        订单拒绝

        :return:
        """
        pass


def order(security, amount=100, price=None, callback=None):
    # type: (str, int, float, Callable) -> Optional[str]
    """
    按股票数量下单

    调用成功后, 您将可以调用 :func:`.get_open_orders` 取得所有未完成的交易, 也可以调用 :func:`.order_cancel` 取消交易

    :param security: 标的代码
    :param amount: 交易数量, 正数表示买入, 负数表示卖出
    :param price: 下单价格，下单价格为空，则认为是市价单，按当前最新价格挂单，否则认为是限价单
    :param callback: 回调函数，订单成交/取消后调用执行， callback(status)

    :return:  成功返回order对象id，失败返回None

    订单撮合规则：

    1. 为简化操作，撮合时不考虑成交量,一个订单一次成交记录
    2. 市价单买入时按当前价格+滑点价格，转成限价单。如果当前价格为涨停价格，则订单取消。
    3. 市价单卖出时按当前价格-滑点价格，转成限价单。如果当前价格为跌停价格，则订单取消。
    4. 如果运行频率为天，则下单后立即撮合，读取剩余的分钟数据曲线,判断最高价是否大于委托价，是则成交。
    5. 如果运行频率为分钟，则下单后，每分钟都判断该订单是否符合成交条件。
    6. 对未成交的订单，在本交易日结束后撤销。
    
    """

    """
    1、根据股票数量判断是买入还是卖出
    2、取股票的最新价和涨跌停价
    3、如果是市价单，则买入价为最新价+滑点、卖出价为最新价-滑点
    4、判断买入卖出的价格是否超过涨跌停价，如果是则返回false
    5、判断买入的金额是否小于账户可用金额，卖出的股票数量是否小于当前持股数量，否则返回false
    6、生成订单对象，并加入到order_list中，锁定账户中对应的资金或股票
    7、如果运行频率为天，则立即撮合，取该股票下单时间后的分钟曲线数据，判断哪个bar能够成交，记录成交价格及成交时间
    
    """

    # log.info('调用order_amount' + str(locals()).replace('{', '(').replace('}', ')'))
    log.info(f'调用order(security={security}, amount={amount}, price={price})')
    slippage = context.slippage if amount > 0 else -context.slippage
    cur_data = get_current_data(security)
    if cur_data.paused:
        log.warning(f"下单失败:{security}当日停牌!")
        return None
    if price is None:
        style = ORDER_TYPE.MARKET
        order_price = round(cur_data.last_price * (1 + slippage), 2)
    else:
        style = ORDER_TYPE.LIMIT
        order_price = price

    if order_price > cur_data.high_limit:
        order_price = cur_data.high_limit
        log.warning('注意:下单价格为涨停价{}'.format(order_price))
    elif order_price < cur_data.low_limit:
        order_price = cur_data.low_limit
        log.warning('注意:下单价格为跌停价{}'.format(order_price))
    if amount > 0:
        new_amount = int(amount / 100) * 100  # 一手为100股
        if new_amount == 0:
            log.warning("下单失败：下单股票数量{}不足一手!".format(amount))
            return None
        if amount != new_amount:
            amount = new_amount
            log.info('注意：开仓数量必须是100的整数倍，调整为{}。'.format(amount))

        money = round(order_price * amount, 2)
        commission = round(max(money * context.trade_cost.open_commission, context.trade_cost.min_commission)
                           + money * context.trade_cost.open_tax, 2)
        money = money + commission

        if context.portfolio.available_cash <= money:
            available_cash = context.portfolio.available_cash - round(
                max(context.portfolio.available_cash * context.trade_cost.open_commission,
                    context.trade_cost.min_commission) + context.portfolio.available_cash * context.trade_cost.open_tax,
                2)

            new_amount = int((available_cash / order_price) / 100) * 100
            if new_amount == 0:
                log.warning("下单失败：账户可用资金可购买股票数量不足一手!")
                return None
            else:
                amount = new_amount
                log.warning("注意：账户可用资金不足! 调整开仓数量为{}".format(amount))

    elif amount < 0:
        if security not in context.portfolio.positions.keys() \
                or context.portfolio.positions[security].closeable_amount < abs(amount):
            log.warning("下单失败:账户无该数量的股票!")
            return None
    else:
        log.warning("下单失败:订单股票数量为0!")
        return None

    _order = Order(security, amount, order_price, style, callback)

    if _order is not None:
        context.order_list[_order.id] = _order
        log.info("下单成功：订单编号：{}，股票代码：{}，下单数量：{}, {}.".
                 format(_order.id, _order.security, amount, ('买入' if _order.is_buy else '卖出')))
        if context.run_freq == 'day' and context.run_type == RUN_TYPE.BACK_TEST:
            order_broker_day(_order.id)
        return _order.id
    else:
        return None


def order_value(security, value, price=None, callback=None):
    # type: (str, float, float, Callable) -> Optional[str]
    """
    按股票价值下单

    :param security: 股票代码
    :param value: 股票价值，value = 最新价 * 手数  * 乘数（股票为100）
    :param price: 下单价格，市价单可不填价格，按当前最新价格挂单
    :param callback: 回调函数，订单成交/取消后调用执行， callback(status)

    :return: Order对象id或者None, 如果创建委托成功, 则返回Order对象id, 失败则返回None
    :Example:
        .. code-block:: python

            # 卖出价值为10000元的平安银行股票
            order_value('000001', -10000)
    """
    log.debug('调用order_value' + str(locals()).replace('{', '(').replace('}', ')'))
    if value == 0:
        log.warning("下单失败:下单股票价值为0!")
        return None

    cur_data = get_current_data(security)

    slippage = context.slippage if value > 0 else -context.slippage
    order_price = price if price is not None else cur_data.last_price * (1 + slippage)
    # order_price = price if price is not None else cur_data.last_price

    amount = int(value / order_price)

    return order(security, amount, price, callback)


def order_target(security, amount, price=None, callback=None):
    # type: (str, int, float, Callable) -> Optional[str]
    """
    按股票目标数量下单

    使最终标的的数量达到指定的amount。
    **注意使用此接口下单时若指定的标的有未完成的订单，则先前未完成的订单将会被取消**

    :param security: 股票代码
    :param amount: 期望的标的最终持有的股票数量
    :param price: 下单价格，市价单可不填价格，按当前最新价格挂单
    :param callback: 回调函数，订单成交/取消后调用执行， callback(status)

    :return: Order对象id或者None, 如果创建委托成功, 则返回Order对象id, 失败则返回None

    """
    log.debug('调用order_target' + str(locals()).replace('{', '(').replace('}', ')'))
    if amount < 0:
        log.warning("下单失败：目标数量不能小于0！")
        return None

    pre_hold = 0  # 之前建仓的股票数量
    if security in context.portfolio.positions.keys():
        pst: Position = context.portfolio.positions[security]
        _order: Order
        for _order in context.order_list.values():
            if _order.security == security and _order.status == ORDER_STATUS.OPEN:
                _order.cancel()
        if pst.today_open_amount > amount:
            log.warning("今日建仓的股票数量大于目标数量！,目标数量修改为今日建仓数量！")
            amount = pst.today_open_amount
        pre_hold = pst.total_amount

    return order(security, amount - pre_hold, price, callback)


def order_target_value(security, value, price=None, callback=None):
    # type: (str, float, float, Callable) -> Optional[str]
    """
    按股票目标价值下单

    调整标的仓位到value价值，
    **注意使用此接口下单时若指定的标的有未完成的订单，则先前未完成的订单将会被取消**

    :param security: 股票代码
    :param value: 期望的标的最终价值，value = 最新价 * 手数  * 乘数（股票为100）
    :param price: 下单价格，市价单可不填价格，按当前最新价格挂单
    :param callback: 回调函数，订单成交/取消后调用执行， callback(status)


    :return: Order对象id或者None, 如果创建委托成功, 则返回Order对象id, 失败则返回None

    :Example:

        .. code-block:: python

            # 卖出价值为10000元的平安银行股票
            order_value('000001', -10000)
            #卖出平安银行所有股票
            order_target_value('000001', 0)
            #调整平安银行股票仓位到10000元价值
            order_target_value('000001', 10000)
    """
    log.debug('调用order_target_value' + str(locals()).replace('{', '(').replace('}', ')'))
    order_price = get_current_data(security).last_price
    amount = int(value / order_price)
    return order_target(security, amount, price, callback)


def order_cancel(order_id):
    # type: (str) -> bool
    """
    撤回已下的订单

    :param order_id: 订单编号
    :return: 成功返回True,失败返回False

    """
    log.debug('调用order_cancel' + str(locals()).replace('{', '(').replace('}', ')'))
    if order_id in context.order_list.keys():
        order_obj: Order = context.order_list[order_id]
        return order_obj.cancel()
    else:
        return False


def get_orders(order_id=None, security=None, status=None):
    # type: (str, str, ORDER_TYPE) -> Dict[str, Order]
    """
    获取当天的所有订单

    :param order_id: 订单 id
    :param security: 标的代码，可以用来查询指定标的的所有订单
    :param status: 查询特定订单状态的所有订单

    :return: 返回一个dict, key是order_id, value是 :class:`.Order` 对象
    """
    log.debug('调用get_orders' + str(locals()).replace('{', '(').replace('}', ')'))
    rtn = {}
    if order_id is not None:
        if order_id in context.order_list.keys():
            rtn[order_id] = context.order_list[order_id]
    elif security is not None:
        for _id, order_obj in context.order_list.items():
            if order_obj.security == security:
                rtn[_id] = context.order_list[_id]
    elif status is not None:
        for _id, order_obj in context.order_list.items():
            if order_obj.status == status:
                rtn[_id] = context.order_list[_id]
    else:
        rtn = context.order_list
    return rtn


def get_open_orders():
    """
    获得当天的所有未完成的订单

    :return: 返回一个dict, key是order_id, value是[Order]对象
    """
    rtn = {}
    for _id, order_obj in context.order_list.items():
        if order_obj.status == ORDER_STATUS.OPEN:
            rtn[_id] = order_obj
    return rtn


def order_broker_day(order_id):
    """
    如果回测运行频率为 'day',则立即进行订单撮合
    :param order_id:
    :return: None
    """
    log.debug('调用order_broker_day' + str(locals()).replace('{', '(').replace('}', ')'))
    _order = context.order_list[order_id]
    code = _order.security

    data: pd.DataFrame = get_current_data(code).min_data_after
    if data is not None and len(data) > 1:
        for i in range(0, len(data)):
            if _order.is_buy:
                if data.iloc[i].low <= _order.order_price:
                    _order.deal(data.index[i])
                    break
            elif data.iloc[i].high >= _order.order_price:
                _order.deal(data.index[i])
                break
    return


def order_broker():
    """
    分钟撮合函数，根据回测频率运行
    :return:
    """
    log.debug('调用order_broker' + str(locals()).replace('{', '(').replace('}', ')'))
    for _order in context.order_list.values():
        if _order.add_time[0:10] != context.current_dt[0:10]:  # 防止框架恢复运行导入其他日期的context
            context.order_list.remove(_order)
        if _order.status == ORDER_STATUS.OPEN and _order.add_time < context.current_dt:  # 防止下单后马上撮合
            code = _order.security
            data = get_current_data(code)
            if _order.is_buy:
                if data.last_low < _order.order_price:
                    _order.deal()
                    # log.info("订单成交：订单编号{}，股票代码{},成交数量{}，成交时间{}"
                    #          .format(_order.id, code, _order.trade_amount, context.current_dt[11:]))

            elif data.last_high > _order.order_price:
                _order.deal()
                # log.info("订单成交：订单编号{}，股票代码{},成交数量{}，成交时间{}"
                #          .format(_order.id, code, _order.trade_amount, context.current_dt[11:]))
