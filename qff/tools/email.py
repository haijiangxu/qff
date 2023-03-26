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


import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from qff.tools.config import get_config
from qff.tools.logs import log
from qff.frame.context import context
from qff.frame.const import RUN_TYPE


def send_message(message):
    """
    给用户自己发送消息提醒, 暂时只支持邮件通知.

    :param message: 消息内容. 字符串.

    :return:  True/False, 表示是否发送成功. 当发送失败时, 会在日志中显示错误信息.

    * 此功能只能在 **实时运行模拟交易** 中使用, 回测中使用会直接忽略, 无任何提示；
    * 要使用模拟交易发送消息提醒功能, 必须在使用前正确设置邮箱配置参数；
    * 参数文件 ~/.qff/setting/config.ini 按以下格式配置参数：

    ::

        [EMAIL]
        from_email = your_email@example.com
        from_email_password = 授权密码
        smtp_server = smtp.example.com
        smtp_port = 587
        to_email = to_receive_email@example.com


    其中授权密码可通过访问 https://www.jiuanweb.com/jz/show-165933770.html 获取生成方法。

    """

    if context.run_type != RUN_TYPE.SIM_TRADE:
        return False

    # 从配置文件中获取参数
    from_email = get_config('EMAIL', 'from_email', 'your_email@example.com')
    from_email_password = get_config('EMAIL', 'from_email_password', 'your_email_password')
    smtp_server = get_config('EMAIL', 'smtp_server', 'smtp.qq.com')
    smtp_port = get_config('EMAIL', 'smtp_port', 465)
    to_email = get_config('EMAIL', 'to_email', 'to_receive_email@example.com')

    # 创建邮件消息
    msg = MIMEText(message)
    msg['From'] = formataddr(('Sender Name', from_email))
    msg['To'] = to_email
    msg['Subject'] = 'QFF邮件通知'

    # 连接SMTP服务器并发送邮件
    try:
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.login(from_email, from_email_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        log.info("邮件消息发送成功!")
        return True

    except Exception as e:
        log.error(f"邮件发送失败！错误信息：{e}")
        return False
