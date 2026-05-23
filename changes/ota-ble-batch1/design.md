# 第一批修复 Design

## 范围

本批只收敛 OTA 主链路与 BLE/WiFi 互斥的确定性缺陷，保持最小修改面，避免和第二批 Web 健壮性修复交叉。

## 设计要点

### 1. OTA 模块导入修复

- 在 `ota_updater.py` 顶部显式导入 `from micropython import const`
- 不改变 `_MAX_RESPONSE_SIZE` 的常量定义方式
- 目标是保证模块在 MicroPython 环境下可直接导入

### 2. OTA 版本清单地址修复

- 将 `config.OTA_VERSION_URL` 从带版本 tag 的路径改为稳定入口
- 稳定入口应始终指向当前仓库默认分支上的 `releases/latest/version.json`
- 目标是让旧版本设备也能看到后续版本，而不是被固定在历史 tag

建议目标格式：

```text
https://gitee.com/mengen4jv/esp32-power/raw/master/releases/latest/version.json
```

如果仓库默认分支已统一为 `main`，则需要同步确认发布脚本、README 和规则文档是否一致。

### 3. BLE 停用结果校验修复

- `WiFiManager.start()` 不再直接无条件：
  - `self.ble_meter.deactivate()`
  - `self.ble_disabled = True`
- 改为统一复用 `_disable_ble()` 的结果
- 只有在 `_disable_ble()` 返回成功时，才允许继续启动 WiFi AP
- 如果 BLE 停用失败：
  - 记录错误日志
  - 终止 WiFi 启动流程
  - 保持 `ble_disabled` 与真实硬件状态一致

## 行为约束

- 保持 ESP32-C3 的 WiFi/BLE 互斥原则不变
- 不新增 WiFi 与 BLE 并发共存路径
- 不引入新的持久化格式变化
- 不改 OTA 下载、CRC 校验、回滚逻辑

## 文档同步要求

由于本批会修改 OTA 地址策略和 BLE 互斥启动行为，必须同步：

- `README.md`
- `specs/wifi-manager.md`
- `specs/ota-updater.md`
- `CHANGELOG.md`

## 验证策略

### 静态验证

- `py_compile` 全部相关 `.py` 文件通过
- `ota_updater.py` 可正常导入
- `WiFiManager.start()` 中不存在“先标记已停用，再判断结果”的路径

### 设备验证

- BLE 正常启动
- 长按确认进入配网后，BLE 先停用，再启动 WiFi AP
- 若人为模拟 BLE 停用失败，WiFi 不应继续启动
- 设备可正常检查 OTA 版本清单

## 第二批预留内容

以下内容明确留到第二批，避免本批过大：

- `wifi_manager.py` 的 HTTP 请求体分段读取
- OTA 检查失败后的重试/刷新机制
- `power_data.py` 配置恢复范围校验
- 状态字段结构化和线程状态收敛
