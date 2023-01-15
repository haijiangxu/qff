

from qff import *

strategy_name = "样例策略文件"


def initialize():
    log.info("{} : 初始化运行".format(strategy_name))

    # 设置指数基准
    set_benchmark(security="000300")
    # 设置定时运行的策略函数
    run_daily(handle_trade, run_time="09:50")


def before_trading_start():
    log.info("before_trading_start函数运行...")
    pass


def handle_trade():
    log.info("handle_trade函数运行...")
    pass


def after_trading_end():
    log.info("after_trading_end函数运行...")
    pass


if __name__ == '__main__':
    run_file(__file__, start="2021-08-27", end="2022-03-25")
