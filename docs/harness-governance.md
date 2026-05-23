# Harness 治理体系文档

> 基于 Anthropic 官方 Harness 工程思想 + Claude Code 源码架构分析 + 社区最佳实践，结合 ESP32-C3 嵌入式项目特点构建的七层防御体系。
> 核心目标：把规范从"软约束"（靠 AI 记忆）变成"硬护栏"（靠代码强制）。
> 参考来源：Anthropic 官方博客「How Claude Code works in large codebases」(2026-05-14)、Claude Code 源码分析、Anthropic Skills 规范

---

## 一、背景与动机

### 1.1 痛点

| 痛点 | 描述 | 根因 |
|------|------|------|
| AI 失忆 | 对话中说的约束（如"WiFi 启动前必须关 BLE"），context compact 后全忘 | context 压缩时临时口头约束全部丢失 |
| 规范执行不稳定 | 命名规范、BLE 回调禁止新对象、Socket 不超过 3 等，靠 prompt 记忆的遵守率只有 70-80% | 规范停留在"LLM 记忆中的指导性内容"，不是"每次执行时强制检查的护栏" |
| 跨模块影响遗漏 | 修改 config.py 常量后忘记同步 specs/、power_data.py、web_pages.py | 靠 AI 记忆检查关联模块，容易遗漏 |
| CLAUDE.md 膨胀 | 规则文件越写越长，AI 对长规则的遵循率下降 | Anthropic 官方经验：单个文件 60~120 行最优，200 行封顶后规则被降权 |
| 经验无法沉淀 | 每次踩坑只在当前会话记忆，下次会话重复踩 | 缺少跨会话的经验持久化机制 |

### 1.2 核心思想

> **"决定 Claude Code 表现上限的，不是模型，是你围绕模型搭的那套脚手架。"**
> —— Anthropic 官方博客「How Claude Code works in large codebases」

> **模型决定做什么，Harness 负责执行怎么做。**
> —— Claude Code 源码分析

> **规范执行是人的短板、AI 的长板；业务判断是 AI 的短板、人的长板。**
> Harness 的目标：把"执行层"的不稳定因素系统性消掉。

### 1.3 Harness 核心公式

来自 Claude Code 源码架构分析：

```
Harness = Tools + Knowledge + Observation + Action Interfaces + Permissions

  Tools:       file I/O, shell, network, database, browser
  Knowledge:   product docs, domain references, API specs, style guides
  Observation: git diff, error logs, browser state, sensor data
  Action:      CLI commands, API calls, UI interactions
  Permissions: sandboxing, approval workflows, trust boundaries
```

---

## 二、七层防御体系

### 架构总览

基于 Anthropic 官方定义的 Harness 七层扩展点（CLAUDE.md → Hooks → Skills → Plugins → LSP → MCP → Subagents），结合本项目 ESP32-C3 嵌入式场景适配：

```
┌──────────────────────────────────────────────────────┐
│  第一层：迭代状态持久化（对应 CLAUDE.md）              │
│  .trae/rules/iteration_state.md                      │
│  每次 compact 后从磁盘重新注入                         │
│  Anthropic 原则：保持精简，60~120 行最优               │
├──────────────────────────────────────────────────────┤
│  第二层：技术踩坑记忆（对应 Auto Memory）              │
│  MEMORY.md 第九章                                     │
│  跨会话积累踩坑经验，"每个错误都变成一条规则"           │
├──────────────────────────────────────────────────────┤
│  第三层：SKILL 分步封装（对应 Skills）                 │
│  .trae/rules/task_templates.md                        │
│  按需加载，Progressive Disclosure 渐进式披露           │
├──────────────────────────────────────────────────────┤
│  第四层：Hooks 自动检查护栏（对应 Hooks）              │
│  .trae/rules/auto_hooks.md + entropy_scan.py          │
│  确定性强制执行，不依赖 AI 记忆                         │
├──────────────────────────────────────────────────────┤
│  第五层：Stop Hook 自改进（对应 Stop Hook）            │
│  会话结束时回顾经验，自动更新规则文件                    │
│  Anthropic 原则：Hooks 的最高阶用法是自我改进           │
├──────────────────────────────────────────────────────┤
│  第六层：Entropy 治理扫描（对应 Plugin 分发）          │
│  版本发布前全量扫描，确保规范与代码同步                  │
├──────────────────────────────────────────────────────┤
│  第七层：配置一致性闭环（对应 MCP/LSP 集成）           │
│  config.py ↔ specs ↔ power_data ↔ web_pages ↔ 文档    │
│  修改一处自动检查所有关联                               │
└──────────────────────────────────────────────────────┘
```

