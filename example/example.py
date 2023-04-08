

from qff import *

strategy_name = "样例策略文件"


def initialize(context):
    log.info("{} : 初始化运行".format(strategy_name))

    # 设置指数基准
    set_benchmark(security="000300")


def before_trading_start(context):
    log.info("before_trading_start函数，每个交易日开盘前运行...")
    pass


def handle_data(context, data):
    log.info("handle_data函数，根据运行频率，开盘后每日/分钟/tick运行一次...")
    pass


def after_trading_end(context):
    log.info("after_trading_end函数，每个交易日收盘后运行...")
    pass


def on_strategy_end(context):
    log.info("on_strategy_end函数，策略结束后运行...")
    pass


if __name__ == '__main__':
    run_file(__file__, start="2021-08-27", end="2022-03-25", name=strategy_name)
