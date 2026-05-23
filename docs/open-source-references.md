# 相关优秀开源项目参考

搜集与 BikePower 项目（ESP32-C3 + MicroPython，BLE Cycling Power + Heart Rate 双服务，WiFi 配网，按钮交互）相关的优秀开源项目，按功能维度分类，分析每个项目的借鉴价值。

---

## 一、BLE 骑行功率计类

### 1.1 gsoros/ESPM — 最完整的 ESP32 骑行功率计

- **仓库**: https://github.com/gsoros/ESPM
- **语言**: C++ (PlatformIO)
- **硬件**: ESP32 + HX711 应变片 + MPU9250/MPU6500
- **活跃度**: 167 commits

**可借鉴点：**

- **真实传感器数据融合**: 使用 HX711（称重传感器）+ MPU6500（IMU）计算真实功率，而非模拟值。如果未来想从"模拟器"升级为"真实功率计"，这是最佳参考
- **Crank 数据格式**: 完整的 Cycling Power Measurement 特征实现，包含 pedal power balance、accumulated torque 等可选字段
- **校准流程**: 自动零偏校准 + 手动校准，比本项目当前只有模拟数据更专业
- **分区表设计**: `partitions.csv` 展示了如何为 OTA 和 LittleFS 分配 Flash 空间

**与本项目差异**: C++ 而非 MicroPython，但 BLE GATT 协议层的设计思路完全通用。

### 1.2 kochcodes/ESP32_BLE_CyclingPowerMeter — 已验证兼容性的功率计

- **仓库**: https://github.com/kochcodes/ESP32_BLE_CyclingPowerMeter
- **语言**: C++ (PlatformIO)
- **验证**: Zwift (iPhone/iPad/Mac) + Garmin Edge 130

**可借鉴点：**

- **Zwift 兼容性**: 已在主流骑行 App 上验证通过，可以学习其广播数据格式和 MTU 设置
- **Crank Revolution Data**: 完整的曲柄转数 + 时间戳实现，这是 Zwift 识别功率计的关键字段
- **简洁的 BLE 服务注册**: 代码量小，适合快速理解 Cycling Power Service 的最小实现

### 1.3 wie-niet/BLECyclePower-SpinningBike — 动感单车功率计

- **仓库**: https://github.com/wie-niet/BLECyclePower-SpinningBike
- **语言**: Arduino C++
- **特色**: 轮传感器 + 近似功率计算 + 深度睡眠

**可借鉴点：**

- **Deep Sleep 省电模式**: 空闲 180 秒后自动进入深度睡眠，传感器变化唤醒。本项目目前没有省电逻辑，这是很好的补充方向
- **近似功率计算算法**: 基于每圈固定能量消耗估算功率，比纯随机模拟更真实
- **LED 状态指示**: BLE 扫描时闪烁、配对时常亮，与本项目 LED 状态机设计思路一致

### 1.4 ElMaxow/skills-github-pages — MicroPython 功率计

- **仓库**: https://github.com/ElMaxow/skills-github-pages
- **语言**: **MicroPython**（与本项目相同）
- **硬件**: ESP32 + HX711 + MPU6500
- **特色**: 使用 `com.py` 模块发送 BLE 数据到 Garmin

**可借鉴点：**

- **MicroPython BLE 实现**: 这是少数使用 MicroPython 实现骑行功率计的项目，代码结构可直接参考
- **com.py 模块化设计**: BLE 通信独立为模块，与本项目 `ble_service.py` 的设计理念一致
- **Garmin 兼容性**: 已验证与 Garmin 设备的连接

### 1.5 JohanWieslander/ESP32-Bike-Powermeter — 可调功率/踏频的模拟功率计

- **仓库**: https://github.com/JohanWieslander/ESP32-Bike-Powermeter
- **语言**: C++ (PlatformIO)
- **特色**: 电位器控制功率和踏频

**可借鉴点：**

