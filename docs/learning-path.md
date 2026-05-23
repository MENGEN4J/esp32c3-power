# BikePower 课程学习路线

> 这份文档把项目资料整理成可学习、可授课的路线。目标不是替代用户手册，而是帮助开发者按主题理解 ESP32-C3、MicroPython、BLE、WiFi 配网、OTA 和 AI 工程化。

## 学习目标

完成本路线后，应能理解：

- ESP32-C3 的硬件限制，尤其是 WiFi/BLE 互斥和内存约束
- MicroPython 在小内存设备上的工程化写法
- BLE Cycling Power / Heart Rate 服务的基本数据结构
- WiFi AP 配网、Web 表单、Socket 服务端的实现思路
- 文件级 OTA、CRC 校验、原子替换和安全回滚
- 如何用规格文档、规则文档和变更文档约束 AI Coding

## 课程路线

### 第 1 课：项目全貌与使用流程

推荐阅读：

- [user-manual.md](user-manual.md)
- [README.md](../README.md)

学习重点：

- 设备能做什么
- 蓝牙连接、按钮操作、WiFi 配网、OTA 更新的用户路径
- 哪些功能是“用户可感知行为”，哪些是“内部实现”

实践任务：

- 按用户手册画出完整使用流程图
- 列出 BLE、WiFi、OTA 三条主链路的入口和退出条件

### 第 2 课：ESP32-C3 硬件约束

推荐阅读：

- [esp32c3-board-guide.md](esp32c3-board-guide.md)
- [esp32c3-optimization.md](esp32c3-optimization.md)
- [.trae/rules/hardware_constraints.md](../.trae/rules/hardware_constraints.md)

学习重点：

- GPIO9 按钮、GPIO12 LED 的使用约束
- WiFi 与 BLE 共享 RF 的限制
- MicroPython 堆内存、Socket 数量和无 PSRAM 限制

实践任务：

- 解释为什么本项目采用 WiFi/BLE 互斥，而不是共存
- 给出“进入配网模式必须先关 BLE”的状态机

### 第 3 课：MicroPython 工程结构

推荐阅读：

- [firmware-build.md](firmware-build.md)
- [.trae/rules/code_style.md](../.trae/rules/code_style.md)
- [spec-coding-insights.md](spec-coding-insights.md)

学习重点：

- MicroPython 与 CPython 的差异
- `const()`、预分配缓冲区、`gc.collect()`、轻量日志
- 模块级 docstring、配置集中化、禁止硬编码

实践任务：

- 找出项目中所有预分配缓冲区
- 说明为什么业务代码不能使用 `requests`、`asyncio`、`threading`

### 第 4 课：BLE 功率计服务

推荐阅读：

- [../specs/ble-service.md](../specs/ble-service.md)
- [open-source-references.md](open-source-references.md)

学习重点：

- Cycling Power Service 与 Heart Rate Service
- BLE 广播、连接、断开、通知
- 8 字节功率数据包和踏频计算

实践任务：

- 拆解一次 BLE 通知的字节结构
- 说明为什么通知缓冲区要复用 `bytearray`

### 第 5 课：按钮与 LED 状态机

推荐阅读：

- [../specs/button-handler.md](../specs/button-handler.md)
- [user-manual.md](user-manual.md)

学习重点：

- 短按、中按、长按、二次确认
- LED 慢闪、常亮、快闪、熄灭、OTA 双闪
- 用户操作如何转化为系统状态变化

实践任务：

- 用表格写出按钮事件和 LED 状态迁移
- 解释为什么长按不能直接进入 WiFi 配网

### 第 6 课：WiFi 配网与 Web 服务

推荐阅读：

- [../specs/wifi-manager.md](../specs/wifi-manager.md)
- [robot-deploy.md](robot-deploy.md)
- [esp32c3-optimization.md](esp32c3-optimization.md)

学习重点：

- AP 热点、STA 连接、Web 表单和 JSON API
- Socket `listen(3)` 与连接关闭
- WiFi 自动关闭和重启恢复 BLE

实践任务：

- 画出 `start()` 到 `_shutdown_wifi()` 的完整流程
- 找出 Web API 中哪些接口依赖 WiFi 已配网

### 第 7 课：OTA 文件级更新

推荐阅读：

- [ota-update-design.md](ota-update-design.md)
- [../specs/ota-updater.md](../specs/ota-updater.md)
- [release-template.md](release-template.md)

学习重点：

- `version.json` 字段、`mpy_version` 校验、CRC32
- `.tmp`、`.bak`、`.update_pending` 的作用
- 启动时 `__import__` 校验和自动回滚

实践任务：

- 设计一次“下载中断”的回滚流程
- 解释为什么 OTA 版本清单应使用稳定 `latest` 入口，而不是历史 tag

### 第 8 课：测试、部署与发版

推荐阅读：

- [firmware-build.md](firmware-build.md)
- [robot-deploy.md](robot-deploy.md)
- [release-template.md](release-template.md)
- [../MEMORY.md](../MEMORY.md)

学习重点：

- 语法检查、编译、部署、真机验证的区别
- `CHANGELOG` 测试报告如何记录
- 为什么要分批提交并每批 push

实践任务：

- 按 `release-template.md` 填一份测试版 Release 说明
- 为一次 Bug 修复拆分“代码提交”和“文档提交”

### 第 9 课：AI Coding 工程化

推荐阅读：

- [spec-coding-insights.md](spec-coding-insights.md)
- [.trae/rules/project_rules.md](../.trae/rules/project_rules.md)
- [.trae/rules/entropy-governance.md](../.trae/rules/entropy-governance.md)

学习重点：

- 规则层、规格层、变更层如何协同
- `specs/` 是行为契约，`changes/` 是变更工作区
- Entropy 治理：文档 Drift、命名漂移、死代码、配置一致性

实践任务：

- 为一个新功能写 `proposal/design/tasks`
- 检查一次代码变更是否同步了 specs、README、CHANGELOG

## 推荐补充资料

项目内已有资料以实战为主，如果要做完整课程，建议补充以下主题：

- **MicroPython 基础课**：文件系统、模块导入、异常处理、`machine`、`network`、`bluetooth`
- **BLE 协议基础课**：GATT、Service、Characteristic、Notify、Advertising
- **HTTP 与 Socket 基础课**：HTTP 请求头、`Content-Length`、短连接、超时与资源释放
- **嵌入式可靠性课**：看门狗、断电恢复、原子替换、配置损坏恢复
- **版本发布课**：SemVer、CHANGELOG、Release Notes、固件附件、回滚策略

## 建议新增的课程材料

后续如果继续完善，可以新增：

- `docs/course-micropython-basics.md`：MicroPython 入门与 ESP32-C3 常用模块
- `docs/course-ble-cps.md`：BLE Cycling Power Service 数据结构详解
- `docs/course-ota-reliability.md`：嵌入式 OTA 可靠性设计
- `docs/course-ai-coding-workflow.md`：从规格到提交的 AI Coding 工作流

这些文档暂不创建，避免空文档堆积；等开始实际授课或整理笔记时再补。
