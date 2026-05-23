# BikePower 项目记忆

AI 助手在执行任务前必须先回顾此文档，严格按照历史要求执行。
代码风格和硬件约束详见 `.trae/rules/code_style.md` 和 `.trae/rules/hardware_constraints.md`。

---

## 一、脚本与部署要求

1. **串口地址不写死** — 自动扫描 ESP32-C3 设备（通过 USB VID/PID 智能识别）
2. **跨平台支持** — macOS / Linux / Windows 三平台，编译烧录打包时需判断区分
3. **固件名称** — 编译输出的固件文件名统一为 `firmware.bin`
4. **部署后必须测试** — 每次部署后必须执行测试并生成 HTML 测试报告
5. **测试报告** — 生成 `web/test-report.html` 并在浏览器中打开
6. **target 固件保留策略** — `target/` 只保留 `firmware.bin` 和最新 3 个 `firmware-*.bin` 时间戳固件，旧时间戳固件自动清理
7. **OTA 发布目录** — `vX.Y.Z` 的 `.mpy` 推送文件统一放在 `releases/ota/vX.Y.Z/`，禁止继续散落在项目根目录

---

## 二、Git 提交与发布要求

1. **commit message 格式** — 遵循 Conventional Commits：`<type>(<scope>): <subject>`（详见 project_rules.md）
2. **详细变更记录在 CHANGELOG.md** — commit 只写简短标题，详情在 CHANGELOG.md 中记录
3. **版本号自增** — 基于 `git describe --tags --abbrev=0` 获取最新 tag，按 SemVer 规则递增
4. **版本号格式** — 三位语义化版本 `v主版本.次版本.补丁`（如 v1.8.0, v1.9.0）
5. **commit message、git tag、Gitee Release 版本号三者必须一致**
6. **推送发行版** — 代码提交后推送到 Gitee Release，上传固件文件
7. **发行版推送前置条件** — 必须包含 CHANGELOG 变更记录 + 测试报告，必须合并到 main 分支后才能打 tag 推送（详见 project_rules.md「发行版固件推送规则」）
7.5 **发行版必须包含固件文件** — Gitee Release 必须上传 target/firmware.bin（全量烧录固件），确保用户可直接下载烧录。编译通过后先确认 firmware.bin 存在再推送
8. **分批提交** — 按功能分批提交，不要一股脑全部提交，让用户清楚每次变更内容
9. **修改无误后自动提交并推送** — 每次修改验证无误后自动 commit + push，不需要额外确认。分批提交时每批 commit 后立即 push，不要积攒多批再统一推送
10. **提交前 diff 自检** — 每次提交前基于 diff 做自检：改动是否覆盖完整链路、是否有未使用 import、是否违反代码风格、是否需要更新文档
11. **commit message 末尾附带模型信息** — 每次 commit message 末尾必须附加当前使用的 AI 模型名称和版本，格式：`Co-authored-by: AI <ai@trae>` 换行 `Model: {模型名}`，例如 `Model: GLM-5.1`，便于追溯代码生成来源
12. **长流程必须文档化** — 涉及多步骤发版、测试、Agent 规则治理、复盘沉淀时，必须写入 `docs/agent-governance.md` 或对应专项文档，不能只停留在对话里
13. **多主题任务先拆批次** — 项目整体优化、发版整理、测试修复、文档规则治理混在同一轮时，必须先列分批计划，每批单独验证、提交、push

### 提交主流程（默认强制执行）

当用户说“提交”“推送”“按规则发版”时，默认按下面顺序执行，不能跳步骤：

1. **先看 diff** — 先检查工作区改动范围，确认是否只包含当前任务，避免把无关改动混入本次提交
2. **先做自检** — 检查链路是否完整、是否有未使用 import、是否违反代码风格、是否需要同步 README/specs/CHANGELOG/rules/docstring
3. **先编译和测试** — 与改动相关的语法检查、编译检查、部署测试、真机验证必须先做；未通过禁止提交
4. **测试通过后再提交** — 不允许用“理论上没问题”“待测试”代替已验证结果
5. **按功能分批提交** — 一个功能一批、一个 bug 修复一批、一个文档主题一批；禁止把不相关改动混在同一个 commit
6. **每批提交后立即 push** — 不要积攒多批改动再统一 push，确保每批历史都清晰可追踪
7. **进入发版流程时补齐产物** — 发版前必须补全 CHANGELOG、测试报告、`.mpy`、`firmware.bin`、`version.json`、tag、Release 说明

