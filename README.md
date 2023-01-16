# QFF: Quantize Financial Framework

![PyPI](https://img.shields.io/pypi/v/qff)
![Python](https://img.shields.io/pypi/pyversions/qff.svg)
![Docker Image Version (latest by date)](https://img.shields.io/docker/v/haijiangxu/qff)
[![Documentation Status](https://readthedocs.org/projects/qff/badge/?version=latest)](https://qff.readthedocs.io/zh_CN/latest/)



**QFF** is a Python package of quantitative financial framework, which is used to provide a localized backtesting and simulation trading environment for individuals, so that users can focus more on trading strategy writing.

## Main Features
Here are just a few of the things that QFF does well:
+ Provide one-stop solutions such as data crawling, data cleaning, data storage, strategy writing, strategy analysis, strategy backtest and simulated trade.
+ Provide graceful interface for strategy writing (similar to JoinQuant), facilitate users to get started quickly.
+ Provide a local running environment to improve the strategy running efficiency.
+ Provide rich interfaces to obtain free stock data, such as fundamental data, real-time and historical market data etc.
+ Provide practical auxiliary functions to simplify strategy writing, such as indicator calculation, trading system framework, etc.

## Installation
### Source code
The source code is currently hosted on GitHub at: https://github.com/haijiangxu/qff

### General

```shell
pip install qff --upgrade
```

### China

```shell
pip install qff -i http://mirrors.aliyun.com/pypi/simple/ --upgrade
```

### Docker

Docker image for the QFF is at https://hub.docker.com/r/haijiangxu/qff.

#### pull docker image
```shell
docker pull qff
```

#### run docker image
```shell
docker run -d -v /root/xxxx:/root/work -p 8765:8765  qff
```



## Document

Documentation for the latest Current release is at https://qff.readthedocs.io/zh_CN/latest/. 


## Contribution
QFF is still under developing, feel free to open issues and pull requests:

+ Report or fix bugs
+ Require or publish interface
+ Write or fix documentation
+ Add test cases
  

## Statement

1. QFF only supports stocks, but not other financial products such as futures, funds, foreign exchange, bonds, cryptocurrencies, etc.
2. All data provided by QFF is just for academic research purpose.
3. The data provided by QFF is for reference only and does not constitute any investment proposal.
4. Any investor based on QFF research should pay more attention to data risk.
5. QFF will insist on providing open-source financial data.
6. Based on some uncontrollable factors, some data interfaces in QFF may be removed.
7. Please follow the relevant open-source protocol used by QFF.

## Acknowledgement

Special thanks [QUANTAXIS](https://github.com/QUANTAXIS/QUANTAXIS) for the opportunity of learning from the project;

Special thanks [AKShare](https://github.com/akfamily/akshare) for the opportunity of learning from the project;

Special thanks [JoinQuant](https://www.joinquant.com) for the opportunity of learning from the project;


