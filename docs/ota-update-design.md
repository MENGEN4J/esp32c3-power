# v1.9.0 OTA 固件更新设计文档

> BikePower ESP32-C3 蓝牙功率计 — 配网后一键检查并更新固件版本

---

## 1. 背景与目标

### 1.1 现状

- 设备通过 USB 串口 + `deploy.sh` 脚本部署 `.py` 文件到 ESP32-C3 文件系统
- 用户需物理连接电脑才能更新固件，操作门槛高
- v1.8.0 已实现 WiFi 一键配网（STA 连接家庭网络），但配网后仅用于参数配置

### 1.2 目标

- 用户配网后，设备自动检查是否有新版本
- 发现新版本时，用户在 Web 页面点击即可完成更新
- 更新失败时设备可自动回滚，不会变砖
- 版本托管在 GitHub，与源码、tag 和 Release 附件保持同一发布源

### 1.3 约束

| 约束 | 说明 |
|------|------|
| WiFi/BLE 互斥 | ESP32-C3 只有一路 RF，WiFi 和 BLE 无法同时运行 |
| 内存有限 | WiFi STA 启动后可用堆约 80KB |
| Socket 并发 ≤ 3 | 无 PSRAM，最多同时 3 个 socket |
| 无 asyncio/requests | MicroPython 环境，仅可用 socket 原生操作 |
| 配网窗口有限 | WiFi AP 默认 180 秒后自动关闭 |

---

## 2. 方案选型

### 2.1 三种方案对比

| 维度 | 方案 A: 文件级 OTA | 方案 B: 固件级 OTA | 方案 C: 文件级 OTA + 安全回滚 |
|------|-------------------|-------------------|---------------------------|
| 实现复杂度 | 低 | 高 | 中 |
| 内存占用 | 低（逐文件下载） | 高（需缓冲完整固件 ~1.5MB） | 低（逐文件下载） |
| 更新粒度 | 单文件差量 | 全量替换 | 单文件差量 |
| 下载大小 | ~5-20KB（仅变更文件） | ~1.5MB（完整固件） | ~5-20KB（仅变更文件） |
| 可回滚 | ❌ 无 | ✅ A/B 分区 | ✅ .bak 备份回滚 |
| 能否更新 MicroPython 运行时 | ❌ 不能 | ✅ 能 | ❌ 不能 |
| 失败风险 | 中（文件损坏需手动恢复） | 低（A/B 切换） | 低（boot.py 自动回滚） |

### 2.2 选择方案 C

理由：

1. 本项目 99% 的更新都是 `.py` 文件变更，无需更新 MicroPython 运行时
2. 内存约束（WiFi STA 后仅 ~80KB）无法缓冲完整固件
3. 文件级差量更新下载量极小（5-20KB vs 1.5MB），配网窗口内即可完成
4. boot.py 安全回滚机制确保设备不会变砖

### 2.3 关于 A/B 分区

A/B 分区是 ESP-IDF 原生固件（C 编译的 `.bin`）的 OTA 方案，需要双 partition table。本项目是 MicroPython `.py` 文件部署在文件系统上，没有编译固件的分区概念。方案 C 用文件级 `.bak` 备份 + boot.py 校验回滚实现等价效果。

### 2.4 关于差量更新

本项目所有业务逻辑都是 `.py` 文件，天然支持文件级差量更新。通过版本清单中的 CRC32 哈希对比，只下载哈希值变化的文件，无需二进制 diff 算法。

---

## 3. 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      GitHub 仓库                             │
│  releases/latest/version.json  ← 版本清单（版本号+文件哈希）   │
│  v1.9.0/app.py                ← 变更文件                     │
│  v1.9.0/wifi_manager.py       ← 变更文件                     │
│  v1.9.0/web_pages.py          ← 变更文件                     │
└─────────────────────────────────────────────────────────────┘
                           │ HTTP GET
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    ESP32-C3 设备                              │
│                                                              │
│  boot.py ──→ 检查 .update_pending 标志                       │
│    │         ├── 有 → 校验新文件完整性 → 成功则删除备份        │
│    │         │         └── 失败 → 从 .bak 回滚               │
│    │         └── 无 → 正常启动                                │
│                                                              │
│  ota_updater.py ──→ 版本检查 + 文件下载 + 原子替换            │
│                                                              │
│  wifi_manager.py ──→ 配网成功后触发 OTA 检查                  │
│                                                              │
│  web_pages.py ──→ 新增「检查更新」区域                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 版本清单格式