### 禁止事项（提交流程）

- **禁止先 commit 后测试** — 必须先验证通过，再提交代码
- **禁止测试失败仍提交** — 测试失败时先修复或明确阻塞原因，不能带着失败结果提交
- **禁止一股脑混提** — 文档、脚本、功能、修复若无直接关系，必须拆成多批提交
- **禁止只本地提交不 push** — 用户明确要求进入提交流程时，默认 commit 后继续 push
- **禁止伪造测试结论** — 真机未测就写未测，不能写成已通过
- **禁止绕过发版前置条件** — 未补 CHANGELOG、测试报告、`firmware.bin`、`version.json` 时，不能推送发行版
- **禁止在功能分支直接打正式 tag** — 必须先合并到 `main` 再按规则发版
- **禁止提交无关脏改动** — 提交前必须确认工作区中没有当前任务之外的误改文件
- **禁止在多主题工作区直接 `git add -A`** — 只有确认本次改动属于单一主题时才允许，否则必须按路径分批 add

### 文档改动提交流程清单

适用范围：`README.md`、`docs/`、`specs/`、`CHANGELOG.md`、`MEMORY.md`、`.trae/rules/`、模板文档等纯文档改动。

1. **检查改动范围** — 用 `git diff` 确认只包含文档文件，没有混入代码文件
2. **检查文档关联** — 确认是否需要同步 `README`、`CHANGELOG`、`specs`、`rules`、文件结构树、版本号、操作说明
3. **检查内容一致性** — 文档描述必须和当前代码、当前规则、当前目录结构一致
4. **做基础验证** — 至少执行文档诊断、Markdown 结构检查、链接路径检查；不要虚报真机测试
5. **明确验证范围** — 文档提交只写“文档检查通过”，不能写成“功能测试通过”
6. **单独成批提交** — 文档规则、发版模板、用户手册、README 同步等，按主题单独提交
7. **提交后立即 push** — 用户要求提交时，文档批次 commit 后立即 push 到远端

文档改动提交前自问：

- 这次是否只改文档，没有混入业务代码？
- 文档里的版本号、文件结构、命令、路径是否还是最新的？
- 是否把“未验证”的内容误写成“已验证”？
- 是否需要同步 `CHANGELOG.md` 或规则文档？

### 代码改动提交流程清单

适用范围：`.py` 业务代码、脚本、配置常量、启动逻辑、BLE/WiFi/OTA/按钮链路等任何会影响运行行为的改动。

1. **检查改动范围** — 用 `git diff` 确认本批只包含当前功能或当前 bug 修复相关文件
2. **先做链路自检** — 按改动类型检查 BLE、WiFi、按钮、配置持久化、OTA 等链路是否完整
3. **同步受影响文档** — 必须检查并同步 `docstring`、`README`、`specs`、`templates`、`CHANGELOG`、`rules`
4. **先做语法检查** — 至少确认相关 Python 文件语法正确
5. **先做编译/打包检查** — 若影响发版链路、OTA、脚本、构建流程，必须补做相关编译或打包验证
6. **先做部署/真机验证** — 只要改动影响设备行为，必须优先部署验证，不允许只做静态分析就提交
7. **测试通过后再提交** — 未通过时先修复，或明确阻塞原因并暂停提交
8. **按功能分批提交** — 一个功能一批、一个 bug 修复一批、一个脚本改造一批，禁止大杂烩
9. **提交后立即 push** — 每批通过验证的代码提交后立即 push，不要积压
10. **如进入发版流程** — 继续补齐 `CHANGELOG`、测试报告、版本号、`.mpy`、`firmware.bin`、`version.json`、tag、Release