### 与 Anthropic 官方七层扩展点的映射

| Anthropic 官方层 | 本项目对应 | 实现方式 | 状态 |
|-----------------|----------|---------|------|
| **CLAUDE.md** | iteration_state.md + code_style.md + hardware_constraints.md | .trae/rules/ 规则文件 | ✅ |
| **Hooks** | auto_hooks.md + entropy_scan.py --hooks | 23 项确定性检查 | ✅ |
| **Skills** | task_templates.md | 6 个 SKILL 模板，按需加载 | ✅ |
| **Plugins** | Entropy 治理扫描 | 版本发布前全量检查 | ✅ |
| **LSP** | 配置一致性闭环 | config.py ↔ 多模块自动检查 | ✅ |
| **MCP** | 暂不需要 | 本项目无外部工具集成需求 | ⏭️ |
| **Subagents** | 暂不需要 | 本项目代码量 < 3000 行 | ⏭️ |

### 各层详细说明

#### 第一层：迭代状态持久化（对应 CLAUDE.md）

| 属性 | 说明 |
|------|------|
| 文件 | `.trae/rules/iteration_state.md` |
| 机制 | 作为 always applied rules，每次 context 加载时自动注入 |
| 内容 | 正在开发的模块、本次迭代约束、待验证项、全局不变约束 |
| 操作 | 进入新迭代时更新"正在开发"和"本次迭代约束"，上线后清空 |

**Anthropic 官方最佳实践**：
- CLAUDE.md 不是剪贴簿，是路由层——只放"去掉就会犯错"的规则
- 单个文件 60~120 行最优，200 行封顶，超过后规则被默认降权
- 每行自问："去掉这行会导致 AI 犯错吗？"如果不会，删掉
- 用 `IMPORTANT` 或 `YOU MUST` 提升关键规则权重
- 子目录放局部约定，根目录放全局规范，Claude 移动时自动叠加

**解决的问题**：AI 在长对话中忘记"当前正在做什么"和"本次不能改什么"。

#### 第二层：技术踩坑记忆（对应 Auto Memory）

| 属性 | 说明 |
|------|------|
| 文件 | `MEMORY.md` 第九章 |
| 机制 | 跨会话持久化，AI 每次执行任务前回顾 |
| 内容 | 按模块分类的踩坑记录，标记严重度（CRITICAL/WARNING/INFO） |
| 操作 | 每次发现踩坑时主动追加，版本发布前 review，CRITICAL 级别升级为规则 |

**Anthropic 官方最佳实践**：
- "每当 Claude 犯错，就把规则加入 CLAUDE.md"——Boris Cherny（Claude Code 创建者）的黄金法则
- Stop Hook 可以在会话结束时自动回顾经验并更新规则文件
- 经验沉淀的闭环：犯错 → 记录 → 规则化 → 自动检查 → 不再犯错

**解决的问题**：同一类错误在不同会话中重复出现。

#### 第三层：SKILL 分步封装（对应 Skills）

| 属性 | 说明 |
|------|------|
| 文件 | `.trae/rules/task_templates.md` |
| 机制 | 复杂任务拆成 Step 1~N，每步只关注当前步骤的规范 |
| 内容 | 6 个 SKILL 模板：BLE 修改、WiFi 修改、新增配置、按钮修改、编译烧录、OTA 发布 |
| 操作 | 每步完成后运行 Hooks 检查，确认通过后再进入下一步 |