托管在 GitHub 仓库的 `releases/latest/version.json`：

```json
{
  "version": "1.9.0",
  "min_version": "1.8.0",
  "changelog": "新增 OTA 固件更新功能",
  "files": [
    {
      "name": "app.py",
      "hash": "a1b2c3d4",
      "size": 5234,
      "url": "https://raw.githubusercontent.com/MENGEN4J/esp32c3-power/v1.9.0/app.py"
    },
    {
      "name": "wifi_manager.py",
      "hash": "e5f6g7h8",
      "size": 14820,
      "url": "https://raw.githubusercontent.com/MENGEN4J/esp32c3-power/v1.9.0/wifi_manager.py"
    }
  ]
}
```

字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | string | 目标版本号 |
| `min_version` | string | 最低可升级版本，防止跨大版本升级导致不兼容 |
| `changelog` | string | 更新说明，显示在页面上 |
| `files` | array | 仅包含**有变更**的文件 |
| `files[].name` | string | 文件名（相对于设备根目录） |
| `files[].hash` | string | CRC32 哈希值，用于判断是否需要下载和校验完整性 |
| `files[].size` | int | 文件大小（字节），用于进度显示 |
| `files[].url` | string | GitHub Raw 文件直链 |

---

## 5. 新增模块：ota_updater.py

### 5.1 职责

- 从 GitHub 获取 `version.json`
- 对比本地文件 CRC32 哈希，确定需更新的文件列表
- 逐文件下载 → 写入临时文件 → 校验哈希 → 原子替换
- 设置更新标志，触发重启

### 5.2 内存策略

- 逐文件处理，不在内存中同时持有多个文件内容
- 下载时边读边写（socket recv → file write），不缓冲整个文件
- 每次读取 512 字节（`OTA_DOWNLOAD_CHUNK`），写入文件后立即释放
- 每个文件下载完成后 `gc.collect()`
- 峰值内存占用 < 10KB

### 5.3 核心流程

```
check_update()
  │
  ├── HTTP GET version.json
  ├── 解析 JSON
  ├── 对比 version > FIRMWARE_VERSION
  ├── 对比 min_version <= FIRMWARE_VERSION
  └── 返回 (has_update, version_info)

download_update(version_info)
  │
  ├── 遍历 files 列表
  │   │
  │   ├── 计算本地文件 CRC32
  │   │
  │   ├── 哈希相同 → 跳过
  │   │
  │   └── 哈希不同 → 下载
  │       │
  │       ├── 备份旧文件: app.py → app.py.bak
  │       ├── 下载到临时文件: app.py.tmp
  │       ├── 校验 CRC32
  │       │   ├── 校验通过 → os.rename("app.py.tmp", "app.py")
  │       │   └── 校验失败 → 删除 .tmp，记录错误
  │       └── gc.collect()
  │
  ├── 写入新版本号到 ota_version.json
  ├── 创建 .update_pending 标志文件
  └── machine.reset()
```

### 5.4 HTTP 下载实现

MicroPython 无 `requests` 库，需用 `socket` 原生实现：

```
1. 解析 URL → 提取 host / path
2. socket.getaddrinfo(host, 80) → DNS 解析
3. socket.connect((ip, 80))
4. 发送 HTTP GET 请求
5. 读取响应头，解析 Content-Length
6. 逐块读取 body（每次 512 字节），写入文件
7. 关闭 socket
```

关键细节：

- HTTP 响应头与 body 以 `\r\n\r\n` 分隔，需先跳过头部
- 设置 socket 超时 10 秒，防止卡死
- GitHub Raw URL 可能经由重定向，需处理重定向（最多 3 次）
- 每次下载完成后立即 `sock.close()`，释放 socket 资源

---

## 6. boot.py 安全回滚

### 6.1 回滚流程