代码改动提交前自问：

- 这批改动是否只解决一个明确问题？
- 相关链路是否真的走通，而不是只看代码觉得没问题？
- 受影响文档是否都同步了？
- 是否存在未使用 import、死代码、遗漏异常路径、未关闭资源？
- 若涉及硬件行为，是否已经部署并验证？

### 文档截图与 HTML 生成正确流程

适用范围：更新 `docs/user-manual.md`、`docs/html/`、`images/page*.png`、`web/config-preview.html`、`web/screenshots.html`、`scripts/capture_screenshots.py`。

1. **先确认工作区** — 截图和 HTML 生成前先执行 `git status --short`，确认没有无关删除或误改
2. **先生成临时预览页** — 执行 `python3 scripts/capture_screenshots.py` 生成 `web/page*.html`
3. **同步版本号** — 临时预览页、截图工具、预览页中的 `当前版本` 必须和 `config.FIRMWARE_VERSION` 一致
4. **截图必须隔离浏览器会话** — Chrome `--screenshot` 和 DevTools 在当前 macOS 会话可能复用已有窗口并截错页面，必须使用独立 profile / 独立实例，并在每张图生成后校验内容
5. **截图后必须抽查** — 至少读取 `page1_home.png`、`page2_wifi_scan.png`、`page4_update_available.png`、`page6_update_progress.png`，确认不是空图、不是浏览器窗口、没有裁切
6. **清理临时文件** — 截图完成后删除 `web/page*.html`，这些只是临时中间产物，不要提交
7. **重新生成 HTML 手册** — 更新 Markdown 后必须同步 `docs/html/user-manual.html`，并确认图片路径在 `docs/html/` 下可访问
8. **记录验证结果** — 在 `CHANGELOG.md` 写清文档诊断、HTML 解析、截图尺寸和未做真机验证的原因
9. **按页面内容动态选截图口径** — 不要给所有页面固定同一高度，先看页面信息量，再选最小可完整承载正文的高度，优先减少底部空白

截图流程踩坑记录：

- `chrome --headless --screenshot` 或 DevTools 连续截图都可能截到当前浏览器已有页面，导致图片看起来像页面被裁切、内容不对或混入其他网页。
- 如果截图异常，不能直接提交；先用 `git show HEAD:images/xxx.png > images/xxx.png` 恢复旧图，再重试正确方案。
- 只要抽查发现截图不是 BikePower 页面，必须恢复旧图并停止提交截图，不允许把错误截图写进仓库。
- 生成后的 `web/page*.html` 被删除是正常清理动作；如果 `git status` 没有 `D web/page*.html`，说明没有误删跟踪文件。

动态截图规则（2026-05-22 实测有效）：

1. **先生成 HTML 再截图** — 先执行 `python3 scripts/capture_screenshots.py`，以 `web/page*.html` 为唯一截图输入，禁止直接从浏览器当前标签页肉眼截图
2. **统一宽度，动态高度** — 手册网页图默认宽度用 `570px`，高度按页面内容动态选，不再把所有页面固定成同一张长图
3. **首页用短口径** — `page1_home.png` 这类首页/引导页优先用 `570x844`，保证视觉紧凑，减少底部空白
4. **表单状态页用中口径** — `page3_config.png`、`page4_update_available.png` 这类包含表单和状态卡片的页面优先用 `570x1180`
5. **进度页按信息量单独定高** — 进度提示页、成功页、扫描页根据正文高度单独试拍，原则是“正文完整 + 底部空白最少”
6. **先裁截图，不先改页面** — 若问题只是底部留白过多，优先调整截图高度，不要先改 `web_pages.py` 真实布局
7. **版式问题先对照基准图** — 若用户感觉页面“不对”，先拿 `page4_update_available.png` 或已确认正确的参考图对比，再判断是布局问题还是截图口径问题
8. **保留参考图只作对照** — 临时参考图如 `images/_tmp_page1_wide.png` 仅用于比对，确认正式图后应删除，避免混入仓库
9. **正式截图命令固定参数** — 使用独立 Chrome 实例 + `--headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --window-size=<宽>,<高> --screenshot=<输出> file://<html>`

