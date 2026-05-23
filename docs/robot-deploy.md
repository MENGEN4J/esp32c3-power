# Robot 部署指南

> 本文件供 AI 助手阅读，定义自动部署流程。项目已封装一键脚本，优先使用脚本部署。

---

## 一键脚本

| 场景 | 脚本 | 命令 |
|------|------|------|
| 代码部署 | `deploy.sh` | `bash scripts/deploy.sh` |
| 固件烧录 | `flash_firmware.sh` | `bash scripts/flash_firmware.sh -e` |
| 固件编译 | `build_firmware.sh` | `bash scripts/build_firmware.sh` |
| 串口扫描 | `common.sh` | `bash scripts/common.sh scan` |
| 跨平台入口 | `bikepower.sh` | `bash scripts/bikepower.sh deploy/flash/build/scan` |

Windows 使用 `deploy.ps1`：`.\scripts\deploy.ps1`

---

## deploy.sh 执行流程

脚本自动完成 7 步：扫描串口 → 释放占用 → 验证连接 → BOM/语法检查 → 上传文件 → 启动运行 → 日志分析自修复

### 关键注意事项

1. **部署前清理旧文件** — 删除设备上的旧 main.py 等残留文件，防止上电自动运行导致 BLE 硬件状态残留
2. **BOM 检查** — 自动检测并移除 UTF-8 BOM（`EF BB BF`），避免 MicroPython NameError
3. **语法检查** — `py_compile.compile('app.py', doraise=True)` 验证代码正确性
4. **日志监控** — 启动后监控 N 秒，检测异常并自动修复（最多重试 2 次）

---

## 异常模式与修复策略

| 异常模式 | 原因 | 修复策略 |
|----------|------|---------|
| `NameError` | BOM 字符 / 语法错误 | 移除 BOM，检查语法，重新上传 |
| `ImportError` | 缺少模块 | 检查固件版本，确认模块可用 |
| `OSError: ENOMEM` | 内存不足 | 减少缓冲区大小，优化代码 |
| `[Errno 5] EIO` | BLE 硬件状态残留 | 物理断电重启设备 |
| `[Errno 19] ENODEV` | BLE 射频控制器未就绪 | 物理断电重启设备 |
| `WiFi启动失败` | 射频冲突 | 先关闭 BLE 再启动 WiFi |
| `Traceback` | 运行时错误 | 分析错误行号，修复代码后重新部署 |

---

## 本地监控页面

`web/monitor.html` 通过 Web Bluetooth API 直接连接 ESP32 BLE 设备，需在 Chrome/Edge 中打开。

### 启动方式

部署/烧录脚本完成后会自动启动 HTTP 服务器并打开监控页面。

手动启动：
```bash
cd web && python3 -m http.server 8765
# 浏览器访问 http://localhost:8765/monitor.html
```

> ⚠️ Trae IDE 内置预览不支持 Web Bluetooth API，必须使用外部 Chrome/Edge 浏览器。

---

## 部署检查清单

- [ ] 串口连接正常（自动扫描）
- [ ] 文件上传成功
- [ ] 程序启动无 Traceback
- [ ] 蓝牙广播正常（日志含 "蓝牙功率计已启动"）
- [ ] 内存 free > 80KB
- [ ] 测试报告已生成并打开