```
设备启动
  │
  ├── 检查 .update_pending 标志
  │   │
  │   ├── 不存在 → 正常启动
  │   │
  │   └── 存在 → 进入校验模式
  │       │
  │       ├── 逐个 __import__() 核心模块
  │       │   │
  │       │   ├── 全部通过
  │       │   │   ├── 删除所有 .bak 文件
  │       │   │   ├── 删除 .update_pending
  │       │   │   ├── 更新 ota_version.json 中的版本号
  │       │   │   └── 正常启动
  │       │   │
  │       │   └── 任一模块 import 失败
  │       │       ├── 遍历文件系统，将 .bak 还原
  │       │       ├── 删除 .update_pending
  │       │       ├── 删除 ota_version.json（回退到编译时版本号）
  │       │       └── 正常启动（使用旧版本）
  │       │
  │       └── 回滚也失败（极端情况）
  │           └── 保留 .bak 文件，用户可通过 USB 串口手动恢复
  │
  └── 正常启动 app.main()
```

### 6.2 校验范围

校验以下核心模块的 import 可用性：

- `config`
- `logger`
- `utils`
- `ble_service`
- `power_data`
- `wifi_manager`
- `web_pages`
- `app`
- `ota_updater`（新增模块也需校验）

### 6.3 为什么用 `__import__` 而非 `py_compile`

- `py_compile` 在 MicroPython 中不可用（CPython 专有）
- `__import__` 会执行模块级代码，验证语法 + 依赖 + 运行时正确性
- 校验完成后模块已缓存，不影响后续启动速度

---

## 7. 用户交互流程

### 7.1 完整时序

```
用户长按2秒 → 二次确认 → BLE关闭 → WiFi AP启动
    │
    ▼
用户连接 AP → 打开 192.168.4.1 → 一键配网
    │
    ▼
选择家庭WiFi → 输入密码 → STA 连接成功
    │
    ├── 自动检查更新（后台线程，不阻塞页面）
    │
    ▼
跳转到配置页面
    │
    ├── 有更新 → 页面顶部显示「发现新版本 v1.9.0」横幅
    │   │
    │   └── 用户点击「立即更新」
    │       │
    │       ├── 暂停 WiFi 关闭计时器
    │       ├── 逐文件下载 + 替换
    │       ├── 页面显示下载进度
    │       ├── 下载完成 → machine.reset()
    │       └── 下载失败 → 提示错误，恢复计时器
    │
    └── 无更新 → 显示「当前已是最新版本 v1.8.0」
```

### 7.2 自动检查时机

- **仅在 STA 连接成功后自动检查 1 次**，不做定时轮询
- 检查结果缓存在 `WiFiManager._ota_info` 中
- 配置页面渲染时读取缓存，无需重复请求

---

## 8. 页面设计

### 8.1 配置页面（修改现有）

在现有配置页面基础上，新增版本信息和更新区域：

```
┌──────────────────────────────────────┐
│         BikePower 配置               │
│                                      │
│  ┌──────────────────────────────┐    │
│  │  ⬆ 发现新版本 v1.9.0        │    │  ← 绿色横幅（有更新时显示）
│  │  新增 OTA 固件更新功能       │    │
│  │  [立即更新]                  │    │
│  └──────────────────────────────┘    │
│                                      │
│  ┌──────────────────────────────┐    │
│  │  ✔ WiFi已配网成功            │    │  ← 现有组件
│  └──────────────────────────────┘    │
│                                      │
│  功率(W)  [  200  ]                  │
│  踏频(RPM) [  90  ]                  │
│  心率(BPM) [ 140  ]                  │
│                                      │
│  [保存]                              │
│                                      │
│  当前版本: v1.8.0                     │  ← 新增版本信息
│  180秒后关闭WiFi                      │
└──────────────────────────────────────┘
```

无更新时：

```
┌──────────────────────────────────────┐
│  ✔ 当前已是最新版本 v1.8.0           │  ← 灰色横幅
└──────────────────────────────────────┘
```

未连接 WiFi 时：

```
┌──────────────────────────────────────┐
│  ℹ 需先配网才能检查更新              │  ← 黄色横幅
└──────────────────────────────────────┘
```

### 8.2 更新进度页面（新增）

用户点击「立即更新」后跳转：

