# ESP32-C3 MicroPython 优化技巧与最佳实践

基于 ESP-IDF 官方文档、MicroPython 社区讨论和实际项目经验整理。

---

## 1. WiFi/BLE 共存机制

### 1.1 硬件限制

ESP32-C3 只有一路 RF，WiFi 和 BLE 共享射频，**无法同时收发数据**，采用时分复用方式。

官方共存支持矩阵（ESP-IDF v5.0）：

| | BLE Scan | BLE Advertising | BLE Connecting | BLE Connected |
|---|---|---|---|---|
| **WiFi STA Scan** | Y | Y | Y | Y |
| **WiFi STA Connected** | Y | Y | Y | Y |
| **WiFi SOFTAP TX Beacon** | Y | Y | Y | Y |
| **WiFi SOFTAP Connected** | C1 | C1 | C1 | C1 |
| **ESP-NOW RX** | X | X | X | X |

- **Y**: 支持且性能稳定
- **C1**: 不能保证性能稳定
- **X**: 不支持

### 1.2 本项目策略

当前项目采用**互斥模式**（先关 BLE 再开 WiFi AP），而非共存模式。原因：

1. WiFi SOFTAP + BLE Connected 标记为 C1（不稳定）
2. MicroPython 固件默认未启用 `CONFIG_ESP32_WIFI_SW_COEXIST_ENABLE`
3. 内存不足以同时运行两个协议栈

### 1.3 优化方向

如需共存模式，需自定义编译 MicroPython 固件：
- 启用 `CONFIG_ESP32_WIFI_SW_COEXIST_ENABLE`
- 设置 `CONFIG_BT_NIMBLE_MAX_CONNECTIONS=1` 减少 BLE 内存占用
- 使用 NimBLE 替代 Bluedroid（节省约 50KB RAM）

---

## 2. 内存优化

### 2.1 ESP32-C3 内存布局

| 区域 | 大小 | 用途 |
|------|------|------|
| ROM | 384 KB | 启动代码、内置协议栈 |
| SRAM | 400 KB | 其中 16KB 用于 Cache |
| RTC SRAM | 8 KB | 深度睡眠保持 |
| Flash | 4 MB | 固件 + 文件系统 |

MicroPython 可用堆内存约 **150KB**（BLE 启动后约 120KB）。

### 2.2 关键优化技巧

#### 预分配缓冲区（本项目已采用）

```python
self._power_buf = bytearray(8)
self._hr_buf = bytearray(2)
```

避免在 BLE 通知回调中频繁创建 bytearray，减少 GC 压力。

#### gc.collect() 时机

- WiFi 启动前：`gc.collect()` 释放最大连续内存块
- 大对象创建后：立即 `del` + `gc.collect()`
- 周期性调用：主循环中每 N 次迭代调用一次

```python
loop_count += 1
if loop_count % 100 == 0:
    gc.collect()
```

#### gc.threshold() 自动回收

```python
gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())
```

设置 GC 阈值，当分配内存超过阈值时自动触发回收，避免内存碎片化。

#### 避免字符串拼接

```python
# 差 - 每次拼接创建新字符串对象
msg = "power=" + str(power) + " cadence=" + str(cadence)

# 好 - 使用格式化（单次分配）
msg = "power=%d cadence=%d" % (power, cadence)
```

#### Socket 数量限制

ESP32-C3 无 PSRAM，最多同时打开 **3-4 个 socket**。本项目 Web 服务器应限制并发连接：

```python
self.server.listen(3)  # 而非 5
```

### 2.3 内存监控

```python
import gc, micropython
gc.collect()
print(f"free={gc.mem_free()} alloc={gc.mem_alloc()}")
micropython.mem_info()
```

关键指标：
- `max new split`: ESP-IDF 可用的最大连续内存块（低于 10KB 时 WiFi 可能失败）
- `max free sz`: MicroPython 堆内最大连续块
- `max blk sz`: 最大可分配单块大小

---

## 3. BLE 优化

### 3.1 NimBLE vs Bluedroid

| 特性 | Bluedroid | NimBLE |
|------|-----------|--------|
| RAM 占用 | ~100KB | ~50KB |
| 初始化时间 | ~500ms | ~100ms |
| Classic BT | 支持 | 不支持 |
| BLE 连接数 | 多个 | 1（默认） |

MicroPython v1.28 默认使用 NimBLE，更适合 ESP32-C3。

### 3.2 通知间隔优化

```python
self._min_notify_interval = 1000  # 1秒
```

