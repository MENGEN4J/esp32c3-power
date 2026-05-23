# WiFi 管理器规格

> Source of Truth：`wifi_manager.py` 的行为规格
> AI 修改 WiFi 模块时，先加载此文件确认当前行为

---

## 初始化

- GIVEN 程序启动
- WHEN `WiFiManager(power_engine, ble_meter, ota_updater)` 被调用
- THEN 保存 power_engine、ble_meter 和 ota_updater 引用
- THEN wlan=None, server=None, sta_if=None（延迟创建）
- THEN _wifi_close_event=False, _submitted=False, ble_disabled=False, _connect_result=None
- THEN _ota_check_result=None, _ota_downloading=False

## 启动 AP 热点

- GIVEN 用户长按按钮 >= 2s
- WHEN `start()` 被调用
- THEN 先调用 `_disable_ble()` 关闭 BLE
- THEN 仅在 `_disable_ble()` 成功时才设置 `ble_disabled=True` 并继续启动 WiFi AP
- THEN 若 `_disable_ble()` 失败，则记录错误并立即终止 WiFi 启动
- THEN 执行 `gc.collect()` 回收内存
- THEN 创建 AP 接口，ESSID="BikePower"，AUTH_OPEN
- THEN 设置 IP=192.168.4.1, 子网=255.255.255.0
- THEN 创建 TCP server，绑定 0.0.0.0:80，listen(3)
- THEN 预构建首页 HTML 缓存 `_landing_cache`
- THEN 启动 `_server_thread` 线程处理请求
- THEN 启动 `_wifi_shutdown_timer` 线程计时关闭
- THEN 记录启动时间 `_start_time`

## Web 服务器

- GIVEN AP 热点已启动
- WHEN 手机连接 WiFi 并发送 HTTP 请求
- THEN `_server_thread` 接受连接，设置 5s 超时
- THEN 读取请求（最大 2048 字节）
- THEN 路由到对应处理方法
- THEN 发送响应后关闭连接（finally 中）
- THEN 连接异常（ETIMEDOUT/ECONNRESET）静默处理

## JSON 响应

- GIVEN 响应字段包含版本、SSID、错误信息或更新日志等动态字符串
- WHEN 构造 JSON 响应
- THEN 使用 `_json_escape()` 转义反斜杠、双引号、换行和回车
- THEN 避免动态内容破坏 JSON 结构

## 请求路由

| 方法 | 路径 | 处理方法 |
|------|------|---------|
| GET | / | 返回 `_landing_cache`（预构建缓存） |
| GET | /wifi_setup | `_build_wifi_setup_page()` |
| GET | /config | `_build_config_page()` |
| POST | /config | `_handle_config_submit()` |
| GET | /scan | `_handle_scan()` |
| POST | /wifi_connect | `_handle_wifi_connect()`（异步，启动后台线程） |
| GET | /wifi_status | `_handle_wifi_status()`（轮询连接状态） |
| GET | /check_update | `_handle_check_update()`（OTA 版本检查） |
| POST | /start_update | `_handle_start_update()`（OTA 开始下载） |
| GET | /update_status | `_handle_update_status()`（OTA 下载进度轮询） |
| GET | /update_page | 返回 OTA 更新进度页面 |
| GET | /disable_bt | `_handle_disable_bt()` |
| GET | /time | 返回剩余秒数 |
| GET | /success | `_build_success_page()` |

## WiFi 扫描

- GIVEN BLE 已关闭
- WHEN `/scan` 请求到达
- THEN 激活 STA 接口
- THEN 扫描附近 WiFi，按信号强度排序
- THEN 取前 10 个不重复 SSID
- THEN 返回 JSON：`[{ssid, rssi, encrypted}]`

- GIVEN BLE 未关闭
- WHEN `/scan` 请求到达
- THEN 返回 `{"error":"请先关闭蓝牙"}`

## WiFi 连接（异步）

- GIVEN BLE 已关闭且无进行中的连接
- WHEN POST `/wifi_connect` 带 ssid + password
- THEN 设置 `_connect_result="pending"`
- THEN 启动后台线程 `_connect_wifi_thread` 执行连接
- THEN 立即返回 `{"ok":true,"msg":"connecting"}`
- THEN 后台线程激活 STA 接口，尝试连接（超时 15s）
- THEN 连接成功：`_connect_result="ok:{ip}"`，保存凭据到 `wifi_config.txt`
- THEN 连接失败：`_connect_result="fail:{msg}"`

- GIVEN 已有进行中的连接请求
- WHEN POST `/wifi_connect` 到达
- THEN 返回 `{"ok":false,"msg":"正在连接中，请稍候"}`

## WiFi 连接状态查询

- GIVEN 前端发起 WiFi 连接后
- WHEN GET `/wifi_status` 到达
- THEN `_connect_result=None`：返回 `{"status":"idle"}`
- THEN `_connect_result="pending"`：返回 `{"status":"connecting"}`
- THEN `_connect_result="ok:{ip}"`：返回 `{"status":"connected","ip":"..."}`，清除结果
- THEN `_connect_result="fail:{msg}"`：返回 `{"status":"failed","msg":"..."}`，清除结果

