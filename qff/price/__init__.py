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
    fetch_stock_block,
    fetch_stock_xdxr,
    fetch_ticks
)
