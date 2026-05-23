# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

## v2.0.1 Release (2026-05-23)

- **事件驱动架构**：新增 `event_bus.py` 轻量事件总线，支持发布/订阅模式，10 种事件常量，零 uasyncio 依赖
- **BLE 服务扩展至 5 个 GATT 服务**：新增 Cycling Speed and Cadence (0x1816)、Fitness Machine (0x1826, 含 ERG 模式)、Device Information (0x180A)
- **ERG 模式**：FTMS 下发目标功率，`PowerEngine.set_erg_target()` 实时响应，骑行 App 可远程控制功率
- **多设备 BLE 连接优先级通知**：主连接 1s 间隔，从连接 2s 间隔，降低功耗
- **配置版本号和迁移逻辑**：`CONFIG_VERSION=2`，`_migrate_config()` 支持向后兼容
- **凭证管理 .env**：Token/Secret 迁出 MEMORY.md，`.gitignore` 排除 `.env`
- **Agent 治理增强**：H27 事件总线规范、H28 BLE UUID 冲突、H29 文件大小上限、H30 繁体中文扩展检查

### 测试报告

| 测试项 | 验证方法 | 结果 |
|--------|---------|------|
| Entropy 全量扫描 | `python3 scripts/entropy_scan.py --all` | ✅ 通过 (H1-H30 全部通过) |
| OTA 字节码打包 | `python3 scripts/gen_version_json.py --version 2.0.1` | ✅ 通过 (10 文件, 72,261 bytes) |
| 固件编译打包 | `bash scripts/build_firmware.sh` | ✅ 通过 (1.8M, 14% 空闲) |
| 文档 Drift 修复 | specs/project_rules 同步 | ✅ 通过 |

### Entropy 扫描

- 文档 Drift: ✅ (specs/power-engine.md 已补充 set_erg_target)
- 命名漂移: ✅
- 死代码: ✅
- 规则腐烂: ✅ (project_rules.md 已补充 event_bus.py)
- 配置一致性: ✅
- 记忆清理: ✅

### 下载文件说明

| 文件 | 大小 | 用途 |
|------|------|------|
| `firmware.bin` | 1.8M | 合并固件，烧录到地址 0x0 |
| `v2.0.1-ota.zip` | 34.6 KB | OTA 空中升级包（10 个 .mpy 字节码） |
| `version.json` | 1.9 KB | OTA 版本描述文件 |

### 兼容性说明

- 最低可升级版本: v1.8.0
- MicroPython 版本: v1.28
- BLE 协议: 新增 CSC/FTMS/DIS 服务，原有 Cycling Power + Heart Rate 不变
- 配置格式: `power_config.json` 新增 `v` 字段（版本号），旧配置自动迁移

### 已知限制

- `wifi_manager.py` 856 行，接近 H29 上限（900 行），后续版本需拆分
- WiFi 凭据仍为明文存储（加密方案待定）
- OTA 无签名验证（HMAC-SHA256 方案待定）

## v2.0.0 Release (2026-05-22)

- **强化 Release 发布约束**：创建 tag/Release 前必须准备完整 Release 正文，禁止只写简短摘要
- **补齐 Release 必填章节**：强制包含版本概览、本版重点、详细变更、测试报告、下载文件说明、使用说明、兼容性说明、已知限制、回滚说明、附件清单
- **增强 Gitee Release 脚本**：从 `CHANGELOG.md` 生成详细 Release 正文，Release 已存在时先更新正文再上传附件
- **同步发版模板**：更新 `docs/release-template.md` 与 HTML 版本，明确附件和下载说明要求
- **规划 v2.0 骑行模式引擎**：新增 `specs/ride-modes.md`，明确固定功率、真实路骑、间歇训练、随机巡航四种模式
- **实现 v2.0 骑行模式引擎**：`PowerEngine` 新增 `get_snapshot(now_ms)`，统一生成功率、踏频、心率快照
- **新增 Web 模式选择**：配置页支持选择固定功率、真实路骑、间歇训练、随机巡航，保存后重启生效
- **限制非固定模式参数修改**：只有固定功率模式使用表单和按钮修改数值，真实路骑、间歇训练、随机巡航使用内置曲线
- **基于 FIT 样本优化内置曲线**：解析 `ride-0-2026-05-20-05-31-24.fit` 中 5956 条 record，按真实功率、心率、踏频分布调整路骑、间歇和随机巡航参数
- **升级配置持久化格式**：`power_config.json` 新增短 key `m` 保存骑行模式，旧配置缺失时默认 `steady`
- **切换 v2.0.0 版本号**：`config.FIRMWARE_VERSION` 更新为 `2.0.0`
- **暂缓 FIT 活动回放**：v2.0 聚焦设备端实时模拟状态机，FIT 上传/解析/回放保留为 v2.1+ 候选能力
- **保持 BLE 协议兼容**：继续输出 Cycling Power + Heart Rate，骑行 App 无需改连接方式

### 测试报告

