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
策略评价框架：

        鉴于我们要考察的是策略的选股效果，通过计算信号频率、交易胜率、盈亏比三个指标，再通过凯利公式计算最佳投资比例
    =(胜率*盈亏比-(1-胜率))/盈亏比。并从全市场、行业、市场环境、股票流通盘大小四个维度对上述    评价指标进行比较。
    最后我们选取凯利值高，信号频率高，胜率分布呈左偏特征，行业及不同市场环境下效果较为稳定的策略。纳入高阶策略基础池，
    然后再进一步优化寻找高阶形态组合。注：凯利值为每次建仓的比例，不是总资金的比例，而是可接受最大损失的单次投资比例。
        具体而言，根据提供的策略择时函数，遍历找出所有股票评价周期内的买点信号，考虑 A 股不能T+0 的交易机制，我们设
    定持仓期天数为1、3、5、10、20 个交易日，以持仓结束日期的收盘价作为卖点信号，从而考察策略信号在不同持仓周期下的收
    益表现。通过从信号频率、交易胜率、盈亏比三个角度评价策略的选股表现。然后再进一步评判其在不同市场环境中的适用性，这
    里的市场环境划分可以借助道氏理论或者缠论体系，将回测区间划分成上涨区间、下跌区间以及震荡区间。最后再判断其对于不同
    股本股票的适应性进行分析。

    为了方便对比策略的胜率、盈亏比分布，我们引入分布的均值、峰度和偏度三个指标。
    观察目前已测试的单形态结果，胜率分布特征可以归纳为两类：一种是呈现类正态分布的钟型结构，这也是大部分形态表现出的特征。
    具体到不同的单一形态，会呈现出不同程度的左偏/右偏。 另外一种则呈现两极分布结构，即胜率在中间组的个股数较少，胜率极高
    组及胜率极低组个股数较多。
    在评价具体的形态时，我们期望形态的胜率分布尽可能地符合左偏钟型结构，这样既保证了形态在个股表现上的高胜率，又保证了对
    不同个股适用性的稳定性要求。
  参见《光大证券-技术形态选股系列报告之一：开宗明义论形态》

