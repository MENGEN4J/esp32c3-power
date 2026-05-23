# BikePower 项目深度分析：架构演进、优化建议与学习路线

> 基于 git 历史版本记录，全面分析 ESP32-C3 蓝牙功率计模拟器项目从 v1.0 到 v2.0 的架构演进过程，结合最新 IoT/Agent 理论给出优化建议与学习路线规划。

---

## 目录

- [一、项目概览](#一项目概览)
- [二、版本演进全景图](#二版本演进全景图)
- [三、架构演进深度分析](#三架构演进深度分析)
- [四、AI Agent 治理体系分析](#四ai-agent-治理体系分析)
- [五、优秀实践总结](#五优秀实践总结)
- [六、优化建议](#六优化建议)
- [七、优秀 ESP32 开源项目参考](#七优秀-esp32-开源项目参考)
- [八、学习路线规划](#八学习路线规划)
- [九、参考资料汇总](#九参考资料汇总)

---

## 一、项目概览

### 1.1 项目定位

BikePower 是一个基于合宙 ESP32-C3 开发板、使用 MicroPython v1.28 开发的**蓝牙功率计模拟器**。它通过 BLE 广播骑行功率、踏频和心率数据，可被 Zwift、TrainerRoad、MyWoosh 等主流骑行 App 识别为真实功率计设备。

### 1.2 核心技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| 硬件 | 合宙 CORE ESP32-C3 | RISC-V 单核 160MHz, 400KB SRAM, 4MB Flash |
| 固件 | MicroPython v1.28 | Python 3 精简版，专为微控制器优化 |
| 蓝牙 | BLE 5.0 GATT | Cycling Power Service (0x1818) + Heart Rate Service (0x180D) |
| 网络 | WiFi 802.11b/g/n | AP 模式配网，STA 模式 OTA |
| 配置 | JSON 持久化 | power_config.json 单文件覆盖写入 |
| OTA | .mpy 字节码差量更新 | CRC32 校验 + .bak 安全回滚 |
| 构建 | mpy-cross + ESP-IDF | 冻结模块编译 + 固件打包 |
| 部署 | mpremote + pyserial | 跨平台串口智能扫描 |
| AI 辅助 | Trae IDE + GLM-5.1 | Agent 规则治理 + Hooks 确定性检查 |

### 1.3 当前模块架构

```
boot.py          → 启动入口，安全回滚校验
app.py           → 主程序，按钮事件 + LED 状态机 + 主循环
config.py        → 全局常量，const() 包装
logger.py        → 日志器，% 格式化
utils.py         → 工具函数，start_thread
ble_service.py   → BLE 双服务广播器
power_data.py    → 骑行模式引擎（4 种模式）
wifi_manager.py  → WiFi AP 配网 + HTTP 服务器
web_pages.py     → HTML 页面模板
ota_updater.py   → OTA 固件差量更新器
```

---

## 二、版本演进全景图

### 2.1 时间线总览

| 版本 | 日期 | 主题 | 关键里程碑 |
|------|------|------|-----------|
| v1.0.0 | 2026-05-16 | Cadence | 初始版本，BLE 功率计 + WiFi 配网 + 按钮控制 |
| v1.1.0 | 2026-05-18 | 重构 | 5 大模块划分，ampy→mpremote，配置持久化 |
| v1.2.0 | 2026-05-19 | 蓝牙优先 | BLE 优先架构，按钮交互重设计，WiFi/BLE 互斥 |
| v1.3.0 | 2026-05-20 | 跨平台 | 串口智能扫描，common.sh 公共库，MEMORY.md |
| v1.4.0 | 2026-05-20 | 部署模式 | .deploy 标志机制，JSON 配置持久化，deploy.sh 重构 |
| v1.5.0 | 2026-05-20 | Spec Coding | specs/ 规格文档，templates/ 代码模板，Entropy 治理，AI 质疑规则 |
| v1.6.0 | 2026-05-20 | 优化审查 | 首次全面优化审查，f-string 清理，BLE 预分配 |
| v1.7.0 | 2026-05-20 | 规范化 | f-string 全面清理，import 规范化，心率公式简化 |
| v1.8.0 | 2026-05-20 | Glow | LED 状态指示，二次确认配网，默认值调整 |
| v1.9.0 | 2026-05-21 | OTA | OTA 固件更新，SSL/TLS，boot.py 安全回滚 |
| v1.9.1 | 2026-05-21 | 字节码 | .mpy 编译打包，9 模块 51KB |
| v1.9.2 | 2026-05-21 | 修复 | OTA 下载期间 WiFi 关闭 Bug，socket 泄漏修复 |
| v1.9.3 | 2026-05-22 | Patch | OTA 版本字段兼容，JSON 转义安全，配置保存健壮性 |
| v1.9.4 | 2026-05-22 | 治理 | Entropy 扫描全通过，用户手册补齐，发布文档漂移修正 |
| v2.0.0 | 2026-05-22 | 骑行模式 | PowerEngine 4 种骑行模式，FIT 样本优化，Web 模式选择 |
| v2.0.1 | 2026-05-23 | 修复 | BLE 初始化失败 machine.reset()，WiFi 重连状态判断 |

### 2.2 版本演进阶段划分

```
阶段一：功能原型（v1.0~v1.1）
  └─ 从单文件到模块化，建立基本可运行的 BLE 功率计

阶段二：架构重构（v1.2~v1.4）
  └─ 蓝牙优先架构，WiFi/BLE 互斥，跨平台部署，JSON 配置

阶段三：工程治理（v1.5~v1.8）
  └─ Spec Coding，Entropy 治理，优化审查，LED 状态机，二次确认

阶段四：OTA 闭环（v1.9.0~v1.9.4）
  └─ OTA 固件更新，字节码打包，安全回滚，Bug 修复

阶段五：功能升级（v2.0.0~v2.0.1）
  └─ 骑行模式引擎，FIT 数据驱动，Web 模式选择
```

---

## 三、架构演进深度分析

### 3.1 从单文件到模块化（v1.0 → v1.1）

**问题**：初始版本代码集中在少量文件中，耦合度高，难以维护和测试。

**演进**：
- 划分 5 大模块：常量（config.py）、BLE（ble_service.py）、功率引擎（power_data.py）、WiFi（wifi_manager.py）、主程序（app.py）
- 添加类和方法级 docstring
- 常量提升：按钮阈值、WiFi 超时等提升为模块级常量
- 部署工具从 ampy 切换为 mpremote（官方推荐）

**启示**：模块化是嵌入式项目可维护性的基础。MicroPython 虽然是脚本语言，但模块边界同样重要——ESP32-C3 内存有限，延迟 import 可以在 WiFi 模块不使用时节省 RAM。

### 3.2 蓝牙优先架构（v1.2）

**问题**：开机自动启动 WiFi 导致无限重启循环，WiFi 和 BLE 同时运行触发硬件互斥限制。

**演进**：
- 确立"蓝牙优先"原则：开机仅启动 BLE，WiFi 由用户长按触发
- 按钮交互重设计：短按 -10W / 中按 +10W / 长按 ≥2s 进入配网
- WiFi/BLE 互斥处理：start() 先关闭 BLE 再启动 WiFi AP
- BLE 初始化异常恢复：激活失败时 machine.reset()
- WiFiManager 异步创建：不阻塞主循环

**启示**：ESP32-C3 的 WiFi 和 BLE 共用射频前端，不能同时运行。这是硬件约束，不是软件 Bug。架构设计必须尊重硬件限制，而不是试图绕过它。

### 3.3 跨平台与部署工程化（v1.3~v1.4）

**问题**：串口地址硬编码，部署流程不跨平台，配置持久化格式低效。

**演进**：
- 串口智能扫描：通过 USB VID/PID 精准识别 ESP32-C3 设备
- 跨平台公共函数库 common.sh
- .deploy 标志机制：解决 mpremote 无法连接运行中设备的问题
- JSON 配置持久化：从文件名编码改为单文件 JSON，内存从 112KB 提升到 118KB

**启示**：嵌入式项目的部署体验直接影响开发效率。串口扫描、跨平台兼容、配置格式优化这些"非功能"需求，往往比功能本身更决定项目是否可持续。

### 3.4 Spec Coding 与工程治理（v1.5~v1.8）

**问题**：AI 生成的代码缺乏行为规格约束，文档与代码容易漂移，技术债积累。

**演进**：
- **Spec Coding**：引入 specs/ 目录，GIVEN/WHEN/THEN 格式定义模块行为规格
- **代码模板**：templates/ 目录提供 BLE 服务、WiFi 处理、配置持久化等代码模板
- **Entropy 治理**：5 项技术债扫描（文档 Drift、命名漂移、死代码、规则腐烂、配置一致性）
- **AI 质疑规则**：4 类质疑触发条件（硬件约束冲突、跨模块影响、更优方案、安全风险）
- **优化审查**：首次全面优化审查，f-string 全面清理，BLE 通知预分配
- **LED 状态机**：4 种 LED 状态指示 + 二次确认进入配网

**启示**：Spec Coding 是 AI 辅助开发的关键实践。当 AI 生成代码时，规格文档是"合同"，模板是"模具"，Entropy 扫描是"质检"。三者结合，才能让 AI 输出可预测、可验证的代码。

### 3.5 OTA 闭环（v1.9.0~v1.9.4）

**问题**：固件更新需要物理连接，用户体验差；OTA 过程中存在 WiFi 被提前关闭、socket 泄漏等 Bug。

**演进**：
- OTA 核心模块：文件级差量更新，CRC32 校验，.bak 安全回滚
- boot.py 安全回滚：启动时校验 9 个核心模块，失败自动回滚
- WiFi 配网集成 OTA：STA 连接成功后自动检查更新
- .mpy 字节码托管：9 模块编译后 51KB，压缩率 50%
- Bug 修复：OTA 下载期间暂停 WiFi 关闭计时器，HTTP 异常路径 socket 关闭
- 版本字段兼容、JSON 转义安全、配置保存健壮性

**启示**：OTA 是嵌入式产品的"最后一公里"。在 ESP32-C3 上实现 OTA 需要处理内存限制（10KB 响应上限）、SSL/TLS 兼容、原子替换、安全回滚等大量边界情况。每个 Bug 都是真机实测发现的，静态分析无法覆盖。

### 3.6 骑行模式引擎（v2.0.0）

**问题**：只有固定功率模式，模拟数据不够真实，无法满足不同训练场景需求。

**演进**：
- PowerEngine 新增 get_snapshot(now_ms) 统一生成快照
- 4 种骑行模式：固定功率、真实路骑、间歇训练、随机巡航
- 基于 FIT 样本优化内置曲线：解析 5956 条真实骑行 record
- Web 模式选择：配置页支持选择模式
- 非固定模式参数限制：只有固定功率模式使用表单和按钮修改数值

**启示**：从"能跑"到"好用"的跨越，需要真实数据驱动。FIT 文件解析让内置曲线不再是拍脑袋的参数，而是基于真实骑行数据的统计分布。这是从"玩具"到"工具"的关键一步。

---

## 四、AI Agent 治理体系分析

### 4.1 五层防御架构

BikePower 项目建立了一套完整的 AI Agent 治理体系，这在嵌入式开源项目中非常罕见：

```
第一层：MEMORY.md — 经验记忆
  └─ 用户偏好、已验证决策、踩坑记录、凭证信息

第二层：.trae/rules/ — 规则护栏
  └─ code_style.md, hardware_constraints.md, project_rules.md
  └─ ai-challenge.md, optimization-review.md, pre_dev_checklist.md

第三层：specs/ + templates/ — 规格与模板
  └─ GIVEN/WHEN/THEN 行为规格
  └─ 代码模板（BLE 服务、WiFi 处理、配置持久化）

第四层：Hooks — 确定性检查
  └─ H1~H26 自动检查项
  └─ entropy_scan.py --hooks 强制执行
  └─ git pre-commit hook

第五层：Stop Hook 自改进
  └─ S1: 踩坑经验 → MEMORY.md
  └─ S2: CRITICAL 级别 → .trae/rules/ 规则
  └─ S5: 代码修改后运行 entropy_scan.py
```

### 4.2 与业界最佳实践的对比

| 维度 | BikePower 实践 | 业界最新理论 | 匹配度 |
|------|---------------|-------------|--------|
| 规则层级 | MEMORY → rules → specs → hooks → 自改进 | Advisory → Probabilistic → Deterministic → Organizational | ★★★★★ |
| Hooks 机制 | entropy_scan.py + pre-commit | PreToolUse/PostToolUse/Stop hooks | ★★★★☆ |
| 确定性执行 | H1~H26 编译检查、禁止项扫描 | "确定性 > 概率性"原则 | ★★★★★ |
| 经验沉淀 | 犯错 → MEMORY → CRITICAL → 规则 → Hook | Stop Hook 自改进闭环 | ★★★★★ |
| 安全分级 | Allow/Ask/Deny 三级 | 权限模式 + Hook 优先于权限 | ★★★★☆ |

### 4.3 关键创新点

1. **经验沉淀闭环**：犯错 → 记录到 MEMORY.md → CRITICAL 级别升级为规则 → Hooks 自动检查 → 不再犯错。这与 Anthropic 官方推荐的 Stop Hook 自改进机制完全一致。

2. **Entropy 治理**：定期扫描 6 项技术债（文档 Drift、命名漂移、死代码、规则腐烂、配置一致性、记忆清理），这在嵌入式项目中是独创的实践。

3. **AI 质疑规则**：要求 AI 在发现方案漏洞时必须主动提出，而不是谄媚用户。这与 OpenSSF 发布的《Security-Focused Guide for AI Code Assistant Instructions》中"Be Security-Conscious"原则一致。

4. **操作权限分类**：Allow（自动执行）/ Ask（需确认）/ Deny（禁止），对应 Agent 行为的确定性控制层级。

---

## 五、优秀实践总结

### 5.1 硬件约束优先

| 实践 | 说明 |
|------|------|
| WiFi/BLE 互斥 | ESP32-C3 射频前端共享，不能同时运行 |
| 内存预算 | BLE 启动后 < 120KB 可用，避免创建大对象 |
| Socket 并发限制 | 最多 3 个 socket，listen(3) |
| 预分配缓冲区 | BLE 通知回调中使用 bytearray，避免 GC |
| const() 包装 | 模块级整数常量用 const() 优化内存 |

### 5.2 代码规范

| 实践 | 说明 |
|------|------|
| % 格式化 | 替代 f-string，减少运行时内存分配 |
| 延迟 import | WiFi 模块延迟加载，BLE 运行时节省 RAM |
| gc.collect() | 关键节点手动回收 |
| 禁止 print() | 统一使用 logger.get_logger() |
| 禁止硬编码 | 端口、IP、引脚号必须提取到 config.py |

### 5.3 工程治理

| 实践 | 说明 |
|------|------|
| SemVer 版本号 | v主版本.次版本.补丁，严格递增 |
| Conventional Commits | type(scope): subject 格式 |
| 分批提交 | 按功能分批，不混提 |
| 先测试后提交 | 未通过验证禁止提交 |
| Entropy 扫描 | 版本发布前全量扫描 |

### 5.4 安全实践

| 实践 | 说明 |
|------|------|
| OTA CRC32 校验 | 下载文件完整性验证 |
| .bak 安全回滚 | 原子替换前备份 |
| boot.py 启动校验 | __import__ 校验 9 个核心模块 |
| WiFi AP 超时关闭 | 180s 后自动关闭 + machine.reset() |
| OTA 受保护文件列表 | wifi_config.txt 不被 OTA 覆盖 |

---

## 六、优化建议

### 6.1 架构层面

#### 6.1.1 引入事件驱动架构

当前主循环采用轮询模式（while True + time.sleep_ms），建议引入事件驱动架构：

```python
# 当前：轮询模式
while True:
    current_time = time.ticks_ms()
    _update_led(...)
    if button_pressed:
        _handle_button(...)
    time.sleep_ms(50)

# 建议：事件驱动模式
import uasyncio as asyncio

async def button_watcher():
    while True:
        await asyncio.sleep_ms(10)
        if button.value() == 0:
            handle_button()

async def ble_notifier():
    while True:
        await asyncio.sleep_ms(config.BLE_NOTIFY_INTERVAL)
        ble_meter.update_data(engine)

async def led_controller():
    while True:
        await asyncio.sleep_ms(100)
        update_led()

loop = asyncio.get_event_loop()
loop.create_task(button_watcher())
loop.create_task(ble_notifier())
loop.create_task(led_controller())
loop.run_forever()
```

**权衡**：uasyncio 在 MicroPython v1.28 上可用，但会增加约 5KB 内存开销。对于当前 109KB 空闲内存是可接受的。

#### 6.1.2 配置管理增强

当前 power_config.json 使用短 key（p/c/h/m），建议增加配置版本号和迁移逻辑：

```python
CONFIG_VERSION = const(2)

def _load_config(self):
    try:
        with open(config.POWER_CONFIG_FILE, 'r') as f:
            cfg = json.load(f)
        version = cfg.get('v', 1)
        if version < CONFIG_VERSION:
            cfg = self._migrate_config(cfg, version)
    except OSError:
        cfg = {'v': CONFIG_VERSION, 'p': config.DEFAULT_POWER, ...}
```

#### 6.1.3 BLE 服务扩展

当前仅支持 Cycling Power + Heart Rate，可考虑扩展：

| 服务 | UUID | 用途 |
|------|------|------|
| Cycling Speed and Cadence | 0x1816 | 独立踏频数据 |
| Fitness Machine | 0x1826 | 支持 ERG 模式，接收 App 下发功率目标 |
| Device Information | 0x180A | 固件版本、制造商信息 |

Fitness Machine Service 特别有价值——它支持"训练器控制点"特征，可以让 Zwift 等软件下发功率目标，实现真正的智能训练。

### 6.2 安全层面

#### 6.2.1 OTA 签名验证

当前 OTA 仅做 CRC32 完整性校验，无来源验证。建议增加 Ed25519 签名：

```
发布流程：开发者用私钥对 version.json 签名 → 签名附加到 version.json
验证流程：设备用内嵌公钥验证签名 → 通过后才下载更新
```

Ed25519 在 MicroPython 中可通过 `ucrypto` 或纯 Python 实现实现，签名验证约 2KB 代码。

#### 6.2.2 WiFi 配网安全

| 当前 | 建议 |
|------|------|
| AP 无密码 | 保持（配网模式短暂开放 180s 超时） |
| WiFi 密码明文存储 | 考虑使用 MicroPython 的 `esp32.Partition` 加密存储 |
| BLE 无配对验证 | 可接受（模拟器场景），但可增加可选 PIN 码 |

#### 6.2.3 凭证管理

MEMORY.md 中存储了 Gitee Token 和飞书 App Secret，建议：
- 使用环境变量替代明文存储
- 或使用 `.env` 文件 + `.gitignore` 排除

### 6.3 功能层面

#### 6.3.1 FIT 活动回放

v2.0 已预留 FIT 上传/解析/回放能力（推迟到 v2.1+），建议实现路径：

1. Web 页面上传 .fit 文件
2. 设备端解析 FIT record（功率/心率/踏频时间序列）
3. 按时间轴回放，BLE 实时输出
4. 支持倍速播放和暂停

#### 6.3.2 多设备连接优化

当前支持 3 个 BLE 连接，但通知是广播式的。建议：
- 按连接优先级分配通知频率
- 主连接（第一个）1s 间隔，从连接 2s 间隔
- 减少不必要的通知，降低功耗

#### 6.3.3 数据记录

增加骑行数据本地记录功能：
- 使用 Flash 空间存储骑行历史
- 通过 WiFi 配网页面导出 CSV/FIT
- 统计骑行时长、平均功率、TSS 等

### 6.4 Agent 治理层面

#### 6.4.1 Hooks 覆盖率提升

当前 H1~H26 覆盖了主要检查项，但可增加：

| 新增 Hook | 检查内容 |
|-----------|---------|
| H27 | uasyncio 使用时检查内存预算 |
| H28 | BLE 服务扩展时检查 UUID 冲突 |
| H29 | FIT 解析时检查文件大小上限 |
| H30 | 多语言支持时检查繁体中文 |

#### 6.4.2 自动化测试增强

当前测试以手动为主，建议增加：

```bash
# 单元测试（本地 Mock）
python3 -m pytest test/ --tb=short

# 集成测试（真机）
bash test/test_runner.sh -p=/dev/ttyUSB0

# Entropy 扫描
python3 scripts/entropy_scan.py --all
```

#### 6.4.3 CI/CD 流水线

建议在 Gitee/GitHub 上配置 CI：

```yaml
# .gitee/pipelines/ci.yml
stages:
  - lint
  - test
  - build
  - deploy

lint:
  - python3 -m py_compile *.py
  - python3 scripts/entropy_scan.py --hooks

test:
  - python3 -m pytest test/

build:
  - bash scripts/build_firmware.sh
  - python3 scripts/gen_version_json.py
```

---

## 七、优秀 ESP32 开源项目参考

### 7.1 蓝牙功率计相关

| 项目 | 地址 | 技术栈 | 特点 |
|------|------|--------|------|
| ESPM | github.com/gsoros/ESPM | C++/ESP-IDF | 真实功率计，HX711 应变片 + MPU9250 IMU，支持左右踏板 |
| BLECyclePower-SpinningBike | github.com/wie-niet/BLECyclePower-SpinningBike | Arduino/ESP32 | 轮速传感器模拟功率，Deep Sleep 省电，MyWoosh 兼容 |
| ESP32 Multi-Sensor BLE | github.com/kerojohan/ESP32-fake-sensors-garmin | Arduino/ESP32 | 多传感器 BLE（CPS+CSCS+HRS），Garmin 兼容 |
| Proform 智能自行车 | CSDN 资源 | Arduino/ESP32-C3 | Zwift 坡度控制，ERG 模式，阻力自动调节 |

**对比分析**：BikePower 是唯一使用 MicroPython 的项目，也是唯一支持 WiFi 配网页面和 OTA 更新的项目。其他项目都是 C++/Arduino，功能更偏硬件层面（真实传感器），而 BikePower 更偏软件层面（模拟数据 + 用户体验）。

### 7.2 ESP32 通用优秀项目

| 项目 | 地址 | 领域 | 亮点 |
|------|------|------|------|
| Tasmota | github.com/arendst/Tasmota | 智能家居 | 万能固件，MQTT 本地控制，Berry 脚本，数百设备支持 |
| ESPHome | esphome.io | 智能家居 | YAML 配置生成固件，HomeAssistant 生态，零代码 |
| ESPresense | github.com/ESPresense/ESPresense | 存在检测 | BLE 扫描定位，MQTT 推送，房间级精度 |
| Project Aura | hackaday.io/project/204993 | 空气质量 | ESP32-S3 + LVGL 触摸屏，Sensirion 传感器，HomeAssistant 集成 |
| OpenAirScope | GitHub | 环境监测 | STM32H743 + ESP32-C3 双核，LoRaWAN 扩展 |
| 小智 AI 机器人 | GitHub | AIoT | ESP32 + 语音交互，Rasa NLU，Docker 部署 |
| ESP32-C3 BLE 键盘 | oshwhub.com/linyin592 | 消费电子 | BLE HID，WS2812 灯效，串口配置，亚克力外壳 |

### 7.3 可借鉴的设计模式

| 模式 | 来源项目 | BikePower 可应用 |
|------|---------|-----------------|
| MQTT 本地控制 | Tasmota | 增加 MQTT 上报骑行数据 |
| YAML 配置生成 | ESPHome | WiFi 配网参数 YAML 化 |
| BLE 存在检测 | ESPresense | 增加 BLE 广播自定义数据 |
| LVGL 触摸屏 UI | Project Aura | 如有屏幕需求可参考 |
| Deep Sleep 省电 | BLECyclePower | 空闲时进入低功耗模式 |
| Berry 脚本扩展 | Tasmota | 用户自定义骑行逻辑 |

---

## 八、学习路线规划

### 8.1 ESP32 嵌入式开发路线

```
入门阶段（1~2 个月）
├── MicroPython 基础
│   ├── REPL 交互开发
│   ├── GPIO/UART/I2C/SPI 外设控制
│   └── 中断和定时器
├── ESP32-C3 硬件基础
│   ├── RISC-V 架构理解
│   ├── 内存映射和 Flash 分区
│   └── WiFi/BLE 射频特性
└── 开发工具链
    ├── mpremote 部署
    ├── esptool 烧录
    └── Thonny/VS Code 开发环境

进阶阶段（2~3 个月）
├── BLE 开发深入
│   ├── GATT 服务设计
│   ├── Cycling Power Service 规范
│   ├── 通知优化和连接管理
│   └── BLE 安全和配对
├── WiFi 和网络
│   ├── AP/STA 模式
│   ├── HTTP 服务器
│   ├── SSL/TLS
│   └── MQTT 协议
├── OTA 更新
│   ├── 固件差量更新
│   ├── 安全回滚
│   └── 版本管理
└── 内存优化
    ├── 预分配和 const()
    ├── gc.collect() 策略
    └── .mpy 字节码编译

高级阶段（3~6 个月）
├── ESP-IDF 原生开发
│   ├── FreeRTOS 任务管理
│   ├── NimBLE 协议栈
│   └── 分区表和启动流程
├── 功率计硬件
│   ├── 应变片原理
│   ├── HX711 ADC 采样
│   └── 功率校准算法
├── 骑行科学
│   ├── 功率训练理论
│   ├── FIT 文件格式
│   └── TSS/FTP/训练区间
└── 产品化
    ├── PCB 设计
    ├── 3D 打印外壳
    ├── 认证（FCC/CE）
    └── 批量生产
```

### 8.2 AI Agent 开发路线

```
基础阶段（1~2 周）
├── Agent 规则体系
│   ├── CLAUDE.md / AGENTS.md 编写
│   ├── 规则分层：Advisory → Deterministic
│   └── MEMORY.md 经验沉淀
├── Hooks 机制
│   ├── PreToolUse / PostToolUse / Stop
│   ├── Exit code 语义（0=允许，2=阻止）
│   └── git pre-commit hook
└── 代码质量保障
    ├── 静态分析（py_compile, linter）
    ├── Entropy 治理扫描
    └── 测试报告自动化

进阶阶段（2~4 周）
├── Spec Coding
│   ├── GIVEN/WHEN/THEN 行为规格
│   ├── 代码模板（templates/）
│   └── 规格与代码同步机制
├── Agent 安全
│   ├── 操作权限分级（Allow/Ask/Deny）
│   ├── 安全编码指南（OpenSSF）
│   └── 凭证管理最佳实践
└── 自改进闭环
    ├── 踩坑经验 → 规则升级
    ├── CRITICAL 项必须有 Hook
    └── Stop Hook 回顾与沉淀

高级阶段（1~2 个月）
├── 多 Agent 协作
│   ├── Subagent 权限隔离
│   ├── 上下文注入和压缩
│   └── 结果聚合
├── CI/CD 集成
│   ├── Agent 驱动的代码审查
│   ├── 自动化测试流水线
│   └── 发布流程自动化
└── 领域特定 Agent
    ├── 嵌入式 Agent（IoT-SkillsBench）
    ├── Skills 模板设计
    └── 硬件感知代码生成
```

### 8.3 推荐学习资源

#### 书籍

| 书名 | 领域 | 说明 |
|------|------|------|
| 《MicroPython for the Internet of Things》 | MicroPython | ESP32/ESP8266 实战入门 |
| 《BLE 数据设计手册》 | BLE | GATT 服务设计权威指南 |
| 《The Cyclist's Training Bible》Joe Friel | 骑行科学 | 功率训练理论基础 |
| 《Designing Data-Intensive Applications》 | 系统设计 | 数据流和状态管理思想 |

#### 在线资源

| 资源 | 链接 | 说明 |
|------|------|------|
| MicroPython 官方文档 | docs.micropython.org | API 参考和教程 |
| ESP-IDF 编程指南 | docs.espressif.com | ESP32 开发权威文档 |
| Bluetooth SIG 规范 | bluetooth.com | GATT 服务标准定义 |
| Anthropic Claude Code Hooks | docs.claude.com/en/docs/claude-code/hooks | Agent Hooks 最佳实践 |
| OpenSSF AI 安全指南 | best.openssf.org/Security-Focused-Guide | AI 代码助手安全指南 |
| IoT-SkillsBench 论文 | arxiv.org/pdf/2603.19583 | 嵌入式 AI Agent 技能框架 |
| Agent Patterns | agentpatterns.ai | Agent 设计模式库 |
| Hackaday.io | hackaday.io | 硬件项目灵感社区 |

#### KOL 和社区

| 渠道 | 关注方向 | 代表内容 |
|------|---------|---------|
| 乐鑫官方博客 | ESP32 技术深度 | ESP-IDF 新特性、功耗优化 |
| CSDN 嵌入式专栏 | MicroPython 实战 | ESP32-C3 项目教程、传感器集成 |
| Hackster.io | 创客项目 | ESP32 创意应用、竞赛项目 |
| Reddit r/esp32 | 社区讨论 | 问题排查、项目分享 |
| Discord Tasmota | 智能家居 | Tasmota 固件开发、Berry 脚本 |
| 微信公众号「芯片之家」 | 国产芯片 | ESP32-C3 RISC-V 深度解析 |

---

## 九、参考资料汇总

### 学术论文

1. **IoT-SkillsBench** — "Skilled AI Agents for Embedded and IoT Systems Development", Duke University, 2026. 提出基于技能的 Agent 框架，在 378 次硬件验证实验中，人类专家技能实现接近完美的成功率。
2. **Lightweight Embedded IoT Gateway** — "Lightweight Embedded IoT Gateway for Smart Homes Based on an ESP32 Microcontroller", Computers 2025. 证明 ESP32 可作为功能完整的 IoT 网关，RAM 使用仅 3.6%~6.8%。

### 行业报告与指南

3. **OpenSSF Security-Focused Guide for AI Code Assistant Instructions**, 2025-08. AI 代码助手安全指南，强调"你是开发者，AI 是助手"原则。
4. **Anthropic Claude Code Hooks Guide**, 2026. Hooks 确定性执行机制，从 Advisory 到 Deterministic 的演进。
5. **Agent Patterns: Enforcing Agent Behavior with Hooks**, 2026. 策略即代码，将关键规则从提示词迁移到确定性 Shell Hooks。

### 技术博客

6. **MicroPython 在 ESP32 上的快速理解：入门必看指南**, CSDN 2026. MicroPython + ESP32 开发全流程。
7. **ESP32 物联网项目参考设计去哪找**, CSDN 2026. 开源固件框架、完整项目方案、芯片原厂资源分类。
8. **Stop Wasting Hours Debugging: Use AI to Write Better Embedded Systems Code**, markaicode.com 2025. AI 辅助嵌入式开发实践。
9. **How to Build a Safe and Efficient AI Code Generation Workflow for Embedded C/C++**, wedolow.com 2025. 嵌入式 AI 代码生成安全工作流。
10. **ESP32-C3 RISC-V 低成本**, CSDN 2025. ESP32-C3 架构深度解析，RISC-V 优势分析。

### 开源项目

11. **Tasmota** — github.com/arendst/Tasmota. ESP8266/ESP32 万能固件，MQTT 本地控制。
12. **ESPM** — github.com/gsoros/ESPM. ESP32 真实功率计，HX711 + MPU9250。
13. **BLECyclePower-SpinningBike** — github.com/wie-niet/BLECyclePower-SpinningBike. ESP32 模拟功率计。
14. **Project Aura** — hackaday.io/project/204993. ESP32-S3 空气质量监测站。

---

## 附录：项目数据统计

### 代码量统计

| 模块 | 行数 | 职责 |
|------|------|------|
| app.py | ~200 | 主程序入口 |
| ble_service.py | ~250 | BLE 双服务广播 |
| power_data.py | ~300 | 骑行模式引擎 |
| wifi_manager.py | ~500 | WiFi 配网 + HTTP |
| web_pages.py | ~700 | HTML 页面模板 |
| ota_updater.py | ~400 | OTA 更新器 |
| config.py | ~150 | 全局常量 |
| logger.py | ~50 | 日志器 |
| utils.py | ~20 | 工具函数 |
| boot.py | ~40 | 启动入口 |
| **总计** | **~2,610** | — |

### 版本发布统计

| 指标 | 数值 |
|------|------|
| 总版本数 | 15 |
| 总提交数 | ~100+ |
| 开发周期 | 2026-05-16 ~ 2026-05-23（8 天） |
| Bug 修复版本 | 5 个（v1.9.2~v2.0.1） |
| Entropy 扫描通过率 | 100%（v1.9.4 起） |
| .mpy 编译压缩率 | 50%（102.7KB → 51KB） |
| BLE 启动后空闲内存 | ~109KB |

### 关键决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 开发语言 | MicroPython | 开发效率 10x，REPL 实时调试 |
| 芯片选型 | ESP32-C3 | WiFi+BLE 集成，RISC-V 低成本 |
| 配置格式 | JSON | 比 os.listdir() 扫描更轻量 |
| OTA 格式 | .mpy 字节码 | 代码保护 + 50% 压缩 |
| 部署工具 | mpremote | 官方推荐，比 ampy 更稳定 |
| 版本规范 | SemVer + Conventional Commits | 业界标准，自动递增 |
| AI 治理 | 五层防御 + Entropy 扫描 | 确定性 > 概率性 |
