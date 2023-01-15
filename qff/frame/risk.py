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

# 风险指标计算模块
# TODO: 使用empyrical、pyfolio计算风险指标和生成图形文件

import os
import platform
import math
import numpy as np
import pandas as pd
from functools import lru_cache
from pyecharts import options as opts
from pyecharts.charts import Line, Grid
from pyecharts.commons.utils import JsCode
from qff.tools.local import temp_path
from qff.frame.context import context


class Risk:

    def __init__(self, asset: pd.DataFrame = None):
        """
        :param asset: 资产日数据：包括：       "date":        # 日期
                                            "acc_value":   # 当日账户总资产
                                            "bm_value":    # 基准对应的总资产
                                            "pos_value":   # 当日持仓总价值
        """
        self._asset = asset if asset is not None else context.df_asset

        # 每日收益率
        self._asset["acc_return"] = round(self._asset["acc_value"] / self._asset["acc_value"].iloc[0] - 1, 4)
        # 每日基准收益率
        self._asset["bm_return"] = round(self._asset["bm_value"] / self._asset["bm_value"].iloc[0] - 1, 4)
        # 每日超额收益率
        self._asset["ei_return"] = round((self._asset["acc_value"] + 1) / (self._asset["bm_value"] + 1) - 1, 4)
        # 每日资产涨跌幅pct
        self._asset["acc_pct"] = self._asset["acc_value"].pct_change().fillna(1)
        self._asset["bm_pct"] = self._asset["bm_value"].pct_change().fillna(1)
        # 每日可用资金
        self._asset["cash_value"] = self._asset["acc_value"] - self._asset["pos_value"]

        # self.time_gap = get_trade_gap(context.start_date, context.end_date)  # 策略执行天数
        self.time_gap = len(self._asset) - 1
        self.rf = 0.04  # 无风险利率（默认0.04）

    @property
    def assets(self):
        return self._asset["acc_value"]

    @property
    def profit_pct(self):
        """ 利润  """
        return self._asset["acc_pct"]

    @property
    def total_returns(self):
        """ 策略总收益 """
        return self._asset["acc_return"].iloc[-1]

    @property
    def benchmark_return(self):
        """ 基准收益 """
        return self._asset["bm_return"].iloc[-1]

    @property
    def ei_return(self):
        """ 超额收益 = （策略收益+100%）/（基准收益+100%） -100% """
        return self._asset["ei_return"].iloc[-1]

    @property
    def aei_return(self):
        """
        日均超额收益
        """
        return round((self._asset["ei_return"] - self._asset["ei_return"].shift(1))
                     .sum() / self.time_gap, 4)

    @property
    def total_annualized_returns(self):
        """ 年化收益率 """
        return round((1 + self.total_returns) ** (250 / self.time_gap) - 1, 4)

    @property
    def benchmark_annualized_returns(self):
        """ 基准年化收益率 """
        return round((1 + self.benchmark_return) ** (250 / self.time_gap) - 1, 4)

    @property
    def max_dropback(self):
        """最大回撤
        """
        return round(
            float(
                max(
                    [
                        (self.assets.iloc[idx] - self.assets.iloc[idx::].min())
                        / self.assets.iloc[idx]
                        if self.assets.iloc[idx] != 0 else 0
                        for idx in range(len(self.assets))
                    ]
                )
            ),
            4
        )

    @property
    def max_ei_dropback(self):
        """
        超额收益最大回撤 ： 描述策略可能出现的跑输基准的最糟糕情况。
        """
        return round(
            float(
                max(
                    [
                        (self._asset["ei_return"].iloc[idx] - self._asset["ei_return"].iloc[idx::].min())
                        / self._asset["ei_return"].iloc[idx]
                        if self._asset["ei_return"].iloc[idx] != 0 else 0
                        for idx in range(len(self._asset["ei_return"]))
                    ]
                )
            ),
            4
        )

    @property
    def volatility(self):
        """ 波动率 """
        return round(float(self.profit_pct.std() * math.sqrt(250)), 2)

    @property
    def beta(self):
        assest_profit = self._asset["acc_pct"].values
        benchmark_profit = self._asset["bm_pct"].values
        calc_cov = np.cov(assest_profit, benchmark_profit)
        beta = round(calc_cov[0, 1] / np.var(benchmark_profit), 2)
        return beta

    @property
    def alpha(self):
        alpha = self.total_annualized_returns - (self.rf + self.beta *
                                                 (self.benchmark_annualized_returns - self.rf))
        return round(alpha, 2)

    @property
    def ir(self):
        sigma = (self._asset["acc_return"] - self._asset["bm_return"]).std()
        return round((self.total_annualized_returns - self.benchmark_annualized_returns) / sigma, 2)

    @property
    def sharpe(self):
        """ 夏普比率 """
        if self.volatility == 0:
            return 0
        return round((self.total_annualized_returns - self.rf) / self.volatility, 2)

    def calc_sortino(self, annualized_returns, volatility_year, rfr=0.00):
        """
         计算索提诺比率
        """
        if volatility_year == 0:
            return 0

        # Define risk free rate and target return of 0
        target = 0

        # Calculate the daily returns from price data
        df = pd.DataFrame(
            columns=['Returns',
                     'downside_returns'],
            index=self.assets.index
        )
        df['Returns'] = (self.assets.values / self.assets.shift(1).values) - 1
        df['downside_returns'] = 0

        # Select the negative returns only
        df.loc[df['Returns'] < target, 'downside_returns'] = df['Returns']**2
        expected_return = df['Returns'].mean()

        # Calculate expected return and std dev of downside returns
        down_stdev = np.sqrt(df['downside_returns'].mean())

        # Calculate the sortino ratio
        if down_stdev == 0:
            sortino_ratio = 0
        else:
            sortino_ratio = (expected_return - rfr) / down_stdev

        # 这里不知道计算年化率如何
        return sortino_ratio

    @property
    def sortino(self):
        """
        索提诺比率 投资组合收益和下行风险比值


        """
        return round(
            float(
                self.calc_sortino(self.total_annualized_returns,
                                  self.volatility,
                                  0.05)
            ),
            2
        )

    @property
    def daily_win_ratio(self):
        """
        日胜率：策略盈利超过基准盈利的天数在总交易数中的占比。
        """

        return len(self._asset[self._asset["acc_pct"] > self._asset["bm_pct"]]) / self.time_gap

    @property
    def max_holdmarketvalue(self):
        """最大持仓市值

        Returns:
            [type] -- [description]
        """
        return round(self._asset["pos_value"].max(), 2)

    @property
    def min_holdmarketvalue(self):
        """最小持仓市值

        Returns:
            [type] -- [description]
        """
        return round(self._asset["pos_value"].min(), 2)

    @property
    def average_holdmarketvalue(self):
        """平均持仓市值

        Returns:
            [type] -- [description]
        """
        return round(self._asset["pos_value"].mean(), 2)

    @property
    def max_cashhold(self):
        """最大闲置资金
        """

        return round(self._asset["cash_value"].max(), 2)

    @property
    def min_cashhold(self):
        """最小闲置资金
        """

        return round(self._asset["cash_value"].min(), 2)

    @property
    def average_cashhold(self):
        """平均闲置资金

        Returns:
            [type] -- [description]
        """

        return round(self._asset["cash_value"].mean(), 2)

    @property
    @lru_cache()
    def message(self):
        return {
            '策略执行天数': self.time_gap,
            '策略总收益': '{:.2%}'.format(self.total_returns),
            '基准总收益': '{:.2%}'.format(self.benchmark_return),
            '超额收益': '{:.2%}'.format(self.ei_return),
            '日均超额收益': '{:.2%}'.format(self.aei_return),
            '策略年化收益': '{:.2%}'.format(self.total_annualized_returns),
            '基准年化收益': '{:.2%}'.format(self.benchmark_annualized_returns),
            '策略最大回撤': '{:.2%}'.format(self.max_dropback),
            '超额收益最大回撤': self.max_ei_dropback,
            '策略收益波动率': self.volatility,
            'beta': self.beta,
            'alpha': self.alpha,
            'sharpe': self.sharpe,
            # 'sortino': self.sortino,
            'ir': self.ir,
            '日胜率': '{:.2%}'.format(self.daily_win_ratio),
            '最大持仓市值': self.max_holdmarketvalue,
            '最小持仓市值': self.min_holdmarketvalue,
            '平均持仓市值': self.average_holdmarketvalue,
            '最大闲置资金': self.max_cashhold,
            '最小闲置资金': self.min_cashhold,
            '平均闲置资金': self.average_cashhold,
        }

    def save(self, filename='risk.xlsx'):
        msg = self.message
        df_risk = pd.Series(data=msg)
        df_risk.to_excel(filename)

    def show_chart(self, filename=None):

        if filename is None:
            filename = '{}{}{}.html'.format(temp_path, os.sep, 'profit_chart')
        kx = self._asset["date"].tolist()
        ky_acc = (self._asset["acc_return"]*100).tolist()
        ky_bm = (self._asset["bm_return"]*100).tolist()
        kline_line = (
            Line()
            .add_xaxis(xaxis_data=kx)
            .add_yaxis(
                series_name="策略收益率",
                y_axis=ky_acc,
                is_smooth=True,
                is_symbol_show=False,
                color='red',
                linestyle_opts=opts.LineStyleOpts(opacity=1, width=3),  # color='rgb(0, 65, 153)',
                label_opts=opts.LabelOpts(is_show=False),
                # label_opts=opts.LabelOpts(is_show=True,
                #                           formatter=JsCode("function (params) {return params.value[1] + '%'}")),
                areastyle_opts=opts.AreaStyleOpts(opacity=0.6, color='rgb(229, 240, 255)'),

            )
            .add_yaxis(
                series_name="基准收益率",
                y_axis=ky_bm,
                is_smooth=True,
                is_symbol_show=False,
                color='rgb(0, 65, 153)',
                # color='blue',
                linestyle_opts=opts.LineStyleOpts(opacity=1, width=3),  # color='rgb(255, 0, 0)',
                label_opts=opts.LabelOpts(is_show=False),
            )
            # .add_yaxis(
            #     series_name="超额收益率",
            #     y_axis=ky_ie,
            #     is_smooth=True,
            #     is_symbol_show=False,
            #     linestyle_opts=opts.LineStyleOpts(opacity=1),
            #     label_opts=opts.LabelOpts(is_show=False, formatter="{c}%"),
            # )
            .set_global_opts(
                title_opts=opts.TitleOpts(title="{} 到 {}, ￥{},{}".
                                          format(kx[0], kx[-1],
                                                 context.portfolio.starting_cash,
                                                 ' 天' if context.run_freq == 'day' else ' 分钟'),
                                          pos_right="5%"),
                legend_opts=opts.LegendOpts(pos_left='5%', legend_icon='rect', item_width=14,
                                            textstyle_opts=opts.TextStyleOpts(font_weight='bold', font_size=16),

                                            ),
                xaxis_opts=opts.AxisOpts(
                    type_="category",
                    is_scale=True,
                    boundary_gap=False,
                    axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                    splitline_opts=opts.SplitLineOpts(is_show=True),
                    split_number=20,
                    min_="dataMin",
                    max_="dataMax",
                ),
                yaxis_opts=opts.AxisOpts(
                    name='累计收益',
                    name_location='middle',
                    name_rotate=270,
                    name_gap=40,
                    is_scale=True,
                    splitline_opts=opts.SplitLineOpts(
                        is_show=True,
                        linestyle_opts=opts.LineStyleOpts(opacity=0.5, type_='dashed')
                    ),
                    axislabel_opts=opts.LabelOpts(formatter="{value}%", position='inside'),
                    position="right",
                    name_textstyle_opts=opts.TextStyleOpts(font_weight='bold', font_size=16),
                    # axistick_opts=opts.AxisTickOpts(is_inside=True)
                ),
                tooltip_opts=opts.TooltipOpts(
                    trigger="axis",
                    axis_pointer_type="line",
                    border_width=1,
                    border_color='rgb(51, 153, 255)',
                    background_color='rgb(255, 255, 255)',
                    textstyle_opts=opts.TextStyleOpts(color='rgb(0, 0, 0)'),

                    formatter=JsCode(
                        """
                        function(params){
                            return params[0].name + '<br/>' + 
                            ' <div style="width:10px;height:10px;border-radius:50%;
                            background-color:blue;display:inline-block;"></div>'+
                            '  ' +params[0].seriesName + '  ' +'<b>'+ params[0].value[1].toFixed(2)+'%'+'</b>'+'<br/>' + 
                            '<div style="width:10px;height:10px;border-radius:50%;
                            background-color:red;display:inline-block;"></div>'+
                            '  ' +params[1].seriesName + '  ' +'<b>'+ params[1].value[1].toFixed(2)+'%'+'</b>'

                        }"""
                    ),
                ),
                datazoom_opts=opts.DataZoomOpts(
                    is_show=True,
                    pos_top='95%',
                    range_start=0,
                    range_end=100,
                ),

            )
        )

        grid_chart = Grid(init_opts=opts.InitOpts(width="1200px", height="600px"))
        grid_chart.add(
            kline_line,
            grid_opts=opts.GridOpts(pos_left="5%", pos_right="5%"),
        )
        grid_chart.render(filename)
        if platform.system() == 'Windows':
            os.startfile(filename)
        else:
            print(f"生成收益曲线文件：{filename}")

        return grid_chart
