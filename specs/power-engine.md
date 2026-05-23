# 功率引擎规格

> Source of Truth：`power_data.py` 的行为规格
> AI 修改功率数据模块时，先加载此文件确认当前行为

---

## 公共接口

### PowerEngine 类

| 属性/方法 | 类型 | 说明 |
|-----------|------|------|
| `get_snapshot(now_ms)` | method | 按当前骑行模式生成 BLE 广播快照 |
| `set_mode(mode)` | method | 设置骑行模式，范围校验，标记 _dirty |
| `get_mode()` | method | 返回当前骑行模式 ID |
| `reset_mode_state()` | method | 重置骑行模式内部状态 |
| `power` | property (int) | 兼容旧接口，生成功率值 = base_power + random(-10, 20) |
| `cadence` | property (int) | 兼容旧接口，生成踏频值 = clamp(cadence_base + random(-3, 3), 20, 120) |
| `heartrate` | property (int) | 兼容旧接口，返回 last_heartrate + random(-2, 2) |
| `base_power` | attribute (int) | 基准功率（W），范围 [0, 2000] |
| `cadence_base` | attribute (int) | 基准踏频（RPM），范围 [20, 120] |
| `last_heartrate` | attribute (int) | 上次心率值，用于指数平滑 |
| `user_heartrate` | attribute (int/None) | 用户手动设定的心率，None 时按功率估算 |
| `mode` | attribute (str) | 当前骑行模式，默认 `steady` |
| `set_power(val)` | method | 设置基准功率，范围校验 [0, 2000]，标记 _dirty |
| `set_cadence(val)` | method | 设置基准踏频，范围校验 [20, 120]，标记 _dirty |
| `set_heartrate(val)` | method | 设置用户心率，范围校验 [60, 200]，标记 _dirty |
| `set_erg_target(val)` | method | 设置 ERG 模式目标功率（FTMS 下发），范围校验 [0, 2000]，标记 _dirty |
| `adjust_power(delta)` | method | 增量调整功率 = clamp(base_power + delta, 0, 2000) |
| `adjust_cadence(delta)` | method | 增量调整踏频 = clamp(cadence_base + delta, 20, 120) |
| `update_heartrate()` | method | 兼容旧接口，按当前功率估算并平滑更新心率 |
| `flush_if_dirty()` | method | 检查 _dirty 标志，若脏则保存配置到 JSON，保存失败保留脏标记 |

## 初始化

- GIVEN 设备上电启动
- WHEN `PowerEngine()` 被调用
- THEN 设置默认值：base_power=200W, cadence_base=90RPM, last_heartrate=140BPM
- THEN user_heartrate=None（未手动设定）
- THEN mode=steady（固定功率模式）
- THEN 调用 `_load_config()` 从 JSON 文件恢复配置
- THEN 调用 `reset_mode_state()` 初始化模式状态

## 配置加载

- GIVEN `power_config.json` 文件存在
- WHEN `_load_config()` 被调用
- THEN 读取 JSON 文件，key: `p`=功率, `c`=踏频, `h`=心率, `m`=骑行模式
- THEN 缺失 key 使用默认值：`cfg.get('p', config.DEFAULT_POWER)`
- THEN 心率值需通过范围校验 [60, 200]
- THEN 模式值需在 `config.RIDE_MODES` 内，否则回退 `steady`

- GIVEN `power_config.json` 不存在
- WHEN `_load_config()` 被调用
- THEN 使用默认值（旧版 `config_*` 文件名格式迁移已移除）

## 配置保存

- GIVEN 配置值发生变化（adjust_power/set_power/set_cadence/set_heartrate）
- WHEN setter 方法被调用
- THEN 设置 `_dirty = True` 标记（不立即保存，避免阻塞主循环）
- THEN 主循环检测到 `_dirty` 后，通过 `_async_save_config()` 后台线程调用 `_save_config()`
- THEN `_build_config()` 构造 JSON 对象：`{'p': base_power, 'c': cadence_base, 'h': heartrate, 'm': mode}`
- THEN 覆盖写入 `power_config.json`
- THEN 心率取值优先级：user_heartrate > last_heartrate
- THEN 仅在保存成功且当前配置仍与保存快照一致时清除 `_dirty`
- THEN 保存失败时保留 `_dirty=True`，等待下次重试

## 功率调整

- GIVEN 当前基准功率为 P
- WHEN `adjust_power(delta)` 被调用
- THEN 新功率 = clamp(P + delta, 0, 2000)
- THEN 若值变化，设置 `_dirty = True`（由主循环异步保存）
- THEN 返回调整后的功率值

