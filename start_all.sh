#!/bin/bash

# 定义颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # 恢复默认颜色

# 获取当前目录
CURRENT_DIR=$(pwd)

# 检查参数
MODE="development"  # 默认为开发模式
if [ "$1" = "prod" ] || [ "$1" = "production" ]; then
    MODE="production"
    export FLASK_ENV=production
else
    unset FLASK_ENV
fi

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}      Mercari监控系统 - 启动脚本${NC}"
echo -e "${BLUE}==============================================${NC}"
echo -e "${YELLOW}启动模式:${NC} $MODE"
echo -e "${YELLOW}当前目录:${NC} $CURRENT_DIR"
echo

# 启动后端
echo -e "${BLUE}[1/2] 启动后端服务...${NC}"
if [ "$MODE" = "production" ]; then
    ./start_production.sh
    BACKEND_PID=$(cat mercari.pid)
    echo -e "${GREEN}后端服务已在后台启动，进程ID: ${BACKEND_PID}${NC}"
else
    # 开发模式下，在后台启动
    echo -e "${YELLOW}以开发模式启动后端...${NC}"
    python3 index.py > backend_dev.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > mercari.pid
    echo -e "${GREEN}后端服务已在后台启动，进程ID: ${BACKEND_PID}${NC}"
    echo -e "${YELLOW}日志保存在: backend_dev.log${NC}"
fi

# 等待后端启动
echo -e "${YELLOW}等待后端服务启动...${NC}"
sleep 3

# 检查后端是否成功启动
if ! ps -p $BACKEND_PID > /dev/null; then
    echo -e "${RED}后端服务启动失败！${NC}"
    echo -e "${YELLOW}请检查日志文件以获取更多信息${NC}"
    if [ "$MODE" = "production" ]; then
        echo -e "    cat start_log.txt"
    else
        echo -e "    cat backend_dev.log"
    fi
    exit 1
fi

echo -e "${GREEN}后端服务已成功启动在 http://localhost:5000${NC}"
echo

# 启动前端
echo -e "${BLUE}[2/2] 启动前端服务...${NC}"
if [ "$MODE" = "production" ]; then
    # 后台启动前端
    ./start_frontend.sh production
else
    # 前台启动前端开发服务器
    echo -e "${YELLOW}前端将在前台启动，按Ctrl+C可以停止前端服务${NC}"
    echo -e "${YELLOW}如果要停止后端服务，请使用:${NC} kill $(cat mercari.pid)"
    echo
    ./start_frontend.sh
fi

# 前端开发模式在前台运行，所以下面的代码不会执行
# 仅在生产模式中添加完整关闭系统的提示
if [ "$MODE" = "production" ]; then
    echo
    echo -e "${BLUE}==============================================${NC}"
    echo -e "${GREEN}全部服务已成功启动!${NC}"
    echo -e "${YELLOW}前端地址:${NC} http://localhost:3000"
    echo -e "${YELLOW}后端API:${NC} http://localhost:5000"
    echo
    echo -e "${YELLOW}要停止所有服务，请运行:${NC}"
    echo -e "    kill \$(cat mercari.pid) && kill \$(cat frontend.pid)"
    echo -e "${BLUE}==============================================${NC}"
fi 