```
┌──────────────────────────────────────┐
│         固件更新中                    │
│                                      │
│     ⬇ 下载中... 3/5 文件             │
│     ████████░░░░ 60%                 │
│                                      │
│  正在下载: wifi_manager.py           │
│  已完成: app.py ✓ web_pages.py ✓     │
│                                      │
│  ⚠ 更新期间请勿断电或关闭页面         │
│  ⚠ 更新完成后设备将自动重启           │
└──────────────────────────────────────┘
```

更新失败时：

```
┌──────────────────────────────────────┐
│         更新失败                      │
│                                      │
│     ✘ 下载失败                       │
│     wifi_manager.py 校验不通过        │
│                                      │
│  [重试]                              │
│  [返回配置页]                         │
│                                      │
│  设备仍可正常使用（当前版本 v1.8.0）   │
└──────────────────────────────────────┘
```

---

## 9. API 路由设计

在 `wifi_manager.py` 中新增以下路由：

| 路由 | 方法 | 说明 |
|------|------|------|
| `/check_update` | GET | 触发/查询 OTA 更新检查 |
| `/start_update` | POST | 开始下载更新 |
| `/update_status` | GET | 查询更新下载进度 |

### 9.1 `/check_update`

```json
// 有更新
{"has_update": true, "version": "1.9.0", "changelog": "新增 OTA 固件更新功能", "file_count": 3, "total_size": 25890}

// 无更新
{"has_update": false, "current": "1.8.0"}

// 检查中
{"status": "checking"}

// 检查失败
{"has_update": false, "error": "网络超时"}
```

### 9.2 `/start_update`

```json
// 开始下载
{"ok": true, "msg": "downloading"}

// 已在下载中
{"ok": false, "msg": "正在更新中，请稍候"}

// 未检查过更新
{"ok": false, "msg": "请先检查更新"}
```

### 9.3 `/update_status`

```json
// 下载中
{"status": "downloading", "current_file": "wifi_manager.py", "completed": 2, "total": 5, "percent": 40}

// 下载完成，即将重启
{"status": "done", "msg": "更新完成，设备即将重启"}

// 下载失败
{"status": "failed", "msg": "wifi_manager.py 校验失败", "completed": 2, "total": 5}

// 空闲
{"status": "idle"}
```

---

## 10. config.py 新增常量

```python
FIRMWARE_VERSION = "1.9.4"
OTA_VERSION_URL = "https://raw.githubusercontent.com/MENGEN4J/esp32c3-power/main/releases/latest/version.json"
OTA_PENDING_FLAG = ".update_pending"
OTA_VERSION_FILE = "ota_version.json"
OTA_BACKUP_SUFFIX = ".bak"
OTA_TEMP_SUFFIX = ".tmp"
OTA_MPY_SUFFIX = ".mpy"
OTA_DOWNLOAD_CHUNK = const(512)
OTA_HTTP_TIMEOUT = const(10)
OTA_MAX_REDIRECTS = const(3)
```

| 常量 | 说明 |
|------|------|
| `FIRMWARE_VERSION` | 当前固件版本号，每次发版时更新 |
| `OTA_VERSION_URL` | version.json 的 GitHub Raw 地址 |
| `OTA_PENDING_FLAG` | 更新待校验标志文件名 |
| `OTA_VERSION_FILE` | 本机 OTA 后写入的版本记录文件 |
| `OTA_BACKUP_SUFFIX` | 旧文件备份后缀 |
| `OTA_TEMP_SUFFIX` | 下载临时文件后缀 |
| `OTA_MPY_SUFFIX` | OTA 字节码文件后缀 |
| `OTA_DOWNLOAD_CHUNK` | 每次读取块大小（字节） |
| `OTA_HTTP_TIMEOUT` | HTTP 请求超时（秒） |
| `OTA_MAX_REDIRECTS` | HTTP 重定向最大次数 |

---

## 11. 内存预算

| 阶段 | 可用堆 | OTA 占用 | 剩余 | 说明 |
|------|--------|---------|------|------|
| WiFi STA 连接后 | ~80KB | ~5KB | ~75KB | DNS 解析 + socket 创建 |
| 下载单个文件中 | ~75KB | ~3KB | ~72KB | 1 个 socket + 512B 读缓冲 |
| JSON 解析 | ~72KB | ~4KB | ~68KB | version.json 约 500B |
| 文件写入 | ~68KB | ~2KB | ~66KB | 文件 I/O 缓冲 |

