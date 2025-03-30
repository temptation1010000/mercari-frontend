#!/bin/bash

# 设置生产环境变量
export FLASK_ENV=production

# 启动应用，将输出重定向到日志文件
echo "正在以生产模式启动Mercari监控系统..."
python3 index.py > start_log.txt 2>&1 &

# 显示进程ID
PID=$!
echo "应用已启动，进程ID: $PID"
echo $PID > mercari.pid

echo "可以通过以下命令停止服务："
echo "kill \$(cat mercari.pid)"
echo "启动日志将保存在 start_log.txt 文件中" 