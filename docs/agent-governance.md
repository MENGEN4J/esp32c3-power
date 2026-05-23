# AI Agent 治理规范

> 本文记录 AI Agent 在本项目中的记忆、规则、测试、提交和复盘流程。目标是减少长对话漂移，避免规则冲突，并把正确方案沉淀为可复用规范。

## 一、信息分层

| 文件 | 职责 | 维护原则 |
|------|------|----------|
| `MEMORY.md` | 用户偏好、历史要求、已验证结论、踩坑记录 | 只记录项目特有且会反复影响决策的内容 |
| `AGENTS.md` | 跨 AI 工具的最小入口规则 | 只放必须先读的索引和高优先级禁止项 |
| `.trae/rules/*.md` | 强制执行规则、硬件约束、代码风格、提交流程 | 写成可检查条款，避免长篇背景说明 |
| `specs/*.md` | 模块行为规格 | 只描述 GIVEN/WHEN/THEN 行为，不放发散建议 |
| `docs/*.md` | 给人看的教程、设计、流程说明 | 长流程放这里，规则文件只链接或摘录要点 |
| `CHANGELOG.md` | 每次变更和测试报告 | 提交前必须补齐实际验证结果 |

## 二、记忆写入规则

以下内容必须写入 `MEMORY.md`：

| 触发条件 | 记录内容 |
|----------|----------|
| 用户提出长期偏好 | 偏好、适用范围、日期 |
| 某个方案被验证正确 | 问题、最终方案、验证方法、日期 |
| 反复踩坑 | 错误现象、根因、禁止做法、正确做法 |
| 提交流程变更 | 新增步骤、前置条件、禁止事项 |

以下内容不要写入 `MEMORY.md`：

| 类型 | 原因 |
|------|------|
| 一次性任务细节 | 会污染后续上下文 |
| 已能从源码推导的信息 | 增加 token 成本，容易过时 |
| 未验证猜测 | 容易被后续 Agent 当成事实 |
| 与规则重复的大段说明 | 规则放 `.trae/rules/`，记忆只放索引和结论 |

## 三、规则冲突治理

每次修改 `.trae/rules/` 或 `MEMORY.md` 后，必须做冲突检查：

| 检查项 | 通过标准 |
|--------|----------|
| `MEMORY.md` vs `project_rules.md` | 提交、发版、版本号、测试要求一致 |
| `code_style.md` vs 源码 | 命名、日志、MicroPython 限制一致 |
| `hardware_constraints.md` vs `config.py` | 引脚、按钮阈值、BLE/WiFi 参数一致 |
| `optimization-review.md` vs 实际目录 | 文件归属原则与目录结构一致 |
| `docs/README.md` vs `docs/` | 文档分类和真实文件一致 |

冲突处理顺序：

1. 先以硬件事实和源码实际行为为准。
2. 再同步 `specs/` 和 `.trae/rules/`。
3. 最后同步 `MEMORY.md`、`README.md`、`docs/README.md`。
4. 如果无法判断，停止修改并向用户确认。

## 四、测试与报告

每次提交前必须有测试记录，记录粒度按改动类型选择：

| 改动类型 | 必做验证 | 报告位置 |
|----------|----------|----------|
| MicroPython 业务代码 | `py_compile` + 相关链路测试 + 必要时真机部署 | `CHANGELOG.md` 测试报告 |
| 脚本/发版流程 | `bash -n` 或帮助命令 + dry-run/实际产物检查 | `CHANGELOG.md` 测试报告 |
| 文档/规则 | 文档诊断、链接/路径检查、目录一致性检查 | `CHANGELOG.md` 或提交说明 |
| 固件发版 | 语法检查、`.mpy` 编译、固件编译、部署测试、version.json 校验 | `CHANGELOG.md` 版本条目 |

禁止事项：

| 禁止项 | 原因 |
|--------|------|
| 未测试就提交 | 违反项目主流程 |
| 测试失败仍提交 | 会污染 main 分支 |
| 把未验证写成已通过 | 破坏测试报告可信度 |
| 文档改动写成真机已验证 | 验证范围不匹配 |