**Anthropic 官方最佳实践**：
- Skills 采用 **Progressive Disclosure（渐进式披露）** 策略，分三层加载：
  - Level 1: Metadata（元数据触发描述）——Agent 首先看到的摘要
  - Level 2: Body（主体内容）——判断需要后加载的详细信息
  - Level 3: References（引用资料）——深入分析时才加载的参考资料
- Skills 可以绑定路径，只在相关目录下激活
- 不是每次会话都加载全部知识，按需加载避免 context 膨胀

**解决的问题**：复杂任务一次性加载所有规范导致 context 膨胀，AI 注意力分散。

#### 第四层：Hooks 自动检查护栏（对应 Hooks）

| 属性 | 说明 |
|------|------|
| 规则文件 | `.trae/rules/auto_hooks.md` |
| 执行脚本 | `scripts/entropy_scan.py --hooks` |
| 机制 | 代码修改后运行脚本，自动检查 23 项规范 |
| 内容 | H1~H23 检查项，覆盖语法、CPython 库、print()、const()、日志器、繁体中文、docstring、配置一致性、BLE/WiFi/OTA/按钮/LED 硬件约束 |

**Anthropic 官方最佳实践**：
- Hooks 与 CLAUDE.md 的关键区别：CLAUDE.md 是"建议"（advisory），Hooks 是"确定性执行"（deterministic）
- 大多数团队把 Hook 当安全护栏防止犯错，但**更高阶的用法是 Stop Hook 自我改进**
- 自动化检查（lint、format、typecheck）不应该靠 AI 记住，应该靠 Hook 强制执行
- Hooks 可以在特定操作点触发 shell 命令，保证 100% 执行

**检查项分类**：

| 分类 | 检查项 | 数量 |
|------|--------|------|
| 通用代码规范 | H1~H7 | 7 |
| 配置一致性 | H8~H11 | 4 |
| BLE 硬件约束 | H12~H14 | 3 |
| WiFi 硬件约束 | H15~H18 | 4 |
| OTA 安全约束 | H19~H21 | 3 |
| 按钮/LED 约束 | H22~H23 | 2 |

#### 第五层：Stop Hook 自改进（新增）

| 属性 | 说明 |
|------|------|
| 机制 | 会话结束时回顾本次会话经验，自动更新规则文件 |
| 触发 | 每次完成代码修改后 |
| 内容 | 检查是否有新的踩坑经验需要记录、是否有规则需要更新 |

**Anthropic 官方最佳实践**：
- "大多数团队把 Hook 当安全护栏，但更高阶的用法是 Stop Hook，每次会话结束时让 Claude 回顾干了什么，自动总结经验并更新 CLAUDE.md"
- "会话结束，经验沉淀。下次会话，Claude Code 就会更懂你"
- Stop Hook 应检查是否已触发（防止无限循环），使用 `stop_hook_active` 标志

**本项目实现**：
- AI 在完成代码修改后，主动检查是否有新踩坑经验
- 如果有，追加到 MEMORY.md 第九章
- 如果 CRITICAL 级别，同步更新 .trae/rules/ 中的规则文件

#### 第六层：Entropy 治理扫描（对应 Plugin 分发）

| 属性 | 说明 |
|------|------|
| 执行脚本 | `scripts/entropy_scan.py` / `--all` |
| 机制 | 版本发布前全量扫描，确保规范与代码同步 |
| 内容 | 5 项 Entropy 扫描 + 23 项 Hooks 检查 |

**Anthropic 官方最佳实践**：
- Plugin 的核心价值：把好的本地配置从"部落知识"变成"可分发的标准"
- 新工程师第一天安装 Plugin，就能拥有和老工程师一样的起点
- 配置需要定期维护——模型在更新，为上一代模型写的规则可能在下一代不适用

**Entropy 扫描项**：

| 检查项 | 说明 |
|--------|------|
| 文档 Drift | specs/ 与代码实际行为是否一致 |
| 命名漂移 | 变量/函数命名是否符合 code_style.md |
| 死代码 | 未被 import 的模块、未被调用的函数、未被引用的常量 |
| 规则腐烂 | .trae/rules/ 中是否有过时内容 |
| 配置一致性 | config.py 常量是否在 specs/power_data/web_pages 中正确引用 |