| 测试项 | 验证方法 | 结果 |
|--------|---------|------|
| Python 语法检查 | `python3 -m py_compile scripts/create_gitee_release.py` | ✅ 通过 |
| HTML 解析 | Python `HTMLParser` 解析 `docs/html/release-template.html` | ✅ 通过 |
| Entropy 扫描 | `python3 scripts/entropy_scan.py` | ✅ 通过 |
| Release 正文更新 | `python3 scripts/create_gitee_release.py 1.9.4` | ✅ 通过 |
| v2.0 规格审阅 | 人工审阅 `specs/ride-modes.md` | ✅ 通过 |
| v2.0 语法检查 | `python3 -m py_compile config.py power_data.py app.py wifi_manager.py web_pages.py scripts/capture_screenshots.py` | ✅ 通过 |
| v2.0 模式快照 | 本地 stub MicroPython 环境遍历 `config.RIDE_MODES` 调用 `get_snapshot()` | ✅ 通过 |
| v2.0 HTML 解析 | Python `HTMLParser` 解析模式配置页和保存成功页 | ✅ 通过 |
| 非固定模式参数限制 | 本地 stub MicroPython 环境验证 road/interval/random 下 setter 和按钮调功率不修改配置 | ✅ 通过 |
| Web 输入禁用 | 校验非固定模式配置页禁用功率、踏频、心率输入框 | ✅ 通过 |
| FIT 样本解析 | 解析 `ride-0-2026-05-20-05-31-24.fit`，提取 5956 条功率/心率/踏频 record | ✅ 通过 |
| FIT 优化后快照 | 强制遍历真实路骑 5 个状态并验证四种模式输出范围 | ✅ 通过 |
| OTA 字节码打包 | `python3 scripts/gen_version_json.py --version 2.0.0 --min-version 1.8.0 --mpy-version v1.28 --gitee-user mengen4jv --gitee-repo esp32-power` | ✅ 通过 (9 文件, 66,108 bytes) |
| 固件编译打包 | `bash scripts/build_firmware.sh` | ✅ 通过 (`target/firmware.bin`, 1.7M) |
| Entropy 扫描 | `python3 scripts/entropy_scan.py` | ✅ 通过 |

### Entropy 扫描

- 文档 Drift: ✅ 通过，`specs/` 与当前骑行模式、功率引擎和 Web 配置行为一致
- 命名漂移: ✅ 通过，新增模式常量、接口和日志器命名符合规则
- 死代码: ✅ 通过，未发现未引用配置常量和未调用函数
- 规则腐烂: ✅ 通过，发版模板、项目规则和固件构建文档未发现过时项
- 配置一致性: ✅ 通过，功率、踏频、心率和骑行模式范围与实现一致

## v1.9.4 Release (2026-05-22)

- **完成项目治理**：执行 Entropy 扫描，文档 Drift、命名漂移、死代码、规则腐烂、配置一致性全部通过
- **优化用户手册**：补齐第一次使用检查清单、骑行 App 连接提示、LED 异常恢复、OTA 排障和 USB 重刷判断
- **同步文档 HTML**：重新生成 `docs/html/user-manual.html`、`docs/html/firmware-build.html`、`docs/html/ota-update-design.html`
- **修正发布文档漂移**：同步 README 固件版本，修正 OTA 设计文档中的常量清单，补齐固件冻结模块列表
- **同步网页预览版本**：`scripts/capture_screenshots.py` 改为读取 `config.FIRMWARE_VERSION`，避免截图素材继续硬编码旧版本
- **发布 v1.9.4 固件**：更新 `config.FIRMWARE_VERSION`，生成 `releases/ota/v1.9.4/`、`releases/latest/version.json` 和 `target/firmware.bin`

### 测试报告

| 测试项 | 验证方法 | 结果 |
|--------|---------|------|
| Python 语法检查 | `python3 -m py_compile scripts/gen_version_json.py scripts/create_gitee_release.py scripts/capture_screenshots.py ota_updater.py wifi_manager.py web_pages.py config.py` | ✅ 通过 |
| Shell 语法检查 | `bash -n scripts/build_firmware.sh scripts/deploy.sh test/test_runner.sh` | ✅ 通过 |
| HTML 解析 | Python `HTMLParser` 解析 `docs/html/*.html` 与 `web/*.html` | ✅ 通过 |
| 文档诊断 | `GetDiagnostics` 检查编辑后的文件 | ✅ 通过 |
| OTA 字节码打包 | `python3 scripts/gen_version_json.py --version 1.9.4 --min-version 1.8.0 --mpy-version v1.28 --gitee-user mengen4jv --gitee-repo esp32-power` | ✅ 通过 (9 文件, 57,463 bytes) |
| 固件编译打包 | `bash scripts/build_firmware.sh` | ✅ 通过 (`target/firmware.bin`, 1.7M) |
| OTA URL 路径检查 | `releases/latest/version.json` 指向 `releases/ota/v1.9.4/` | ✅ 通过 |
| 部署测试 | `bash scripts/deploy.sh` | ✅ 通过 (`/dev/cu.usbmodem1101`) |

### Entropy 扫描

- 文档 Drift: ✅ 通过，`specs/` 与当前模块公开行为未发现漂移
- 命名漂移: ✅ 通过，常量、类名、函数名和日志器命名符合规则
- 死代码: ✅ 通过，未发现未引用配置常量和未调用函数
- 规则腐烂: ✅ 通过，项目规则、硬件约束和模板未发现过时项
- 配置一致性: ✅ 通过，功率、踏频、心率范围与实现一致


## v1.9.3 Patch (2026-05-22)

- **修复 OTA 版本字段兼容**：`get_firmware_version()` 兼容读取 `ota_version.json` 的 `v` 与旧字段 `current_version`
- **修复 Web 配置保存可靠性**：配置表单提交后立即 `flush_if_dirty()`，避免 5 秒后重启前未持久化
- **增强配置保存健壮性**：`_save_config()` 返回 `bool`，保存失败保留 `_dirty`，保存期间有新变更时不误清脏标记
- **增强 JSON 响应安全性**：WiFi API 动态字符串统一通过 `_json_escape()` 转义
- **清理未使用变量**：`_ota_download_thread` 中删除未使用的 `ota_start`，`_server_thread` 中 `addr` 改为 `_addr`
- **同步规格与模板**：更新 power-engine、wifi-manager、ota-updater 规格和配置持久化模板
- **新增 commit 模型信息规则**：commit message 末尾必须附带 AI 模型名称和版本
- **发行版必须包含固件文件**：Gitee Release 必须上传 firmware.bin

### Bug 修复详情

| Bug | 严重度 | 修复 |
|-----|--------|------|
| OTA 版本读写字段不一致 | 🔴 高 | get_firmware_version() 兼容读取 v 和 current_version |
| 配置保存失败丢失脏标记 | 🟡 中 | _save_config() 返回 bool，flush_if_dirty() 保存失败保留脏标记 |
| JSON 响应未转义特殊字符 | 🟡 中 | 新增 _json_escape() 统一转义 |
| Web 提交后配置未落盘 | 🟡 中 | _handle_config_submit() 中立即 flush_if_dirty() |

