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
策略统计分析模块
"""

from qff.frame.perf import Perf
from qff.frame.context import context
from qff.tools.logs import log
import os
import pandas as pd
from typing import Optional

import platform
from pyecharts import options as opts
from pyecharts.charts import Line, Grid
from pyecharts.commons.utils import JsCode
from jinja2 import Environment, FileSystemLoader
import empyrical as em


def stats_risk(ctx):
    """
    对策略运行结果进行风险指标分析


    :return: 包括指标名称和指标值的字典

    """
    df = pd.DataFrame(ctx.asset_hists)
    _date = df['日期']
    price = df['账户总资产']
    bm_price = df['基准总资产']
    pos_price = df['持仓资产']

    returns = df['累计收益率']
    bm_returns = df['基准收益率']

    # 超额收益（除法版）
    ei_returns = (returns + 1) / (bm_returns + 1) - 1

    # 每日涨跌幅pct
    pct = price.pct_change().iloc[1:]
    bm_pct = bm_price.pct_change().iloc[1:]
    ei_pct = (pct + 1) / (bm_pct + 1) - 1

    # 日均超额收益
    aei = (ei_returns - ei_returns.shift(1)).sum() / (len(ei_returns) - 1)
    # 年化收益率
    annualized_returns = em.annual_return(pct)
    # 基准年化收益
    bm_annualized_returns = em.annual_return(bm_pct)
    # 策略最大回撤
    # max_dropback = em.max_drawdown(pct)
    # 超额收益最大回撤
    ei_max_dropback = em.max_drawdown(ei_pct)
    # 策略收益波动率
    volatility = em.annual_volatility(pct)
    # alpha beta  无风险利率（默认0.04）
    # alpha, beta = em.alpha_beta(pct, bm_pct, 0.04)
    beta = em.beta(pct, bm_pct, 0.04)
    # beta = round(np.cov(pct, bm_pct)[0, 1] / np.var(bm_pct), 3)
    # alpha = em.alpha(pct, bm_pct, 0.04, _beta=beta)  # 计算结果与公式不符
    alpha = annualized_returns - (0.04 + beta * (bm_annualized_returns - 0.04))
    # sharpe
    sharpe = em.sharpe_ratio(pct)
    # 超额收益夏普比率
    ei_sharp = em.sharpe_ratio(ei_pct)
    # sortino
    sortino = em.sortino_ratio(pct)
    # 卡玛比率 : 年化收益 / 最大回测
    calmar = em.calmar_ratio(pct)
    # Omega 比率
    omega = em.omega_ratio(pct, 0.04)

    # 信息比率
    sigma = (returns - bm_returns).std()
    ir = round((annualized_returns - bm_annualized_returns) / sigma, 2)
    # 日胜率：策略盈利超过基准盈利的天数在总交易数中的占比。
    daily_win_ratio = len(pct[pct > bm_pct]) / len(pct)
    # 最大回撤
    dropback = [
        (price.iloc[idx] - price.iloc[idx::].min())
        / price.iloc[idx]
        if price.iloc[idx] != 0 else 0
        for idx in range(len(price))
    ]
    max_dropback = max(dropback)
    max_index = dropback.index(max_dropback)
    min_index = price.iloc[max_index::].idxmin()
    mdb_start = _date.loc[max_index]
    mdb_end = _date.loc[min_index]

    return {
        '策略收益': '{:.2%}'.format(returns.iloc[-1]),
        '策略年化收益': '{:.2%}'.format(annualized_returns),
        '基准收益': '{:.2%}'.format(bm_returns.iloc[-1]),
        '超额收益': '{:.2%}'.format(ei_returns.iloc[-1]),
        '阿尔法': '{:.3f}'.format(alpha),
        '贝塔': '{:.3f}'.format(beta),
        '夏普率': '{:.3f}'.format(sharpe),
        '索提诺比率': '{:.3f}'.format(sortino),
        '信息比率': '{:.3f}'.format(ir),
        '卡玛比率': '{:.3f}'.format(calmar),
        'omega比率': '{:.3f}'.format(omega),
        '策略最大回撤': '{:.2%}'.format(max_dropback),
        '超额最大回撤': '{:.2%}'.format(ei_max_dropback),
        '日均超额收益': '{:.2%}'.format(aei),
        '超额夏普率': '{:.3f}'.format(ei_sharp),
        '基准年化收益': '{:.2%}'.format(bm_annualized_returns),
        '策略波动率': '{:.3f}'.format(volatility),
        '日胜率': '{:.2%}'.format(daily_win_ratio),
        '资金使用率': '{:.2%}'.format(pos_price.sum() / price.sum()),
        '最大回撤起点': mdb_start,
        '最大回撤终点': mdb_end,
    }


def stats_charts(ctx):
    """
    对策略运行结果绘制策略收益图
    :ctx: 策略运行上下文
    :mp: 最大回撤标注点[mdb_start, mdb_end]

    :return: 包括指标名称和指标值的字典

    """
    df = pd.DataFrame(ctx.asset_hists)
    _date = df['日期']
    price = df['账户总资产']
    returns = df['累计收益率']
    bm_returns = df['基准收益率']
    ei_returns = round((returns + 1) / (bm_returns + 1) - 1, 4)
    vol_rate = round(df['持仓资产'] / df['账户总资产'], 4)

    kx = _date.tolist()
    ky_acc = (returns * 100).tolist()
    ky_bm = (bm_returns * 100).tolist()
    ky_ie = (ei_returns * 100).tolist()
    ky_vol = (vol_rate * 100).tolist()

    dropback = [
        (price.iloc[idx] - price.iloc[idx::].min())
        / price.iloc[idx]
        if price.iloc[idx] != 0 else 0
        for idx in range(len(price))
    ]
    max_index = dropback.index(max(dropback))
    min_index = price.iloc[max_index::].idxmin()
    mdb_start = _date.loc[max_index]
    mdb_end = _date.loc[min_index]

    kline_line = (
        Line()
        .add_xaxis(xaxis_data=kx)
        .add_yaxis(
            series_name="策略收益",
            y_axis=ky_acc,
            is_smooth=True,
            is_symbol_show=False,
            # color='#4682B4',
            # color='#225ab2',
            color='#4572a7',
            linestyle_opts=opts.LineStyleOpts(opacity=1, width=2),  # color='rgb(0, 65, 153)', 线的宽度
            label_opts=opts.LabelOpts(is_show=False),  # 鼠标滑动时不显示数值
            areastyle_opts=opts.AreaStyleOpts(opacity=0.6, color='#dae3ed'),  # 与0轴间区域显示浅蓝色
            markpoint_opts=opts.MarkPointOpts(
                data=[
                    opts.MarkPointItem(name='最大回撤起点',
                                       coord=[mdb_start, ky_acc[kx.index(mdb_start)]],
                                       itemstyle_opts=opts.ItemStyleOpts(
                                           color='green'
                                       )
                                       ),
                    opts.MarkPointItem(name='最大回撤终点',
                                       coord=[mdb_end, ky_acc[kx.index(mdb_end)]],
                                       itemstyle_opts=opts.ItemStyleOpts(
                                           color='green'
                                       )
                                       ),
                ],
                symbol='circle',
                symbol_size=15,
            ),

        )
        .add_yaxis(
            series_name="基准收益",
            y_axis=ky_bm,
            is_smooth=True,
            is_symbol_show=False,

            # color='#8B3626',
            color='#aa4643',
            linestyle_opts=opts.LineStyleOpts(opacity=1, width=2),  # color='rgb(255, 0, 0)',
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="超额收益",
            y_axis=ky_ie,
            is_smooth=True,
            is_symbol_show=False,
            color='#ffa042',
            linestyle_opts=opts.LineStyleOpts(opacity=1, width=2),
            label_opts=opts.LabelOpts(is_show=False, formatter="{c}%"),
        )
        .set_global_opts(
            # title_opts=opts.TitleOpts(title="{} 到 {}, ￥{},{}".
            #                           format(kx[0], kx[-1],
            #                                  starting_cash,
            #                                  ' 天' if context.run_freq == 'day' else ' 分钟'),
            #                           pos_right="5%"),
            legend_opts=opts.LegendOpts(pos_left='5%', legend_icon='rect', item_width=14, border_width=0,
                                        textstyle_opts=opts.TextStyleOpts(font_weight='bold', font_size=16),
                                        selected_map={'策略收益': True, '基准收益': True, '超额收益': False},
                                        ),

            xaxis_opts=opts.AxisOpts(  # 配置x坐标轴
                type_="category",
                is_scale=True,  # 自动收缩
                # is_show=False,
                # boundary_gap=False,
                axisline_opts=opts.AxisLineOpts(is_show=False, is_on_zero=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=True),  # 分割线
                split_number=20,
                axislabel_opts=opts.LabelOpts(is_show=False),
                offset=200,
                # min_="dataMin",
                # max_="dataMax",
            ),
            yaxis_opts=opts.AxisOpts(
                name='累计收益',
                name_location='middle',
                name_rotate=270,
                name_gap=40,
                is_scale=True,
                axistick_opts=opts.AxisTickOpts(
                    is_inside=False,
                ),
                axisline_opts=opts.AxisLineOpts(
                    is_show=True,
                    symbol=None,
                ),
                splitline_opts=opts.SplitLineOpts(
                    is_show=True,
                    linestyle_opts=opts.LineStyleOpts(opacity=0.5, type_='solid')
                ),
                axislabel_opts=opts.LabelOpts(formatter="{value}%", position='inside'),
                position="right",
                name_textstyle_opts=opts.TextStyleOpts(font_weight='bold', font_size=16),
                # axistick_opts=opts.AxisTickOpts(is_inside=True)
                axispointer_opts=opts.AxisPointerOpts(  # 关闭y轴tooltip指示线
                    is_show=False,
                ),
            ),

            tooltip_opts=opts.TooltipOpts(
                is_show=True,
                trigger="axis",
                axis_pointer_type="line",
                border_width=1,
                padding=8,
                border_color='rgb(51, 153, 255)',
                background_color='rgb(255, 255, 255)',
                textstyle_opts=opts.TextStyleOpts(color='rgb(0, 0, 0)'),
                extra_css_text='box-shadow: 0 0 3px rgba(0, 0, 0, 0.3);',

                formatter=JsCode(
                    """
                    function(params){
                        var ret = params[0].name + '<br/>';
                        for (var i=0; i<params.length;i++)
                        {
                            var str_color= params[i].color;
                            if (i==params.length-1)
                            {
                               str_color = '#f9cb9c';
                            }
                            ret = ret + '<div style=\"width:10px;height:10px;border-radius:50%;
                            display:inline-block;background-color:'+ str_color + '\"></div>'+
                            '&nbsp;' +params[i].seriesName + '&nbsp;<b>'+
                            params[i].value[1].toFixed(2)+'%'+'</b>'+'<br/>';
                        }
                        return ret;
    
                    }"""
                ),
            ),
            axispointer_opts=opts.AxisPointerOpts(
                is_show=True,
                type_='shadow',
                link=[{'xAxisIndex': [0, 1]}],
            ),
            datazoom_opts=opts.DataZoomOpts(
                is_show=True,
                type_='slider',
                xaxis_index=[0, 1],  # 控制两个x轴
                pos_top='93%',
                range_start=0,
                range_end=100,
            ),
        )
    )

    vol_line = (
        Line().add_xaxis(xaxis_data=kx)
        .add_yaxis(
            series_name="仓位占比",
            y_axis=ky_vol,
            is_smooth=True,
            is_symbol_show=False,
            color='#f9cb9c',
            linestyle_opts=opts.LineStyleOpts(opacity=1, width=2, color='#f9cb9c'),  # color='rgb(255, 0, 0)',
            # linestyle_opts=opts.LineStyleOpts(opacity=1, width=1, color='#f9cb9c',),
            label_opts=opts.LabelOpts(is_show=False),  # 鼠标滑动时不显示数值
            areastyle_opts=opts.AreaStyleOpts(opacity=0.6, color='#fce5cd'),  # 与0轴间区域显示浅蓝色

        )
        .set_global_opts(
            xaxis_opts=opts.AxisOpts(  # 配置x坐标轴
                type_="category",
                is_scale=True,  # 自动收缩
                grid_index=1,
                # boundary_gap=False,
                axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                splitline_opts=opts.SplitLineOpts(is_show=True),  # 分割线
                split_number=20,
                min_="dataMin",
                max_="dataMax",
            ),
            yaxis_opts=opts.AxisOpts(
                name='仓位占比',
                name_location='middle',
                name_rotate=270,
                name_gap=40,
                is_scale=True,
                grid_index=1,
                split_number=2,
                splitline_opts=opts.SplitLineOpts(
                    is_show=True,
                    linestyle_opts=opts.LineStyleOpts(opacity=0.5, type_='dashed')
                ),
                axislabel_opts=opts.LabelOpts(formatter="{value}%", position='inside'),
                position="right",
                name_textstyle_opts=opts.TextStyleOpts(font_weight='bold', font_size=16),
                # axistick_opts=opts.AxisTickOpts(is_inside=True)
                axistick_opts=opts.AxisTickOpts(
                    is_inside=False,
                ),
                axisline_opts=opts.AxisLineOpts(
                    is_show=True,
                    symbol=None,
                ),
                axispointer_opts=opts.AxisPointerOpts(  # 关闭y轴tooltip指示线
                    is_show=False,
                ),
            ),
            # tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="line"),
            legend_opts=opts.LegendOpts(is_show=False),

        )
    )

    grid_chart = Grid(init_opts=opts.InitOpts(width="1200px", height="450px"))
    grid_chart.add(
        kline_line,
        # grid_index=1,
        grid_opts=opts.GridOpts(pos_left="5%", height="50%"),
    )
    grid_chart.add(
        vol_line,
        grid_opts=opts.GridOpts(
            pos_left="5%",
            pos_top="65%",
            height="20%",

        ),
    )

    return grid_chart


def stats_report(ctx=None, file_name=None):
    # type: (Optional[str], Optional[str]) -> None
    """
    分析策略运行结果，并输出分析报告。QFF回测运行完成后会自动调用，模拟交易中每天收盘后也会自动调用。

    :param ctx: 策略运行的上下文环境，默认为当前运行的策略。也可以通过 `pickle.dump` 函数读取以前策略的pkl文件获取context.
    :param file_name: 策略分析报告输出路径，默认为 `.qff/output/backtest/<策略名称>策略分析报告.html`

    :return: None

    """
    log.debug('调用stats_report' + str(locals()).replace('{', '(').replace('}', ')'))
    if ctx is None:
        ctx = context
    if file_name is None:
        file_name = os.path.join(os.getcwd(), '策略运行报告({}).html'.format(ctx.strategy_name))
    loader = FileSystemLoader(os.path.dirname(__file__))
    jinja2_env = Environment(lstrip_blocks=True, trim_blocks=True, loader=loader)
    template = jinja2_env.get_template("template.html")
    content = template.render(ctx=ctx,
                              risk=stats_risk(ctx),
                              charts=stats_charts(ctx),
                              perf=Perf(ctx)
                              )

    with open(file_name, 'w', encoding='utf8') as file:
        file.write(content)
    if platform.system() == 'Windows':
        os.startfile(file_name)
    else:
        print("策略分析报告已生成，文件位置：{}".format(file_name))


if __name__ == '__main__':

    from qff.tools.local import back_test_path, temp_path
    import pickle

    chart_file = '{}{}{}.html'.format(temp_path, os.sep, 'strategy_chart')
    pkl_filename = '{}{}{}.pkl'.format(back_test_path, os.sep, 'simple(9)')
    load_ctx = pickle.load(open(pkl_filename, "rb"))
    stats_report(load_ctx, chart_file)
