#!/bin/bash

# 定义颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # 恢复默认颜色

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}      Playwright 安装脚本${NC}"
echo -e "${BLUE}==============================================${NC}"

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}请使用 sudo 运行此脚本${NC}"
    exit 1
fi

# 安装必要的系统依赖
echo -e "${BLUE}[1/4] 安装系统依赖...${NC}"
apt update
apt install -y python3-venv python3-pip libwoff1 libopus0 libwebp6 libwebpdemux2 libenchant1c2a libgudev-1.0-0 libsecret-1-0 libhyphen0 libgdk-pixbuf2.0-0 libegl1 libnotify4 libxslt1.1 libevent-2.1-7 libgles2 libvpx6 libxcomposite1 libatk1.0-0 libatk-bridge2.0-0 libepoxy0 libgtk-3-0 libharfbuzz-icu0

# 创建Python虚拟环境
echo -e "${BLUE}[2/4] 创建Python虚拟环境...${NC}"
if [ -d "venv" ]; then
    echo -e "${YELLOW}虚拟环境已存在，将重新创建...${NC}"
    rm -rf venv
fi

python3 -m venv venv
source venv/bin/activate

# 安装Playwright
echo -e "${BLUE}[3/4] 安装Playwright...${NC}"
pip install playwright

# 安装浏览器
echo -e "${BLUE}[4/4] 安装Chromium浏览器...${NC}"
python -m playwright install chromium

echo -e "${GREEN}安装完成！${NC}"
echo -e "${YELLOW}使用以下命令激活虚拟环境:${NC}"
echo -e "    source venv/bin/activate"
echo -e "${BLUE}==============================================${NC}" 