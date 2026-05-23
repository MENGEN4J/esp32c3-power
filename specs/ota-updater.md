# OTA 固件更新模块规格

## 公共接口

### 模块级函数

| 函数 | 说明 |
|------|------|
| `get_firmware_version()` | 获取当前固件版本号，优先读取 ota_version.json 的 `v` 字段，兼容旧字段 `current_version`，回退到 config.FIRMWARE_VERSION |

### OTAUpdater 类

| 属性/方法 | 类型 | 说明 |
|-----------|------|------|
| `current_version` | property (str) | 当前固件版本号，优先读取 ota_version.json，回退到 config.FIRMWARE_VERSION |
| `check_result` | property (dict/None) | 最近一次版本检查结果，如 `{'has_update': True, 'version': '1.9.0', ...}` |
| `download_state` | property (dict/None) | 当前下载状态，如 `{'status': 'downloading', 'completed': 2, 'total': 5, 'downloaded_bytes': 10240, 'total_bytes': 40960, ...}` |
| `check_update()` | method | 从 Gitee 获取 version.json，校验版本号和 mpy_version，返回检查结果 dict |
| `start_download()` | method | 逐文件下载 .mpy → CRC32 校验 → 原子替换 → 设置 .update_pending → machine.reset() |

### 静态方法

| 方法 | 说明 |
|------|------|
| `_ssl_wrap(sock)` | 为 socket 包装 SSL/TLS（HTTPS 连接用），SSL 不可用时抛出 OSError |
| `_crc32(data)` | 计算 bytes 数据的 CRC32 哈希值，返回 8 位十六进制字符串 |
| `_file_crc32(filepath)` | 计算文件的 CRC32 哈希值，失败返回空字符串 |
| `_parse_url(url)` | 解析 HTTP URL，返回 (host, path, port) |
| `_http_request(url, dest_path=None)` | HTTPS/HTTP 请求，dest_path=None 时返回响应内容（上限 10KB），dest_path 非空时流式下载到文件 |
| `_version_cmp(v1, v2)` | 比较两个语义化版本号，返回正/负/零 |

### 类常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `_MAX_RESPONSE_SIZE` | 10240 | _http_get 响应大小上限（字节），防止 OOM |

## 版本检查

### GIVEN: 设备已通过 WiFi STA 连接家庭网络

WHEN: WiFiManager 调用 `_auto_check_ota()`

THEN:
- 后台线程从 `config.OTA_VERSION_URL` 下载 `version.json`（HTTPS，SSL/TLS 加密连接）
- `config.OTA_VERSION_URL` 必须指向仓库默认分支上的稳定 `releases/latest/version.json` 入口，不能绑定到历史版本 tag
- 响应超过 `_MAX_RESPONSE_SIZE`(10KB) 时拒绝，防止 OOM
- 解析 JSON 获取 `version`、`min_version`、`mpy_version`、`files` 列表
- 对比 `version` > `FIRMWARE_VERSION`，且 `FIRMWARE_VERSION` >= `min_version`
- 校验 `mpy_version` 与设备 `config.MPY_VERSION` 匹配，不匹配则拒绝更新
- 结果写入 `_ota_check_result`，配置页面读取显示

### GIVEN: version.json 不可达或解析失败

WHEN: HTTP 请求超时或 JSON 格式错误

THEN:
- `_ota_check_result` 设置为 `{'has_update': False, 'error': '...'}`
- 不影响正常配网和配置功能

### GIVEN: mpy_version 与设备 MicroPython 版本不匹配

WHEN: version.json 中 mpy_version != config.MPY_VERSION

THEN:
- `_ota_check_result` 设置为 `{'has_update': False, 'error': 'MicroPython版本不匹配...'}`
- 拒绝下载，避免 .mpy 字节码版本不兼容

## 文件下载

### GIVEN: 用户点击「立即更新」且 check_result 显示有更新

WHEN: WiFiManager 调用 `_handle_start_update()`