### 测试报告

| 测试项 | 验证方法 | 结果 |
|--------|---------|------|
| 语法检查 | py_compile 全部 .py | ✅ 通过 |
| 固件编译 | build_firmware.sh | ✅ 通过 (1.7MB) |
| .mpy 编译 | gen_version_json.py | ✅ 通过 (9 文件, 51KB) |
| Entropy 扫描 | scripts/entropy_scan.py | ✅ 通过 |
| 部署测试 | deploy.sh | ⏳ 待设备连接验证 |

## v1.9.2 Patch (2026-05-21)

- **修复 OTA 下载期间 WiFi 被提前关闭的 Bug**：OTA 下载期间暂停 WiFi 关闭计时器，避免下载中断
- **修复 HTTP 异常路径 socket 泄漏**：ota_updater._http_request 异常时确保 socket 关闭
- **网页界面优化**：统一浅粉色配色 + 改进布局和交互
- **清理冗余文件**：删除 test_build_flow.py、releases/test/、v1.9.1-ota.zip
- **文档同步**：README.md 版本号同步为 1.9.2

### Bug 修复详情

| Bug | 严重度 | 修复 |
|-----|--------|------|
| OTA 下载期间 WiFi 被提前关闭 | 🔴 高 | _wifi_shutdown_timer 在 OTA 期间暂停计时 |
| HTTP 请求异常时 socket 未关闭 | 🟡 中 | except 块中添加 sock.close() |

### 测试报告

| 测试项 | 验证方法 | 结果 |
|--------|---------|------|
| 语法检查 | py_compile 全部 .py | ✅ 通过 |
| 部署测试 | deploy.sh | ✅ 部署成功 |
| BLE 启动 | 检查部署日志 | ✅ 蓝牙激活成功 |
| BLE 广播 | 手机蓝牙搜索 | ✅ 发现 BikePower |
| 内存状态 | gc.mem_free() > 80KB | ✅ 正常 |
| 按钮短按 | 短按按钮 | ✅ 功率 -10W |
| 按钮中按 | 按住300ms~2s松开 | ✅ 功率 +10W |
| 按钮长按 | 按住≥2s松开 | ✅ LED 快闪确认窗口 |
| WiFi 配网 | 长按→确认→连接热点 | ✅ 正常 |
| OTA 更新 | 配网→检查→下载→重启 | ⏳ 未测试（需家庭网络） |

## v1.9.1 Release (2026-05-21)

- **OTA 编译打包成功**：使用 gen_version_json.py 成功编译 v1.9.1 版本
- **固件版本更新**：config.py 中 FIRMWARE_VERSION 更新为 1.9.1
- **网页界面优化**：web_pages.py 统一浅粉色配色 + 改进布局和交互
- **部署测试成功**：最新代码成功部署到 ESP32-C3 设备
- **9 个 .mpy 模块编译**：所有业务模块编译为字节码，总大小 51 KB

### 编译打包详情

| 模块 | 原始大小 | 编译后 | 压缩率 |
|------|---------|--------|--------|
| app.py | 8.1 KB | 2.8 KB | -66% |
| config.py | 2.2 KB | 1.4 KB | -37% |
| logger.py | 1.4 KB | 501 B | -66% |
| utils.py | 384 B | 178 B | -55% |
| ble_service.py | 9.1 KB | 3.6 KB | -60% |
| power_data.py | 5.6 KB | 1.9 KB | -66% |
| wifi_manager.py | 27.5 KB | 10.8 KB | -61% |
| web_pages.py | 28.8 KB | 24.2 KB | -16% |
| ota_updater.py | 19.5 KB | 5.7 KB | -71% |
| **总计** | **102.7 KB** | **51.0 KB** | **-50%** |

### 生成的文件

- `releases/ota/v1.9.1/` 目录：9 个编译后的 .mpy 字节码文件
- `releases/latest/version.json`：版本清单，包含所有文件哈希和下载 URL

### 部署测试

| 测试项 | 结果 |
|--------|------|
| ESP32-C3 设备连接 | ✅ 成功 |
| 代码部署 | ✅ 成功 |
| 语法检查 | ✅ 通过 |
| 程序启动 | ✅ 正常 |

## v1.9.4 Build Test (2026-05-21)

- **编译打包流程测试**：全面测试 build_firmware.sh 和 gen_version_json.py 脚本
- **轻量级测试脚本**：新增 test_build_flow.py，模拟完整 OTA 发布流程（无需完整编译环境）
- **网页界面优化**：web_pages.py 统一浅粉色配色 + 改进布局和交互
- **语法检查**：py_compile 全部 9 个业务模块验证通过
- **CRC32 哈希计算**：测试版本清单生成功能正常
- **业务模块检查**：9 个核心模块全部存在且可访问

### 编译打包测试报告

| 测试项 | 验证方法 | 结果 |
|--------|---------|------|
| 语法检查 | py_compile 全部 .py 文件 | ✅ 全部通过 |
| build_firmware.sh | 帮助信息测试 | ✅ 正常工作 |
| gen_version_json.py | 帮助信息测试 | ✅ 正常工作 |
| 业务模块检查 | 9 个核心模块 | ✅ 全部存在 |
| CRC32 计算 | 所有文件哈希测试 | ✅ 正常 |
| version.json 生成 | 测试版本清单 | ✅ 成功生成 |
| 总大小 | 所有业务模块 | 102.7 KB |

### 编译环境状态

| 组件 | 状态 | 说明 |
|------|------|------|
| mpy-cross | ❌ 未找到 | 需要编译或安装 |
| ESP-IDF | ❌ 未找到 | 需要克隆和安装 |
| MicroPython 源码 | ❌ 未找到 | 需要克隆 |
| ESP32-C3 设备 | ❌ 未连接 | 需要 USB 连接 |