- **电位器控制**: 使用 10K 电位器连接 GPIO34（功率）和 GPIO39（踏频），提供物理旋钮调节体验
- **FakeBikePowerMeter.ino**: 单文件实现，简洁易懂，适合快速验证 BLE Cycling Power Service 的广播格式

---

## 二、FTMS 健身机服务类（进阶方向）

### 2.1 doudar/SmartSpin2k — 最成熟的 ESP32 骑行智能训练器

- **仓库**: https://github.com/doudar/SmartSpin2k
- **语言**: C++ (Arduino/ESP-IDF)
- **活跃度**: 2676 commits，149 tags，非常活跃
- **功能**: BLE FTMS Server + Client + ERG 模式 + WiFi OTA + Web 配置

**这是本项目最重要的参考项目，可借鉴点极多：**

- **FTMS 协议完整实现**: Fitness Machine Service (UUID 0x1826) 包含 Control Point、Indoor Bike Data、Training Status 等 12+ 个 Characteristic，这是 Cycling Power Service 的进阶版
- **ERG 模式（目标功率闭环控制）**: PID 算法动态调节阻力，保持目标功率。如果本项目未来想做"智能训练模式"，这是核心参考
- **BLE 多设备复用**: 同时作为 BLE Server（广播 FTMS）和 Client（接收 HRM/功率计数据），然后合并重播
- **WiFi Web 配置界面**: 完整的 Web 配置 + OTA 固件更新，比本项目更成熟
- **Power Table 映射**: 档位→阻力值的查找表（LUT），支持用户自定义曲线
- **Zwift/TrainerRoad/Kinomap 兼容性**: 已验证与所有主流骑行 App 的兼容性，包括 Android Zwift 的特殊处理
- **LittleFS 配置持久化**: 使用 LittleFS 而非 SPIFFS，更可靠
- **mDNS 服务发现**: 支持 OpenBikeControl 等第三方控制器

**与本项目对比**: SmartSpin2k 是 C++ 实现，功能远超本项目，但其架构设计（BLE 服务注册、WiFi 管理、配置持久化、ERG 控制）的思路可以直接借鉴到 MicroPython 版本。

### 2.2 kswiorek/ble-ftms — DIY 智能训练器

- **仓库**: https://github.com/kswiorek/ble-ftms
- **语言**: C++ (ESP-IDF)
- **特色**: 完整 FTMS + 步进电机阻力控制 + 12864 LCD

**可借鉴点：**

- **FTMS Control Point 状态机**: Start/Stop/Reset/Set Target Power 等 17 种命令的完整实现
- **双 ESP32 协同**: 采集节点 + 控制节点分离，解决 BLE 和传感器采样争抢 CPU 的问题
- **SD 卡训练计划**: CSV 格式的训练脚本解释器，支持预设训练课程

### 2.3 eiffelpeter/esp32_ftms_indoor_bike — 简洁的 FTMS 实现

- **仓库**: https://github.com/eiffelpeter/esp32_ftms_indoor_bike
- **语言**: Arduino C++
- **特色**: 单文件 751 行，含 Fake Data 模式

**可借鉴点：**

- **Fake Data 模式**: `#define FAKE_DATA 1` 开关，与本项目模拟数据的设计完全一致
- **FTMS 最小实现**: 代码简洁，适合理解 FTMS 的核心逻辑
- **Kinomap 兼容**: 已验证与 Kinomap 的连接

---

## 三、WiFi 配网 / Captive Portal 类

### 3.1 tonyp7/esp32-wifi-manager — 最成熟的 ESP32 WiFi 管理器

- **仓库**: https://github.com/tonyp7/esp32-wifi-manager
- **语言**: C (ESP-IDF)
- **活跃度**: 282 commits，12 tags

**可借鉴点：**

- **WiFi 扫描 + AP 自动切换**: 启动时尝试连接已保存网络，失败则自动开启 AP 模式
- **DNS 劫持**: 所有 HTTP 请求重定向到配网页面（Captive Portal）
- **自动关闭 AP**: 连接成功后 1 分钟自动关闭 AP，与本项目 `WIFI_SHUTDOWN_MS` 设计一致
- **NVS 持久化**: WiFi 凭证存储在 NVS（非易失性存储），比文件系统更可靠

