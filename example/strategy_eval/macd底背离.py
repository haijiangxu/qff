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

import pandas as pd
import numpy as np
import talib as tl
from typing import List, Optional

strategy_name = "MACD_底背离"
strategy_desc = """ MACD底背离一般出现在股价的低位区。当股价K线图上的股票走势，股价还在下跌，而MACD指标图形上的由绿柱构
成的图形的走势是一底比一底高。即当股价的低点比前一次低点底，而指标的低点却比前一次的低点高，这叫底背离现象。底背离现象一般是预
示股价在低位可能反转向上的信号，表明股价短期内可能反弹向上，是短期拿入股票的信号。底背离的次数越多，反转上涨的可能性就越大，此
时，不必盲目割肉，当市场出现了明显的放量上涨信号的时候，可以反手做多。本策略通过在MACD金叉位置比较白线DIF和股价进行底背离判断"""


def get_buy_signal(code: Optional[str], df: pd.DataFrame) -> Optional[List[str]]:
    """
    用于策略评估的回调函数，返回K线数据中所有发生顶背离的买点信号

    :param code:
    :param df:
    :return:
    """
    ret = []
    close = df['close'].values
    _dif, _dea, _macd = np.around(tl.MACD(close), 4)
    idx_gold = np.where((_macd[:-1] < 0) & (_macd[1:] > 0))[0] + 1
    for i in range(1, len(idx_gold)):
        idx, pre = idx_gold[i], idx_gold[i-1]
        if close[idx] < close[pre] and _dif[idx] > _dif[pre]:
            ret.append(df.index[idx])
    return ret


if __name__ == '__main__':
    from qff.frame.evaluation import strategy_eval
    strategy_eval(get_buy_signal, strategy_name, strategy_desc, csv='pnl.csv')
