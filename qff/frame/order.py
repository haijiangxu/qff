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
from qff.frame.context import context, Position, RUNTYPE

from qff.tools.utils import util_gen_id
from qff.tools.logs import log

LIMIT_PRICE = "限价单"  # LIMIT_PRICE
MARKET_ORDER = "市价单"  # "MARKET_ORDER"

# 订单未完成, 无任何成交
ORDER_OPEN = "open"
# 订单完成, 已撤销,
ORDER_CANCELED = "canceled"
# 订单完成, 全部成交
ORDER_DEAL = "held"


# 订单状态


class Order:
    """
     订单对象
    """

    def __init__(self, security, amount, price=None, style=MARKET_ORDER, callback=None):
        self.id = util_gen_id()  # 订单ID
        self.security = security  # 股票代码
        self.is_buy = amount > 0  # 买入 or 卖出
        self.amount = abs(amount)  # 委托数量
        self.status = ORDER_OPEN  # 订单状态
        self.add_time = context.current_dt  # 订单添加时间
        self.deal_time = None  # 订单成交时间
        self.cancel_time = None  # 订单取消时间
        self.style = style  # 市价单 or 限价单
        self.order_price = price  # 委托价格,当订单为限价单
        self.trade_amount = 0  # 成交数量
        # self.cancel_amount = 0  # 撤销数量
        self.trade_money = 0  # 成交金额(含交易费用）
        self.trade_price = 0  # 成交均价，为简化本框架成交价等于委托价
        self.commission = 0  # 交易费用（佣金、税费等）
        self.gain = 0  # 订单收益  股票卖出时计算该值
        self._callback = callback

        # 对账户资金或股票进行锁定
        if self.is_buy:  # 买入
            context.portfolio.locked_cash += self.amount * self.order_price
            context.portfolio.available_cash -= self.amount * self.order_price
        else:  # 卖出
            context.portfolio.positions[security].locked_amount += self.amount
            context.portfolio.positions[security].closeable_amount -= self.amount

    def message(self):
        return {
            '订单编号': self.id,
            '股票代码': self.security,
            '交易方向': '买入' if self.is_buy else '卖出',
            '下单时间': self.add_time,
            '成交状态': self.status,
            '委托数量': self.amount,
            '委托价格': self.order_price,
            '订单类型': self.style,
            '成交时间': self.deal_time,
            '成交单价': self.trade_price,
            '成交数量': self.trade_amount,
            '成交金额': self.trade_money,
            '交易费用': self.commission,
        }

    def deal(self, deal_time=None):
        """
        订单成交
        :return:
        """
        self.status = ORDER_DEAL
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
            context.portfolio.locked_cash -= self.amount * self.order_price
            context.portfolio.available_cash += self.amount * self.order_price
            context.portfolio.available_cash -= self.trade_money
            if self.security in context.portfolio.positions.keys():
                # 加仓
                position: Position = context.portfolio.positions[self.security]
                position.today_amount += self.trade_amount  # 当日加仓数量
                position.transact_time = self.deal_time  # 最后交易时间
                position.avg_cost = round((position.avg_cost * position.total_amount + self.trade_money) / \
                                          (position.total_amount + self.trade_amount), 2)  # 当前持仓成本
                position.acc_avg_cost = round((position.acc_avg_cost * position.total_amount + self.trade_money) / \
                                              (position.total_amount + self.trade_amount), 2)  # 累计持仓成本
                position.total_amount += self.trade_amount  # 总仓位

            else:
                # 生成一个position对象
                position = Position(self.security, self.deal_time, self.trade_amount, self.trade_price)
                context.portfolio.positions[self.security] = position

        else:  # 卖出
            context.portfolio.available_cash += self.trade_money
            position: Position = context.portfolio.positions[self.security]
            position.locked_amount -= self.amount  # 挂单冻结仓位
            position.transact_time = self.deal_time  # 最后交易时间
            if position.total_amount > self.trade_amount:
                position.acc_avg_cost = round((position.acc_avg_cost * position.total_amount - self.trade_money) \
                                              / (position.total_amount - self.amount), 2)  # 累计持仓成本
            position.total_amount -= self.trade_amount  # 总仓位
            if position.total_amount == 0:
                context.portfolio.positions.pop(position.security)

        log.info("订单成交：订单编号：{}，股票代码：{}，下单数量：{}， 成交时间：{}.".
                 format(self.id, self.security, self.trade_amount, self.deal_time))
        if self._callback is not None:
            self._callback(ORDER_DEAL)

    def cancel(self):
        """
        订单取消
        :return: 成功返回True
        """
        if self.status != ORDER_OPEN:
            return False
        self.status = ORDER_CANCELED
        self.cancel_time = context.current_dt

        # 对账户资金或股票进行解锁
        if self.is_buy:  # 买入
            context.portfolio.locked_cash -= self.amount * self.order_price
            context.portfolio.available_cash += self.amount * self.order_price
        else:  # 卖出
            context.portfolio.positions[self.security].locked_amount -= self.amount
            context.portfolio.positions[self.security].closeable_amount += self.amount
        log.info("订单取消：订单编号：{}，股票代码：{}，下单数量：{}, {}."
                 .format(self.id, self.security, self.amount, ('买入' if self.is_buy else '卖出')))
        if self._callback is not None:
            self._callback(ORDER_CANCELED)

    def rejected(self):
        """
        订单拒绝
        :return:
        """
        pass


