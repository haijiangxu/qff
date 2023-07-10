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
import sys
import pandas as pd
from typing import Optional

if sys.platform == 'win32':

    import pywinauto
    from pywinauto import clipboard, Application, ElementNotFoundError
    from pywinauto.application import AppStartError

    import abc
    import os
    import time
    import functools
    import io

    from qff.tools.logs import log
    from qff.tools.local import temp_path
    from qff.tools.config import get_config
    from qff.trader.captcha import captcha_recognize
    from qff.tools.tdx import select_market_code

    __all__ = ['trader_connect', 'trader_balance', 'trader_position', 'trader_entrusts', 'trader_deal', 'trader_buy',
               'trader_sell', 'trader_cancel']


    class THS_CONST:
        """

        """
        DEFAULT_EXE_PATH: str = "C:\\同花顺\\xiadan.exe"
        TITLE = "网上股票交易系统5.0"

        COMMON_GRID_CONTROL_ID = 1047

        BALANCE_CONTROL_ID_GROUP = {
            "资金余额": 1012,
            "冻结金额": 1013,
            "可用金额": 1016,
            "可取金额": 1017,
            "股票市值": 1014,
            "总资产": 1015,
            "持仓盈亏": 1027
        }

        ENTRUSTS_DTYPE = {
            '委托时间': str,
            '证券代码': str,
            '证券名称': str,
            '操作': str,
            '备注': str,
            '委托数量': int,
            '成交数量': int,
            '委托价格': float,
            '成交均价': float,
            '撤单数量': int,
            '合同编号': int,
            '交易市场': str
        }

        DEAL_DTYPE = {
            '成交时间': str,
            '证券代码': str,
            '证券名称': str,
            '操作': str,
            '成交数量': int,
            '成交均价': float,
            '成交金额': float,
            '合同编号': int,
            '成交编号': int
        }

        POSITION_DTYPE = {
            '证券代码': str,
            '证券名称': str,
            '股票余额': int,
            '可用余额': int,
            '冻结数量': int,
            '成本价': float,
            '市价': float,
            '盈亏': float,
            '盈亏比例(%)': float,
            '市值': float,
            '当日买入': int,
            '当日卖出': int,
            '交易市场': str,
            '持股天数': str
        }


    class Trader(abc.ABC):

        @property
        @abc.abstractmethod
        def app(self):
            """Return current app instance"""
            pass

        @property
        @abc.abstractmethod
        def main(self):
            """Return current main window instance"""
            pass

        @abc.abstractmethod
        def connect(self):
            """连接交易软件客户端"""
            pass

        @property
        @abc.abstractmethod
        def balance(self):
            """ 返回当前股票账户结算金额 """
            pass

        @property
        @abc.abstractmethod
        def position(self):
            """ 返回当前账户股票列表 """
            pass

        @abc.abstractmethod
        def buy(self, security, price, amount):
            """ 买入股票 """
            pass

        @abc.abstractmethod
        def sell(self, security, price, amount):
            """ 卖出股票 """
            pass

        @property
        @abc.abstractmethod
        def today_entrusts(self):
            """ 返回当前委托记录 """
            pass

        @property
        @abc.abstractmethod
        def today_trades(self):
            """ 返回今日成交记录 """
            pass

        @abc.abstractmethod
        def cancel_entrust(self, entrust_no):
            """ 撤销指定委托订单 """
            pass

        @abc.abstractmethod
        def cancel_all_entrusts(self):
            """ 撤销当前所有委托 """
            pass


    class ThsTrader(Trader):
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

        def wait(self, seconds):
            time.sleep(seconds)

        def exit(self):
            self._app.kill()

        def connect(self):
            """
            直接连接登陆后的客户端
            """
            try:
                self._app = pywinauto.Application("uia").connect(title=THS_CONST.TITLE)
            except pywinauto.ElementNotFoundError:
                try:
                    log.info("同花顺交易接口: 下单程序未启动，正在自动加载...")
                    xiadan_path = get_config('THS', 'path', THS_CONST.DEFAULT_EXE_PATH)
                    self._app = pywinauto.Application("uia").start(cmd_line=xiadan_path)
                    self._app.Pane2.child_window(title="登录", control_type="Button").click()
                    # self.wait(1)
                    # self._app = Application("uia").connect(title='网上股票交易系统5.0')
                    # self._app.top_window().wait_not("exists visible", 10)
                    count = 10
                    while count > 0:
                        if self._app.top_window().window_text() == THS_CONST.TITLE:
                            self._main = self._app.top_window()
                            break
                        else:
                            self.wait(0.5)
                            count -= 1

                    if count == 0:
                        log.error("同花顺交易接口: 下单程序登录密码未自动保存或保存错误！ ")
                        return False
                except AppStartError:
                    log.error("同花顺交易接口: 同花顺下单程序路径错误! ")
                    return False

            # self._close_prompt_windows()
            while True:
                if self._app.top_window().window_text() == THS_CONST.TITLE:
                    self._main = self._app.top_window()
                    break

            # self._toolbar = self._main.child_window(class_name="ToolbarWindow32")
            log.info("同花顺交易接口: 连接下单程序成功! ")
            return True

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

            return self._get_grid_data(THS_CONST.COMMON_GRID_CONTROL_ID, THS_CONST.POSITION_DTYPE)

        @property
        def today_entrusts(self):
            self._switch_left_menus(["查询[F4]", "当日委托"])

            return self._get_grid_data(THS_CONST.COMMON_GRID_CONTROL_ID, THS_CONST.ENTRUSTS_DTYPE)

        @property
        def today_trades(self):
            self._switch_left_menus(["查询[F4]", "当日成交"])

            return self._get_grid_data(THS_CONST.COMMON_GRID_CONTROL_ID, THS_CONST.DEAL_DTYPE)

        @property
        def cancel_entrusts(self):
            self._switch_left_menus(["撤单[F3]"])

            return self._get_grid_data(THS_CONST.COMMON_GRID_CONTROL_ID, THS_CONST.ENTRUSTS_DTYPE)

        def cancel_entrust(self, entrust_no):
            result = {
                "success": False,
                "msg": "委托单状态错误，不能撤单, 该委托单可能已经成交或者已撤"
            }
            entrust_list = self.cancel_entrusts.to_dict('records')
            for i, entrust in enumerate(entrust_list):
                if entrust["合同编号"] == entrust_no:
                    log.info(f"同花顺交易接口: 撤销第{i}笔委托订单，合同编号：{entrust_no} ")
                    self._cancel_entrust_by_double_click(i)
                    result = self._handle_pop_dialogs()
                    break

            log.info(f"同花顺交易接口: 撤销委托订单{entrust_no}, 返回值:{result} ")
            return result

        def cancel_all_entrusts(self):
            log.info("同花顺交易接口: 撤销所有委托订单！ ")
            self._switch_left_menus(["撤单[F3]"])

            # 点击全部撤销控件
            self._app.top_window().child_window(
                control_id=30001, class_name="Button", title_re="""全撤.*"""
            ).click()
            self.wait(0.2)
            result = self._handle_pop_dialogs()
            log.info(f"同花顺交易接口: 撤销所有委托订单, 返回值:{result} ")
            return result

        def buy(self, security, price, amount):
            self._switch_left_menus(["买入[F1]"])
            result = self.trade(security, price, amount)
            log.info(f"同花顺交易接口: 买入股票{security}, 返回值:{result} ")
            return result

        def sell(self, security, price, amount):
            self._switch_left_menus(["卖出[F2]"])
            result = self.trade(security, price, amount)
            log.info(f"同花顺交易接口: 卖出股票{security}, 返回值:{result} ")
            return result

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

        def _get_grid_data(self, control_id, grid_dtype=None, is_records=False):
            clipboard.EmptyClipboard()
            grid = self.main.child_window(
                control_id=control_id, class_name="CVirtualGridCtrl"
            )

            grid.set_focus()
            grid.type_keys("^A^C", set_foreground=False)

            content = self._get_clipboard_data()

            try:
                if grid_dtype:
                    df = pd.read_csv(io.StringIO(content), delimiter="\t", na_filter=False, usecols=grid_dtype.keys(),
                                     dtype=grid_dtype)
                else:
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

                        if not self._app.top_window().window(class_name="Static", title_re=".*验证码.*").exists(
                                timeout=1):
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
            y = (40 + 20 * row)
            grid = self._app.top_window().child_window(
                control_id=THS_CONST.COMMON_GRID_CONTROL_ID,
                class_name="CVirtualGridCtrl",
            )
            grid.set_focus()
            # grid.double_click_input(coords=(x, y))
            grid.click_input(coords=(x, y))
            self.wait(0.5)
            grid.click_input(coords=(x, y))

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
                    return {"success": True}

            return {"success": True}

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
            n = editor.line_length(0)
            if n > 0:
                editor.type_keys('{BS}' * 8)
            editor.type_keys(text)

        def _set_trade_params(self, security, price, amount):
            code = security[:6]
            self._type_edit_control_keys(1032, code)

            # wait security input finish
            self.wait(0.1)

            # 设置交易所
            # market = select_market_code(code)
            # if market == 1:  # sh
            #     item_text = "上海A股"
            # elif market == 0:  # sz
            #     item_text = "深圳A股"
            # else:
            #     log.error(f"同花顺交易接口: _set_trade_params 股票代码错误！{code}")
            #     return
            # selects = self._main.child_window(control_id=1003, class_name="ComboBox")
            # if selects.selected_text() != item_text:
            #     selects.select(item_text)

            # self.wait(0.1)

            self._type_edit_control_keys(1033, '{:.2f}'.format(price))
            self._type_edit_control_keys(1034, str(int(amount)))
            self.wait(0.1)


    client: Trader = ThsTrader()


    def trader_connect():
        # type: () -> bool
        """
            连接交易软件客户端

            调用本函数连接已启动的交易软件客户端，本函数需在其他实盘操作函数前运行。为使qff成功连接交易软件，需要提前启动并登录交易软件，
            对于通用版同花顺下单程序，需要先手动登录一次：添加券商，填入账户号、密码、验证码，勾选“保存密码”，并在config文件中配置下单
            程序的完整路径。

            :return:  成功返回True，失败返回False

        """
        if client.main is None:
            return client.connect()
        else:
            return True


    def trader_balance():
        # type: () -> Optional[dict]
        """
            返回当前账户资金股票信息

            通过操作交易软件客户端，获取当前账户的资金股票信息。

            :return:  返回字典类型，包括'资金余额', '冻结金额', '可用金额', '可取金额', '股票是在', '总资产', '持仓盈亏'等信息。

        """
        if trader_connect():
            return client.balance
        else:
            return None


    def trader_position():
        # type: () -> Optional[pd.DataFrame]
        """
            返回当前账户股票持仓信息

            通过操作交易软件客户端，获取当前账户的股票持仓信息。

            :return:  返回DataFrame类型，字段包括：'证券代码', '证券名称', '股票余额', '可用余额', '冻结数量', '成本价', '市价', '盈亏',
             '盈亏比例(%)', '市值', '当日买入', '当日卖出', '交易市场', '持股天数'等信息。

        """
        if trader_connect():
            return client.position
        else:
            return None


    def trader_buy(security, price, amount):
        # type: (str, float, int) -> Optional[int]
        """
            买入股票

            通过操作交易软件客户端，买入指定的股票。

            :param security: 股票代码
            :param price: 买入价格
            :param amount: 买入数量

            :return:  成功委托返回合同编号，失败则返回None

        """
        if trader_connect():
            if isinstance(security, str) and isinstance(price, float) and isinstance(amount, int):
                result = client.buy(security, price, amount)
                if result['success'] and 'entrust_no' in result.keys():
                    return result['entrust_no']
            else:
                log.error("trader_buy: 输入参数类型错误！")

        return None


    def trader_sell(security, price, amount):
        # type: (str, float, int) -> Optional[int]
        """
            卖出股票

            通过操作交易软件客户端，卖出指定的股票。

            :param security: 股票代码
            :param price: 卖出价格
            :param amount: 卖出数量

            :return:  成功委托返回合同编号，失败则返回None

        """
        if trader_connect():
            if isinstance(security, str) and isinstance(price, float) and isinstance(amount, int):
                result = client.sell(security, price, amount)
                if result['success'] and 'entrust_no' in result.keys():
                    return result['entrust_no']
            else:
                log.error("trader_sell: 输入参数类型错误！")

        return None


    def trader_entrusts():
        # type: () -> Optional[pd.DataFrame]
        """
            返回当日委托记录

            通过操作交易软件客户端，获取当前账户的当日委托记录信息。

            :return:  成功返回委托记录，字段包括： '委托时间','证券代码', '证券名称', '操作', '备注', '委托数量', '成交数量', '委托价格','成交均价', '撤单数量', '合同编号', '交易市场'等信息。

        """
        if trader_connect():
            return client.today_entrusts
        else:
            return None


    def trader_deal():
        # type: () -> Optional[pd.DataFrame]
        """
            返回当日成交记录

            通过操作交易软件客户端，获取当前账户的当日成交记录信息。

            :return:  成功返回委托记录，字段包括：'成交时间','证券代码','证券名称','操作','成交数量','成交均价','成交金额','合同编号','成交编号'等信息.

        """
        if trader_connect():
            return client.today_trades
        else:
            return None


    def trader_cancel(entrust_no=None):
        # type: (Optional[int]) -> bool
        """
            撤销当日委托

            通过操作交易软件客户端，撤销当日提交的委托订单。

            :param entrust_no: 委托合同编号，如果参数为None,则撤销当前所有委托

            :return:  成功返回True，失败返回False

        """
        # log.info(f"trader_cancel调用，参数entrust_no={entrust_no}")
        if trader_connect():
            if entrust_no:
                result = client.cancel_entrust(entrust_no)
            else:
                result = client.cancel_all_entrusts()

            return result['success']
        else:
            return False