## 踏频调整

- GIVEN 当前基准踏频为 C
- WHEN `adjust_cadence(delta)` 被调用
- THEN 新踏频 = clamp(C + delta, 20, 120)
- THEN 若值变化，设置 `_dirty = True`（由主循环异步保存）
- THEN 返回调整后的踏频值

## 功率生成

- GIVEN 主循环需要 BLE 广播数据
- WHEN 调用 `get_snapshot(now_ms)`
- THEN 根据当前 `mode` 生成一次性快照：`power/cadence/heartrate/mode`
- THEN 主循环只消费该快照，不再分散读取 `power`、`cadence`、`heartrate`

## 骑行模式

| 模式 | 行为 |
|------|------|
| `steady` | 固定功率模式，使用用户表单值，功率/踏频/心率小幅稳定波动 |
| `road` | 真实路骑模式，使用内置状态机模拟滑行、巡航、爬坡、冲刺和恢复 |
| `interval` | 间歇训练模式，使用内置高强度和恢复周期切换 |
| `random` | 随机巡航模式，使用内置 110-300W 中等幅度随机游走 |

## 快照生成

- GIVEN mode=`steady`
- WHEN `get_snapshot(now_ms)` 被调用
- THEN 功率围绕 `base_power` 使用 `STEADY_POWER_FLUCTUATION` 小幅波动
- THEN 踏频围绕 `cadence_base` 使用 `STEADY_CADENCE_FLUCTUATION` 小幅波动
- THEN 心率围绕目标心率缓慢波动

- GIVEN mode=`road`
- WHEN `get_snapshot(now_ms)` 被调用
- THEN 内部状态机在 `coast/cruise/climb/surge/recover` 间切换
- THEN `coast` 输出 0-15W / 20-28RPM
- THEN `cruise` 输出 130-220W / 66-90RPM
- THEN `climb` 输出 235-335W / 75-93RPM
- THEN `surge` 输出 385-480W / 78-100RPM
- THEN `recover` 输出 55-110W / 50-88RPM
- THEN 心率延迟跟随功率变化
- THEN 忽略用户表单里的功率、踏频、心率数值

- GIVEN mode=`interval`
- WHEN `get_snapshot(now_ms)` 被调用
- THEN 高强度段输出 285-355W / 84-96RPM
- THEN 恢复段输出 85-145W / 62-84RPM
- THEN 忽略用户表单里的功率、踏频、心率数值

- GIVEN mode=`random`
- WHEN `get_snapshot(now_ms)` 被调用
- THEN 功率在 110-300W 内基于上次输出随机游走
- THEN 踏频在 65-94RPM 内基于上次输出随机游走
- THEN 心率按功率趋势平滑变化
- THEN 忽略用户表单里的功率、踏频、心率数值

## 参数修改限制

- GIVEN mode=`steady`
- WHEN `set_power()`、`set_cadence()`、`set_heartrate()` 或 `adjust_power()` 被调用
- THEN 按正常范围校验后修改配置

- GIVEN mode 不为 `steady`
- WHEN `set_power()`、`set_cadence()`、`set_heartrate()` 或 `adjust_power()` 被调用
- THEN 不修改配置，保留内置模式曲线

## 心率生成

- GIVEN user_heartrate 已设定且 mode=`steady`
- WHEN 计算目标心率
- THEN 以用户设定值为基准

- GIVEN user_heartrate 已设定且 mode 不为 `steady`
- WHEN 计算目标心率
- THEN 根据当前功率相对 `base_power` 的偏移做轻量修正

- GIVEN user_heartrate 未设定
- WHEN 计算目标心率
- THEN base_hr = int(0.45 * power + 45)

- GIVEN 目标心率已确定
- WHEN 生成快照
- THEN 使用模式对应的平滑系数更新 `last_heartrate`

## 踏频生成

- GIVEN 基准踏频为 C
- WHEN 读取 `cadence` 属性
- THEN 返回 clamp(C + random(-3, 3), 20, 120)

## 配置参数范围

| 参数 | 最小值 | 最大值 | 默认值 | JSON Key |
|------|--------|--------|--------|----------|
| 功率 | 0 | 2000 | 200 | p |
| 踏频 | 20 | 120 | 90 | c |
| 心率 | 60 | 200 | 140 | h |
| 骑行模式 | - | - | steady | m |
