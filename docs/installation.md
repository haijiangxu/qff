#  安装指导

## 重要提示

1. 目前 [OpenQFF] 仅支持 64 位版本的操作系统安装和使用;
2. 目前 [OpenQFF] 仅支持 [Python](https://www.python.org/) 3.7(64 位) 及以上版本, 这里推荐 [Python](https://www.python.org/) 3.8.13(64 位) 版本;
3. [OpenQFF] 推荐安装最新版本的 [Anaconda (64 位)](https://www.anaconda.com/), 可以解决大部分环境配置问题;
4. 对于熟悉容器技术的小伙伴, 可以安装 Docker 使用, 指导教程如下: [OpenQFF Docker 部署].

## 安装 [OpenQFF]


### 通用安装

```
pip install openqff  --upgrade
```


### 国内安装-Python

```
pip install openqff -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host=mirrors.aliyun.com  --upgrade
```

### 国内安装-Anaconda

```
pip install openqff -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host=mirrors.aliyun.com  --user  --upgrade
```

## 升级 [OpenQFF](https://github.com/akfamily/akshare)

P.S. **由于目前版本更新迭代频繁, 请在使用 [OpenQFF](https://github.com/akfamily/akshare) 前先升级, 命令如下所示**

```
pip install openqff --upgrade -i https://pypi.org/simple
```


## 安装报错解决方案

### 1. 安装 lxml 库失败的错误

- 安装 wheel, 需要在 Windows 的命令提示符中运行如下命令:

```
pip install wheel
```

- 在[这里下载](http://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml3)与您的 Python 版本对应的 **.whl** 文件, **注意别改文件名!**

以下提供 64 位电脑的版本, 所以下载对应的 64 位就可以, 点击如下链接也可以下载:

1. [lxml‑4.5.0‑cp36‑cp36m‑win_amd64.whl](https://jfds-1252952517.cos.ap-chengdu.myqcloud.com/akshare/software/lxml/lxml-4.5.0-cp36-cp36m-win_amd64.whl)
2. [lxml‑4.5.0‑cp37‑cp37m‑win_amd64.whl](https://jfds-1252952517.cos.ap-chengdu.myqcloud.com/akshare/software/lxml/lxml-4.5.0-cp37-cp37m-win_amd64.whl)
3. [lxml‑4.5.0‑cp38‑cp38‑win_amd64.whl](https://jfds-1252952517.cos.ap-chengdu.myqcloud.com/akshare/software/lxml/lxml-4.5.0-cp38-cp38-win_amd64.whl)

- 进入 **.whl** 所在的文件夹, 执行命令即可完成安装, 如下

```
pip install 带后缀的完整路径和文件名
```

### 2. 安装超时的错误

1.大致报错如下, 出现关键词 **amt** :

```
Traceback (most recent call last):
File "/home/xiaoduc/.pyenv/versions/3.7.3/lib/python3.7/site-packages/pip/_vendor/requests/packages/urllib3/response.py", line 228, in _error_catcher
yield
File "/home/xiaoduc/.pyenv/versions/3.7.3/lib/python3.7/site-packages/pip/_vendor/requests/packages/urllib3/response.py", line 310, in read
data = self._fp.read(amt)
File "/home/xiaoduc/.pyenv/versions/3.7.3/lib/python3.7/site-packages/pip/_vendor/cachecontrol/filewrapper.py", line 49, in read
data = self.__fp.read(amt)
```

2.解决方案如下:

方法一

```
pip --default-timeout=100 install -U openqff
```

方法二

使用全局代理解决

### 3. 拒绝访问错误

1.大致报错如下, 出现关键词 **拒绝访问** :

```
Could not install packages due to an EnvironmentError: [Errno 13] Permission denied: '/Users/mac/Anaconda/anaconda3/lib/python3.7/site-packages/cv2/__init__.py'
Consider using the `--user` option or check the permissions.
```

2.解决方案如下:

方法一

```
pip install openqff --user
```

方法二

使用管理员权限(右键单击选择管理员权限)打开 Anaconda Prompt 进行安装

### 4. 提示其他的错误

- 方法一: 确认并升级您已安装 64 位的 **Python3.7** 及以上版本
- 方法二: 使用 conda 的虚拟环境来安装, 详见 **[OpenQFF]环境配置** 板块的内容
