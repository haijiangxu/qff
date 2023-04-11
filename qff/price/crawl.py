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

import akshare as ak
import pandas as pd
import requests
from bs4 import BeautifulSoup


def crawl_delist_stock():
    """
    获取当前退市股票信息列表
    :return [pd.DataFrame]
      code      name      start      end
0    000003   PT金田Ａ  1991-01-14  2002-06-14
1    000013  *ST石化A  1992-05-06  2004-09-20
2    000015   PT中浩Ａ  1992-06-25  2001-10-25
    """
    sz = ak.stock_info_sz_delist(symbol="终止上市公司")
    sz.columns = pd.Index(['code', 'name', 'start', 'end'])

    sh = ak.stock_info_sh_delist()
    sh.columns = pd.Index(['code', 'name', 'start', 'end'])

    delist = pd.concat([sz, sh])
    delist = delist[delist['code'].str[:1].isin(['6', '0', '3'])]
    delist.start = delist.start.apply(lambda x: str(x)[:10])
    delist.end = delist.end.apply(lambda x: str(x)[:10])
    return delist


def crawl_stock_list():
    """
    获取A股股票列表
    :return:
    """
    sh1 = ak.stock_info_sh_name_code(symbol="主板A股")
    sh2 = ak.stock_info_sh_name_code(symbol="科创板")
    sh = pd.concat([sh1, sh2])
    sh = sh.iloc[:, [0, 1, 3]]
    sh.columns = pd.Index(['code', 'name', 'start'])

    sz = ak.stock_info_sz_name_code(indicator="A股列表")
    sz = sz.iloc[:, [1, 2, 3]]
    sz.columns = pd.Index(['code', 'name', 'start'])

    bj = ak.stock_info_bj_name_code()
    bj = bj.iloc[:, [0, 1, 4]]
    bj.columns = pd.Index(['code', 'name', 'start'])

    df = pd.concat([sh, sz, bj])
    df.start = df.start.apply(lambda x: str(x)[:10])

    return df


def crawl_index_list():
    """
    获取最新指数列表
    :return:
    """
    df = ak.index_stock_info()
    df.columns = pd.Index(['code', 'name', 'start'])
    return df


def crawl_index_stock_cons(symbol: str = "000300") -> pd.DataFrame:
    """
    改写akshare.index_stock_cons函数
    最新股票指数的成份股目录
    http://vip.stock.finance.sina.com.cn/corp/view/vII_NewestComponent.php?page=1&indexid=000300
    :param symbol: 指数代码, 可以通过 ak.index_stock_info() 函数获取
    :type symbol: str
    :return: 最新股票指数的成份股目录
    :rtype: pandas.DataFrame
    """
    url = f"http://vip.stock.finance.sina.com.cn/corp/go.php/vII_NewestComponent/indexid/{symbol}.phtml"
    r = requests.get(url)
    r.encoding = "gb2312"
    soup = BeautifulSoup(r.text, "lxml")
    page_num = (
        soup.find(attrs={"class": "table2"})
            .find("td")
            .find_all("a")[-1]["href"]
            .split("page=")[-1]
            .split("&")[0]
    )
    if page_num == "#":
        # temp_df = pd.read_html(r.text, header=1)[3].iloc[:, :3]
        temp_df = pd.read_html(r.text)[3].iloc[:, :3]
        temp_df.columns = pd.Index(temp_df.loc[0].to_list())
        temp_df = temp_df.drop(0)
        temp_df["品种代码"] = temp_df["品种代码"].astype(str).str.zfill(6)
        return temp_df

    temp_df = pd.DataFrame()
    for page in range(1, int(page_num) + 1):
        url = f"http://vip.stock.finance.sina.com.cn/corp/view/vII_NewestComponent.php?page={page}&indexid={symbol}"
        r = requests.get(url)
        r.encoding = "gb2312"
        temp_df = pd.concat([temp_df, pd.read_html(r.text, header=1)[3]], ignore_index=True)
    temp_df = temp_df.iloc[:, :3]
    temp_df["品种代码"] = temp_df["品种代码"].astype(str).str.zfill(6)
    return temp_df


