# Mercari监控系统 - 前端部署与启动说明

本文档提供关于如何启动、管理和停止Mercari监控系统前端和后端的说明。

## 系统要求

- Node.js 14.0 或更高版本
- npm 6.0 或更高版本
- Python 3.6 或更高版本

## 可用脚本

本系统提供了三个主要脚本来管理应用程序：

1. `start_all.sh` - 同时启动前端和后端服务
2. `start_frontend.sh` - 仅启动前端服务
3. `stop_all.sh` - 停止所有服务

## 启动方式

### 开发模式

在开发模式下启动系统（前端使用热重载，后端在后台运行）：

```bash
./start_all.sh
```

开发模式下，前端将在前台运行，您可以按下`Ctrl+C`来停止前端服务。要停止后端服务，请使用：

```bash
kill $(cat mercari.pid)
```

或者直接运行：

```bash
./stop_all.sh
```

### 生产模式

在生产模式下启动系统（前端和后端都在后台运行）：

```bash
./start_all.sh production
```

或者简写为：

```bash
./start_all.sh prod
```

要停止所有服务，请运行：

```bash
./stop_all.sh
```

## 单独启动前端

如果您希望单独启动前端（例如后端已经运行），可以使用以下命令：

### 开发模式
```bash
./start_frontend.sh
```

### 生产模式
```bash
./start_frontend.sh production
```

## 访问应用

- 前端地址：http://localhost:3000
- 后端API：http://localhost:5000

## 日志文件

- 开发模式后端日志：`backend_dev.log`
- 生产模式后端日志：`mercari_monitor.log`
- 生产模式前端日志：`frontend_prod.log`

## 故障排除

如果在启动过程中遇到问题，请检查对应的日志文件：

1. 后端启动失败 - 检查 `start_log.txt` 或 `backend_dev.log`
2. 前端启动失败 - 检查 `frontend_prod.log`
3. 找不到Node或npm - 确保Node.js已正确安装

如果前端无法连接后端API，请确保：

1. 后端服务正在运行 (`ps -p $(cat mercari.pid)`)
2. 后端服务运行在 http://localhost:5000
3. package.json 中的 "proxy" 设置为 "http://localhost:5000" 