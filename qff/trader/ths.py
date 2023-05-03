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
 同花顺交易接口: 封装同花顺下单软件客户端操作API，进行自动化的程序化股票交易，以支持实盘交易功能
"""
import pywinauto
from pywinauto import clipboard
import os
import time
import functools
import io
import pandas as pd
from qff.tools.logs import log
from qff.tools.local import temp_path
from qff.trader.captcha import captcha_recognize
from qff.tools.tdx import select_market_code


class THS_CONST:
    """

    """
    DEFAULT_EXE_PATH: str = ""
    TITLE = "网上股票交易系统5.0"

    COMMON_GRID_CONTROL_ID = 1047

    BALANCE_CONTROL_ID_GROUP = {
        "资金余额": 1012,
        "冻结金额": 1013,
        "可用金额": 1016,
        "可取金额": 1017,
        "股票市值": 1014,
        "总资产": 1015,
    }

    GRID_DTYPE = {
        "操作日期": str,
        "委托编号": str,
        "申请编号": str,
        "合同编号": str,
        "证券代码": str,
        "股东代码": str,
        "资金帐号": str,
        "资金帐户": str,
        "发生日期": str,
    }


class Trader:
    def __init__(self):
        self._app = None
        self._main = None
        self._toolbar = None

    @property
    def app(self):
        """Return current app instance"""
        return self._app

    @property
    def main(self):
        """Return current main window instance"""
        return self._main

    @staticmethod
    def wait(seconds):
        time.sleep(seconds)

    def exit(self):
        self._app.kill()

    def connect(self, exe_path=None):
        """
        直接连接登陆后的客户端
        :param exe_path: 客户端路径类似 r'C:\\htzqzyb2\\xiadan.exe', 默认 r'C:\\htzqzyb2\\xiadan.exe'
        :return:
        """
        connect_path = exe_path or THS_CONST.DEFAULT_EXE_PATH
        if connect_path is None:
            raise ValueError(
                "参数 exe_path 未设置，请设置客户端对应的 exe 地址,类似 C:\\客户端安装目录\\xiadan.exe"
            )

        self._app = pywinauto.Application("uia").connect(path=connect_path, timeout=10)
        self._close_prompt_windows()
        self._main = self._app.top_window()
        self._toolbar = self._main.child_window(class_name="ToolbarWindow32")
        log.info("同花顺交易接口: 连接下单程序成功! ")

    @property
    def balance(self):
        """ 当前股票账户结算金额 """
        self._switch_left_menus(["查询[F4]", "资金股票"])

        result = {}
        for key, control_id in THS_CONST.BALANCE_CONTROL_ID_GROUP.items():
            result[key] = float(
                self._main.child_window(
                    control_id=control_id, class_name="Static"
                ).window_text()
            )
        return result

    @property
    def position(self):
        self._switch_left_menus(["查询[F4]", "资金股票"])

        return self._get_grid_data(THS_CONST.COMMON_GRID_CONTROL_ID)

    @property
    def today_entrusts(self):
        self._switch_left_menus(["查询[F4]", "当日委托"])

        return self._get_grid_data(THS_CONST.COMMON_GRID_CONTROL_ID)

    @property
    def today_trades(self):
        self._switch_left_menus(["查询[F4]", "当日成交"])

        return self._get_grid_data(THS_CONST.COMMON_GRID_CONTROL_ID)

    @property
    def cancel_entrusts(self):
        self._switch_left_menus(["撤单[F3]"])

        return self._get_grid_data(THS_CONST.COMMON_GRID_CONTROL_ID)

    def cancel_entrust(self, entrust_no):

        for i, entrust in enumerate(self.cancel_entrusts):
            if entrust["合同编号"] == entrust_no:
                log.info(f"同花顺交易接口: 撤销第{i}笔委托订单，合同编号：{entrust_no} ")
                self._cancel_entrust_by_double_click(i)
                return self._handle_pop_dialogs()

        return {"message": "委托单状态错误不能撤单, 该委托单可能已经成交或者已撤"}

    def cancel_all_entrusts(self):
        self._switch_left_menus(["撤单[F3]"])

        # 点击全部撤销控件
        self._app.top_window().child_window(
            control_id=30001, class_name="Button", title_re="""全撤.*"""
        ).click()
        self.wait(0.2)
        return self._handle_pop_dialogs()

    def buy(self, security, price, amount):
        self._switch_left_menus(["买入[F1]"])
        result = self.trade(security, price, amount)
        log.info(f"同花顺交易接口: 买入股票{security}, 返回值:{result} ")
        return

    def sell(self, security, price, amount):
        self._switch_left_menus(["卖出[F2]"])
        result = self.trade(security, price, amount)
        log.info(f"同花顺交易接口: 卖出股票{security}, 返回值:{result} ")
        return

    def trade(self, security, price, amount):
        self._set_trade_params(security, price, amount)

        self._main.child_window(control_id=1006, class_name="Button").click()

        return self._handle_pop_dialogs()

    def _close_prompt_windows(self):
        """
        关闭启动时的提示窗口
        """
        self.wait(1)
        for window in self._app.windows(class_name="#32770", visible_only=True):
            title = window.window_text()
            if title != THS_CONST.TITLE:
                log.info("同花顺交易接口: 关闭提示窗口 " + title)
                window.close()
                self.wait(0.2)

    def _switch_left_menus(self, path, sleep=0.2):
        self._get_left_menus_handle().get_item(path).select()
        self._app.top_window().type_keys('{F5}')
        self.wait(sleep)

    @functools.lru_cache()
    def _get_left_menus_handle(self):
        count = 2
        while True:
            try:
                handle = self._main.child_window(control_id=129, class_name="SysTreeView32")
                if count <= 0:
                    return handle
                # sometime can't find handle ready, must retry
                handle.wait("ready", 2)
                return handle
            except Exception as ex:
                log.error(f"同花顺交易接口: _get_left_menus_handle: {ex}")
            count = count - 1

    def _get_grid_data(self, control_id, is_records=True):
        clipboard.EmptyClipboard()
        grid = self.main.child_window(
            control_id=control_id, class_name="CVirtualGridCtrl"
        )

        grid.set_focus()
        grid.type_keys("^A^C", set_foreground=False)

        content = self._get_clipboard_data()

        try:
            df = pd.read_csv(io.StringIO(content), delimiter="\t", na_filter=False)
            if is_records:
                return df.to_dict('records')
            else:
                return df
        except Exception as ex:
            log.error(f"同花顺交易接口: _get_grid_data: {ex}")
            return None

    def _get_clipboard_data(self) -> str:
        if self.app.top_window().window(class_name="Static", title_re=".*验证码.*").exists(timeout=1):
            file_path = '{}{}{}'.format(temp_path, os.sep, 'tmp.png')
            count = 5
            found = False
            while count > 0:
                self.app.top_window().window(control_id=2405, class_name="Static").capture_as_image(). \
                    save(file_path)  # 保存验证码

                captcha_num = captcha_recognize(file_path).strip()  # 识别验证码
                captcha_num = "".join(captcha_num.split())
                log.info("同花顺交易接口: 验证码识别输出 " + captcha_num)
                if len(captcha_num) == 4:
                    captcha_input = self._main.window(control_id=2404, class_name='Edit')
                    captcha_input.set_focus()
                    captcha_input.type_keys(captcha_num)
                    # self.app.top_window().window(control_id=0x964, class_name="Edit").set_text(captcha_num)  # 模拟输入验证码
                    self._main.window(control_id=1, class_name='Button').click()  # 模拟点击确定
                    self.wait(0.5)

                    if not self._app.top_window().window(class_name="Static", title_re=".*验证码.*").exists(timeout=1):
                        found = True
                        break

                count -= 1
                self.wait(0.1)
                self.app.top_window().window(control_id=2405, class_name="Static").click()

            if not found:
                self._main.window(control_id=2, class_name='Button').click()  # 模拟点击取消

        count = 5
        while count > 0:
            try:
                return clipboard.GetData()

            except Exception as ex:
                count -= 1
                log.error(f"同花顺交易接口: _get_clipboard_data: {ex}")

    def _cancel_entrust_by_double_click(self, row):
        x = 100
        y = (50 + 20 * row)
        grid = self._app.top_window().child_window(
            control_id=THS_CONST.COMMON_GRID_CONTROL_ID,
            class_name="CVirtualGridCtrl",
        )
        grid.set_focus()
        grid.double_click_input(coords=(x, y))

    def _handle_pop_dialogs(self):
        while self._main.child_window(control_id=1365).exists(timeout=0.5):
            try:
                title = self._main.child_window(control_id=1365).window_text()

                if title in ["提示信息", "委托确认", "网上交易用户协议", "撤单确认"]:
                    self._main.window(control_id=6, class_name="Button").click()
                elif title == "提示":
                    result = self._main.window(control_id=1004, class_name='Static').window_text()
                    self._main.window(control_id=2, class_name="Button").click()
                    return self.__parse_result(result)

            except pywinauto.findwindows.ElementNotFoundError:
                return {"message": "success"}

    @staticmethod
    def __parse_result(result):
        """ 解析买入卖出的结果 """

        # "您的买入委托已成功提交，合同编号：865912566。"
        # "您的卖出委托已成功提交，合同编号：865967836。"
        # "您的撤单委托已成功提交，合同编号：865967836。"
        # "系统正在清算中，请稍后重试！ "

        if r"已成功提交，合同编号：" in result:
            return {
                "success": True,
                "msg": result,
                "entrust_no": result.split("合同编号：")[1].split("。")[0]
            }
        else:
            return {
                "success": False,
                "msg": result
            }

    def _type_edit_control_keys(self, control_id, text):
        editor = self._main.child_window(control_id=control_id, class_name="Edit")
        editor.set_focus()
        editor.type_keys(text)

    def _set_trade_params(self, security, price, amount):
        code = security[:6]
        self._type_edit_control_keys(1032, code)

        # wait security input finish
        self.wait(0.1)

        # 设置交易所
        market = select_market_code(code)
        if market == 1:  # sh
            item_text = "上海A股"
        elif market == 0:  # sz
            item_text = "深圳A股"
        else:
            log.error(f"同花顺交易接口: _set_trade_params 股票代码错误！{code}")
            return
        selects = self._main.child_window(control_id=1003, class_name="ComboBox")
        if selects.selected_text() != item_text:
            selects.select("上海A股")

        # self.wait(0.1)

        self._type_edit_control_keys(1033, '{:.2f}'.format(price))
        self._type_edit_control_keys(1034, str(int(amount)))
        self.wait(0.1)