- 骑行 App 通常每秒更新一次数据
- 过快通知会导致 BLE 缓冲区溢出和连接断开
- 建议范围：500ms - 2000ms

### 3.3 MTU 优化

```python
ble.config(mtu=69)  # 减小 MTU 降低内存占用
```

默认 MTU=256，对于功率计数据（8字节）过大。减小 MTU 可节省约 400 字节 RAM。

### 3.4 广播间隔

```python
ble.gap_advertise(interval=100)  # 100ms
```

- 100ms：快速连接，功耗较高
- 500ms：平衡模式
- 1000ms：低功耗模式

---

## 4. WiFi 优化

### 4.1 AP 模式内存占用

WiFi AP 启动约消耗 **30-40KB** 堆内存，加上 socket 缓冲区可能达到 50KB。

### 4.2 Socket 最佳实践

```python
# 及时关闭不用的 socket
conn.close()

# 设置超时避免阻塞
conn.settimeout(5)

# 限制请求体大小
data = conn.recv(512)  # 而非 recv(1024) 或更大
```

### 4.3 HTTP 响应优化

```python
# 差 - 一次性构建整个 HTML
html = "<html>..." + dynamic_data + "...</html>"
conn.send(html)

# 好 - 分段发送
conn.send("HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n")
conn.send(static_html_part1)
conn.send(dynamic_data)
conn.send(static_html_part2)
```

---

## 5. 线程安全

### 5.1 _thread 限制

MicroPython 的 `_thread` 是简化版 threading：
- 无锁机制（无 `threading.Lock`）
- 内存共享但无同步原语
- 线程中异常不会传播到主线程

### 5.2 安全模式

```python
# 使用全局标志代替锁
wifi_ready = False

# 主线程
def main_loop():
    global wifi_ready
    while True:
        if wifi_ready:
            do_something()
        time.sleep_ms(50)

# WiFi 线程
def wifi_thread():
    global wifi_ready
    start_wifi()
    wifi_ready = True
```

### 5.3 避免在线程中创建对象

线程中创建的 Python 对象可能导致 GC 问题。建议在主线程预分配所有需要的对象。

---

## 6. 低功耗优化

### 6.1 电源模式

| 模式 | 功耗 | 适用场景 |
|------|------|---------|
| Active | ~15-20mA | 正常运行 |
| Modem-sleep | ~3-5mA | WiFi/BLE 空闲时 |
| Light-sleep | ~0.5mA | CPU 空闲，定时唤醒 |
| Deep-sleep | ~5μA | 长期待机 |

### 6.2 Modem-sleep 自动启用

```python
# WiFi 连接后自动进入 Modem-sleep
wlan.config(pm=0xa11142)  # 默认省电模式
```

### 6.3 BLE 广播优化

```python
# 降低广播频率节省功耗
ble.gap_advertise(interval=500)  # 500ms 而非 100ms
```

---

## 7. 固件自定义编译

如需突破 MicroPython 预编译固件限制，可自定义编译：

```bash
# 克隆 MicroPython
git clone https://github.com/micropython/micropython.git
cd micropython/ports/esp32

# 修改 sdkconfig
make menuconfig  # 启用共存、调整内存分区等

# 编译
make BOARD=ESP32C3_GENERIC submodules
make BOARD=ESP32C3_GENERIC
```

关键配置项：
- `CONFIG_ESP32_WIFI_SW_COEXIST_ENABLE` - WiFi/BLE 共存
- `CONFIG_BT_NIMBLE_MAX_CONNECTIONS` - BLE 最大连接数
- `CONFIG_BT_BLE_DYNAMIC_ENV_MEMORY` - BLE 动态内存分配
- `CONFIG_ESP32_WIFI_STATIC_RX_BUFFER_NUM` - WiFi 接收缓冲区数量

---

## 参考来源

- [ESP-IDF RF 共存文档](https://docs.espressif.com/projects/esp-idf/zh_CN/v5.0-beta1/esp32c3/api-guides/coexist.html)
- [MicroPython ESP32-C3 WiFi+BLE 内存讨论 #18860](https://github.com/orgs/micropython/discussions/18860)
- [MicroPython Socket 内存问题 #14421](https://github.com/micropython/micropython/issues/14421)
- [ESP-IDF RAM 优化指南](https://docs.espressif.com/projects/esp-idf/en/v4.4/esp32c3/api-guides/performance/ram-usage.html)
- [MicroPython GC 最佳实践](https://www.pythontutorials.net/blog/gc-esp32-micropython/)