## 首页缓存

- GIVEN WiFi AP 已启动
- WHEN GET `/` 请求到达
- THEN 返回 `_landing_cache`（在 `start()` 中预构建的 HTTP 响应）
- THEN 避免每次请求重新拼接 HTML 字符串

## 配置提交

- GIVEN 用户在配置页面提交表单
- WHEN POST `/config` 到达
- THEN 解析表单参数：power, cadence, heartrate
- THEN 范围校验后应用到 power_engine
- THEN 调用 `power_engine.flush_if_dirty()` 立即持久化，避免 5s 后重启前配置未保存
- THEN 5s 后自动关闭 WiFi（`_shutdown_wifi()`）
- THEN 302 重定向到 /success

## 自动关闭

- GIVEN WiFi 已启动
- WHEN 距启动时间 >= `config.WIFI_SHUTDOWN_MS`(180000ms = 3分钟)
- THEN 设置 `_wifi_close_event=True`
- THEN 关闭 server socket
- THEN 关闭 STA 接口
- THEN 关闭 AP 接口
- THEN 若 `ble_disabled=True`，1s 后 `machine.reset()` 重启恢复蓝牙
- THEN 若 `ble_disabled=False`，仅关闭 WiFi，蓝牙保持运行

## BLE 互斥

- GIVEN BLE 正在运行
- WHEN `start()` 被调用
- THEN 自动调用 `_disable_ble()` 关闭 BLE
- THEN 只有 `_disable_ble()` 返回成功时，才允许继续启动 WiFi

- GIVEN BLE 已停用但 WiFi AP 启动过程中发生异常
- WHEN `start()` 捕获启动异常
- THEN 记录错误日志
- THEN 调用 `machine.reset()` 重启设备，恢复 BLE 到可靠状态

- GIVEN BLE 有活跃连接
- WHEN `_disable_ble()` 被调用
- THEN 返回 (False, "蓝牙有活跃连接，请先断开所有蓝牙设备")

## WiFi 凭据持久化

- GIVEN WiFi 连接成功
- WHEN `_save_wifi_config(ssid, password)` 被调用
- THEN 写入 `wifi_config.txt`，格式：`ssid\npassword`

## Socket 限制

- 最大同时 3 个 socket（`listen(3)`）
- 每个连接 5s 超时
- 请求缓冲区 2048 字节
- 连接处理完毕后必须 `conn.close()`

## OTA 自动检查

- GIVEN WiFi STA 连接家庭网络成功
- WHEN `_auto_check_ota()` 被调用
- THEN 若 ota_updater 为 None，跳过
- THEN 若 _ota_check_result 已有值，跳过
- THEN 设置 `_ota_check_result = "pending"`
- THEN 启动后台线程 `_ota_check_thread` 执行版本检查
- THEN 检查结果写入 `_ota_check_result`

## OTA 更新检查请求

- GIVEN WiFi 已配网
- WHEN GET `/check_update` 到达
- THEN 若 ota_updater 为 None，返回 `{"has_update":false,"error":"OTA不可用"}`
- THEN 若未配网，返回 `{"has_update":false,"error":"需先配网连接WiFi"}`
- THEN 若检查中，返回 `{"status":"checking"}`
- THEN 若有更新，返回 `{"has_update":true,"version":"...","changelog":"...","file_count":N,"total_size":M}`
- THEN 若无更新，返回 `{"has_update":false,"current":"..."}`

## OTA 开始下载请求

- GIVEN check_update 已返回有更新
- WHEN POST `/start_update` 到达
- THEN 若已在下载中，返回 `{"ok":false,"msg":"正在更新中，请稍候"}`
- THEN 设置 `_ota_downloading = True`，清除 `_config_cache`
- THEN 启动后台线程 `_ota_download_thread`
- THEN 返回 `{"ok":true,"msg":"downloading"}`

## OTA 下载线程

- GIVEN `_ota_download_thread` 启动
- THEN 设置 `_ota_downloading = True`，暂停 WiFi 关闭计时器
- THEN 调用 `ota_updater.start_download()`
- THEN 下载成功：2 秒后 `machine.reset()`
- THEN 下载失败：设置 `_ota_downloading = False`，恢复 WiFi 关闭计时器

## OTA 下载状态查询

- GIVEN OTA 下载进行中
- WHEN GET `/update_status` 到达
- THEN 下载中：`{"status":"downloading","completed":N,"total":M,"percent":P,"downloaded_bytes":A,"total_bytes":B,"current_file_bytes":C,"current_file_total":D}`
- THEN 完成：`{"status":"done","msg":"更新完成，设备即将重启"}`
- THEN 失败：`{"status":"failed","msg":"...","completed":N,"total":M,"downloaded_bytes":A,"total_bytes":B}`

## OTA 下载期间 WiFi 计时器

- GIVEN OTA 正在下载
- WHEN `_wifi_shutdown_timer` 检查超时
- THEN 检测到 `_ota_downloading = True`，暂停关闭计时（跳过本次检查）
- THEN 下载完成后 `_ota_downloading = False`，恢复正常超时检查
