# Mercari监控系统 - 生产环境部署说明

## 生产环境特性

在生产环境下，系统具有以下特点：

1. 不在终端打印日志信息，所有日志保存到`mercari_monitor.log`文件中
2. 不保存调试文件（HTML、截图等）以节省磁盘空间
3. WebDriver管理器不显示详细输出
4. Flask开发服务器不显示请求信息

## 启动和管理

### 启动服务

```bash
./start_production.sh
```

此命令会在后台启动服务，并将进程ID保存到`mercari.pid`文件中。

### 检查服务状态

```bash
ps -p $(cat mercari.pid) || echo "服务未运行"
```

### 停止服务

```bash
kill $(cat mercari.pid)
```

### 查看日志

```bash
tail -f mercari_monitor.log
```

## 故障排除

如果服务未能正常启动，可以查看`start_log.txt`文件获取启动时的错误信息：

```bash
cat start_log.txt
```

## 注意事项

1. 在生产环境下，调试功能被禁用，错误信息会更简洁
2. 如需进行调试，请将`FLASK_ENV`环境变量设置为其他值
3. 确保`mercari_monitor.log`文件有足够的写入权限 