---

## 三、串口智能扫描规则

通过 USB VID/PID 识别 ESP32-C3 设备：

| VID | 芯片 | 说明 |
|-----|------|------|
| 0x303A | Espressif USB | ESP32-C3/S2/S3 内置 USB CDC |
| 0x10C4 | CP210x | Silicon Labs USB-UART |
| 0x1A86 | CH340/CH341 | 廉价 USB-UART |
| 0x0403 | FTDI FT232 | 经典 USB-UART |

优先使用 pyserial `list_ports`（精确），回退到系统 `ls /dev/`（粗略）。

---

## 四、用户偏好

1. **语言** — 中文沟通，代码注释不添加（除非要求）
2. **操作风格** — 先确认再执行，不要未通知就操作
3. **测试优先** — 每次部署后必须验证，禁止只部署不测试
4. **记录习惯** — 所有要求和约定记录在此文档，执行前先回顾
5. **单位换算** — 报告中文件大小用 KB/MB 表示，不显示原始字节数
6. **代码变动必须检查文档** — 每次代码变动后，必须检查以下内容是否需要同步更新：
   - **docstring**：模块级/类/方法的 docstring 是否与代码行为一致（docstring ≠ 注释，属于接口文档）
   - **specs/**：GIVEN/WHEN/THEN 行为规格是否与代码逻辑一致
   - **templates/**：代码模板是否与实际代码模式一致
   - **README.md**：参数值、操作说明、文件结构是否与代码一致
   - **CHANGELOG.md**：每次代码变更必须记录
   - **project_rules.md**：文件结构树、强制规则是否需要更新
   - **hardware_constraints.md**：硬件参数是否与 config.py 一致

---

## 五、凭证信息

- **Gitee Token**: 已迁移到 `.env` 文件（`GITEE_TOKEN`），不再明文存储
- **Gitee 仓库**: `mengen4jv/esp32-power`
- **飞书 App ID**: 已迁移到 `.env` 文件（`FEISHU_APP_ID`），不再明文存储
- **飞书 App Secret**: 已迁移到 `.env` 文件（`FEISHU_APP_SECRET`），不再明文存储
- **使用方式**: 脚本通过 `os.getenv()` 或解析 `.env` 文件读取凭证

---

## 六、已验证的架构决策（直接给结论，不再重复分析）

| 决策 | 结论 | 原因 | 日期 |
|------|------|------|------|
| 删除 main.py | ✅ 已删除并部署验证通过 | boot.py 已在非部署模式调用 app.main()（无限循环），main.py 永远不会执行；部署模式下 main.py 无条件调用 app.main() 反而是 bug（会干扰 mpremote 连接）。deploy.sh/ps1 同步移除 main.py | 2026-05-20 |
| utils.py 未部署 | ✅ 已修复 | app.py 引用 `from utils import start_thread`，但 utils.py 不在 deploy.sh/ps1 的 MODULE_FILES 列表中，导致 ImportError。已添加到两个部署脚本 | 2026-05-20 |
| _handle_button 缺少 led 参数 | ✅ 已修复 | _handle_button 函数体内使用 `led.value()` 但参数列表中没有 `led`，导致 NameError 崩溃。已添加 `led` 参数并更新调用处 | 2026-05-20 |
| specs/power-engine.md 同步 | ✅ 已修复 | spec 写"自动调用 _save_config()"，实际代码用 _dirty 标记 + 主循环异步保存。已更新 spec 匹配实际代码 | 2026-05-20 |
| templates 与代码同步 | ✅ 已修复 | ble-service.md 添加 _failed_conns；wifi-handler.md _ble_disabled→ble_disabled；config-persist.md 添加 _dirty + flush_if_dirty | 2026-05-20 |
| mock_server.py import 路径 | ✅ 已修复 | 从 `from app import *` 改为从各模块分别 import | 2026-05-20 |
| PowerEngine.flush_if_dirty() | ✅ 已添加 | 公开方法替代 app.py 直接访问 _dirty + _save_config()，封装更完整 | 2026-05-20 |
| reactivate() 从 spec 删除 | ✅ 已删除 | ESP32-C3 上 WiFi 关闭后 BLE 无法可靠重新激活，当前用 machine.reset() 恢复 | 2026-05-20 |
| wifi_manager.py HTML 抽取 | ✅ 已完成 | HTML 抽取到 web_pages.py（17KB），wifi_manager.py 从 35KB 缩减到 20KB。延迟 import 不影响 BLE 内存 | 2026-05-20 |
| esp32c3-led.md 合并 | ✅ 已完成 | QSPI 限制说明移入 hardware_constraints.md，删除 esp32c3-led.md | 2026-05-20 |
| test emit() 去重 | ✅ 已完成 | 抽取到 test/test_utils.py，test_ble.py 和 test_wifi.py 共享 | 2026-05-20 |
| v1.9.0 版本号违规 | ✅ 规则已修正 | 原规则"分支内只能 PATCH 递增"与 SemVer 冲突，已修正为：功能分支开发完成后合并到 main 打 MINOR tag | 2026-05-20 |
| OTA 发布目录散落根目录 | ✅ 已修正 | v1.9.1/v1.9.2/v1.9.3 根目录产物移动到 releases/ota/，gen_version_json.py 和 create_gitee_release.py 同步新路径 | 2026-05-22 |
| target 固件备份过多 | ✅ 已修正 | build_firmware.sh 编译后自动删除旧的 firmware-*.bin，只保留最新 3 个时间戳固件；firmware.bin 作为最新入口保留 | 2026-05-22 |
| Agent 长流程治理缺少文档 | ✅ 已修正 | 新增 docs/agent-governance.md，明确 MEMORY/rules/specs/docs/CHANGELOG 分层、测试报告和规则冲突治理流程 | 2026-05-22 |
| POST 表单参数偶发为空 | ✅ 已修正 | Web 服务器不能只 recv 一次；必须按 Content-Length 收齐 POST body 后再解析表单，Mock 与真机链路测试通过 | 2026-05-22 |
| 多主题改动混成单 commit | ✅ 已复盘 | 5c8251d 将 Web/OTA/测试/产物/治理文档合并提交，违反分批提交规则；已新增 AGENTS.md 和分批防呆规则，后续多主题任务必须先列批次并按路径 add | 2026-05-22 |

## 七、历史对话关键要求索引

| 来源 | 要求 |
|------|------|
| 首次对话 | 代码风格规则、硬件约束规则、项目架构规则 |
| 第二次对话 | 跨平台支持（macOS/Windows），自动扫描串口，串口地址不写死 |
| 第三次对话 | 固件名称改为 firmware.bin，commit 最大10字符，详情记录 README，创建记忆文档 |
| 第四次对话 | 测试报告需浏览器打开，文件大小用 KB/MB 换算 |
| 第五次对话 | 项目结构审查：去重复、去硬编码、统一规范 |
| 第六次对话 | 分批提交代码，按功能拆分 commit |
| 第七次对话 | AI Coding 工程实践：开发前检查清单、禁止事项、任务模板、链路检查、diff 自检 |
| 第八次对话 | 开源项目调研汇总到 docs/open-source-references.md |
| 第九次对话 | 项目文件重复/冲突/可合并/可重构分析，删除 main.py，架构决策记录到 MEMORY |
| 第十次对话 | target 固件保留 3 个、OTA 产物归档到 releases/ota、长流程写入 Agent 治理文档、提交前必须测试打报告 |
| 第十一次对话 | 复盘混提问题，新增 AGENTS.md，强化整体优化分批计划、验证报告、禁止多主题 git add -A |

---

## 八、项目优化检查清单

> 当用户说"优化"或"改进"时，按以下清单逐项扫描，输出问题列表后按优先级修复。

### 第一层：技术缺陷（代码健壮性）

| 检查项 | 检查方法 | 常见问题 |
|--------|---------|---------|
| 内存安全 | 搜索 `f.read()` / `recv()` + 拼接 | 整文件读入、循环中 bytes 拼接导致 OOM |
| 异常路径完整性 | 检查每个 try/except 后状态是否重置 | 异常后标志位卡死、socket 未关闭 |
| 线程安全 | 检查线程间共享变量的读写 | 主线程读 + 工作线程写无原子性保证 |
| 超时逻辑 | 检查计时器基准时间是否正确 | OTA 专用超时与普通超时混用导致提前超时 |
| 版本号解析 | 检查 `int(x)` 是否可能抛 ValueError | 预发布版本号（如 `1.9.0-beta.1`）导致崩溃 |
| SSL/TLS | 检查 HTTPS 连接是否包装 ssl | 裸 socket 连 443 端口无法完成 TLS 握手 |

### 第二层：业务逻辑（功能完整性）

| 检查项 | 检查方法 | 常见问题 |
|--------|---------|---------|
| 链路闭环 | 走完每个链路检查清单 | 保存了凭据但不使用、检查了更新但不展示 |
| 版本一致性 | 检查所有显示版本号的位置 | config.py 硬编码 vs ota_version.json 不同步 |
| 状态展示 | 检查异步操作结果是否可达前端 | 后台检查完成但页面不刷新 |
| 边界条件 | 检查空值/None/零值处理 | 空文件列表、零大小文件、None 返回值 |

### 第三层：规则与文档（Entropy 治理）

| 检查项 | 检查方法 | 常见问题 |
|--------|---------|---------|
| 规则冲突 | 对比 MEMORY.md 与 project_rules.md 同一主题 | 版本号格式、commit 格式、变更记录位置矛盾 |
| 模板过时 | 对比 templates/ 与实际代码 | AUTH_OPEN vs WPA2、参数签名不匹配 |
| specs 过时 | 对比 specs/ GIVEN/WHEN/THEN 与代码 | 缺少新增路由、参数变更未同步 |
| 文件结构 | 对比 project_rules.md 文件树与实际目录 | 新增文件未记录、已删除文件仍列出 |
| docstring | 对比函数签名与 docstring Args/Returns | 参数增删后 docstring 未更新 |

### 第四层：功能增强（可选）

| 检查项 | 说明 |
|--------|------|
| 用户体验 | LED 状态是否覆盖所有场景、页面是否自动刷新 |
| 新功能 | 是否有用户反复提到的需求尚未实现 |
| 性能 | 是否有可优化的热点（GC 频率、内存碎片） |

### 执行流程

```
1. 运行 Entropy 扫描 → 修复第三层问题
2. 逐模块代码审查 → 修复第一层 + 第二层问题
3. 编译验证 + 提交推送
4. 输出改进报告（问题列表 + 修复状态）
```

---

## 九、技术踩坑记忆（Harness 第二层防御）

> 对应 Anthropic 官方 Auto Memory 层：跨会话积累踩坑经验，避免重复踩坑。
> Anthropic 原则："每当 Claude 犯错，就把规则加入 CLAUDE.md"——Boris Cherny（Claude Code 创建者）的黄金法则。
> 经验沉淀闭环：犯错 → 记录 → CRITICAL 级别升级为规则 → Hooks 自动检查 → 不再犯错。
> 严重度标记：CRITICAL（必须遵守，已升级或待升级为规则）/ WARNING（强烈建议）/ INFO（参考经验）
> 每次版本发布前 review 一次，CRITICAL 级别的踩坑应升级为 .trae/rules/ 中的规则。

### BLE 相关

- [CRITICAL] BLE EIO 错误（`[Errno 5] EIO`）只能 `machine.reset()` 恢复，`ble.active(False)` 无法恢复硬件状态残留 [→H14]
- [WARNING] `mpremote exec` 执行时会中断主程序，按钮事件可能丢失，不依赖其做交互测试
- [INFO] NimBLE 栈比 Bluedroid 省 ~50KB RAM，本项目默认使用 NimBLE
- [INFO] BLE 通知回调 `_irq` 中禁止创建新对象（`bytearray()`/`bytes()`），必须用预分配缓冲区 → 已升级为 H12 规则

### WiFi 相关

- [CRITICAL] ESP32-C3 WiFi 与 BLE 共用射频，无法同时运行，共存会触发 `RuntimeError: Wifi Unknown Error 0x0102` [→H15]
- [CRITICAL] 禁止开机自动启动 WiFi，否则无限重启循环（WiFi 超时 → reset → 再启动 → 循环）[→H24]
- [WARNING] WiFi AP 启动消耗 30-40KB 堆内存，BLE 启动后剩余约 120KB，需注意内存余量
- [WARNING] 已连接相同 WiFi 时直接返回 `already_connected`，避免断开重连导致前端请求失败
- [INFO] Web 服务器 POST 表单参数偶发为空，必须按 Content-Length 收齐 POST body 后再解析

### OTA 相关

- [CRITICAL] `wifi_config.txt` 必须在 OTA `_PROTECTED_FILE_NAMES` 中，防止 OTA 意外覆盖 WiFi 凭据 [→H18]
- [CRITICAL] OTA 下载期间必须暂停 WiFi 关闭计时器（`_ota_downloading` 标志），避免下载中断 [→H19]
- [WARNING] 文件替换前必须备份 `.bak`，`boot.py` 校验失败时自动回滚 → 已升级为 H20 规则
- [INFO] 文件级差量更新：仅下载 CRC32 哈希不同的 `.mpy` 字节码文件，节省流量和时间

### 内存相关

- [WARNING] BLE 启动后堆内存约 120KB，低于 80KB 需告警
- [INFO] 字符串格式化用 `%` 比 `+` 拼接更省内存
- [INFO] 预分配 `bytearray` 缓冲区，避免在循环/回调中创建
- [INFO] `gc.collect()` 在关键节点回收内存，`gc.threshold()` 设置自动回收阈值

### 代码规范相关

- [WARNING] `logger.py` 中的 `print()` 是日志系统初始化前的必要输出，属于已知例外
- [INFO] 模块常量必须用 `const()` 包装（`FIRMWARE_VERSION` 例外，因为值为字符串）
- [INFO] 日志器命名必须全大写简称：`get_logger("MODULE")`

### Harness 治理相关

- [INFO] CLAUDE.md（对应 iteration_state.md）不是剪贴簿，是路由层——只放"去掉就会犯错"的规则，60~120 行最优
- [INFO] Hooks 与 CLAUDE.md 的关键区别：CLAUDE.md 是"建议"（advisory），Hooks 是"确定性执行"（deterministic）
- [INFO] Stop Hook 是 Hooks 的最高阶用法：会话结束时回顾经验，自动更新规则文件
- [INFO] Skills 采用 Progressive Disclosure（渐进式披露），分三层加载：Metadata → Body → References
- [INFO] 上下文达到 50% 时手动执行 `/compact`，不要等到自动触发；结构化 prompt 比叙述式 prompt 少消耗 30% token
- [INFO] OODA 循环中 Harness 负责四分之三（Observe/Orient/Act），LLM 只负责 Decide
- [INFO] Claude Code 源码泄露关键发现：Skill 列表最多占窗口 1%、三级压缩+熔断器（连续失败 3 次就停）、ToolSearch 延迟加载、Hook 系统 27 个事件节点
- [INFO] Claude Code 是运行时中心的 Harness，不是纯文档驱动也不是纯 CI 驱动
- [INFO] Harness 五重含义：马具（驯驭）、航天线束（精确）、测试线束（受控环境）、安全带（防坠落）、电气线束（连接一切）
- [INFO] 五大常见陷阱：工具给太多、没用 Prompt Cache、错误信息 LLM 看不懂、省略人工确认、记忆从不整理
- [INFO] 质量保障核心原则：质量不靠 AI 自觉，靠外部神谕（entropy_scan.py 就是外部神谕）