#### 第七层：配置一致性闭环（对应 LSP/MCP 集成）

| 属性 | 说明 |
|------|------|
| 机制 | 修改 config.py 后自动检查所有关联模块 |
| 内容 | config.py ↔ specs/ ↔ power_data.py ↔ web_pages.py ↔ hardware_constraints.md |

**Anthropic 官方最佳实践**：
- LSP 让 Claude 用符号级精度导航代码，而不是靠字符串匹配
- MCP 让 Claude 连接内部工具和数据源
- 本项目规模小，用 Hooks 检查替代 LSP/MCP 实现配置一致性闭环

**闭环检查链**：
```
config.py 修改常量
  → H8:  检查 specs/ 常量值是否一致
  → H9:  检查 power_data.py 范围校验是否一致
  → H10: 检查 web_pages.py 表单范围是否一致
  → H11: 检查 hardware_constraints.md 参数是否一致
```

---

## 三、使用方式

### 3.1 日常开发流程

```
1. 开始新迭代 → 更新 iteration_state.md
2. 选择对应 SKILL 模板 → 按步骤执行
3. 每步完成后 → 运行 python3 scripts/entropy_scan.py --hooks
4. 发现踩坑 → 追加到 MEMORY.md 第九章
5. 会话结束前 → 回顾本次经验，更新规则文件（第五层自改进）
6. 上线前 → 运行 python3 scripts/entropy_scan.py --all
7. 上线后 → 清空 iteration_state.md 本次迭代约束
```

### 3.2 脚本命令

```bash
# Hooks 快速检查（H1~H23，推荐每次修改后运行）
python3 scripts/entropy_scan.py --hooks

# Entropy 治理扫描（5 项，版本发布前运行）
python3 scripts/entropy_scan.py

# 全量扫描（Entropy + Hooks，版本发布前运行）
python3 scripts/entropy_scan.py --all
```

### 3.3 与原有体系的关系

| 原有文件 | 变化 | 说明 |
|---------|------|------|
| `.trae/rules/code_style.md` | 不变 | 代码风格规范，第一层的长期规范来源 |
| `.trae/rules/hardware_constraints.md` | 不变 | 硬件约束规范，第四层 H12~H23 的检查依据 |
| `.trae/rules/entropy-governance.md` | 不变 | Entropy 扫描规则，版本发布前执行 |
| `.trae/rules/project_rules.md` | 更新 | 新增 Harness 文件结构 |
| `.trae/rules/iteration_state.md` | **新增** | 第一层：迭代状态持久化 |
| `.trae/rules/auto_hooks.md` | **新增** | 第四层：Hooks 检查规则 |
| `.trae/rules/task_templates.md` | **升级** | 从简单模板升级为分步 SKILL |
| `scripts/entropy_scan.py` | **增强** | 新增 --hooks 和 --all 模式 |
| `MEMORY.md` | **增强** | 新增第九章：技术踩坑记忆 |

---

## 四、与得物数仓 Harness 的对比

| 维度 | 得物数仓方案 | 本项目方案 | 差异原因 |
|------|------------|----------|---------|
| 代码规模 | 数百个 SQL + 419 个 DataWorks 任务 | 9 个 .py 文件 | 本项目规模小，不需要完整五层 |
| 第五层 Subagent | 必须（血缘查询 500-3000 tokens） | 不需要 | 本项目全量代码 < 3000 行，context 压力小 |
| SKILL 分步 | 8 步 ETL 开发流程 | 6 个 SKILL 模板 | 本项目任务类型少，6 个模板已覆盖 |
| Hooks 检查项 | SQL 规范（INSERT 带 PARTITION 等） | 硬件约束（BLE/WiFi 互斥等） | 领域不同，但"硬护栏"思想一致 |
| 核心收益点 | 第四层 Hooks | 第四层 Hooks | 共识：规范执行不稳定是最大痛点 |

