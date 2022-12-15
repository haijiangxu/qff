# coding=utf-8
#
# The MIT License (MIT)
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

import re
import ast
import sys
from setuptools import setup, find_packages


if sys.version_info.major != 3 or sys.version_info.minor not in [4, 5, 6, 7, 8]:
    print('wrong version, should be 3.4/3.5/3.6/3.7/3.8 version')
    sys.exit()


def get_long_description():
    with open("README.md", "r", encoding="utf-8") as f:
        long_description = f.read()
    return long_description


def read_requirements(filename):
    with open(filename) as f:
        return f.read().splitlines()


def get_version_string() -> str:
    """
    Get the  version number
    :return: version number
    :rtype: str, e.g. '0.6.24'

    """
    with open("qff/__init__.py", "rb") as _f:
        version_line = re.search(
            r"__version__\s+=\s+(.*)", _f.read().decode("utf-8")
        ).group(1)
        return str(ast.literal_eval(version_line))


# REQUIREMENTS = ['pandas>=1.5.1', 'zenlog>=1.1', 'numpy>=1.20.3', 'matplotlib>=3.4.3', 'pytdx>=1.72',
#                 'retrying>=1.3.3', 'pymongo>=3.12.0', 'pyecharts~=1.9.0',
#                 'requests>=2.26.0', 'prettytable>=2.2.0']

setup(
    name="qff",
    version=get_version_string(),
    author="xuhaijiang",
    description="qff: quantize finance framework",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
    ],
    install_requires=read_requirements('requirements.txt'),
    entry_points={
        'console_scripts': [
            'qff=qff.frame.entry:entry'
        ]
    },
    keywords=["QFF", "stock", "quant", 'quantize', "finance", "backtest", 'trading', 'investment', 'JoinQuant'],

    author_email="haijiangxu@hotmail.com",
    url="",
    license="MIT",
    packages=find_packages(),
    # package_data={"qff": ["*.py", "*.json", "*.pk", "*.js", "*.zip"]},
    include_package_data=True,
    zip_safe=True,
    python_requires=">=3.7, <4",
)

# 生成whl安装文件
# python setup.py sdist bdist_wheel
# 安装whl文件
# pip install ***.whl -i https://pypi.doubanio.com/simple