def order_amount(security, amount=100, price=None, callback=None):
    """
    按股票数量下单。
    调用成功后, 您将可以调用[get_open_orders]取得所有未完成的交易, 也可以调用[cancel_order]取消交易

    参数
        :param security: 标的代码
        :param amount: 交易数量, 正数表示买入, 负数表示卖出
        :param price: 下单价格，下单价格为空，则认为是市价单，按当前最新价格挂单，否则认为是限价单
        :param callback: 回调函数，订单成交/取消后调用执行， callback(status)
    返回
        :return:  成功返回order对象，失败返回None
    """

    """
    在回测环境下：
    1、为简化操作，撮合时不考虑成交量,一个订单一次成交记录
    2、市价单买入时按当前价格+滑点价格，转成限价单。如果当前价格为涨停价格，则订单取消。
    3、市价单卖出时按当前价格-滑点价格，转成限价单。如果当前价格为跌停价格，则订单取消。
    4、如果运行频率为天，则下单后立即撮合，读取剩余的分钟数据曲线,判断最高价是否大于委托价，是则成交。
    5、如果运行频率为分钟，则下单后，每分钟都判断该订单是否符合成交条件。
    6、对未成交的订单，在本交易日结束后撤销。已成交订单，在交易日结束后转移至deal_list,order_list清空
    
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

    log.info('调用order_amount' + str(locals()).replace('{', '(').replace('}', ')'))
    slippage = context.slippage if amount > 0 else -context.slippage
    cur_data = get_current_data(security)
    if price is None:
        style = MARKET_ORDER
        order_price = round(cur_data.last_price * (1 + slippage), 2)
    else:
        style = LIMIT_PRICE
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

        if context.portfolio.available_cash <= order_price * amount:
            new_amount = int((context.portfolio.available_cash / order_price)/100) * 100
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

    order = Order(security, amount, order_price, style, callback)

    if order is not None:
        context.order_list[order.id] = order
        log.info("下单成功：订单编号：{}，股票代码：{}，下单数量：{}, {}.".
                 format(order.id, order.security, amount, ('买入' if order.is_buy else '卖出')))
        if context.run_freq == 'day' and context.run_type == RUNTYPE.BACK_TEST:
            order_broker_day(order.id)
        return order.id
    else:
        return None


def order_value(security, value, price=None, callback=None):
    """
    按股票价值下单

    参数
        :param security: 股票代码
        :param value: 股票价值，value = 最新价 * 手数  * 乘数（股票为100）
        :param price: 下单价格，市价单可不填价格，按当前最新价格挂单
        :param callback: 回调函数，订单成交/取消后调用执行， callback(status)

    返回
        :return: Order对象或者None, 如果创建委托成功, 则返回Order对象, 失败则返回None
    示例
        卖出价值为10000元的平安银行股票
        order_value('000001', -10000)
    """
    if value == 0:
        log.warning("下单失败:下单股票价值为0!")
        return None

    cur_data = get_current_data(security)
    slippage = context.slippage if value > 0 else -context.slippage
    order_price = price if price is not None else cur_data.last_price * (1 + slippage)
    # order_price = price if price is not None else cur_data.last_price

    amount = int(value / order_price)

    return order_amount(security, amount, price, callback)


def order_target(security, amount, price=None, callback=None):
    """
    目标股数下单:使最终标的的数量达到指定的amount，
    注意使用此接口下单时若指定的标的有未完成的订单，则先前未完成的订单将会被取消
        参数
        :param security: 股票代码
        :param amount: 期望的标的最终持有的股票数量
        :param price: 下单价格，市价单可不填价格，按当前最新价格挂单
        :param callback: 回调函数，订单成交/取消后调用执行， callback(status)
    """
    if amount < 0:
        log.warning("下单失败：目标数量不能小于0！")
        return None

    pre_hold = 0  # 之前建仓的股票数量
    if security in context.portfolio.positions.keys():
        pst: Position = context.portfolio.positions[security]
        order: Order
        for order in context.order_list.values():
            if order.security == security and order.status == ORDER_OPEN:
                order.cancel()
        if pst.today_amount > amount:
            log.warning("今日建仓的股票数量大于目标数量！,目标数量修改为今日建仓数量！")
            amount = pst.today_amount
        pre_hold = pst.total_amount

    return order_amount(security, amount - pre_hold, price, callback)


def order_target_value(security, value, price=None, callback=None):
    """
    按股票目标价值下单，调整标的仓位到value价值，
    注意使用此接口下单时若指定的标的有未完成的订单，则先前未完成的订单将会被取消
    参数
        :param security: 股票代码
        :param value: 期望的标的最终价值，value = 最新价 * 手数  * 乘数（股票为100）
        :param price: 下单价格，市价单可不填价格，按当前最新价格挂单
        :param callback: 回调函数，订单成交/取消后调用执行， callback(status)

    返回
        :return: Order对象或者None, 如果创建委托成功, 则返回Order对象, 失败则返回None
    示例
        #卖出平安银行所有股票
        order_target_value('000001', 0)
        #调整平安银行股票仓位到10000元价值
        order_target_value('000001', 10000)
    """

    order_price = get_current_data(security).last_price
    amount = int(value / order_price)
    return order_target(security, amount, price, callback)


def order_cancel(order_id):
    if order_id in context.order_list.keys():
        order_obj: Order = context.order_list[order_id]
        return order_obj.cancel()
    else:
        return False


def order_broker_day(order_id):
    """
    如果回测运行频率为 'day',则立即进行订单撮合
    :param order_id:
    :return: None
    """
    order = context.order_list[order_id]
    code = order.security

    data: pd.DataFrame = get_current_data(code).min_data_after
    if data is not None and len(data) > 1:
        for i in range(0, len(data)):
            if order.is_buy:
                if data.iloc[i].low <= order.order_price:
                    order.deal(data.index[i])
                    break
            elif data.iloc[i].high >= order.order_price:
                order.deal(data.index[i])
                break
    return


def order_broker():
    """
    分钟撮合函数，根据回测频率运行
    :return:
    """
    for order in context.order_list.values():
        if order.add_time[0:10] != context.current_dt[0:10]:  # 防止框架恢复运行导入其他日期的context
            context.order_list.remove(order)
        if order.status == ORDER_OPEN and order.add_time < context.current_dt:  # 防止下单后马上撮合
            code = order.security
            data = get_current_data(code)
            if order.is_buy:
                if data.last_low < order.order_price:
                    order.deal()
                    log.info("订单成交：订单编号{}，股票代码{},成交数量{}，成交时间{}"
                             .format(order.id, code, order.trade_amount, context.current_dt[11:]))
                    break
            elif data.last_high > order.order_price:
                order.deal()
                log.info("订单成交：订单编号{}，股票代码{},成交数量{}，成交时间{}"
                         .format(order.id, code, order.trade_amount, context.current_dt[11:]))
                break