### 3.2 wolfofnox/esp32-captive-wifi-manager — ESP-IDF Captive Portal

- **仓库**: https://github.com/wolfofnox/esp32-captive-wifi-manager
- **语言**: C (ESP-IDF)

**可借鉴点：**

- **SK6812 LED 状态指示**: 用 RGB LED 显示不同连接状态（呼吸灯、快闪等），比本项目单色 LED 更直观
- **多认证模式支持**: Open + WPA2-Personal
- **mDNS 支持**: 通过 `http://device.local` 访问配网页面

### 3.3 sutiana/WiFiConfigManager — Arduino ESP32 WiFi 配置管理器

- **仓库**: https://github.com/sutiana/WiFiConfigManager
- **语言**: Arduino C++
- **特色**: 非阻塞 Web 配置 + 双核独立运行

**可借鉴点：**

- **非阻塞设计**: WiFi 连接和 Web 服务器逻辑运行在独立 FreeRTOS 任务（Core 1），主循环（Core 0）不受影响
- **BOOT 按钮触发配网**: 长按 BOOT 按钮强制进入配置模式，与本项目长按按钮进入配网的设计一致
- **STA/AP 双模式切换**: 可在 Station 和 AP 模式间切换

---

## 四、MicroPython BLE 最佳实践类

### 4.1 ekspla/micropython_aioble_examples — 最全的 MicroPython aioble 示例

- **仓库**: https://github.com/ekspla/micropython_aioble_examples
- **语言**: MicroPython (aioble)
- **活跃度**: 121 commits，持续更新

**可借鉴点：**

- **aioble 异步 BLE 框架**: 使用 `asyncio` + `aioble` 替代原生 `bluetooth.BLE`，代码更清晰、更易维护
- **多连接示例**: `conn_multiple.py` 展示了同时连接多个 BLE 设备的方法
- **心率读取**: `hr_read.py` 展示了如何作为 Central 读取标准 HR Service (0x180D)
- **NUS Modem**: 完整的 Nordic UART Service 实现，包含 Server 和 Client

**注意**: 本项目使用原生 `bluetooth.BLE` + IRQ 回调模式，而 aioble 使用 asyncio 协程。在 ESP32-C3 的内存限制下，aioble 的 asyncio 开销需要评估。但 aioble 的代码结构更清晰，值得学习其设计模式。

### 4.2 RandomNerdTutorials — MicroPython BLE 入门教程

- **链接**: https://randomnerdtutorials.com/micropython-esp32-bluetooth-low-energy-ble/

**可借鉴点：**

- **aioble + bluetooth 混合使用**: 展示了如何用 `aioble.Characteristic` 定义服务，同时用 `bluetooth.BLE` 做底层操作
- **传感器 + LED 双特征**: 一个服务包含 read/notify 特征（传感器数据）和 write 特征（LED 控制），与本项目 Power + HR 双服务的设计类似

---

## 五、综合对比

| 项目 | 相关度 | 技术栈 | 最大借鉴价值 |
|------|--------|--------|------------|
| SmartSpin2k | ⭐⭐⭐⭐⭐ | C++ | FTMS 协议、ERG 模式、BLE 多设备复用、Web 配置 |
| ESPM (gsoros) | ⭐⭐⭐⭐ | C++ | 真实功率计算、传感器融合、校准流程 |
| micropython_aioble_examples | ⭐⭐⭐⭐ | MicroPython | aioble 异步框架、多连接、HR 读取 |
| ElMaxow (MicroPython) | ⭐⭐⭐⭐ | MicroPython | 唯一的 MicroPython 功率计实现，直接参考 |
| ble-ftms (kswiorek) | ⭐⭐⭐ | C++ | FTMS Control Point 状态机、训练计划 |
| esp32_ftms_indoor_bike | ⭐⭐⭐ | Arduino C++ | FTMS 最小实现 + Fake Data 模式 |
| ESP32_BLE_CyclingPowerMeter | ⭐⭐⭐ | C++ | Zwift/Garmin 兼容性验证 |
| BLECyclePower-SpinningBike | ⭐⭐ | Arduino C++ | Deep Sleep 省电、近似功率算法 |
| esp32-wifi-manager | ⭐⭐ | C | Captive Portal、自动 AP 切换 |
| Espressif RAM 优化文档 | ⭐⭐⭐ | 通用 | ESP32-C3 内存优化策略 |

