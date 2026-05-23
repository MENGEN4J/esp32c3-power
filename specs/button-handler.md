# 按钮处理规格

> Source of Truth：`app.py` 的按钮事件处理行为规格
> AI 修改按钮逻辑时，先加载此文件确认当前行为

---

## 按钮硬件配置

- GPIO9，PULL_UP 模式
- 按下 = 低电平（0），释放 = 高电平（1）
- 检测方式：轮询（50ms 间隔），非中断

## LED 硬件配置

- GPIO12（合宙 ESP32-C3 板载 D4），高电平有效
- 输出模式：Pin.OUT

## LED 状态指示

| 状态 | LED 行为 | 含义 |
|------|---------|------|
| IDLE_NO_CONN | 慢闪（1s 亮 / 1s 灭） | BLE 广播中，等待连接 |
| CONNECTED | 常亮 | BLE 已连接，正常工作 |
| CONFIRM_WAIT | 快闪（200ms 亮 / 200ms 灭） | 等待二次确认进入配网 |
| WIFI_MODE | 熄灭 | WiFi 配网模式，BLE 已关闭 |

## 事件检测

- GIVEN 按钮状态从 1（释放）变为 0（按下）
- WHEN 检测到下降沿
- THEN 记录按下时间 `btn_press_time = current_time`
- THEN 若处于 CONFIRM_WAIT 状态，立即执行二次确认（进入配网模式）

- GIVEN 按钮状态从 0（按下）变为 1（释放）
- WHEN 检测到上升沿
- THEN 计算按住时长 `press_duration = ticks_diff(current_time, btn_press_time)`
- THEN 根据时长判断操作类型

## 操作判断（释放时判断）

| 操作 | 按住时长 | 动作 |
|------|---------|------|
| 短按 | < 300ms | `power_engine.adjust_power(-10)` 功率-10W |
| 中按 | 300ms ~ 2000ms | `power_engine.adjust_power(10)` 功率+10W |
| 长按 | >= 2000ms | 进入二次确认窗口（LED 快闪 3 秒） |

## 短按（功率 -10W）

- GIVEN 按住时长 < 300ms
- WHEN 按钮释放
- THEN 调用 `power_engine.adjust_power(-10)`
- THEN 功率值 clamp 到 [0, 2000]
- THEN 若值变化，自动持久化到 `power_config.json`

## 中按（功率 +10W）

- GIVEN 按住时长 >= 300ms 且 < 2000ms
- WHEN 按钮释放
- THEN 调用 `power_engine.adjust_power(10)`
- THEN 功率值 clamp 到 [0, 2000]
- THEN 若值变化，自动持久化到 `power_config.json`

## 长按（进入二次确认窗口）

- GIVEN 按住时长 >= 2000ms
- WHEN 按钮释放
- THEN LED 进入 CONFIRM_WAIT 状态（快闪 200ms 间隔）
- THEN 记录确认窗口开始时间 `confirm_start_time = current_time`
- THEN 输出日志 "长按2秒，LED快闪等待二次确认..."

## 二次确认（进入配网模式）

- GIVEN LED 处于 CONFIRM_WAIT 状态
- WHEN 用户在确认窗口内（3 秒）按下按钮
- THEN 检查 `wifi_holder['mgr']` 是否已创建
- THEN 若已创建，调用 `wifi_mgr.start()` 进入配网模式
- THEN LED 切换到 WIFI_MODE 状态（熄灭）
- THEN 输出日志 "二次确认，进入WiFi配网模式"
- THEN 若未创建，输出警告 "WiFiManager 尚未就绪，请稍后重试"，LED 恢复 IDLE_NO_CONN

## 确认窗口超时

- GIVEN LED 处于 CONFIRM_WAIT 状态
- WHEN 确认窗口超过 `config.CONFIRM_WINDOW_MS`(3000ms)
- THEN LED 恢复 IDLE_NO_CONN 状态
- THEN LED 熄灭后恢复慢闪
- THEN 输出日志 "确认窗口超时，取消进入配网模式"

## 主循环

- GIVEN 所有模块已初始化
- WHEN 进入主循环
- THEN 每 50ms 轮询一次按钮状态
- THEN 每 50ms 调用 `ble_meter.update_data()` 发送 BLE 通知
- THEN 每 50ms 更新 LED 状态（根据连接数和闪烁计时器）
- THEN 每 200 次循环执行 `gc.collect()`
- THEN 每次循环喂看门狗 `wdt.feed()`
- THEN BLE 通知在 WiFi 配网模式期间暂停（`ble_disabled=True`）

## WiFiManager 异步创建

- GIVEN BLE 初始化成功
- WHEN 主程序启动
- THEN 在后台线程创建 WiFiManager（不阻塞主循环）
- THEN 创建完成后输出 "WiFiManager 异步创建完成"
- THEN 若创建失败，输出错误日志但不影响主循环

## BLE 初始化失败恢复

- GIVEN BLE 初始化抛出 OSError
- WHEN `SimpleBLEPowerMeter()` 构造失败
- THEN 输出警告日志
- THEN 等待 1000ms
- THEN 调用 `machine.reset()` 重启设备

## 看门狗

- 超时时间：`config.WDT_TIMEOUT_MS`(5000ms)
- 每次主循环喂狗
- 若主循环阻塞超过 5s，设备自动重启
