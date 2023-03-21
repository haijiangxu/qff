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
from datetime import datetime
import os
import sys
from zenlog import logging
from qff.tools.local import log_path
from qff.tools.config import get_config
from qff.frame.context import context


class Log:
    """
    分级别输出日志，跟python的logging模块一致print输出的结果等同于log.info

    * log.error(content)  输出错误日志
    * log.warn(content)  输出报警日志
    * log.info(content) 输出信息日志
    * log.debug(content) 输出调试日志

    """
    def __init__(self):
        try:
            self.file_name = '{}{}qff-{}-{}.log'.format(
                log_path,
                os.sep,
                os.path.basename(sys.argv[0]).split('.py')[0],
                str(datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
            )
        except:
            self.file_name = '{}{}qff-{}-.log'.format(
                log_path,
                os.sep,
                str(datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
            )

        logging.basicConfig(
            level=logging.INFO,
            format='qff>>> %(message)s',
            filename=self.file_name,
            filemode='w',
        )
        self.console = logging.StreamHandler()
        formatter = logging.Formatter('qff>> %(message)s')
        self.console.setFormatter(formatter)
        logging.getLogger().addHandler(self.console)
        self.console_show = True
        log_level = get_config('LOG', 'level', 'info')
        self.set_level(log_level)

    @property
    def pre_time(self):
        if context.current_dt:
            return context.current_dt
        else:
            return "-------------------"

    def info(self, msg, *args, **kwargs):
        msg = self.pre_time + ' - INFO - ' + str(msg)
        logging.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        msg = self.pre_time + ' - WARNING - ' + str(msg)
        logging.warning(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        msg = self.pre_time + ' - DEBUG - ' + str(msg)
        logging.debug(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        msg = self.pre_time + ' - ERROR - ' + str(msg)
        logging.error(msg, *args, **kwargs)

    def set_level(self, level):
        """
        设置不同种类的log的级别, 低于这个级别的log不会输出. 所有log的默认级别是info

        :param level: 字符串, 必须是'debug', 'info', 'warning', 'error'中的一个, 级别: debug < info < warning < error

        :return: None
        """
        # logger = logging.getLogger('')
        if level == 'info':
            self.console.setLevel(logging.INFO)
        elif level in ['warn', 'warning']:
            self.console.setLevel(logging.WARN)
        elif level in ['debug', 'verbose']:
            self.console.setLevel(logging.DEBUG)
        elif level == 'error':
            self.console.setLevel(logging.ERROR)
        else:
            self.error("set_level设置日志级别必须为：debug,info,warning,error")

    def toggle(self):
        """
        开关日志终端显示
        """
        if self.console_show:
            logging.getLogger().removeHandler(self.console)
            self.console_show = False
        else:
            logging.getLogger().addHandler(self.console)
            self.console_show = True


log = Log()