---

## 六、重点学习方向

### 6.1 从 Cycling Power 升级到 FTMS

参考 SmartSpin2k 和 eiffelpeter 的实现，FTMS 是更完整的健身设备协议，支持阻力控制、训练状态等。

FTMS 关键 Characteristic：

| UUID | 名称 | 属性 | 说明 |
|------|------|------|------|
| 0x2ACC | Fitness Machine Feature | Read | 支持的功能位图 |
| 0x2AD2 | Indoor Bike Data | Notify | 实时数据（速度、踏频、功率、心率） |
| 0x2AD3 | Training Status | Read/Notify | 训练状态 |
| 0x2AD6 | Supported Resistance Level Range | Read | 支持的阻力范围 |
| 0x2AD9 | Fitness Machine Control Point | Write/Indicate | 控制命令 |
| 0x2ADA | Fitness Machine Status | Notify | 设备状态 |

### 6.2 ERG 模式（目标功率闭环控制）

参考 SmartSpin2k 的 PID 实现，让训练更智能：

- 用户设定目标功率（如 200W）
- 控制器以 200ms 为周期读取当前功率反馈
- 通过增量式 PID 算法动态调节阻力
- 解决非线性摩擦建模、响应延迟补偿等问题

### 6.3 Deep Sleep 省电

参考 BLECyclePower-SpinningBike：

- 空闲 180 秒后自动进入深度睡眠
- GPIO 传感器变化唤醒
- `machine.deepsleep()` 实现

### 6.4 aioble 框架评估

参考 ekspla 的示例，评估是否值得从 IRQ 回调迁移到 asyncio 模式：

| 维度 | 原生 bluetooth.BLE | aioble |
|------|-------------------|--------|
| 代码清晰度 | 低（IRQ 回调嵌套） | 高（async/await） |
| 内存开销 | 低 | 中（asyncio 运行时） |
| 实时性 | 高（IRQ 直接响应） | 中（事件循环调度） |
| 维护性 | 差 | 好 |
| ESP32-C3 适配 | 已验证 | 需评估内存 |

### 6.5 真实传感器支持

参考 ESPM 和 ElMaxow，为未来接入 HX711/MPU6500 做准备：

- HX711: 24 位 ADC，测量应变片信号，计算扭矩→功率
- MPU6500: 6 轴 IMU，测量曲柄角速度→踏频
- 校准流程: 零偏校准 + 灵敏度校准 + 温度补偿

---

## 七、ESP32-C3 内存优化参考

来源: [Espressif 官方文档 - Minimizing RAM Usage](https://docs.espressif.com/projects/esp-idf/en/latest/esp32c3/api-guides/performance/ram-usage.html)

关键优化点：

| 优化项 | 节省内存 | 对本项目的影响 |
|--------|---------|--------------|
| NimBLE 替代 Bluedroid | ~50KB | 已采用 ✅ |
| 关闭 WiFi IRAM speed optimization | ~25KB | WiFi 吞吐量降 10-15% |
| 关闭 LWIP IRAM optimization | ~12KB | TCP 延迟增加 3-5ms |
| `CONFIG_BT_BLE_DYNAMIC_ENV_MEMORY` | 动态释放 | BLE 关闭后回收内存 |
| 预分配 bytearray 缓冲区 | 避免碎片 | 已采用 ✅ |
| `%` 格式化替代 f-string | 减少临时对象 | 已采用 ✅ |
