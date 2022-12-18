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
import os

"""创建本地文件夹
1. setting_path ==> 用于存放配置文件 config.ini
2. cache_path ==> 用于存放临时文件
3. log_path ==> 用于存放储存的log
4. output_path ==> 用于存放输出的文件
"""

if 'QFF_HOME' in os.environ.keys():
    qff_path = os.getenv('QFF_HOME')
else:
    base_path = os.path.expanduser('~')
    qff_path = '{}{}{}'.format(base_path, os.sep, '.qff')


def generate_path(name, parents=qff_path):
    return '{}{}{}'.format(parents, os.sep, name)


def make_dir(path, exist_ok=True):
    os.makedirs(path, exist_ok=exist_ok)


setting_path = generate_path('setting')
cache_path = generate_path('cache')
log_path = generate_path('log')
temp_path = generate_path('temp')
download_path = generate_path('downloads')
output_path = generate_path('output')
back_test_path = generate_path('back_test', output_path)
sim_trade_path = generate_path('sim_trade', output_path)
evaluation_path = generate_path('evaluation', output_path)

make_dir(qff_path, exist_ok=True)
make_dir(setting_path, exist_ok=True)
make_dir(cache_path, exist_ok=True)
make_dir(log_path, exist_ok=True)
make_dir(temp_path, exist_ok=True)
make_dir(download_path, exist_ok=True)
make_dir(output_path, exist_ok=True)
make_dir(back_test_path, exist_ok=True)
make_dir(sim_trade_path, exist_ok=True)
make_dir(evaluation_path, exist_ok=True)