def crawl_industry_stock_cons(symbol: str = "801010") -> pd.DataFrame:
    """
    :param symbol: 行业代码, 可以通过 ak.index_component_sw() 函数获取
    :type symbol: str
    :return: 最新股票行业的成份股清单
    :rtype: pandas.DataFrame
    """
    component_sw_df = ak.index_component_sw(symbol=symbol)
    return component_sw_df


def crawl_csindex():
    """
    爬取中证指数官网指数列表
    https://www.csindex.com.cn/#/indices/family/list
    :return: 所有指数的列表目录
    :rtype: pandas.DataFrame
    """
    url = "https://www.csindex.com.cn/csindex-home/index-list/query-index-item"

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Content-Length": "284",
        "Content-Type": "application/json; charset=UTF-8",
        "Cookie": 'aliyungf_tc=efcccb97a2f78877e352e742ac2d702390b84701ec75f2b0a718802f431959e6; acw_tc=2f6fc11616701250942595032e175002ab4fd98ced3eb4b6bbc5f16e4d0640; zg_did={"did": "184db38fb75b-0c9be5186dff25-26021151-190140-184db38fb76b2f"}; _uab_collina=167012525727676844963333; ssxmod_itna=eqjxRD0DgDnii=Xx0dK6DUx=QX/wx7Kwot4jbD/KzIDnqD=GFDK40EoOKDCiIbSG75IWNiefmK+3YG7pRW14pRENbDU4i8DCkne4TDem=D5xGoDPxDeDA7qGaDb4Dr2qqGPc0EkH=ODpxGrDlKDRx07Vg5DWxDFf=D4=EFYmxGif=HFP/yhDiHYu=0DfxG1DQ5DsZifYAKD0E3LYmyCht3DEm4OqtYDvxDk3KyF54Gd66H1hhMNQePqT7ctTl03hQ0t=Cexr5+4q0qKenqP7W0tlDUNW0UnDDamWeZD4D===; ssxmod_itna2=eqjxRD0DgDnii=Xx0dK6DUx=QX/wx7Kwot4QG9i=WKDBqwq7phxDCYmO70jrCxnRD8R4g4xrw4o8B7bvqatCYqAPqteErmKUUmLcIYE+ZgBLvyRjj90FpUtZkyvsBzgi2NV3w0CgvEHWjhFCIrWaBaBGx/yzOowGdtE8grA81aEtnOApvaawlx8mr8cAQ+AwASor/EAI9cBO70oOh4EIvUgvfbudcOcDS3C0Km7z/SWYnlqHR7wT1gyOTTWjERd0vainQTMO3ejIqnQrsTe5xs1zqLkYYG4Dw6wxoB4gRG2M/R0qS0iZ/r=Ry/frV7FT05x8D=QDt8A5UyiFYq8BqoyDD08DiQeYD===; zg_6df0ba28cbd846a799ab8f527e8cc62b={"sid": 1670125255544,"updated": 1670125298697,"info": 1670125255547,"superProperty": "{\"应用名称\": \"中证指数官网\"}","platform": "{}","utm": "{}","referrerDomain": "www.baidu.com","landHref": "https://www.csindex.com.cn/#/indices/family/list","prePath": "https://www.csindex.com.cn/#/indices/family/list","duration": 43684.564999999995}',
        "Host": "www.csindex.com.cn",
        "Origin": "https://www.csindex.com.cn",
        "Pragma": "no-cache",
        "Referer": "https://www.csindex.com.cn /",
        "Proxy-Connection": "keep-alive",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    }
    params = {
        "sorter": {"sortField": "null", "sortOrder": None},
        "pager": {"pageNum": 1, "pageSize": 40},
        "indexFilter": {
            "ifCustomized": None,
            "ifTracked": None,
            "ifWeightCapped": None,
            "indexCompliance": None,
            "hotSpot": None,
            "indexClassify": None,
            "currency": None,
            "region": None,
            "indexSeries": None,
            "undefined": None}
    }
    r = requests.post(url, params=params, headers=headers)
    data_json = r.json()
    # todo
