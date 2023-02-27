# 导入函数库
from qff import *


# 初始化函数，设定基准等等
def initialize():
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')

    # 设定沪深300作为基准
    set_benchmark('000300')

    # 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(open_tax=0,
                   close_tax=0.001,
                   open_commission=0.0003,
                   close_commission=0.0003,
                   min_commission=5)

    # 开盘前运行
    run_daily(before_market_open, run_time='before_open')
    # 开盘时运行
    run_daily(market_open, run_time='every_bar')
    # 收盘后运行
    run_daily(after_market_close, run_time='after_close')


# 开盘前运行函数
def before_market_open():
    # 输出运行时间
    log.info('函数运行时间(before_market_open)：' + context.current_dt)

    # 要操作的股票：平安银行（g.为全局变量）
    g.security = '000001'


# 开盘时运行函数
def market_open():
    log.info('函数运行时间(market_open):'+context.current_dt)
    security = g.security
    # 获取股票的收盘价
    close_data = attribute_history(security, count=5, unit='1d', fields=['close'])
    # 取得过去五天的平均价格
    MA5 = close_data['close'].mean()
    # 取得上一时间点价格
    current_price = close_data['close'][-1]
    # 取得当前的现金
    cash = context.portfolio.available_cash

    # 如果上一时间点价格高出五天平均价1%, 则全仓买入
    if (current_price > 1.01*MA5) and (cash > 0):
        # 记录这次买入
        log.info("价格高于均价 1%%, 买入 %s" % security)
        # 用所有 cash 买入股票
        order_value(security, cash)
    # 如果上一时间点价格低于五天平均价, 则空仓卖出
    elif current_price < MA5 and context.portfolio.positions[security].closeable_amount > 0:
        # 记录这次卖出
        log.info("价格低于均价, 卖出 %s" % security)
        # 卖出所有股票,使这只股票的最终持有量为0
        order_target(security, 0)


# 收盘后运行函数
def after_market_close():
    log.info(str('函数运行时间(after_market_close):'+context.current_dt))


if __name__ == '__main__':
    run_file(__file__, start="2022-01-01", end="2022-07-01", cash=100000, freq='day')
