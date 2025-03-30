#!/bin/bash

# 定义颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # 恢复默认颜色

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}      Mercari监控系统 - 停止脚本${NC}"
echo -e "${BLUE}==============================================${NC}"

# 停止后端服务
echo -e "${YELLOW}[1/2] 停止后端服务...${NC}"
if [ -f "mercari.pid" ]; then
    BACKEND_PID=$(cat mercari.pid)
    if ps -p $BACKEND_PID > /dev/null; then
        kill $BACKEND_PID
        echo -e "${GREEN}后端服务(PID: $BACKEND_PID)已停止${NC}"
    else
        echo -e "${YELLOW}后端服务(PID: $BACKEND_PID)不在运行${NC}"
    fi
    rm mercari.pid
else
    echo -e "${YELLOW}没有找到后端PID文件${NC}"
    # 尝试查找可能的Python进程
    PYTHON_PIDS=$(ps aux | grep "python3 index.py" | grep -v grep | awk '{print $2}')
    if [ ! -z "$PYTHON_PIDS" ]; then
        echo -e "${YELLOW}找到可能的后端进程：$PYTHON_PIDS${NC}"
        kill $PYTHON_PIDS
        echo -e "${GREEN}已尝试停止这些进程${NC}"
    fi
fi

# 停止前端服务
echo -e "${YELLOW}[2/2] 停止前端服务...${NC}"
if [ -f "frontend.pid" ]; then
    FRONTEND_PID=$(cat frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null; then
        kill $FRONTEND_PID
        echo -e "${GREEN}前端服务(PID: $FRONTEND_PID)已停止${NC}"
    else
        echo -e "${YELLOW}前端服务(PID: $FRONTEND_PID)不在运行${NC}"
    fi
    rm frontend.pid
else
    echo -e "${YELLOW}没有找到前端PID文件${NC}"
    # 尝试查找可能的Node进程
    NODE_PIDS=$(ps aux | grep "node.*serve -s build" | grep -v grep | awk '{print $2}')
    if [ ! -z "$NODE_PIDS" ]; then
        echo -e "${YELLOW}找到可能的前端进程：$NODE_PIDS${NC}"
        kill $NODE_PIDS
        echo -e "${GREEN}已尝试停止这些进程${NC}"
    fi
fi

echo -e "${GREEN}所有服务已停止${NC}"
echo -e "${BLUE}==============================================${NC}" 