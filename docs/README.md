# 文档目录

> 本目录按用途分类维护。优先从本文件进入，避免在多个文档之间重复查找。

## 一、用户使用

HTML 学习版入口：[html/index.html](html/index.html)

| 文档 | 用途 | 适合读者 |
|------|------|----------|
| [user-manual.md](user-manual.md) | 完整用户手册：硬件、按钮、配网、OTA、FAQ | 普通用户、测试人员 |
| [esp32c3-board-guide.md](esp32c3-board-guide.md) | 合宙 CORE ESP32-C3 开发板硬件参考 | 硬件接线、排障 |

## 二、开发与部署

| 文档 | 用途 | 适合读者 |
|------|------|----------|
| [firmware-build.md](firmware-build.md) | MicroPython 固件编译、冻结模块、烧录 | 开发者、发版人员 |
| [robot-deploy.md](robot-deploy.md) | 自动部署脚本、异常处理、监控页面 | AI Agent、开发者 |
| [release-template.md](release-template.md) | CHANGELOG 与 GitHub Release 填空模板 | 发版人员 |

## 三、架构与专项设计

| 文档 | 用途 | 适合读者 |
|------|------|----------|
| [ota-update-design.md](ota-update-design.md) | OTA 方案设计、版本清单、回滚、API、测试计划 | 架构设计、维护者 |
| [esp32c3-optimization.md](esp32c3-optimization.md) | ESP32-C3 MicroPython 内存、BLE/WiFi、Socket 优化 | 性能优化、问题排查 |

## 四、学习资料

| 文档 | 用途 | 适合读者 |
|------|------|----------|
| [../AGENTS.md](../AGENTS.md) | 跨 AI 工具的最小入口规则，链接到项目规则和治理文档 | AI Agent、维护者 |
| [learning-path.md](learning-path.md) | 课程式学习路线：从硬件到 BLE/WiFi/OTA/工程化 | 新开发者、课程整理 |
| [open-source-references.md](open-source-references.md) | 相关开源项目参考与学习方向 | 技术调研、进阶学习 |
| [spec-coding-insights.md](spec-coding-insights.md) | Spec Coding 与 AI Coding Harness 实践总结 | AI 工程化学习 |
| [agent-governance.md](agent-governance.md) | AI Agent 记忆、规则、测试、提交和复盘治理规范 | AI Agent、维护者 |

## 五、销售与发布文案

| 文档 | 用途 | 适合读者 |
|------|------|----------|
| [sales-listing.md](sales-listing.md) | 闲鱼商品文案 + 发布规则 + 图片建议 | 商品发布 |

## 合并与精简说明

- `sales-listing.md` 与原 `xianyu-reference.md` 内容高度相关，已合并为单文件，避免“文案”和“规则”分散维护。
- `user-manual.md` 与 `esp32c3-board-guide.md` 都包含硬件信息，但定位不同：前者面向用户，后者面向硬件参考，保留分离。
- `firmware-build.md` 与 `robot-deploy.md` 都涉及部署，但定位不同：前者关注编译烧录，后者关注自动部署和脚本流程，保留分离。
- `ota-update-design.md` 与 `release-template.md` 都涉及发版，但定位不同：前者是 OTA 架构设计，后者是发版填空模板，保留分离。
- `agent-governance.md` 只沉淀长流程治理方法，强制执行条款仍以 `.trae/rules/` 和 `MEMORY.md` 为准。

## 维护规则

- 新增文档时，必须在本目录索引中登记分类。
- 文档内容如果跨两类重复，优先保留“源头文档”，其他文档只保留链接。
- 面向用户的操作说明放入 `user-manual.md`，面向开发者的实现细节放入专项设计文档。
- 面向课程学习的资料统一补充到 `learning-path.md` 或从该文档链接出去。
- 面向 AI Agent 的长流程规范统一补充到 `agent-governance.md`，不要散落在临时对话中。
- `html/` 是 Markdown 文档的课程讲义版静态页面，用于快速学习和浏览。