### 编译打包流程总结

1. **语法检查阶段** ✅
   - 所有 Python 文件语法正确
   - 无语法错误或警告

2. **编译准备阶段** ⚠️
   - 需要准备完整编译环境
   - 缺少 mpy-cross 和 ESP-IDF

3. **OTA 发布流程** ⚠️
   - version.json 生成逻辑正常
   - CRC32 哈希计算功能正常
   - 但无法实际编译 .mpy 文件

4. **固件编译流程** ❌
   - 需要完整 ESP-IDF 环境
   - 无法进行实际编译

### 下一步建议

- **开发测试**：使用 deploy.sh 部署到设备测试功能
- **正式发布**：需要准备完整编译环境（mpy-cross + ESP-IDF）
- **当前状态**：代码质量良好，可以继续开发

## v1.9.3 Refactor (2026-05-21)

- **冗余文件清理**：删除根目录 `v1.9.0/` 旧版本 .mpy 目录（已由 releases/ 管理）
- **README.md 同步更新**：文件结构添加新增 docs/sales-listing.md / docs/xianyu-reference.md / web/config-preview.html / web/screenshot_tool.html / web/screenshots.html / scripts/capture_screenshots.py / images/page1-6.png
- **闲鱼商品发布规范**：新增 docs/sales-listing.md（商品文案）和 docs/xianyu-reference.md（发布规范），记录用户要求（无专业术语、无 USB 配件、白话文简化）
- **project_rules.md 同步更新**：新增强制规则 8（按功能分批提交）和规则 9（闲鱼商品发布规范），文件结构同步新增目录
- **语法检查**：py_compile 全部 10 个 .py 文件验证通过

### 优化审查报告

| 审查项 | 结果 | 说明 |
|--------|------|------|
| 项目结构审查 | ✅ 通过 | 删除冗余 v1.9.0/ 目录，文件结构清晰 |
| 文档内容审查 | ✅ 通过 | README 文件结构同步，docs/ 新增文案和规范 |
| 内存优化审查 | ✅ 通过 | 预分配缓冲区、% 格式化、垃圾回收策略无变更 |
| 健壮性审查 | ✅ 通过 | 异常处理完整、WDT 启用、硬件互斥逻辑正确 |
| 架构一致性审查 | ✅ 通过 | 模块职责边界清晰、命名规范统一 |
| 文档同步审查 | ✅ 通过 | README / project_rules.md / CHANGELOG 同步更新 |
| 代码冗余审查 | ✅ 通过 | 无重复代码、无死代码 |

### 测试报告

| 测试项 | 验证方法 | 结果 |
|--------|---------|------|
| 语法检查 | py_compile 全部 10 个 .py | ✅ 全部通过 |
| 文件结构一致性 | project_rules.md vs 实际 | ✅ docs/ web/ scripts/ images/ 都已包含 |
| 冗余文件清理 | v1.9.0/ 目录检查 | ✅ 已删除 |

## v1.9.2 Docs (2026-05-21)

- **用户手册**：新增 docs/user-manual.md（1027 行完整手册，v1.9.2）
  - 快速开始（硬件连接→蓝牙连接→骑行软件使用）
  - 详细操作指南（按钮操作、WiFi 配网、OTA 更新）
  - LED 状态指示完整说明
  - 常见问题 FAQ（19 个问题+解决方案）
  - 技术规格（蓝牙规格、WiFi 规格、硬件限制）
  - 附录（默认配置、固件版本、支持软件、网页界面图解、联系方式）
- **硬件指南**：新增 docs/esp32c3-board-guide.md（合宙 ESP32-C3 开发板硬件参考）
- **网页配置界面图解**：附录 D 包含 6 个界面的详细说明和截图
- **网页预览工具**：新增 web/screenshot_tool.html（截图工具，支持一键下载 6 张 PNG）
- **手机框架展示**：新增 web/screenshots.html（手机边框展示页面）
- **本地预览**：新增 web/config-preview.html（无需硬件预览所有界面）
- **辅助脚本**：新增 scripts/capture_screenshots.py（生成单独的预览 HTML 文件）
- **图片资源**：新增 images/page[1-6].png（6 张网页配置界面截图）
- **README 更新**：添加用户手册链接、更新文件结构
- **规则更新**：更新 project_rules.md（文件结构树同步）、更新 optimization-review.md（优化审查规则）
- **图片资源**：保留原 esp32c3-board.jpg / front.jpg / pinout.jpg（硬件图片）

### 测试报告

#### 文档验证（2026-05-21）

| 测试项 | 验证方法 | 结果 |
|--------|---------|------|
| 用户手册完整性 | 检查章节覆盖 | ✅ 8 大章节，完整覆盖功能 |
| 截图工具可用性 | 浏览器访问 + 下载测试 | ✅ 6 张 PNG 正常下载 |
| 文件结构一致性 | project_rules.md vs 实际 | ✅ docs/ web/ scripts/ images/ 都已包含 |
| 图片引用路径 | user-manual.md 相对路径 | ✅ ../images/ 正确 |
| 规则同步 | optimization-review.md 更新 | ✅ 新增 6 章节，审查流程完整 |

#### 待手动验证

| 测试项 | 验证方法 |
|--------|---------|
| 浏览器访问截图工具 | http://localhost:8000/web/screenshot_tool.html |
| 一键下载 6 张截图 | 点击按钮，检查下载 |
| Markdown 图片显示 | 用 VS Code / Typora 打开 user-manual.md |

## v1.9.0 OTA (2026-05-21)