THEN:
- 启动 `_ota_download_thread` 后台线程
- 设置 `_ota_downloading = True`，暂停 WiFi 关闭计时器
- 调用 `ota_updater.start_download()`

### GIVEN: start_download 执行中（.mpy 字节码文件）

WHEN: 遍历 files 列表处理每个 .mpy 文件

THEN:
- 计算本地 .mpy 文件 CRC32，哈希相同则跳过
- 哈希不同：
  1. 备份本地 .mpy → `.mpy.bak`（如存在）
  2. 备份本地旧 .py → `.py.bak`（如存在同名 .py）
  3. 下载 .mpy 到 `.mpy.tmp`
  4. CRC32 校验 `.mpy.tmp`
  5. 校验通过 → `os.rename` 替换为 .mpy，删除 `.py.bak`
  6. 校验失败 → 删除 `.mpy.tmp`，从 `.bak` 回滚
- 全部完成：写入 `ota_version.json`，创建 `.update_pending` 标志，`machine.reset()`

### GIVEN: MicroPython import 优先级

WHEN: 设备文件系统同时存在 `app.py` 和 `app.mpy`

THEN:
- MicroPython 优先加载 `app.mpy`（预编译字节码）
- OTA 下载 .mpy 后需删除旧 .py，避免冗余文件占用空间

### GIVEN: 下载过程中网络中断

WHEN: HTTP 请求超时或连接断开

THEN:
- `_http_download` 返回 False
- 删除 `.tmp` 文件
- 从 `.bak` 回滚 .mpy 文件和旧 .py 文件
- `_download_state` 设置为 `{'status': 'failed', 'downloaded_bytes': A, 'total_bytes': B, ...}`
- `_ota_downloading` 恢复为 False

## 安全回滚

### GIVEN: 设备重启且 `.update_pending` 标志存在

WHEN: boot.py 执行 `_check_ota_integrity()`

THEN:
- 逐个 `__import__` 9 个核心模块（MicroPython 自动优先加载 .mpy）
- 全部通过：删除 `.bak` 文件 + 删除与 .mpy 同名的旧 .py + 删除 `.update_pending` 标志
- 任一失败：将 `.bak` 还原为原文件名 + 删除所有 `.mpy` 文件 + 删除 `.update_pending` 和 `ota_version.json`

### GIVEN: 回滚后 `.bak` 文件也损坏

WHEN: `os.rename` 回滚失败

THEN:
- 保留 `.bak` 文件不删除
- 用户可通过 USB 串口手动恢复
- 设备仍尝试启动（使用当前损坏文件，可能再次触发回滚）

## API 路由

### GET /check_update

GIVEN: WiFi 已配网

WHEN: 前端请求检查更新

THEN:
- 返回 `{'has_update': true/false, 'version': '...', ...}`
- 未配网返回 `{'has_update': false, 'error': '需先配网连接WiFi'}`
- MPY 版本不匹配返回 `{'has_update': false, 'error': 'MicroPython版本不匹配...'}`

### POST /start_update

GIVEN: check_update 已返回有更新

WHEN: 前端请求开始下载

THEN:
- 返回 `{'ok': true, 'msg': 'downloading'}`
- 已在下载中返回 `{'ok': false, 'msg': '正在更新中，请稍候'}`

### GET /update_status

GIVEN: OTA 下载进行中

WHEN: 前端轮询下载进度

THEN:
- 下载中：`{'status': 'downloading', 'completed': N, 'total': M, 'percent': P}`
- 完成：`{'status': 'done', 'msg': '更新完成，设备即将重启'}`
- 失败：`{'status': 'failed', 'msg': '...'}`

## 发版流程

### GIVEN: 开发完成准备发版

WHEN: 运行 `scripts/gen_version_json.py`

THEN:
- mpy-cross 编译 .py → .mpy 字节码
- 计算 .mpy 文件 CRC32 哈希和大小
- 生成 version.json（含 mpy_version 字段）
- .mpy 文件推送到 Gitee 仓库 `releases/ota/v{version}/` 目录
- version.json 推送到 releases/latest/ 目录