"""
import os
import sys
import pandas as pd
from typing import List, Callable
import inspect
import matplotlib.pyplot as plt
from qff.tools.logs import log
from qff.tools.word import WordWriter
from qff.price.query import get_stock_list, get_price
from qff.price.finance import get_valuation
from qff.tools.date import get_trade_days, get_trade_gap
from qff.tools.local import temp_path, evaluation_path

market = [['震荡', '2002-01-01', '2005-12-31'],
          ['上涨', '2006-01-01', '2007-10-16'],
          ['下跌', '2007-10-17', '2008-10-29'],
          ['上涨', '2008-10-30', '2009-08-04'],
          ['震荡', '2009-08-05', '2014-07-22'],
          ['上涨', '2014-07-23', '2015-06-12'],
          ['下跌', '2015-06-13', '2015-08-26'],
          ['上涨', '2015-08-27', '2015-12-31'],
          ['下跌', '2016-01-01', '2016-02-01'],
          ['震荡', '2016-02-02', '2018-01-26'],
          ['下跌', '2018-01-27', '2019-01-02'],
          ['上涨', '2019-01-03', '2019-04-22'],
          ['下跌', '2019-04-23', '2019-08-09'],
          ['震荡', '2019-08-12', '2020-03-27'],
          ['上涨', '2020-03-30', '2021-02-19'],
          ['震荡', '2021-02-20', '2022-01-28'],
          ['下跌', '2021-01-29', '2022-06-05']]


class Evaluation:
    def __init__(self, pnl, code=None, start=None, end=None, name=None):
        self.pnl: pd.DataFrame = pnl
        self.code = code if code else self.pnl['code'].unique().tolist()
        self.start = start if start else self.pnl['buy_date'].min()
        self.end = end if end else self.pnl['sell_date'].max()
        self.period = get_trade_gap(self.start, self.end)
        self._stock_wr_data = None  # Series结构，索引为股票代码，列为胜率
        self._stock_glr_data = None  # Series结构，索引为股票代码，列为盈亏比
        self._name = name

    @property
    def total_eval(self):
        """
        汇总评估分析
        """
        return _eval_out(self.pnl, self.period)

    @property
    def stock_wr_data(self):
        """
        按个股分布生成胜率Dataframe数据
        """
        if self._stock_wr_data is None:
            self._stock_wr_data = self.pnl.groupby('code').pnl_money.apply(_calc_win_rate)
        return self._stock_wr_data

    @property
    def stock_glr_data(self):
        """
        按个股分布生成盈亏比Dataframe数据
        """
        if self._stock_glr_data is None:
            self._stock_glr_data = self.pnl.groupby('code').pnl_money.apply(_calc_gain_loss_rate)
        return self._stock_glr_data

    def show_plot(self, filename=None):
        plt.figure(figsize=(6, 2.6))
        plt.subplot(1, 2, 1)
        self.stock_wr_data.hist(grid=False, width=0.08, alpha=0.7)
        plt.xlim(0, 1.0)
        plt.title('胜率分布图')

        plt.subplot(1, 2, 2)
        self.stock_glr_data.hist(grid=False, width=0.5, alpha=0.7)
        plt.title('盈亏比分布图')
        plt.xlim(0, 5)
        plt.suptitle(self._name)
        if filename:
            plt.savefig(filename)
        else:
            plt.show()

    @property
    def eval_by_stocks(self):
        """
        根据个股分布进行评估分析
        """
        return {
               '胜率均值': round(self.stock_wr_data.mean(), 2),
               '胜率峰度': round(self.stock_wr_data.kurt(), 2),
               '胜率偏度': round(self.stock_wr_data.skew(), 2),
               '盈亏比均值': round(self.stock_glr_data.mean(), 2),
               '盈亏比峰度': round(self.stock_glr_data.kurt(), 2),
               '盈亏比偏度': round(self.stock_glr_data.skew(), 2),
        }

    @property
    def eval_by_market(self):
        """
        根据市场环境进行评估分析
        """
        ret = []
        mdf = pd.DataFrame(market, columns=['state', 'start', 'end'])
        for state in ['上涨', '震荡', '下跌']:
            msg = {'持仓周期': self._name}
            msg.update({'市场环境': state})
            td = pd.Series(dtype=str)

            mk = mdf[mdf['state'] == state]
            for _, row in mk.iterrows():
                td = pd.concat([td, pd.Series(get_trade_days(row.start, row.end))])
            td = td[(td.values > self.start) & (td.values < self.end)]

            period = len(td)
            df = self.pnl[self.pnl['buy_date'].isin(td)]
            msg.update(_eval_out(df, period))
            ret.append(msg)

        return pd.DataFrame(data=ret, index=pd.Index(['上涨', '震荡', '下跌']))

    @property
    def eval_by_capital(self):
        """
        根据股票流通盘大小进行评价分析
        根据流通盘大小分为超级大盘100E以上， 大盘股40-100E，中盘股10-40E，小盘股小于10E
        """
        ret = []
        a = get_valuation(self.code, end=self.end, fields=['circulating_cap']).set_index('code')['circulating_cap']
        code_caps = {
            '超大盘': a[a >= 100e+3].index.tolist(),
            '大盘': a[(a >= 40e+3) & (a < 100e+3)].index.to_list(),
            '中盘': a[(a >= 10e+3) & (a < 40e+3)].index.to_list(),
            '小盘': a[(a < 10e+3)].index.to_list()
        }
        for k, v in code_caps.items():
            msg = {'持仓周期': self._name}
            msg.update({'流通盘': k})
            df = self.pnl[self.pnl['code'].isin(v)]
            msg.update(_eval_out(df, self.period))
            ret.append(msg)

        return pd.DataFrame(data=ret, index=pd.Index(code_caps.keys()))

    @property
    def eval_by_year(self):
        """
        根据交易日期所在年份进行评估分析
        """

        ret = []
        start = int(self.start[:4])
        end = int(self.end[:4])

        td = _group_date_by_year(self.start, self.end)

        for k, v in td.items():
            msg = {'持仓周期': self._name}
            msg.update({'年度': k})
            df = self.pnl[self.pnl['buy_date'].isin(v)]
            msg.update(_eval_out(df, len(v)))
            ret.append(msg)
        return pd.DataFrame(data=ret, index=pd.Index(td.keys()))


class Evaluations:
    def __init__(self, pnls: pd.DataFrame, code=None, start=None, end=None):
        self.pnls = pnls
        self.code = code if code else self.pnls['code'].unique().tolist()
        self.start = start if start else self.pnls['buy_date'].min()
        self.end = end if end else self.pnls['sell_date'].max()
        self.period = get_trade_gap(self.start, self.end)
        self.hold_gap = pnls['hold_gap'].unique()
        self.evals = {}
        for gap in self.hold_gap:
            self.evals.update({
                f"eval_{gap}": Evaluation(pnls.query(f'hold_gap=={gap}'), code, start, end,
                                          f'eval_{gap}')
            })
        self._eval_by_total = None
        self._eval_by_stocks = None
        self._eval_by_market = None
        self._eval_by_capital = None
        self._eval_by_year = None

    def __getitem__(self, item):
        if item in self.evals.keys():
            return self.evals[item]
        else:
            return None

    @property
    def total_eval(self):
        """
        汇总评估分析
        """
        if self._eval_by_total is None:
            self._eval_by_total = pd.DataFrame(data=[x.total_eval for x in self.evals.values()],
                                               index=pd.Index(self.hold_gap))
        return self._eval_by_total

    def show_total_eval(self, filename=None):
        return _plot_eval_data(self.total_eval, '策略总体收益表现', filename)

    @property
    def eval_by_stocks(self):
        """
        根据个股分布进行评估分析
        """
        if self._eval_by_stocks is None:
            self._eval_by_stocks = pd.DataFrame(data=[x.eval_by_stocks for x in self.evals.values()],
                                                index=pd.Index(self.hold_gap, name='持仓周期'))
        return self._eval_by_stocks

    @property
    def eval_by_market(self):
        """
        根据市场环境进行评估分析
        """
        if self._eval_by_market is None:
            self._eval_by_market = pd.concat([x.eval_by_market for x in self.evals.values()])
        return self._eval_by_market

    @property
    def eval_by_capital(self):
        """
        根据股票流通盘大小进行评价分析
        根据流通盘大小分为超级大盘100E以上， 大盘股40-100E，中盘股10-40E，小盘股小于10E
        """
        if self._eval_by_capital is None:
            self._eval_by_capital = pd.concat([x.eval_by_capital for x in self.evals.values()])
        return self._eval_by_capital

    @property
    def eval_by_year(self):
        """
        根据交易日期所在年份进行评估分析
        """
        if self._eval_by_year is None:
            self._eval_by_year = pd.concat([x.eval_by_year for x in self.evals.values()])
        return self._eval_by_year


def _eval_out(df : pd.DataFrame, period):
    p = _calc_win_rate(df.pnl_money)
    b = _calc_gain_loss_rate(df.pnl_money)
    kelly = round((p*b-(1-p))/b, 4)
    return {
        '信号频率': round(len(df) / period, 2),
        '胜率': p,
        '盈亏比': b,
        'kelly': kelly
    }


def _calc_win_rate(pct: pd.Series):
    # 计算胜率
    return round(len(pct[pct > 0]) / len(pct), 2)


def _calc_gain_loss_rate(pct: pd.Series):
    # 计算盈亏比
    gain_mean = pct[pct > 0].mean()  # 获胜平均收益率
    lose_mean = abs(pct[pct <= 0].mean())  # 失败平均收益率
    gain_loss_rate = min(round(gain_mean / lose_mean + 0.00001, 2), 10)
    return gain_loss_rate


def _group_date_by_year(start, end):
    trade_days = get_trade_days(start, end)
    date_group = {}
    date_in_year = []
    year_key = int(trade_days[0][:4])
    for i in range(len(trade_days)):
        year = int(trade_days[i][:4])
        if year == year_key:
            date_in_year.append(trade_days[i])
            if i == len(trade_days) - 1:
                date_group.update({year_key: date_in_year})
        else:
            date_group.update({year_key: date_in_year})
            year_key = year
            date_in_year = [trade_days[i]]
    return date_group


def _plot_eval_data(data: pd.DataFrame, title: str = None, filename=None):
    data = data[['胜率', '盈亏比']]
    data.plot(x=None, kind='bar', figsize=(6, 2.8), title=title, rot=0, fontsize=9)
    # plt.title(title)
    # plt.xticks(rotation=0, size=9)
    if filename:
        plt.savefig(filename)
    else:
        plt.show()
    return

def _strategy_run(get_signal_fun: Callable, hold_gaps, start, end, stock_list) -> pd.DataFrame:
    """
    策略运行函数，执行get_signal_fun，根据返回值生成pnl数据
    :param get_signal_fun: 择时函数,获取买点信号，输入参数为（code,kline数据), 返回值List[date_str]
    :param hold_gaps : 持仓周期，评估策略在不同持仓周期下的表现，默认[1, 3, 5, 10, 20]
    :param start: 评价测试开始日期
    :param end: 评价测试结束日期
    :param stock_list: 评价测试使用的股票集合，为None表示当前所有上市股票
    :return: pd.DataFrame，columns=['code', 'sell_date', 'buy_date', 'sell_price', 'buy_price',
            'hold_gap', 'pnl_ratio', 'pnl_money']
    """
    pair_table = []
    # fetch_start = get_pre_trade_day(start, 250)[:10]  # 为了取年线数据
    for i in range(len(stock_list)):
        code = stock_list[i]
        log.info("正在执行策略函数{}/{}，当前股票代码：{}".format(i, len(stock_list), code))
        kline: pd.DataFrame = get_price(code, start, end)
        signal_list = get_signal_fun(code, kline)
        if signal_list and isinstance(signal_list, list):
            for buy_date in signal_list:
                if buy_date < start or buy_date > end:
                    continue
                buy_price = kline.loc[buy_date, 'close']
                buy_loc = kline.index.get_loc(buy_date)
                for gap in hold_gaps:
                    # sell_date = get_next_trade_day(buy_date, gap)  # 此方法遇见停牌日期报异常
                    # if sell_date > kline.index[-1]:
                    #     continue
                    sell_loc = buy_loc + gap
                    if sell_loc >= len(kline):
                        continue
                    sell_date = kline.index[sell_loc]
                    sell_price = kline.loc[sell_date, 'close']
                    pair_table.append(
                        [
                            code,
                            sell_date,
                            buy_date,
                            sell_price,
                            buy_price,
                            gap
                        ]
                    )

    pair_title = ['code', 'sell_date', 'buy_date', 'sell_price', 'buy_price', 'hold_gap']
    pnl = pd.DataFrame(pair_table, columns=pair_title)
    pnl['pnl_ratio'] = round((pnl.sell_price / pnl.buy_price) - 1, 4)
    pnl['pnl_money'] = pnl['pnl_ratio'] * 10000
    return pnl


def strategy_eval(get_signal_fun: Callable,
                  name: str = None,
                  desc: str = None,
                  hold_gaps: List[str] = None,
                  start: str = '2010-01-04',
                  end: str = '2022-05-06',
                  security: List[str] = None,
                  csv: str = None) -> None:
    """
    策略评价入口函数
    :param get_signal_fun: 择时函数,获取买点信号，输入参数为（code,kline数据), 返回值List[date_str]
    :param name: 策略名称
    :param desc: 策略描述
    :param hold_gaps : 持仓周期，评估策略在不同持仓周期下的表现，默认[1, 3, 5, 10, 20]
    :param start: 评价测试开始日期
    :param end: 评价测试结束日期
    :param security: 评价测试使用的股票集合，为None表示当前所有上市股票
    :param csv: 保存pnl的数据文件,如果存在该文件，则直接使用该文件数据，否则运行策略函数，并将运行结果保存至csv文件中。
    :return: None
    """

    csv_file = '{}{}{}'.format(temp_path, os.sep, csv) if csv else None

    if csv_file and os.path.exists(csv_file):
        log.info("读取csv文件，获取买点信号...")
        pnl = pd.read_csv(csv_file, index_col=0)
        pnl['code'] = pnl['code'].apply(lambda x: str(x).zfill(6))
        stock_list = pnl['code'].unique().tolist()
        hold_gaps = pnl['hold_gap'].unique()
    else:
        log.info("开始执行策略函数，收集买点信号...")
        stock_list = security if security else get_stock_list()
        if hold_gaps is None:
            hold_gaps = [1, 3, 5, 10, 20]
        pnl: pd.DataFrame = _strategy_run(get_signal_fun, hold_gaps, start, end, stock_list)
        if csv:
            pnl.to_csv(csv_file)

    log.info("策略执行完成，开始生成评价报告...")
    evals = Evaluations(pnl, code=stock_list, start=start, end=end)

    plt.rcParams["font.sans-serif"] = ['SimHei']
    plt.rcParams["axes.unicode_minus"] = False

    # 开始生成评价报告
    _strategy_name = name if name else os.path.basename(sys.argv[0]).split('.')[0]
    file_docx = f"{_strategy_name}策略评价报告"
    file_docx = '{}{}{}-{}.docx'.format(evaluation_path, os.sep, file_docx,
                                        str(pd.Timestamp.now().strftime('%Y-%m-%d %H-%M-%S')))
    png_file = '{}{}tmp.png'.format(temp_path, os.sep)
    reporter = WordWriter()
    reporter.add_title(f'{_strategy_name}策略评价报告')
    reporter.add_heading('一、策略内容介绍', level=1)
    reporter.add_heading(f'1、策略:{_strategy_name}', level=2)
    if desc:
        reporter.add_paragraph(desc.strip().replace("\n", ""))
    else:
        reporter.add_paragraph("策略描述略！")
    reporter.add_heading('2、代码：', level=2)
    reporter.add_paragraph(inspect.getsource(get_signal_fun))
    reporter.add_heading('3、测试参数：', level=2)
    reporter.add_paragraph("测试周期：{} - {},共{}个交易日".format(start, end, get_trade_gap(start, end)))
    reporter.add_paragraph("样本数量：共{}只股票".format(len(stock_list)))

    reporter.add_heading('二、策略表现评价', level=1)
    reporter.add_heading('1、总体收益表现', level=2)
    reporter.add_paragraph("""首先考察策略在不同持仓周期下的收益表现，即胜率越大、盈亏比越高的策略越好，并且
     还需关注信号频率，即样本股票每日产生买入信号的数量，如果信号频率太小，则资金利用率太低。最后通过凯利公式计算
     策略的凯利值，凯利值指导每次买入股票的仓位比例。
     """.replace("\n", ""))
    reporter.add_df_table(evals.total_eval.reset_index())
    evals.show_total_eval(png_file)
    reporter.add_picture(png_file)

    reporter.add_heading('2、个股分布分析', level=2)
    reporter.add_paragraph("""考察胜率和盈亏比在测试样本股票上的分布情况，我们引入分布的均值、峰度和偏度三个
    指标。 在评价具体的策略效果时，我们期望策略的胜率分布尽可能地符合左偏钟型结构，这样既保证了形态在个股表现上的
    高胜率，又保证了对不同个股适用性的稳定性要求。对于盈亏比，我们期望挑选出分布呈现均值高、偏度尽可能大的形态。
    这样保证了策略的盈亏比表现处于较高水平。
     """.replace("\n", ""))
    reporter.add_df_table(evals.eval_by_stocks.reset_index())

    for a in evals.evals.values():
        a.show_plot(png_file)
        reporter.add_picture(png_file)

    reporter.add_heading('3、不同市场环境的适应性', level=2)
    reporter.add_paragraph("""分析策略在不同市场环境中的适用性。将市场环境划分成上涨、下跌及震荡三种状态，观察
    策略在不同市场状态下的指标表现。
     """.replace("\n", ""))

    for i in range(len(hold_gaps)):
        reporter.add_heading('({})、持仓周期{}天'.format(i+1, hold_gaps[i]), level=3)
        a = evals[f'eval_{hold_gaps[i]}']
        data = a.eval_by_market
        reporter.add_df_table(data)
        _plot_eval_data(data, '不同市场环境策略表现', png_file)
        reporter.add_picture(png_file)

    reporter.add_heading('4、股票市值大小的适应性', level=2)
    reporter.add_paragraph("""分析策略对股票市值大小的适应性。根据流通盘大小分为超级大盘100E以上， 大盘股40-100E，
    中盘股10-40E，小盘股小于10E，观察策略针对不同市值股票的指标表现。
    """.replace("\n", ""))
    for i in range(len(hold_gaps)):
        reporter.add_heading('({})、持仓周期{}天'.format(i+1, hold_gaps[i]), level=3)
        a = evals[f'eval_{hold_gaps[i]}']
        data = a.eval_by_capital
        reporter.add_df_table(data)
        _plot_eval_data(data, '不同股票市值对应策略表现', png_file)
        reporter.add_picture(png_file)

    # reporter.add_df_table(evals.eval_by_capital)

    reporter.add_heading('5、股票交易年度的适应性', level=2)
    reporter.add_paragraph("""分析策略对股票在不同年度的适应性。根据回测日期划分不同的年度，观察策略在不同年度的指标表现。
    """.replace("\n", ""))
    # reporter.add_df_table(evals.eval_by_year)
    for i in range(len(hold_gaps)):
        reporter.add_heading('({})、持仓周期{}天'.format(i+1, hold_gaps[i]), level=3)
        a = evals[f'eval_{hold_gaps[i]}']
        data = a.eval_by_year
        reporter.add_df_table(data)
        _plot_eval_data(data, '不同年度对应策略表现', png_file)
        reporter.add_picture(png_file)

    reporter.save(file_docx)
    log.info("成功生成评价报告！")