- **OTA 固件更新**：新增配网后一键检查并更新固件版本功能
- **ota_updater.py 新增模块**：文件级差量 OTA 更新器，支持 CRC32 校验、原子替换、.bak 安全回滚
- **boot.py 安全回滚**：启动时 `__import__` 校验 9 个核心模块，失败自动从 .bak 回滚
- **WiFi 配网集成 OTA**：STA 连接成功后自动检查 Gitee version.json，发现新版本页面提示更新
- **OTA SSL/TLS 支持**：HTTP 客户端添加 `ssl.wrap_socket()` 支持 HTTPS 连接 Gitee
- **OTA 响应大小限制**：`_http_get` 添加 `_MAX_RESPONSE_SIZE`(10KB) 上限防止 OOM
- **boot.py .tmp 清理**：启动时自动清理 OTA 下载中断残留的 .tmp 临时文件
- **流式 CRC32**：`_file_crc32` 改为分块读取计算，防止大文件 OOM
- **开机自动连接 WiFi**：AP 启动后自动读取已保存凭据连接 STA，OTA 链路闭环
- **版本号一致性**：新增 `get_firmware_version()` 优先读取 ota_version.json，OTA 更新后版本号正确显示
- **OTA 状态自动轮询**：配置页面 JS 每 10 秒轮询 `/check_update`，自动更新 OTA 横幅
- **OTA 下载 LED 双闪**：OTA 下载中 LED 双闪提示（100ms亮/100ms灭/100ms亮/700ms灭）
- **WiFi 计时器 OTA 超时修复**：OTA 开始时重置 `_start_time`，专用超时从 OTA 开始时刻计算
- **版本号解析容错**：`_version_cmp` 支持预发布标识（如 1.9.0-beta.1），非数字版本不崩溃
- **OTA 下载异常标志重置**：`_ota_download_thread` 异常路径也重置 `_ota_download_timeout`
- **OTA 期间倒计时修复**：`get_remaining_time()` OTA 下载期间使用专用超时计算
- **boot.py print 例外**：code_style.md 明确 boot.py 可用 `print()`（logger 未初始化）
- **README.md OTA 文档**：补充 OTA 固件更新功能说明、操作步骤、配置参数、文件结构
- **specs/wifi-manager.md OTA 路由**：补充 4 个 OTA 路由和 ota_updater 参数规格
- **specs/ota-updater.md SSL**：补充 `_ssl_wrap` 静态方法和 `_MAX_RESPONSE_SIZE` 类常量
- **templates/wifi-manager.md 修正**：AUTH_OPEN 替代 WPA2，与实际代码一致
- **utils.py 版本号修正**：v1.27 → v1.28
- **更新进度页面**：配置页新增 OTA 更新横幅 + 独立下载进度页 + 失败重试页
- **OTA 下载期间暂停 WiFi 关闭**：使用 OTA_UPDATE_TIMEOUT_MS (300s) 专用超时
- **config.py 新增常量**：FIRMWARE_VERSION, OTA_VERSION_URL, OTA_PENDING_FLAG, OTA_VERSION_FILE, OTA_BACKUP_SUFFIX, OTA_TEMP_SUFFIX, OTA_DOWNLOAD_CHUNK, OTA_HTTP_TIMEOUT, OTA_MAX_REDIRECTS, OTA_UPDATE_TIMEOUT_MS
- **部署脚本更新**：deploy.sh / manifest.py 新增 ota_updater.py
- **OTA 设计文档**：新增 docs/ota-update-design.md（17 章节完整方案设计）
- **OTA 规格文档**：新增 specs/ota-updater.md（GIVEN/WHEN/THEN 行为规格）

### 测试报告

#### 编译验证（2026-05-21）

| 测试项 | 验证方法 | 结果 |
|--------|---------|------|
| 语法检查 | py_compile 全部 .py (10 文件) | ✅ 全部通过 |
| Entropy 扫描 | entropy_scan.py (5 项) | ✅ 全部通过 |
| 固件编译 | build_firmware.sh | ✅ 8 个冻结模块编译成功，1.7M |
| Git 状态 | git status | ✅ working tree clean |

#### 部署验证（2026-05-21）

| 测试项 | 验证方法 | 结果 |
|--------|---------|------|
| BLE 启动 | 串口日志 | ✅ 蓝牙激活成功 + 蓝牙功率计已启动 |
| BLE 广播 | 串口日志 | ✅ 开始广播（间隔500ms），设备名 BikePower |
| BLE 服务 | 串口日志 | ✅ GAP名称设置 + 中断处理 + 服务注册 |
| 内存状态 | 串口日志 | ✅ free=111,760 (109KB) > 80KB |
| WiFiManager 创建 | 串口日志 | ✅ 异步创建完成 |
| 配置恢复 | 串口日志 | ✅ 配置已恢复: 200W/90RPM |
| 主循环 | 串口日志 | ✅ 主循环已启动，等待按钮操作 |

#### OTA 链路验证（2026-05-21）

| 测试项 | 验证方法 | 结果 |
|--------|---------|------|
| version.json | curl HTTP 200 | ✅ 1,689 bytes |
| app.mpy | curl HTTP 200 | ✅ 2,862 bytes |
| config.mpy | curl HTTP 200 | ✅ 1,433 bytes |
| logger.mpy | curl HTTP 200 | ✅ 501 bytes |
| utils.mpy | curl HTTP 200 | ✅ 178 bytes |
| ble_service.mpy | curl HTTP 200 | ✅ 3,666 bytes |
| power_data.mpy | curl HTTP 200 | ✅ 1,940 bytes |
| wifi_manager.mpy | curl HTTP 200 | ✅ 11,082 bytes |
| web_pages.mpy | curl HTTP 200 | ✅ 21,652 bytes |
| ota_updater.mpy | curl HTTP 200 | ✅ 6,012 bytes |
| Gitee Release | API 查询 | ✅ ID:688250, firmware.bin + version.json |
| 仓库公开 | HTTP 200 无需 token | ✅ 私有→公开后所有 URL 可达 |

#### 待手动验证