---

## 五、Anthropic 官方 Harness 核心洞察

> 以下内容综合自 Anthropic 官方博客、Claude Code 源码分析、社区实践。

### 5.1 Harness 决定上限

> "决定 Claude Code 表现上限的，不是模型，是你围绕模型搭的那套脚手架。"

模型只是 Harness 的一个组件。CLAUDE.md 是路由层，Hooks 是确定性护栏，Skills 是按需知识，Plugin 是分发机制，LSP 是符号级导航，MCP 是外部工具连接，Subagents 是探索与编辑的分离。每一层都独立贡献价值。

### 5.2 Hooks 的两种用法

| 用法 | 说明 | 本项目对应 |
|------|------|----------|
| **安全护栏**（初级） | 防止 Claude 犯错：格式化、lint、类型校验 | H1~H23 确定性检查 |
| **自我改进**（高级） | Stop Hook 回顾经验，自动更新规则文件 | 第五层自改进机制 |

### 5.3 Skills 的 Progressive Disclosure

```
Level 1: Metadata    → Agent 首先看到的摘要（触发描述）
Level 2: Body        → 判断需要后加载的详细信息
Level 3: References  → 深入分析时才加载的参考资料
```

不是每次会话都加载全部知识。安全审查 Skill 只在审核代码时加载，文档更新 Skill 只在改了代码之后加载。Skills 还能绑定路径，支付团队的部署 Skill 只在支付服务目录下激活。

### 5.4 CLAUDE.md 维护原则

- 每行自问："去掉这行会导致 AI 犯错吗？"如果不会，删掉
- 模型在更新，为上一代模型写的规则可能在下一代不适用
- 每 3~6 个月做一次配置 review
- 用 `IMPORTANT` 或 `YOU MUST` 提升关键规则权重
- Boris Cherny（Claude Code 创建者）的 CLAUDE.md 只有 ~100 行，却比 800 行配置表现更好

### 5.5 探索与编辑分离

> "先派一个只读子代理去扫描某个子系统，把结果写进文件，然后主代理带着完整认知去更新代码。探索和修改，应该分开进行。"

本项目规模小，暂不需要 Subagent，但"先分析再动手"的原则通过 SKILL 模板的 Step 1（影响分析）实现。

### 5.6 上下文管理是核心约束

> "大多数最佳实践都基于一个约束：上下文窗口填充得很快，填满后性能会下降。"

- 上下文达到 50% 时手动执行 `/compact`，不要等到自动触发
- 每开始新任务时用 `/clear` 清除旧历史
- 结构化 prompt 比叙述式 prompt 少消耗 30% 的 token
- PreCompact hooks 可减少 30% 的关键信息丢失

### 5.7 OODA 循环：Harness 负责四分之三

来自 claudecode-lab.com 的 OODA 循环分析：

| 阶段 | 内容 | 负责方 |
|------|------|--------|
| Observe（观察） | 获取环境状态（读文件、查数据库） | **Harness** |
| Orient（研判） | 整理信息并交给 LLM | **Harness** |
| Decide（决策） | 决定下一步动作 | **LLM** |
| Act（执行） | 落地执行（执行命令、调 API） | **Harness** |

四个阶段中三个归 Harness 负责，LLM 擅长的只有 Decide。撑起其余部分的脚手架质量，直接决定整个 Agent 的水平。

### 5.8 Claude Code 源码泄露的关键发现

来自 36kr/硅星人Pro 对 Claude Code 源码泄露的分析：