## 五、提交前流程

```text
1. git status --short
2. git diff --stat
3. 按功能拆分本批提交范围
4. 执行对应测试
5. 更新 CHANGELOG.md 测试报告
6. 检查 MEMORY.md / rules / specs / docs 是否需要同步
7. git diff 自检
8. git add 指定文件
9. git commit，消息附带 Model
10. git push
```

### 分批提交防呆流程

当一次任务中出现多个主题时，必须先拆分提交计划，再进入 `git add`：

| 改动主题 | 独立提交类型 | 示例范围 |
|----------|--------------|----------|
| Bug 修复 | `fix(...)` | `wifi_manager.py` + 对应 specs/CHANGELOG |
| 测试链路 | `test(...)` | `test/` + Mock 辅助脚本 |
| 发布产物整理 | `chore(release)` | `releases/` + `scripts/gen_version_json.py` |
| 文档/规则治理 | `docs(...)` | `AGENTS.md`、`MEMORY.md`、`.trae/rules/`、`docs/` |
| 截图/网页素材 | `docs(...)` 或 `chore(web)` | `images/`、`web/`、截图脚本 |

防呆要求：

1. 提交前必须执行 `git diff --name-status`。
2. 如果 diff 同时包含业务代码、测试、发布产物、文档规则中的 2 类以上，必须拆分。
3. 每批只 `git add` 本批文件，禁止默认 `git add -A`，除非本次任务本身就是单一主题。
4. 如果已经把多主题提交并 push，不主动改写历史；记录复盘并用后续独立提交修正规则。

## 六、项目结构建议

当前项目建议采用以下归属：

| 类型 | 建议位置 | 说明 |
|------|----------|------|
| ESP32 运行代码 | 根目录 `.py` | 便于 `mpremote cp` 直接部署 |
| Agent 入口规则 | 根目录 `AGENTS.md` | 跨工具最小上下文入口，链接到详细规则 |
| 固件全量包 | `target/` | 只保留 `firmware.bin` 和最新 3 个 `firmware-*.bin` |
| OTA 字节码包 | `releases/ota/vX.Y.Z/` | 每个版本一个目录，避免根目录堆积 |
| OTA 当前清单 | `releases/latest/version.json` | 设备固定读取稳定入口 |
| 长流程文档 | `docs/` | 发版、部署、Agent 治理等都放这里 |
| 复杂变更计划 | `changes/` | proposal/design/tasks，不放最终发布产物 |
| 自动化报告 | `test/reports/` | 本地生成，默认不入库 |

## 七、外部实践参考

| 实践 | 可借鉴点 | 本项目采纳方式 |
|------|----------|----------------|
| `AGENTS.md` 标准 | 把 AI 项目规则作为仓库内的“Agent README”，便于多工具复用 | 已增加根目录 `AGENTS.md`，只保留最小强规则并链接 `.trae/rules/` |
| Cursor Rules / `.cursor/rules` | 按领域拆分规则，避免一个超长规则文件污染所有任务 | 当前 `.trae/rules/` 已按代码风格、硬件、治理拆分，继续保持 |
| 规则最小化原则 | 只写 Agent 无法从代码推断的约束，降低上下文成本 | `MEMORY.md` 避免重复源码事实，只记录用户偏好和已验证决策 |
| 失败复盘规则 | 反复错误要沉淀为禁止事项和正确流程 | 截图污染、BLE/WiFi 互斥、部署测试流程已纳入记忆和规则 |

参考链接：

- [AGENTS.md 说明](https://kilo.ai/docs/customize/agents-md)
- [AGENTS.md 构建建议](https://www.augmentcode.com/guides/how-to-build-agents-md)
- [Cursor Rules 说明](https://aiwiki.ai/wiki/cursor_rules)
- [agent-best-practices 示例仓库](https://github.com/NextFrontierBuilds/agent-best-practices)