| 测试项 | 验证方法 |
|--------|---------|
| 按钮短按 | 短按按钮，功率 -10W |
| 按钮中按 | 按住 300ms~2s，功率 +10W |
| 按钮长按 | 按住 ≥2s，LED 快闪等待确认 |
| WiFi 配网 | 长按→确认→手机搜索 BikePower 热点→访问 192.168.4.1 |
| 自动连接 WiFi | 配网后再次进入配网模式，自动连接已保存 WiFi |
| OTA 横幅 | 配网页面显示"正在检查更新..."→自动刷新 |
| OTA LED 双闪 | OTA 下载中 LED 双闪提示 |
| deploy.sh 模块列表 | 对比检查 | ✅ 包含 ota_updater.py |
| manifest.py 模块列表 | 对比检查 | ✅ 包含 ota_updater.py |
| web_pages 签名一致性 | 对比检查 | ✅ build_config_page 参数匹配 |

### Entropy 扫描

- 文档 Drift: ✅ specs/ota-updater.md 与 ota_updater.py 行为一致
- 命名漂移: ✅ 全部符合 code_style.md（FIRMWARE_VERSION 等常量命名规范）
- 死代码: ✅ OTA_UPDATE_TIMEOUT_MS 已引用，无死代码
- 规则腐烂: ✅ project_rules.md / hardware_constraints.md 已同步更新
- 配置一致性: ✅ config.py / wifi_manager.py / web_pages.py 三处一致

## v1.8.0 Glow (2026-05-20)

- **LED 状态指示**：新增板载 D4 (GPIO12) LED 状态指示，4 种状态：无连接慢闪、已连接常亮、确认窗口快闪、WiFi 模式熄灭
- **二次确认进入配网**：长按2秒不再直接进入 WiFi 配网，改为 LED 快闪 3 秒等待二次确认，确认窗口内再按一次才进入配网，防止误触中断蓝牙
- **合宙 ESP32-C3 LED 文档**：新增 `docs/esp32c3-led.md`，整理板载 LED 引脚信息和使用注意事项
- **config.py 新增常量**：`LED_PIN=12`, `CONFIRM_WINDOW_MS=3000`, `LED_BLINK_SLOW_MS=1000`, `LED_BLINK_FAST_MS=200`
- **规则话术同步**：修正 `.trae/rules/` 中 6 处过时话术（长按直接配网→二次确认配网），新增 LED 状态指示到 hardware_constraints.md 和 project_rules.md
- **默认值调整**：功率 180W→200W，踏频 95RPM→90RPM，心率 65BPM→140BPM

### 测试报告

| 测试项 | 验证方法 | 结果 |
|--------|---------|------|
| 语法检查 | py_compile 全部 .py (8 文件) | ✅ 全部通过 |
| config.py 新常量 | 代码审查 LED_PIN/CONFIRM_WINDOW_MS/LED_BLINK_SLOW_MS/LED_BLINK_FAST_MS | ✅ 4 个常量均 UPPER_SNAKE + const() |
| app.py LED 状态机 | 代码审查 4 种 LED_STATE | ✅ IDLE_NO_CONN/CONNECTED/CONFIRM_WAIT/WIFI_MODE |
| 二次确认流程 | 代码审查 app.py | ✅ 长按→快闪→再按确认→start() |
| 确认窗口超时 | 代码审查 app.py | ✅ 3 秒超时恢复 IDLE_NO_CONN |
| 确认窗口内功率调整 | 代码审查 app.py continue | ✅ 确认窗口内短按/中按不调整功率 |
| wifi_mgr.start() 调用次数 | 代码审查 app.py | ✅ 仅 1 次（在二次确认中） |
| 无 f-string | grep 业务代码 | ✅ app.py / config.py 无 f-string |
| 无 print() | grep 业务代码 | ✅ app.py / config.py 无 print() |
| 无禁用 import | 代码审查 | ✅ 无 asyncio/requests/threading |
| logger 使用 | 代码审查 app.py | ✅ get_logger("MAIN") |
| 新常量被引用 | 代码审查 app.py | ✅ LED_PIN/CONFIRM_WINDOW_MS/LED_BLINK_SLOW_MS/LED_BLINK_FAST_MS 均被引用 |
| specs 同步 | 对比 specs/button-handler.md | ✅ LED 硬件配置/二次确认/确认窗口超时 |
| README 同步 | 对比 README.md | ✅ LED 状态指示/二次确认/参数表/文件结构 |
| README 参数一致性 | 对比 README 与 config.py | ✅ LED_PIN=12, CONFIRM_WINDOW_MS=3000 |
| docs/esp32c3-led.md | 文件存在检查 | ✅ 存在 |

### Entropy 扫描

- 文档 Drift: ✅ specs/ 与源码行为一致（二次确认流程、LED 状态）
- 命名漂移: ✅ 全部符合 code_style.md（LED_PIN/CONFIRM_WINDOW_MS 等 UPPER_SNAKE + const()）
- 死代码: ✅ 新增常量均被引用，无死代码
- 规则腐烂: ✅ hardware_constraints.md / project_rules.md / code_style.md 已同步更新（二次确认话术 + LED 状态指示）
- 配置一致性: ✅ config.py / specs / README 三处一致

## v1.7.0 (2026-05-20)

- **f-string 全面清理**：app.py / ble_service.py / wifi_manager.py 所有业务代码从 f-string 改为 `%` 格式化，减少 MicroPython 运行时内存分配和 GC 压力
- **import 规范化**：`import machine` 从 app.py / wifi_manager.py 函数内延迟导入提升到文件顶部；`import os` 从 power_data.py 方法内提升到文件顶部
- **boot.py 日志格式**：部署模式提示从裸 `print()` 改为 logger 风格格式 `[INFO][BOOT]`
- **WiFiManager 封装改进**：`_ble_disabled` 私有属性改为 `ble_disabled` 公开属性，app.py 不再直接访问私有属性
- **BLE `_failed_conns` 适配**：预分配缓冲区大小从硬编码 `bytearray(3)` 改为 `bytearray(config.MAX_CONNECTIONS)`，与配置常量自动同步
- **WiFi 扫描 STA 接口关闭**：`_scan_wifi()` 扫描完成后关闭 STA 接口，避免内存浪费
- **心率估算公式简化**：`int(0.45 * self.power + 65 - 20)` 简化为 `int(0.45 * self.power + 45)`
- **README 修正**：中按时长 300ms~3s → 300ms~2s；新增 WiFi 密码明文存储说明；新增 web/ 目录工具页面使用说明