else:
    """ 用于生成帮助文档 """
    def trader_connect():
        # type: () -> bool
        """
            连接交易软件客户端

            调用本函数连接已启动的交易软件客户端，本函数需在其他实盘操作函数前运行。为使qff成功连接交易软件，需要提前启动并登录交易软件，
            对于通用版同花顺下单程序，需要先手动登录一次：添加券商，填入账户号、密码、验证码，勾选“保存密码”，并在config文件中配置下单
            程序的完整路径。

            :return:  成功返回True，失败返回False

        """
        return False


    def trader_balance():
        # type: () -> Optional[dict]
        """
            返回当前账户资金股票信息

            通过操作交易软件客户端，获取当前账户的资金股票信息。

            :return:  返回字典类型，包括'资金余额', '冻结金额', '可用金额', '可取金额', '股票是在', '总资产', '持仓盈亏'等信息。

        """
        return None


    def trader_position():
        # type: () -> Optional[pd.DataFrame]
        """
            返回当前账户股票持仓信息

            通过操作交易软件客户端，获取当前账户的股票持仓信息。

            :return:  返回DataFrame类型，字段包括：'证券代码', '证券名称', '股票余额', '可用余额', '冻结数量', '成本价', '市价', '盈亏',
             '盈亏比例(%)', '市值', '当日买入', '当日卖出', '交易市场', '持股天数'等信息。

        """
        return None


    def trader_buy(security, price, amount):
        # type: (str, float, int) -> Optional[int]
        """
            买入股票

            通过操作交易软件客户端，买入指定的股票。

            :param security: 股票代码
            :param price: 买入价格
            :param amount: 买入数量

            :return:  成功委托返回合同编号，失败则返回None

        """
        return None


    def trader_sell(security, price, amount):
        # type: (str, float, int) -> Optional[int]
        """
            卖出股票

            通过操作交易软件客户端，卖出指定的股票。

            :param security: 股票代码
            :param price: 卖出价格
            :param amount: 卖出数量

            :return:  成功委托返回合同编号，失败则返回None

        """
        return None


    def trader_entrusts():
        # type: () -> Optional[pd.DataFrame]
        """
            返回当日委托记录

            通过操作交易软件客户端，获取当前账户的当日委托记录信息。

            :return:  成功返回委托记录，字段包括： '委托时间','证券代码', '证券名称', '操作', '备注', '委托数量', '成交数量', '委托价格','成交均价', '撤单数量', '合同编号', '交易市场'等信息。

        """
        return None


    def trader_deal():
        # type: () -> Optional[pd.DataFrame]
        """
            返回当日成交记录

            通过操作交易软件客户端，获取当前账户的当日成交记录信息。

            :return:  成功返回委托记录，字段包括：'成交时间','证券代码','证券名称','操作','成交数量','成交均价','成交金额','合同编号','成交编号'等信息.

        """
        return None


    def trader_cancel(entrust_no=None):
        # type: (Optional[int]) -> bool
        """
            撤销当日委托

            通过操作交易软件客户端，撤销当日提交的委托订单。

            :param entrust_no: 委托合同编号，如果参数为None,则撤销当前所有委托

            :return:  成功返回True，失败返回False

        """
        return False

