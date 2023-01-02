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

__version__ = "0.4.12"

import sys

if sys.version_info < (3, 7):
    print(f'qff {__version__} require Python 3.7+ and 64 bit OS')
    sys.exit(1)
del sys

from qff.tools.logs import log
from qff.tools.date import (
    get_pre_trade_day,
    get_next_trade_day,
    get_trade_gap,
    get_real_trade_date,
    get_trade_days,
    get_date_gap,
    is_trade_day,
    util_time_stamp,
    util_date_valid,
    run_time
)

from qff.tools.utils import (
    util_gen_id,
    util_code_tolist,
    util_code_tostr,
    util_to_json_from_pandas
)

from qff.tools.config import (
    get_config,
    set_config
)
from qff.tools.mongo import DATABASE

from qff.price.query import (
    get_price,
    history,
    attribute_history,
    get_stock_name,
    get_stock_list,
    get_st_stock,
    get_paused_stock,
    get_stock_block,
    get_block_stock,
    get_index_stocks,
    get_index_name,
    get_mtss,
    get_all_securities,
    get_security_info
)

from qff.price.report import (
    get_financial_data,
    get_valuation,
    query_valuation,
    get_history_fundamentals,
    get_fundamentals,
    get_stock_reports,
    get_fundamentals_continuously
)

from qff.price.fetch import (
    fetch_price,
    fetch_today_min_curve,
    fetch_current_ticks,
    fetch_stock_info,
    fetch_today_transaction,
    fetch_stock_list,
    fetch_ticks,
    fetch_stock_block,
    fetch_stock_xdxr
)
from qff.frame.context import (
    context,
    strategy,
    g,
    Context,
    Portfolio,
    Position,
    RUNTYPE,
    RUNSTATUS,
    Strategy
)

from qff.frame.order import (
    order_amount,
    order_value,
    order_target,
    order_target_value,
    order_cancel
)

from qff.frame.interface import (
    set_run_freq,
    set_backtest_period,
    set_init_cash,
    set_benchmark,
    set_slippage,
    set_order_cost,
    set_universe,
    del_universe,
    run_daily,
    pass_today,
    set_strategy_name,
    load_strategy_file
)

from qff.helper.formula import (
    ABS,
    AVEDEV,
    BBI,
    BBIBOLL,
    BARLAST,
    BARLAST_EXIST,
    COUNT,
    CROSS,
    CROSS_STATUS,
    DIFF,
    EMA,
    EVERY,
    EXIST,
    FILTER,
    HHV,
    IF,
    IFOR,
    IFAND,
    LLV,
    LAST,
    MIN,
    MA,
    MAX,
    MACD,
    REF,
    RENKO,
    RENKOP,
    SMA,
    SUM,
    STD,
    SINGLE_CROSS,
    XARROUND,
)

from qff.helper.indicator import ind_ma, ind_macd, ind_atr, ind_kdj, ind_rsi, ind_boll
from qff.helper.common import filter_st_stock, filter_paused_stock, filter_20pct_stock, select_zt_stock
from qff.price.cache import get_current_data, CacheData
from qff.frame.risk import Risk
from qff.frame.performance import Performance
from qff.frame.backtest import back_test_run
from qff.frame.simtrade import sim_trade_run
from qff.frame.evaluation import strategy_eval