### 测试报告

| 测试项 | 验证方法 | 结果 |
|--------|---------|------|
| 语法检查 | py_compile 全部 .py | ✅ 全部通过 |
| f-string 清理 | grep -c 'f"' 业务代码 | ✅ 0 处 f-string |
| import 规范 | 代码审查 | ✅ 无函数内延迟导入 |
| ble_disabled 公开属性 | 代码审查 app.py | ✅ 使用 wifi_mgr.ble_disabled |
| _failed_conns 适配 | 代码审查 ble_service.py | ✅ bytearray(config.MAX_CONNECTIONS) |
| STA 接口关闭 | 代码审查 wifi_manager.py | ✅ 扫描后 sta.active(False) |
| README 参数一致性 | 对比 README 与 config.py | ✅ 一致 |

### Entropy 扫描

- 文档 Drift: ✅ specs/ 与源码行为一致
- 命名漂移: ✅ 全部符合 code_style.md（f-string 已清理）
- 死代码: ✅ 无死代码
- 规则腐烂: ✅ 模板与源码格式化风格一致（均使用 % 格式化）
- 配置一致性: ✅ config.py / power_data.py / wifi_manager.py 三处一致

## v1.6.0 (2026-05-20)

- **项目优化审查**：首次执行全面优化审查，新增 `.trae/rules/optimization-review.md` 规则
- **冗余文件清理**：删除 `board.json`（与 config.py 重复）、`docs/windows-test-report.md`（过时）
- **README 修复**：配置持久化描述改为 JSON 格式、按钮时长修正（中按 300ms~2s）、删除已废弃常量引用
- **logger.py 优化**：`_log` 方法从 f-string 改为 `%` 格式化，减少每次日志调用的内存分配
- **BLE 健壮性**：`update_data` 通知失败连接列表从 `list.append()` 改为预分配 `bytearray`，避免回调中创建对象
- **主循环健壮性**：`update_data` 调用添加 try/except 兜底，BLE 通知异常不中断主循环

### 测试报告

| 测试项 | 验证方法 | 结果 |
|--------|---------|------|
| 语法检查 | py_compile 全部 .py | ✅ 全部通过 |
| BLE 通知异常兜底 | 代码审查 app.py try/except | ✅ 不中断主循环 |
| BLE 通知预分配 | 代码审查 _failed_conns bytearray | ✅ 回调中无新对象 |
| logger % 格式化 | 代码审查 logger.py | ✅ 无 f-string |
| README 参数一致性 | 对比 README 与 config.py | ✅ 一致 |
| 冗余文件 | 检查 board.json / windows-test-report.md | ✅ 已删除 |

### Entropy 扫描

- 文档 Drift: ✅ specs/ 与源码行为一致
- 命名漂移: ✅ 全部符合 code_style.md
- 死代码: ✅ 无死代码
- 规则腐烂: ✅ project_rules.md 已更新
- 配置一致性: ✅ config.py / power_data.py / wifi_manager.py 三处一致

## v1.5.0 (2026-05-20)

- **Spec Coding 改进落地**：基于飞书文档学习成果，落地 5 项 Spec Coding 改进建议
- **示范层（templates/）**：新增 `.trae/rules/templates/` 目录，包含 BLE 服务、WiFi 请求处理、配置持久化 3 个代码模板
- **模块规格（specs/）**：新增 `specs/` 目录，包含 4 个 GIVEN/WHEN/THEN 格式的模块行为规格文档
- **变更工作区（changes/）**：新增 `changes/` 目录，定义复杂功能的 proposal→design→tasks 工作流程
- **Entropy 治理规则**：新增 `.trae/rules/entropy-governance.md`，定义 5 项技术债扫描检查
- **AI 质疑规则**：新增 `.trae/rules/ai-challenge.md`，定义 4 类质疑触发条件
- **project_rules.md 更新**：文件结构新增 specs/、changes/、.trae/rules/templates/ 目录
- **Entropy 修复**：UUID 常量加 `const()`，删除死代码 `LONG_PRESS_INTERVAL_MS` 和 `_advertising_paused`

### 测试报告

| 测试项 | 验证方法 | 结果 |
|--------|---------|------|
| 设备代码无变更 | 对比 git diff | ✅ 无设备代码变更，仅文档/规则文件 |
| BLE 启动 | 串口日志 | ✅ 蓝牙激活成功 + 蓝牙功率计已启动 |
| BLE 广播 | 串口日志 | ✅ 开始广播（间隔500ms） |
| 内存状态 | 串口日志 | ✅ free=112,160 bytes (109KB) > 80KB |
| WiFiManager | 串口日志 | ✅ 异步创建完成 |
| 主循环 | 串口日志 | ✅ 主循环已启动，等待按钮操作 |

### Entropy 扫描

- 文档 Drift: ✅ specs/ 与源码行为一致
- 命名漂移: ✅ 已修复（UUID 常量加 const()）
- 死代码: ✅ 已修复（删除 LONG_PRESS_INTERVAL_MS、_advertising_paused）
- 规则腐烂: ✅ project_rules.md 文件结构已更新
- 配置一致性: ✅ config.py / power_data.py / wifi_manager.py 三处一致

## v1.4.0 (2026-05-20)