结论：逐文件处理策略确保峰值内存 < 10KB，完全满足约束。

---

## 12. 高可用保障机制

### 12.1 风险与对策

| 风险 | 保障措施 | 恢复方式 |
|------|---------|---------|
| 下载中断电 | `.tmp` 文件未完成 rename，旧文件完好 | 重启后旧版本正常运行 |
| 文件损坏 | 下载后 CRC32 校验，校验失败不替换 | 重试下载或跳过 |
| 更新后无法启动 | boot.py `__import__` 校验，失败自动从 `.bak` 回滚 | 自动回滚到旧版本 |
| 回滚也失败 | 保留 `.bak` 文件 | 用户通过 USB 串口手动恢复 |
| version.json 解析失败 | try/except 捕获，OTA 功能降级为不可用 | 正常功能不受影响 |
| GitHub 不可达 | HTTP 超时 10 秒，超时后跳过更新检查 | 正常功能不受影响 |
| 跨大版本升级 | `min_version` 字段限制 | 提示需 USB 升级 |
| WiFi 断开 | 下载线程异常退出 | 不影响主循环和配置页面 |
| WiFi 超时关闭 | 用户点击更新时暂停计时器 | 更新完成/失败后恢复计时器 |

### 12.2 原子替换保证

文件替换采用三步操作确保原子性：

```
1. 备份: os.rename("app.py", "app.py.bak")     ← 旧文件保留
2. 下载: 写入 "app.py.tmp"                      ← 临时文件
3. 替换: os.rename("app.py.tmp", "app.py")      ← 原子操作
```

`os.rename` 在 MicroPython 的 FAT 文件系统上是原子操作（同一分区），不会出现半写状态。

### 12.3 更新标志机制

```
更新前: 创建 .update_pending 标志文件
更新后: boot.py 校验通过后删除标志文件
回滚后: boot.py 回滚完成后删除标志文件
```

标志文件存在 = 上次更新未完成校验，boot.py 需要介入。

---

## 13. GitHub 仓库目录结构

```
esp32c3-power/                      ← GitHub 仓库
├── releases/
│   └── latest/
│       └── version.json            ← 永远指向最新版本
├── v1.9.0/
│   ├── app.py
│   ├── wifi_manager.py
│   └── web_pages.py
├── v1.8.0/                         ← 历史版本（可选保留）
│   └── ...
├── app.py                          ← 开发分支源码
├── config.py
└── ...
```

### 13.1 发版流程

1. 开发完成，更新 `config.py` 中的 `FIRMWARE_VERSION`
2. 创建 git tag `v1.9.0`
3. 将变更文件复制到 `v1.9.0/` 目录
4. 生成各文件 CRC32 哈希，更新 `releases/latest/version.json`
5. 推送到 GitHub

### 13.2 version.json 生成脚本

可在 `scripts/` 目录新增 `gen_version_json.py`，自动计算文件哈希并生成 version.json：

```bash
python3 scripts/gen_version_json.py --version 1.9.0 --min-version 1.8.0 \
  --files app.py wifi_manager.py web_pages.py \
  --github-owner MENGEN4J --github-repo esp32c3-power
```

---

## 14. 新增/修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `ota_updater.py` | 新增 | OTA 核心逻辑：版本检查、文件下载、原子替换 |
| `config.py` | 修改 | 新增 `FIRMWARE_VERSION` 等 OTA 相关常量 |
| `boot.py` | 修改 | 新增更新完整性校验 + 自动回滚逻辑 |
| `wifi_manager.py` | 修改 | STA 连接成功后触发 OTA 检查；新增 3 个 API 路由 |
| `web_pages.py` | 修改 | 配置页面新增版本信息和更新横幅；新增更新进度页面 |
| `app.py` | 修改 | WiFiManager 初始化传入 OTAUpdater 引用 |
| `scripts/gen_version_json.py` | 新增 | 发版时自动生成 version.json |

---

## 15. WiFi STA + AP 共存

OTA 更新需要 **STA + AP 同时运行**：

- AP：供用户手机访问 Web 页面
- STA：连接家庭网络下载更新文件

