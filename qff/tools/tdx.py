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

# 基于Pytdx的数据接口,好处是可以在linux/mac上联入通达信行情
# 具体参见rainx的pytdx(https://github.com/rainx/pytdx)

from datetime import datetime, timedelta
from pytdx.hq import TdxHq_API
from qff.tools.config import get_config, set_config
from qff.tools.logs import log


def select_market_code(code, market='stock'):
    """
    2 - bj
    1- sh
    0 -sz
    """
    code = str(code)
    if market == 'stock':
        if code[0] in ['5', '6', '9'] or code[:3] in ["009", "126", "110", "201", "202", "203", "204"]:
            return 1
        elif code[0] in ['0', '3']:
            return 0
        elif code[0] in ['4', '8']:
            return 2
        else:
            return None
    elif market == 'index':
        if code[0] == '3':
            return 0
        return 1
    elif market == 'etf':
        if code[:2] == '15':
            return 0
        elif code[:2] == '51':
            return 1


def select_index_code(code):
    code = str(code)
    if code[0] in ['0', '8', '9', '5']:
        return 1
    else:
        return 0


def ping(ip, port=7709):
    api = TdxHq_API()
    __time1 = datetime.now()
    try:
        with api.connect(ip, port):
            res = api.get_security_list(0, 1)

            if res is not None:
                if len(api.get_security_list(0, 1)) > 800:
                    delta = datetime.now() - __time1
                    log.info('GOOD RESPONSE {},{}'.format(ip, delta))
                    return delta
                else:
                    log.warning('BAD RESPONSE {}'.format(ip))
                    return timedelta(9, 9, 0)
            else:
                log.error('BAD RESPONSE {}'.format(ip))
                return timedelta(9, 9, 0)

    except Exception as e:
        if isinstance(e, TypeError):
            log.error(e)
            log.error('内置的pytdx版本不同, 请重新安装pytdx以解决此问题')
            log.error('pip uninstall pytdx')
            log.error('pip install pytdx')

        else:
            log.warning('BAD RESPONSE {}'.format(ip))
        return timedelta(9, 9, 0)


def get_best_ip_by_ping():
    # 根据ping排序返回可用的ip列表
    dt_min = timedelta(0, 9, 0)
    _best_ip = None
    for x in stock_ip_list:
        dt = ping(x['ip'], x['port'])
        if dt < dt_min:
            dt_min = dt
            _best_ip = x

    if _best_ip is None:
        log.warning('ALL IP PING TIMEOUT!')
        return {'ip': None, 'port': None}
    else:
        return _best_ip


def select_best_ip():
    log.info('Selecting the Best Server IP of TDX')

    default_ip = {'ip': None, 'port': None}
    default_ip = get_config(section='IPLIST', option='default', default_value=default_ip)
    default_ip = eval(default_ip) if isinstance(default_ip, str) else default_ip
    assert isinstance(default_ip, dict)
    if default_ip['ip'] is None:
        best_stock_ip = get_best_ip_by_ping()
    else:
        if ping(default_ip['ip'], default_ip['port']) < timedelta(0, 1):
            log.info('USING DEFAULT STOCK IP')
            best_stock_ip = default_ip
        else:
            log.info('DEFAULT STOCK IP is BAD, RETESTING')
            best_stock_ip = get_best_ip_by_ping()

    if best_stock_ip != default_ip:
        set_config(
            section='IPLIST', option='default', value=best_stock_ip)

    log.info('=== The BEST SERVER ===\n stock_ip {} '.format(best_stock_ip['ip']))
    return best_stock_ip


best_ip = {
    'ip': None,
    'port': None
}


def get_best_ip():
    global best_ip
    if best_ip['ip'] is not None and best_ip['port'] is not None:
        ip = best_ip['ip']
        port = best_ip['port']
    else:
        best_ip = select_best_ip()
        ip = best_ip['ip']
        port = best_ip['port']
    return ip, port


