# 安装说明

![Python](https://img.shields.io/pypi/pyversions/qff.svg)

```{admonition} 注解
- 如果执行 `pip install`安装依赖库网络速度比较慢的话，推荐使用 
`pip install -i https://pypi.douban.com/simple` 国内镜像来加速。
- 为避免因为环境问题出现安装失败，建议您使用虚拟环境安装，Python虚拟环境有
venv, conda, pipenv等，请参考相关[教程](https://cloud.tencent.com/developer/article/2124483)。
- 推荐使用 `python -m venv venv` 创建虚拟环境，并执行 `venv\Scripts\activate` 激活运行。
```
## 安装库

以下命令将安装 QFF 及其依赖项。

```bash
$ pip install qff
```

QFF依赖于许多其他Python包，使用软件包安装工具像PIP或Conda等将确保安装必要的依赖软件包，您可以使用包管理器命令 `pip show qff` 查看依赖项，
更多信息可以在其 [PyPI](https://pypi.org/project/qff/) 页面上找到。

P.S. 由于目前版本更新迭代频繁, 请在使用 QFF 前先升级, 命令如下所示:

```bash
$ pip install qff --upgrade -i https://pypi.douban.com/simple
```

查看 QFF 是否安装成功可以通过如下方式:

```bash
$ qff --version
```

## 数据准备
```{admonition} 注解

QFF框架提供所有数据均从互联网上抓取，并经过专业清洗保存在用户**自己搭建的数据库服务器中**，
这样设计的优点是增强数据的可靠性，数据永久保存在用户自己手上，避免后期因为网站更新造成
数据缺失或格式不匹配等问题。

因此，在QFF正常使用前，需进行数据库的安装配置，以及股票数据的下载和更新。

```


### 数据库安装

QFF使用的是MongoDB数据库，它是一个高性能、无模式、文档型的NoSQL数据库。

先进入mongodb的官网[MongoDB](https://www.mongodb.com/try/download/community)下载，选择要下载的版本以及系统，MongoDB数据库安装教程参考如下：

| 操作系统平台                                                                |
| --------------------------------------------------------------------- |
| [Windows](https://www.runoob.com/mongodb/mongodb-window-install.html) |
| [Linux](https://www.runoob.com/mongodb/mongodb-linux-install.html)    |
| [Mac OS](https://www.runoob.com/mongodb/mongodb-osx-install.html)     |

**我们强烈推荐您直接拉取[Docker镜像](mongoimage)安装使用MongoDB数据库。**

### 数据库配置

MongoDB数据库安装成功后，需设置QFF与数据库的连接参数，设置命令如下：

```bash
$ qff config set MONGODB.uri=mongodb://xxx.xxx.xxx.xxx:27017
```

如果MongoDB数据库设置了用户名密码，则需配置相关认证信息：

```bash
$ qff config set MONGODB.uri=mongodb://admin:******@xxx.xxx.xxx.xxx:27017/?authSource=admin&authMechanism=SCRAM-SHA-256
```

另外，可使用命令`qff config list` 查看QFF所有配置信息。

```{important}
**注：如果MongoDB数据库安装在本机，则无需配置连接参数，QFF使用默认连接参数。**
```




### 数据下载

QFF在正常使用前需下载历史数据，执行方法如下所示：

```bash
$ qff save all
```

执行该命令将从互联网下载所有股票、指数、ETF基金的历史行情数据和基本面数据等，并保存至您安装的MongoDB数据库中，根据您计算机和网络性能，下载时间将超过5个小时。

您也可以通过执行`qff save` 命令选择下载您所需要的数据类别。

```{eval-rst} 
       ===========================  ================================================
        qff save all                 保存/更新所有数据                                   
        qff save day                 保存/更新股票日数据、指数日数据、ETF日数据                     
        qff save min                 保存/更新股票分钟数据、指数分钟数据、ETF分钟数据                  
        qff save stock_list          保存/更新股票列表数据                                 
        qff save stock_day           保存/更新股票日线数据                                 
        qff save index_day           保存/更新指数日线数据                                 
        qff save etf_day             保存/更新ETF日线数据                                
        qff save stock_min           保存/更新股票分钟数据                                 
        qff save index_min           保存/更新指数分钟数据                                 
        qff save etf_min             保存/更新ETF分钟数据                                
        qff save stock_xdxr          保存/更新日除权除息数据                                
        qff save stock_block         保存/更新板块股票数据                                 
        qff save report              保存/更新股票财务报表                                 
        qff save valuation           保存/更新股票市值数据                                 
        qff save mtss                保存/更新融资融券数据                                 
        qff save index_stock         保存/更新指数成分股信息                                
        qff save init_info           初始化股票列表、指数列表、ETF列表                          
        qff save init_name           初始化股票历史更名数据                                 
        qff save save_delist         保存退市股票的日数据和分钟数据                             
       ===========================  ================================================
```
```{note}
1. 如果您打算使用 `qff save xxxx` 分项下载数据，则在第一次初始化过程时，务必首先执行 `qff save init_info` 命令。
2. 如果您需要查询股票历史更名数据，需手工执行 `qff save init_name`，否则将使用最近的股票名称，影响回测时ST股的判断。
```
### 数据自动更新

通过配置数据自动更新服务，QFF可以自动下载更新每日股市收盘后最新数据。指令`qff save all`具有数据更新功能，
您需要在您使用的操作系统中，自行配置定时任务，定时任务开始时间建议16:00，执行周期即每个工作日。

**我们强烈推荐您使用[QFF Docker镜像](qffimage)进行数据自动更新。**

