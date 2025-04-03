# Playwright爬虫说明

本项目使用Playwright进行网页内容获取，提高爬虫的稳定性和效率。

## 安装说明

### 1. 使用安装脚本（推荐）

我们提供了一个安装脚本以简化安装过程：

```bash
sudo ./install_playwright.sh
```

此脚本将：
- 安装必要的系统依赖
- 创建Python虚拟环境
- 安装Playwright
- 安装Chromium浏览器

### 2. 手动安装

如果您希望手动安装，请按照以下步骤操作：

```bash
# 安装python3-venv
sudo apt update
sudo apt install -y python3-venv python3-pip

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装Playwright
pip install playwright

# 安装浏览器
python -m playwright install chromium
```

## 使用说明

安装完成后，您需要激活虚拟环境才能使用Playwright：

```bash
source venv/bin/activate
```

然后启动监控系统：

```bash
# 开发模式
./start_all.sh

# 生产模式
./start_all.sh production
```

## 代码工作原理

代码使用Playwright执行网页抓取：

1. 通过异步API控制无头浏览器访问目标网站
2. 模拟真实用户行为，如随机滚动、等待页面加载
3. 在生产环境中只记录必要的日志信息

## 故障排除

### Playwright安装失败

如果您在安装Playwright时遇到问题，可以尝试：

```bash
# 检查Python版本
python3 --version  # 应该是3.7或更高版本

# 手动安装依赖
sudo apt install -y libwoff1 libopus0 libwebp6 libwebpdemux2 libenchant1c2a libgudev-1.0-0 libsecret-1-0 libhyphen0 libgdk-pixbuf2.0-0 libegl1 libnotify4 libxslt1.1 libevent-2.1-7 libgles2 libvpx6 libxcomposite1 libatk1.0-0 libatk-bridge2.0-0 libepoxy0 libgtk-3-0 libharfbuzz-icu0

# 使用系统包管理器安装
sudo apt install -y python3-playwright
```

### 浏览器启动失败

如果浏览器无法启动，您可能需要安装额外的系统依赖：

```bash
# 安装所有依赖
sudo apt install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2
```

## Playwright优势

| 特性 | 说明 |
|------|------|
| 速度 | 比Selenium更快的页面加载和执行速度 |
| 稳定性 | 更少的超时和崩溃问题 |
| 自动等待 | 内置智能等待功能，减少显式等待代码 |
| 网络拦截 | 支持拦截和修改网络请求 |
| 多标签页 | 原生支持多标签页和上下文管理 |
| 移动模拟 | 内置对移动设备的模拟支持 |
| 维护状态 | 由微软积极维护的现代爬虫框架 |
| API | 简洁一致的异步API设计 | 