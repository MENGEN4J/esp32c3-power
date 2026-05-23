# BLE 服务规格

> Source of Truth：`ble_service.py` 的行为规格
> AI 修改 BLE 模块时，先加载此文件确认当前行为

---

## 初始化

- GIVEN 设备上电启动
- WHEN `SimpleBLEPowerMeter(device_name)` 被调用
- THEN 创建 `bluetooth.BLE()` 对象
- THEN 重试激活最多 3 次（间隔 500ms）
- THEN 设置 GAP 名称 = device_name，MTU = 69
- THEN 注册中断回调 `_irq`
- THEN 注册 Cycling Power + Heart Rate 双 GATT 服务
- THEN 以 500ms 间隔开始广播
- THEN 若激活失败，抛出 OSError 触发 `machine.reset()`

## 广播

- GIVEN BLE 已激活
- WHEN 调用 `_start_advertising()`
- THEN 构造广播包：Flags(0x06) + Complete Name + 16-bit UUID(0x1818)
- THEN 以 `config.BLE_ADVERTISING_INTERVAL`(500ms) 间隔广播
- THEN 设置连接参数：min_interval=20ms, max_interval=40ms, supervision_timeout=400

## 连接管理

- GIVEN 设备正在广播
- WHEN 手机发起 BLE 连接
- THEN `_irq` 收到 `IRQ_CENTRAL_CONNECT` 事件
- THEN 若当前连接数 < `config.MAX_CONNECTIONS`(3)，添加到 connections 集合
- THEN 若当前连接数 >= 3，主动断开新连接

- GIVEN 手机已连接
- WHEN 手机断开 BLE 连接
- THEN `_irq` 收到 `IRQ_CENTRAL_DISCONNECT` 事件
- THEN 从 connections 集合移除
- THEN 自动重新开始广播

## 功率通知

- GIVEN 手机已连接 BLE
- WHEN 距上次通知 >= `config.BLE_NOTIFY_INTERVAL`(1000ms)
- THEN 功率值 clamp 到 [0, 2000]
- THEN 心率值 clamp 到 [60, 200]
- THEN 踏频值 clamp 到 [0, 120]
- THEN 写入 8 字节功率缓冲区（flags=0x0020, power小端序, crank_revolutions小端序, crank_time_1024小端序）
- THEN 写入 2 字节心率缓冲区（flags=0x00, hr）
- THEN 通过 `gatts_notify` 通知所有已连接设备
- THEN 若通知失败，移除失效连接

## 停用

- GIVEN BLE 正在运行
- WHEN 调用 `deactivate()`
- THEN 停止广播（`gap_advertise(None)`）
- THEN 断开所有已连接设备
- THEN 清空 connections 集合
- THEN 等待 200ms
- THEN 关闭 BLE（`ble.active(False)`）
- THEN 返回 True（成功）或 False（失败）

## WiFi 关闭后 BLE 恢复

- GIVEN WiFi 配网完成或超时
- WHEN `_shutdown_wifi()` 被调用
- THEN 关闭 WiFi AP 和 Web 服务器
- THEN 调用 `machine.reset()` 重启设备恢复 BLE
- NOTE ESP32-C3 上 WiFi 关闭后 BLE 可能无法在同一进程内重新激活，因此使用 `machine.reset()` 而非 `reactivate()`

## 数据格式

### 功率特征值（8 字节）

| 偏移 | 长度 | 含义 |
|------|------|------|
| 0-1 | 2B | Flags（0x0020 = 踏频数据存在） |
| 2-3 | 2B | 功率值（W，小端序） |
| 4-5 | 2B | 曲柄转数（小端序） |
| 6-7 | 2B | 曲柄时间（1/1024秒，小端序） |

### 心率特征值（2 字节）

| 偏移 | 长度 | 含义 |
|------|------|------|
| 0 | 1B | Flags（0x00 = UINT8 心率） |
| 1 | 1B | 心率值（BPM） |
