#!/bin/bash

# crontab任务在执行时读取不到环境变量，设置的MONGODB在cron任务中无效
sed -i "s|localhost|$MONGODB|" /usr/local/lib/python3.8/dist-packages/qff/tools/mongo.py

cron

jupyter lab --allow-root