| 发现 | 源码证据 | 本项目启示 |
|------|---------|----------|
| Skill 列表最多占窗口 1% | `MAX_LISTING_DESC_CHARS = 250` | 触发描述要精简，50 字和 500 字匹配率无差别 |
| System prompt 切成两半 | 固定部分缓存复用 + 动态部分按需生成 | .trae/rules/ 固定规则与动态迭代状态分离 |
| 三级压缩 + 熔断器 | `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3` | 压缩失败不应无限重试，3 次就停 |
| 记忆筛选过滤刚用过的工具 | `selectRelevantMemories` 过滤 `recentTools` | 不重复注入已知信息 |
| ToolSearch 延迟加载 | MCP 工具默认延迟，ToolSearch 永远完整 | 按需加载，不是全部塞进 context |
| 权限弹窗提前消除 | 分类器在弹窗准备期间已判断 | 减少等待，提升体验 |
| Sub-agent 四种执行模式 | 同步/异步/Worktree/跨机器 | 风险越高，隔离越彻底 |
| Hook 系统 27 个事件节点 | PreToolUse/PostToolUse/Stop 等 | Hook 让 Harness 从产品变成平台 |

### 5.9 运行时中心的 Harness 风格

来自果叔（mrguo.life）的源码深度分析：

> "Claude Code 不是纯文档驱动 Harness，也不是纯 CI 驱动 Harness，它是一套运行时中心的 Harness。"

Claude Code 的气质最接近：
- OpenAI 的"Agent Runtime + 机械化护栏"
- 加上 Anthropic 的"长任务连续性与跨会话恢复"
- 再加一点 Hashimoto 的"把历史失败折叠回系统约束"

四大支柱映射：

| 支柱 | Claude Code 实现 | 本项目对应 |
|------|-----------------|----------|
| 上下文架构 | 分层、裁剪、压缩、角色化、动态装配 | iteration_state.md + code_style.md + hardware_constraints.md |
| Agent 专业化 | Agent 是运行时规格对象（tools/disallowedTools/skills/hooks/model/effort） | SKILL 模板的工具面裁剪 |
| 持久化记忆 | 任务/会话状态 + Agent 角色记忆双层 | MEMORY.md 第九章 + iteration_state.md |
| 结构化执行 | Plan Mode + Verification Agent + query loop 状态机 | SKILL 模板 Step 1 影响分析 + H1~H23 检查 |

### 5.10 Harness 的五重含义

来自花叔（公众号「花叔」）的 Harness 工程方法论：

| 含义 | 解释 | AI 对应 |
|------|------|---------|
| 马具 | 驯驭野马，缰绳让马的力量变得有用 | 约束和引导系统，让 AI 的能力有用 |
| 航天线束 | NASA 严格标准，一根线松了整个任务完了 | 在混乱的语义环境中确保意图准确执行 |
| 测试线束 | 创建受控环境，让被测对象可预测运作 | 隔离 Agent 行为，提供约束和反馈的执行环境 |
| 安全带 | 不限制自由，但防止坠落 | 不限制 Agent 创造力，但阻止灾难 |
| 电气线束 | 连接一切，让零件不再是孤岛 | 连接模型、工具、文档、测试、部署管道 |

### 5.11 六大关键实践

来自腾讯云/人月聊IT 的 Claude Code 六维度分析：

| 维度 | 核心原则 | 本项目对应 |
|------|---------|----------|
| 工具集成调用 | 工具即缰绳，Tool Search 节省 85% Token | SKILL 模板按需加载 |
| 上下文管理 | 智能不是瓶颈，上下文才是 | iteration_state.md 精简注入 |
| 安全设计 | 三级权限体系（Allow/Ask/Deny） | Hooks H1~H23 确定性检查 |
| 可控性设计 | 六种权限模式连续谱 | auto_hooks.md + Stop Hook |
| 代码质量保障 | 质量不靠 AI 自觉，靠外部神谕 | entropy_scan.py 确定性扫描 |
| 长周期静默运行 | 无人值守时依然被结构化驾驭 | CI 集成（规划中） |

### 5.12 五大常见陷阱

来自 claudecode-lab.com 的实践总结：