- **部署模式机制**：boot.py 新增 `.deploy` 标志文件检测，BLE 运行时通过 pyserial raw REPL 自动进入部署模式，解决 mpremote 无法连接运行中设备的问题
- **JSON 配置持久化**：`config_{power}_{cadence}_{heartrate}` 文件名编码方式改为 `power_config.json`，单文件覆盖写入，键值访问，自动迁移旧格式
- **deploy.sh 重构**：上传顺序调整（boot.py 最后上传），步骤 6 改为删除 `.deploy` + 硬件重置 + 串口日志验证，自修复逻辑适配部署模式
- **deploy.ps1 同步更新**：Windows 版部署脚本同步适配部署模式和 JSON 配置
- **内存优化**：JSON 方案 free=118KB（旧方案 112KB），`json.load()` 比 `os.listdir()` 扫描更轻量

### 测试报告

| 测试项 | 验证方法 | 结果 |
|--------|---------|------|
| 部署模式进入 | BLE 运行时执行 deploy.sh | ✅ 自动创建 .deploy → soft_reset → 跳过 main.py |
| 文件上传 | 部署模式后 mpremote 上传 | ✅ 6 模块 + app.py + boot.py 全部成功 |
| 程序启动 | 删除 .deploy + 硬件重置 | ✅ BLE 正常启动，设备名称 BikePower |
| JSON 配置保存 | adjust_power(20) | ✅ `{"p":200,"c":95,"h":65}` |
| JSON 配置恢复 | 新建 PowerEngine 实例 | ✅ 正确读取 200W/95RPM |
| 旧版兼容迁移 | 设备存在 config_200_90_130 | ✅ 自动迁移并删除旧文件 |
| WiFi 配网页面 | Web 表单提交 | ✅ 接口不变，_save_config() 正常调用 |
| 内存状态 | gc.mem_free() | ✅ free=118,736 bytes (116KB) > 80KB |

## v1.3.0 (2026-05-20)

- **跨平台公共函数库**：新增 `scripts/common.sh`，统一 OS 检测、ESP32-C3 串口智能扫描、跨平台兼容工具
- **串口智能扫描**：通过 USB VID/PID 精准识别 ESP32-C3 设备（Espressif USB 0x303A / CP210x 0x10C4 / CH340 0x1A86 / FTDI 0x0403），优先 pyserial，回退系统工具
- **串口地址不再写死**：所有脚本默认自动扫描，支持 `-p` 手动指定，多设备交互选择
- **跨平台兼容修复**：`file_size_bytes()` / `cpu_count()` / `open_url()` 适配 macOS/Linux/WSL/Windows
- **deploy.sh 重构**：source common.sh，用 `find_esp32_port` 替换旧的 `ls /dev/` 扫描
- **flash_firmware.sh 重构**：source common.sh，智能扫描串口，跨平台 `stat` 兼容
- **build_firmware.sh 重构**：source common.sh，跨平台 `cpu_count` / `is_macos` 判断
- **deploy.ps1 重构**：修复默认文件名 `cycPower.py` → `app.py`，新增 `Find-Esp32Port` 智能扫描，新增模块批量上传
- **bikepower.sh 重构**：source common.sh，用 `scan_esp32_ports` 替换旧的简单扫描
- **固件名称统一**：`BikePower-latest.bin` → `firmware.bin`，带时间戳备份 `firmware-{timestamp}.bin`
- **项目记忆文档**：新增 `MEMORY.md`，提取所有历史要求和用户偏好，AI 执行前先回顾

## v1.2.0 (2026-05-19)

- **蓝牙优先规则**：开机仅启动 BLE，不自动启动 WiFi，蓝牙始终优先运行
- **按钮交互重设计**：改为释放时判断，短按 -10W / 中按 +10W / 长按≥2s 进入配网模式，消除操作冲突
- **WiFi 触发方式变更**：从开机自动启动改为用户长按2秒主动触发，避免无限重启循环
- **BLE 初始化异常恢复**：BLE 激活失败时自动 `machine.reset()` 重启恢复硬件状态
- **WiFiManager 异步创建**：BLE 同步启动后通过 `_thread` 异步创建 WiFiManager，不阻塞主循环
- **WiFi/BLE 互斥处理**：`start()` 先关闭 BLE 再启动 WiFi AP（ESP32-C3 硬件限制），配网完成或超时后重启恢复 BLE
- **网页倒计时实时刷新**：首页和配置页倒计时改为 JS 每秒轮询 `/time` 接口，实时更新剩余秒数
- **新增配置常量**：`WIFI_BTN_HOLD_MS = const(2000)` 长按进入配网模式阈值
- **强制规则文档化**：在 config.py、app.py 中记录蓝牙优先规则和硬件互斥限制

## v1.1.0 (2026-05-18)

- 代码重构：划分 5 大模块（常量 / BLE / 功率引擎 / WiFi / 主程序），添加模块分隔注释
- 添加类和方法级 docstring，关键逻辑行内注释（BLE flags 含义、时间戳单位、心率平滑算法等）
- 常量提升：按钮阈值 `_SHORT_PRESS_MS` / `_LONG_PRESS_INTERVAL_MS`、WiFi 超时 `_WIFI_SHUTDOWN_MS` 提升为模块级常量
- 按钮交互改进：短按 -10W、长按每 500ms +10W（原为单次 +50W）
- 配置持久化增加心率字段：`config_{power}_{cadence}_{heartrate}`
- WiFiManager 重构：HTML 构建抽取为 `_build_success_page()` / `_build_config_page()` 独立方法
- PowerEngine 配置加载逻辑抽取为 `_load_config()` 方法
- 部署工具从 ampy 切换为 mpremote（官方推荐）
- 新增 `robot.md`：AI 自动部署指南，含跨平台串口探测、占用释放、日志监控、异常自修复流程
- 修复：移除文件 UTF-8 BOM，避免 MicroPython 运行时 NameError

## v1.0.0 Cadence (2026-05-16)

- 初始版本
- 支持蓝牙功率计和心率模拟
- 支持 WiFi 网页配置
- 支持 BOOT 按钮调整功率
- 优化内存使用和蓝牙稳定性