ESP32-C3 支持 STA+AP 共存模式（同信道），但内存消耗增加约 20KB。

内存验证：

| 项目 | 占用 |
|------|------|
| AP + STA 双接口 | ~50-60KB |
| OTA 下载（逐文件） | ~10KB |
| 剩余可用 | ~60-70KB |

结论：内存足够，但需在 STA 连接成功后验证实际可用堆。

---

## 16. 代码保护与托管格式

### 16.1 问题分析

当前 OTA 托管原始 `.py` 源码，存在三个问题：

| 问题 | 风险等级 | 说明 |
|------|---------|------|
| 代码明文暴露 | 中 | 任何人访问 GitHub 仓库都能看到完整源码逻辑 |
| 下载体积大 | 低 | Python 源码未压缩，`wifi_manager.py` 26KB、`web_pages.py` 25KB |
| 启动速度慢 | 低 | MicroPython 运行时需编译 `.py` 为字节码，占用 CPU 和内存 |

### 16.2 三种托管格式对比

| 维度 | .py 源码（当前） | .mpy 字节码（推荐） | .mpy.gz 压缩字节码 |
|------|----------------|-------------------|-------------------|
| 代码保护 | ❌ 明文可读 | ⚠️ 字节码反编译有门槛 | ⚠️ 字节码+压缩，双重门槛 |
| 下载体积 | 100%（基准） | ~70%（字节码更紧凑） | ~25%（gzip 再压缩） |
| 设备端解压 | 不需要 | 不需要 | 需要 `uzlib` 解压 |
| 启动速度 | 慢（运行时编译） | 快（预编译字节码） | 快（解压后即字节码） |
| 内存占用 | 高（编译需临时内存） | 低（直接执行） | 中（解压需临时缓冲） |
| MicroPython 版本耦合 | ❌ 无 | ⚠️ `.mpy` 必须匹配设备 MPY 版本 | ⚠️ 同左 |
| 实现复杂度 | 低 | 中 | 中高 |
| GitHub 托管 | 直接 Raw 下载 | 直接 Raw 下载 | 直接 Raw 下载 |

### 16.3 选择 .mpy 字节码托管

理由：

1. **代码保护**：字节码不可直接阅读，反编译需要专业工具和经验
2. **下载更小**：字节码比源码小约 30%
3. **启动更快**：跳过运行时编译，直接执行
4. **内存更省**：无需编译临时内存
5. **实现简单**：只需发版时用 `mpy-cross` 预编译，OTA 下载 `.mpy` 替换 `.py`
6. **无需设备端解压**：避免 `uzlib` 兼容性和内存问题

### 16.4 .mpy 版本耦合问题

`.mpy` 字节码包含 MicroPython 版本号，**必须与设备运行的 MicroPython 版本严格匹配**：

```
设备 MicroPython v1.28 → .mpy 必须用 v1.28 的 mpy-cross 编译
设备升级到 v1.29 → 所有 .mpy 必须重新编译
```

本项目当前使用 MicroPython v1.28，`mpy-cross` 已在 `build_firmware.sh` 中编译。发版时用同一版本 `mpy-cross` 编译即可。

### 16.5 version.json 变更

新增 `mpy_version` 字段，设备下载前校验 MicroPython 版本是否匹配：

```json
{
  "version": "1.9.0",
  "min_version": "1.8.0",
  "mpy_version": "v1.28",
  "changelog": "新增 OTA 固件更新功能",
  "files": [
    {
      "name": "wifi_manager.mpy",
      "hash": "a1b2c3d4",
      "size": 8200,
      "url": "https://raw.githubusercontent.com/MENGEN4J/esp32c3-power/v1.9.0/wifi_manager.mpy"
    }
  ]
}
```

### 16.6 MicroPython import 优先级

MicroPython 的 import 机制：当 `app.mpy` 和 `app.py` 同时存在时，**优先加载 `.mpy`**。因此 OTA 流程只需：

```
1. 下载 app.mpy → 校验 CRC32 → 写入文件系统
2. 删除旧版 app.py（避免同时存在）
3. 下次 import app 时自动加载 app.mpy
```

### 16.7 OTA 下载逻辑变更