stock_ip_list = [
    # added 20190222 from tdx
    {"ip": "106.120.74.86", "port": 7711, "name": "北京行情主站1"},
    {"ip": "113.105.73.88", "port": 7709, "name": "深圳行情主站"},
    {"ip": "113.105.73.88", "port": 7711, "name": "深圳行情主站"},
    {"ip": "114.80.80.222", "port": 7711, "name": "上海行情主站"},
    {"ip": "117.184.140.156", "port": 7711, "name": "移动行情主站"},
    {"ip": "119.147.171.206", "port": 443, "name": "广州行情主站"},
    {"ip": "119.147.171.206", "port": 80, "name": "广州行情主站"},
    {"ip": "218.108.50.178", "port": 7711, "name": "杭州行情主站"},
    {"ip": "221.194.181.176", "port": 7711, "name": "北京行情主站2"},
    # origin
    {"ip": "106.120.74.86", "port": 7709},  # 北京
    {"ip": "112.95.140.74", "port": 7709},
    {"ip": "112.95.140.92", "port": 7709},
    {"ip": "112.95.140.93", "port": 7709},
    {"ip": "113.05.73.88", "port": 7709},  # 深圳
    {"ip": "114.67.61.70", "port": 7709},
    {"ip": "114.80.149.19", "port": 7709},
    {"ip": "114.80.149.22", "port": 7709},
    {"ip": "114.80.149.84", "port": 7709},
    {"ip": "114.80.80.222", "port": 7709},  # 上海
    {"ip": "115.238.56.198", "port": 7709},
    {"ip": "115.238.90.165", "port": 7709},
    {"ip": "117.184.140.156", "port": 7709},  # 移动
    {"ip": "119.147.164.60", "port": 7709},  # 广州
    {"ip": "119.147.171.206", "port": 7709},  # 广州
    {"ip": "119.29.51.30", "port": 7709},
    {"ip": "121.14.104.70", "port": 7709},
    {"ip": "121.14.104.72", "port": 7709},
    {"ip": "121.14.110.194", "port": 7709},  # 深圳
    {"ip": "121.14.2.7", "port": 7709},
    {"ip": "123.125.108.23", "port": 7709},
    {"ip": "123.125.108.24", "port": 7709},
    {"ip": "124.160.88.183", "port": 7709},
    {"ip": "180.153.18.17", "port": 7709},
    {"ip": "180.153.18.170", "port": 7709},
    {"ip": "180.153.18.171", "port": 7709},
    {"ip": "180.153.39.51", "port": 7709},
    {"ip": "218.108.47.69", "port": 7709},
    {"ip": "218.108.50.178", "port": 7709},  # 杭州
    {"ip": "218.108.98.244", "port": 7709},
    {"ip": "218.75.126.9", "port": 7709},
    {"ip": "218.9.148.108", "port": 7709},
    {"ip": "221.194.181.176", "port": 7709},  # 北京
    {"ip": "59.173.18.69", "port": 7709},
    {"ip": "60.12.136.250", "port": 7709},
    {"ip": "60.191.117.167", "port": 7709},
    {"ip": "60.28.29.69", "port": 7709},
    {"ip": "61.135.142.73", "port": 7709},
    {"ip": "61.135.142.88", "port": 7709},  # 北京
    {"ip": "61.152.107.168", "port": 7721},
    {"ip": "61.152.249.56", "port": 7709},  # 上海
    {"ip": "61.153.144.179", "port": 7709},
    {"ip": "61.153.209.138", "port": 7709},
    {"ip": "61.153.209.139", "port": 7709},
    {"ip": "hq.cjis.cn", "port": 7709},
    {"ip": "hq1.daton.com.cn", "port": 7709},
    {"ip": "jstdx.gtjas.com", "port": 7709},
    {"ip": "shtdx.gtjas.com", "port": 7709},
    {"ip": "sztdx.gtjas.com", "port": 7709},
    {"ip": "113.105.142.162", "port": 7721},
    {"ip": "23.129.245.199", "port": 7721},
]
