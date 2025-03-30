#!/bin/bash

# 定义颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # 恢复默认颜色

# 获取当前目录
CURRENT_DIR=$(pwd)

# 检查node和npm是否已安装
if ! command -v node &> /dev/null; then
    echo -e "${RED}错误: Node.js未安装，请先安装Node.js${NC}"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}错误: npm未安装，请先安装npm${NC}"
    exit 1
fi

# 显示Node和npm版本
echo -e "${YELLOW}Node版本:${NC} $(node -v)"
echo -e "${YELLOW}npm版本:${NC} $(npm -v)"

# 检查参数
MODE="development"  # 默认为开发模式
if [ "$1" = "prod" ] || [ "$1" = "production" ]; then
    MODE="production"
fi

echo -e "${YELLOW}启动模式:${NC} $MODE"

# 检查node_modules目录是否存在，不存在则安装依赖
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}正在安装依赖...${NC}"
    npm install
fi

# 根据模式启动应用
if [ "$MODE" = "production" ]; then
    # 生产模式 - 构建并使用静态文件服务器
    echo -e "${GREEN}正在构建生产版本...${NC}"
    npm run build

    # 检查serve是否已安装，没有则全局安装
    if ! command -v serve &> /dev/null; then
        echo -e "${YELLOW}正在安装serve...${NC}"
        npm install -g serve
    fi

    # 使用serve提供静态文件服务
    echo -e "${GREEN}正在启动静态文件服务器...${NC}"
    PORT=3000 serve -s build > frontend_prod.log 2>&1 &

    # 保存PID
    FRONTEND_PID=$!
    echo $FRONTEND_PID > frontend.pid
    echo -e "${GREEN}前端服务已在后台启动，进程ID: ${FRONTEND_PID}${NC}"
    echo -e "${GREEN}访问地址: http://localhost:3000${NC}"
    echo -e "${YELLOW}日志保存在: frontend_prod.log${NC}"
    echo -e "${YELLOW}可以通过以下命令停止服务:${NC}"
    echo -e "    kill \$(cat frontend.pid)"
else
    # 开发模式 - 直接使用react-scripts启动开发服务器
    echo -e "${GREEN}正在启动开发服务器...${NC}"
    echo -e "${YELLOW}按Ctrl+C可以停止服务${NC}"
    
    # 转到前台运行开发服务器
    npm start
fi 