| 陷阱 | 说明 | 本项目规避方式 |
|------|------|--------------|
| 工具给得太多 | 一口气塞 30 个工具，模型选择犹豫精度下降 | 6 个 SKILL 模板，经验值 5~15 个 |
| 没用 Prompt Cache | 冗长 system prompt 每次全量发送 | .trae/rules/ 固定规则与动态状态分离 |
| 错误信息 LLM 看不懂 | 工具只返回 `Error: undefined` | entropy_scan.py 输出具体文件+行号+原因 |
| 省略人工确认 | 破坏性操作设为自动通过 | WiFi 启动需用户二次确认 |
| 记忆从不整理 | 旧信息让 Agent 在错误前提下动作 | MEMORY.md 版本发布前 review，CRITICAL 升级为规则 |

---

## 六、演进路线

| 阶段 | 内容 | 状态 |
|------|------|------|
| v2.0.1 | 第一层迭代状态 + 第四层 Hooks + 第二层踩坑记忆 + 第三层 SKILL | ✅ 已完成 |
| v2.0.1 | Hooks 扫描发现的 9 个问题修复 | ✅ 已完成 |
| v2.0.1 | 七层架构对齐 + 官方最佳实践整合 | ✅ 已完成 |
| v2.1.0 | 第五层 Stop Hook 自改进机制完善 | 规划中 |
| v2.2.0 | Hooks 集成到 CI（git pre-commit hook） | 规划中 |
| v3.0.0 | 第七层 Subagent（如项目规模增长需要） | 远期规划 |

---

## 七、参考资料

| 来源 | 标题 | 日期 | 关键洞察 |
|------|------|------|---------|
| Anthropic 官方博客 | How Claude Code works in large codebases | 2026-05-14 | Harness 七层扩展点、CLAUDE.md 维护原则、三种配置模式 |
| Anthropic 官方博客 | Claude Code Best Practices | 2025-04-18 | 探索-计划-编码工作流、上下文管理、验证机制 |
| Claude Code 源码分析 | 从 Harness 角度对 Claude Code 源码深度解读 | 2026-04-02 | Harness 核心公式、Agent Loop、工具系统、上下文压缩 |
| Anthropic Skills 规范 | How to create Skills | 2025-11-19 | Progressive Disclosure、Skill 触发描述写法 |
| Claude Code Hooks 文档 | Hooks 完全指南 | 2026 | 18 种 Hook 事件、Stop Hook 自改进、PreCompact 上下文保护 |
| 社区实践 | Claude Code 实战最佳实践 | 2026-03 | 上下文 50% 时 compact、结构化 prompt 省 30% token |
| moony01.com | Claude Code Large Repos Need More Than A Bigger Model | 2026-05-17 | "CLAUDE.md 不是剪贴簿，是路由层" |
| 得物技术（微信公众号） | Claude Code Harness 工程:数仓侧落地方案 | 2026-05 | 五层防御体系、compact 丢什么、SQL 规范 Hooks |
| 36kr/硅星人Pro | Claude Code 大泄露：别光 Clone 了，当今最顶 Harness 开源了 | 2026-04-01 | 源码泄露分析：Skill 列表 1%、三级压缩熔断器、Hook 27 事件 |
| claudecode-lab.com | Harness 工程完全指南 | 2026-04-16 | OODA 循环、三档 Harness、五大常见陷阱、迷你 harness 代码 |
| 果叔/mrguo.life | Harness Engineering 深度解析：Claude Code 运行时护栏 | 2026-03-31 | 运行时中心 Harness、四大支柱、Agent 专业化、结构化执行 |
| 腾讯云/人月聊IT | ClaudeCode-Harness Engineering 驾驭者工程的最佳实践者 | 2026-04-13 | 六大关键实践、三级权限体系、六种权限模式、外部神谕 |
| 花叔（公众号） | Harness Engineering AI 编程时代的工程方法论 | 2026-04-02 | 五重含义、五个组件、减法哲学、7 个案例 |
| 极客时间/黄佳 | Harness 架构深度解析 | 2026 | Agentic Loop、Harness 五组件、OODA 循环 |
| GitHub/flying-coyote | Claude Code Project Best Practices | 2026-03 | 6-Layer Harness Stack、Three Properties、Bitter Lesson |
| mrguo.life | Harness Engineering 深度解析 | 2026-03-31 | 运行时中心 Harness、四大支柱映射、Agent 规格对象 |
