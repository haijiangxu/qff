FROM ubuntu:focal

MAINTAINER haijiangxu <haijiangxu@hotmail.com>

# 设置中文显示支持
ENV LANG=C.UTF-8
ENV MONGODB=localhost:27017

COPY init.sh /root/
COPY jupyter_lab_config.py /root/.jupyter/

ARG TZ=Asia/Shanghai
RUN set -x \
    && export DEBIAN_FRONTEND=noninteractive \
    && sed -i s@/archive.ubuntu.com/@/mirrors.aliyun.com/@g /etc/apt/sources.list \
    && apt update \
    && apt install -y apt-utils tzdata wget python3.8 python3-pip cron vim\
    && ln -s /usr/bin/python3.8 /usr/bin/python \
    && ln -sf /usr/share/zoneinfo/$TZ  /etc/localtime \
    && echo $TZ > /etc/timezone \
    && apt clean \
    && rm -rf /tmp/* /var/tmp/* /var/cache/* /usr/share/doc/* /usr/share/man/* /var/lib/apt/lists/*

RUN wget https://downloads.sourceforge.net/project/ta-lib/ta-lib/0.4.0/ta-lib-0.4.0-src.tar.gz \
    && tar xvf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib \
    && ./configure --prefix=/usr \
    && make \
    && make install \
    && cd .. \
    && rm -rf ta-lib \
    && rm ta-lib-0.4.0-src.tar.gz

RUN pip config set global.index-url http://pypi.douban.com/simple \
    && pip config set global.trusted-host pypi.douban.com \
    && pip install -U qff \
    && pip install ta_lib \
    && pip install jupyterlab jupyter-console jupyterlab-language-pack-zh-CN jupyterlab-drawio jupyterlab-code-formatter black isort jupyterlab-lsp 'python-lsp-server[all]'


RUN mkdir /root/work\
    && echo "00 16 * * mon-fri root python /usr/local/lib/python3.8/dist-packages/qff/store/update_all.py > /root/work/cron.log 2>&1" > /etc/cron.d/daily_update\
    && crontab /etc/cron.d/daily_update\
    && chmod +x /root/init.sh

EXPOSE 8888
WORKDIR /root
VOLUME /root/work

CMD ["bash", "/root/init.sh"]

