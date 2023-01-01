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
 显示k线数据图像
"""
import os
import platform
from pyecharts import options as opts
from pyecharts.commons.utils import JsCode
from pyecharts.charts import Kline, Line, Bar, Grid

from qff.helper.formula import MA, MACD
from qff.tools.local import temp_path
from qff.price.query import get_stock_name, get_index_name


def kshow(df, code, mp=None, index=False):
    """
    通过pyechart生成K线图
    :param df: dataframe 股票数据
    :param code: str 股票代码
    :param mp: dict 标注点，用于标注买入信号或卖出信号，格式为
      {
       “标注名称1”：[日期，价格]，
       “标注名称2”：[日期，价格]，
       }
    :param index: bool 是否指数代码
    :return:
    """
    ky = df.loc[:, ['open', 'close', 'low', 'high']].to_dict('split')['data']
    kx = df.index.tolist()
    vol = df.vol.tolist()
    ma5 = MA(df.close, 5).tolist()
    ma10 = MA(df.close, 10).tolist()
    ma20 = MA(df.close, 20).tolist()
    ma60 = MA(df.close, 60).tolist()
    ma120 = MA(df.close, 120).tolist()
    ma250 = MA(df.close, 250).tolist()
    _macd = MACD(df.close)
    dif = _macd.DIFF.tolist()
    dea = _macd.DEA.tolist()
    macd = _macd.MACD.tolist()
    if index:
        stock_name = get_index_name(code)[code]
    else:
        stock_name = get_stock_name(code, date=kx[-1])[code]

    mp_data = []
    if mp is not None:
        for key, value in mp.items():
            mp_data.append(opts.MarkPointItem(name=key,
                                              coord=value,
                                              value=value[1],
                                              ))

    kline = (
        Kline()
        .add_xaxis(xaxis_data=kx)
        .add_yaxis(
            series_name="",
            y_axis=ky,
            itemstyle_opts=opts.ItemStyleOpts(
                color="#ef232a",
                color0="#14b143",
                border_color="#ef232a",
                border_color0="#14b143",
            ),
            markpoint_opts=opts.MarkPointOpts(
                data=mp_data,
                symbol='pin',
                label_opts=opts.LabelOpts(
                    position='inside',
                    color="#fff"
                )
            ),
        ).set_global_opts(
            title_opts=opts.TitleOpts(title="K线图-{} {}".format(code, stock_name), pos_left="0"),
            xaxis_opts=opts.AxisOpts(
                type_="category",
                is_scale=True,
                boundary_gap=False,
                axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
                split_number=20,
                min_="dataMin",
                max_="dataMax",
            ),
            yaxis_opts=opts.AxisOpts(
                is_scale=True,
                splitline_opts=opts.SplitLineOpts(
                    is_show=True,
                    linestyle_opts=opts.LineStyleOpts(opacity=0.5, type_='dashed')
                )
            ),
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="line"),
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=False, type_="inside", xaxis_index=[0, 0], range_end=100
                ),
                opts.DataZoomOpts(
                    is_show=True, xaxis_index=[0, 1], pos_top="97%", range_end=100
                ),
                opts.DataZoomOpts(is_show=False, xaxis_index=[0, 2], range_end=100),
            ],

        )

    )

    kline_line = (
        Line()
        .add_xaxis(xaxis_data=kx)
        .add_yaxis(
            series_name="MA5",
            y_axis=ma5,
            is_smooth=True,
            is_symbol_show=False,
            linestyle_opts=opts.LineStyleOpts(opacity=1),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="MA10",
            y_axis=ma10,
            is_smooth=True,
            is_symbol_show=False,
            linestyle_opts=opts.LineStyleOpts(opacity=1),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="MA20",
            y_axis=ma20,
            is_smooth=True,
            is_symbol_show=False,
            linestyle_opts=opts.LineStyleOpts(opacity=1),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="MA60",
            y_axis=ma60,
            is_smooth=True,
            is_symbol_show=False,
            linestyle_opts=opts.LineStyleOpts(opacity=1),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="MA120",
            y_axis=ma120,
            is_smooth=True,
            is_symbol_show=False,
            linestyle_opts=opts.LineStyleOpts(opacity=1),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="MA250",
            y_axis=ma250,
            is_smooth=True,
            is_symbol_show=False,
            linestyle_opts=opts.LineStyleOpts(opacity=1),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(
            xaxis_opts=opts.AxisOpts(
                type_="category",
                grid_index=1,
                axislabel_opts=opts.LabelOpts(is_show=False),
            ),
            yaxis_opts=opts.AxisOpts(
                grid_index=1,
                split_number=3,
                axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
                axislabel_opts=opts.LabelOpts(is_show=True),
            ),
        )
    )

    overlap_kline_line = kline.overlap(kline_line)

    # Bar-1
    bar_1 = (
        Bar()
        .add_xaxis(xaxis_data=kx)
        .add_yaxis(
            series_name="成交量",
            y_axis=vol,
            xaxis_index=1,
            yaxis_index=1,
            label_opts=opts.LabelOpts(is_show=False),
            itemstyle_opts=opts.ItemStyleOpts(
                # color='#ef232a'
                color=JsCode(
                    """
                function(params) {
                    var colorList;
                    if (barData[params.dataIndex][1] > barData[params.dataIndex][0]) {
                        colorList = '#ef232a';
                    } else {
                        colorList = '#14b143';
                    }
                    return colorList;
                }
                """
                )
            ),
        )
        .set_global_opts(
            xaxis_opts=opts.AxisOpts(
                type_="category",
                grid_index=1,
                axislabel_opts=opts.LabelOpts(is_show=False),
            ),
            legend_opts=opts.LegendOpts(is_show=False),
        )
    )

    # Bar-2 (Overlap Bar + Line)
    bar_2 = (
        Bar()
        .add_xaxis(xaxis_data=kx)
        .add_yaxis(
            series_name="MACD",
            y_axis=macd,
            xaxis_index=2,
            yaxis_index=2,
            label_opts=opts.LabelOpts(is_show=False),
            itemstyle_opts=opts.ItemStyleOpts(
                color=JsCode(
                    """
                        function(params) {
                            var colorList;
                            if (params.data >= 0) {
                              colorList = '#ef232a';
                            } else {
                              colorList = '#14b143';
                            }
                            return colorList;
                        }
                        """
                )
            ),
        )
        .set_global_opts(
            xaxis_opts=opts.AxisOpts(
                type_="category",
                grid_index=2,
                axislabel_opts=opts.LabelOpts(is_show=False),
            ),
            yaxis_opts=opts.AxisOpts(
                grid_index=2,
                split_number=4,
                axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
                axislabel_opts=opts.LabelOpts(is_show=True),
            ),
            legend_opts=opts.LegendOpts(is_show=False),
        )
    )

    line_2 = (
        Line()
        .add_xaxis(xaxis_data=kx)
        .add_yaxis(
            series_name="DIF",
            y_axis=dif,
            xaxis_index=2,
            yaxis_index=2,
            is_symbol_show=False,
            # linestyle_opts=opts.LineStyleOpts(color="white"),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="DEA",
            y_axis=dea,
            xaxis_index=2,
            yaxis_index=2,
            is_symbol_show=False,
            linestyle_opts=opts.LineStyleOpts(color='#FFFF00'),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(legend_opts=opts.LegendOpts(is_show=False))
    )

    # 最下面的柱状图和折线图
    overlap_bar_line = bar_2.overlap(line_2)

    # 最后的 Grid
    grid_chart = Grid(init_opts=opts.InitOpts(width="1400px", height="800px"))

    # 这个是为了把 data.datas 这个数据写入到 html 中,还没想到怎么跨 series 传值
    # demo 中的代码也是用全局变量传的
    grid_chart.add_js_funcs("var barData = {}".format(ky))

    # K线图和 MA5 的折线图
    grid_chart.add(
        overlap_kline_line,
        grid_opts=opts.GridOpts(pos_left="3%", pos_right="1%", height="60%"),
    )
    # Volumn 柱状图
    grid_chart.add(
        bar_1,
        grid_opts=opts.GridOpts(
            pos_left="3%", pos_right="1%", pos_top="71%", height="10%"
        ),
    )
    # MACD DIFS DEAS
    grid_chart.add(
        overlap_bar_line,
        grid_opts=opts.GridOpts(
            pos_left="3%", pos_right="1%", pos_top="82%", height="14%"
        ),
    )
    chart_filename = '{}{}{}.html'.format(temp_path, os.sep, 'kline_chart')
    grid_chart.render(chart_filename)

    if platform.system() == 'Windows':
        os.startfile(chart_filename)
    else:
        print(f"生成k线图文件：{chart_filename}")

    return grid_chart
