# 第一批修复 Proposal

> 状态：规划中 | 目标：先修 OTA 主链路和 BLE/WiFi 互斥关键问题

## 背景

本轮项目审查发现，当前系统存在 3 个会直接影响升级链路或配网链路的高优先级问题：

1. `ota_updater.py` 类定义使用 `const()`，但文件未导入 `micropython.const`
2. `config.py` 中 `OTA_VERSION_URL` 绑定到版本 tag，导致旧版本设备无法持续发现后续新版本
3. `wifi_manager.py` 启动 WiFi AP 时未校验 BLE 停用结果，可能在 BLE 未真正关闭时继续启动 WiFi

这些问题会直接影响：

- 设备能否正常导入 OTA 模块并启动
- 旧版本设备能否看到新版本更新
- ESP32-C3 上 WiFi/BLE 互斥链路是否可靠

## 本批目标

第一批只修复 OTA 与 BLE 互斥主链路，不处理 Web 请求体截断、OTA 重试、配置恢复校验等第二批内容。

本批完成后应达到：

- OTA 模块可稳定导入，不因 `const()` 缺失直接崩溃
- OTA 版本清单地址使用稳定入口，旧版本设备可继续发现后续版本
- 启动 WiFi 前必须确认 BLE 已停用，否则拒绝继续进入配网链路

## 涉及文件

- `ota_updater.py`
- `config.py`
- `wifi_manager.py`
- `README.md`
- `specs/wifi-manager.md`
- `specs/ota-updater.md`
- `CHANGELOG.md`

## 不在本批范围

- `wifi_manager.py` 的 HTTP 大请求体读取
- OTA 检查失败后的重试策略
- `power_data.py` 的配置恢复范围校验
- 更细的线程状态结构化重构