```
当前: 下载 app.py → 校验 CRC32 → 备份 app.py → 替换 app.py
变更: 下载 app.mpy → 校验 CRC32 → 备份旧 app.py → 写入 app.mpy → 删除旧 app.py
```

回滚时恢复 `.py` 文件并删除 `.mpy` 文件。

### 16.8 发版流程变更

```bash
# 1. 编译 mpy-cross（已在 build_firmware.sh 中完成）
make -C micropython/mpy-cross -j4

# 2. 预编译所有 .py 为 .mpy
for f in app.py config.py logger.py utils.py ble_service.py \
         power_data.py wifi_manager.py web_pages.py ota_updater.py; do
    micropython/mpy-cross/build/mpy-cross "$f"
done

# 3. 生成 version.json（含 .mpy 哈希和 mpy_version）
python3 scripts/gen_version_json.py --mpy --version 1.9.0 \
  --mpy-version v1.28 --min-version 1.8.0 \
  --github-owner MENGEN4J --github-repo esp32c3-power

# 4. 推送 .mpy 文件和 version.json 到 GitHub
```

### 16.9 GitHub 仓库目录结构变更

```
esp32c3-power/                      ← GitHub 仓库
├── releases/
│   └── latest/
│       └── version.json            ← 永远指向最新版本（含 mpy_version）
├── v1.9.0/
│   ├── app.mpy                     ← 预编译字节码
│   ├── wifi_manager.mpy
│   └── web_pages.mpy
├── v1.8.0/                         ← 历史版本
│   └── ...
├── app.py                          ← 开发分支源码（不用于 OTA）
├── config.py
└── ...
```

### 16.10 关于 AES 加密

MicroPython ESP32 构建**不内置 `ucryptolib`**（AES），需要自定义固件才能启用。对于本项目：

- 模拟器场景，代码敏感度不高
- XOR 对称加密实现简单但安全性弱
- 引入加密会增加复杂度和密钥管理问题
- `.mpy` 字节码本身已提供基本的代码混淆

**结论：不引入加密，用 `.mpy` 字节码作为基本代码保护即可。** 如果未来确实需要加密，再考虑 XOR 或 AES。

---

## 17. 已知限制

| 限制 | 说明 | 应对 |
|------|------|------|
| 无法更新 MicroPython 运行时 | 文件级 OTA 只能替换 .py/.mpy 文件 | 运行时更新仍需 USB 烧录 |
| GitHub Raw 可能有频率限制 | 频繁请求可能被限流 | 每次配网仅检查 1 次 |
| WiFi 密码明文存储 | 已知限制（v1.8.0 及之前） | 配网模式短暂开放，可接受 |
| OTA 无加密校验 | 仅 CRC32 完整性校验，无签名验证 | 模拟器场景可接受 |
| 跨大版本不支持 OTA | min_version 限制 | 提示用户 USB 升级 |
| 回滚依赖 .bak 文件 | 极端情况 .bak 也损坏 | 保留 .bak，用户可 USB 手动恢复 |
| .mpy 版本耦合 | .mpy 必须与设备 MicroPython 版本匹配 | version.json 中 mpy_version 校验 |

---

## 18. 测试计划

| 测试项 | 验证方法 | 预期结果 |
|--------|---------|---------|
| 版本检查 | 配网后访问配置页面 | 显示「发现新版本 v1.9.0」横幅 |
| 无更新 | version.json 版本与本地相同 | 显示「当前已是最新版本」 |
| 文件下载 | 点击「立即更新」 | 逐文件下载，进度条更新 |
| CRC32 校验 | 模拟下载损坏文件 | 校验失败，提示错误，不替换 |
| 原子替换 | 下载中断电 | 重启后旧版本正常运行 |
| 自动回滚 | 更新后 __import__ 失败 | boot.py 自动从 .bak 回滚 |
| 回滚成功 | 回滚后正常启动 | 旧版本正常运行，.bak 已清理 |
| WiFi 超时 | 更新中 WiFi 超时 | 更新时暂停计时器，完成后恢复 |
| GitHub 不可达 | 断网测试 | 10 秒超时，正常功能不受影响 |
| 内存监控 | gc.mem_free() 日志 | OTA 期间可用堆 > 50KB |
| Socket 泄漏 | 多次更新后检查 | socket 及时关闭，无泄漏 |
