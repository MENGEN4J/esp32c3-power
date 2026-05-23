# 第一批修复 Tasks

## 批次目标

- 修复 OTA 模块导入问题
- 修复 OTA 版本清单地址策略
- 修复 WiFi 启动前 BLE 停用结果校验

## 修改清单

- [ ] `ota_updater.py`
  - [ ] 增加 `from micropython import const`
  - [ ] 确认 `_MAX_RESPONSE_SIZE` 类常量定义在 MicroPython 下可正常生效
- [ ] `config.py`
  - [ ] 将 `OTA_VERSION_URL` 改为稳定 `latest` 入口
  - [ ] 确认版本号常量与发版链路说明不冲突
- [ ] `wifi_manager.py`
  - [ ] `start()` 统一复用 `_disable_ble()`
  - [ ] BLE 停用失败时立即中止 WiFi 启动
  - [ ] 避免 `ble_disabled` 与真实 BLE 状态不一致
  - [ ] 补充失败日志，便于定位互斥问题

## 文档同步清单

- [ ] `README.md`
  - [ ] 同步 OTA 版本清单地址策略说明
  - [ ] 同步 WiFi 启动前必须确认 BLE 已停用的行为说明
- [ ] `specs/ota-updater.md`
  - [ ] 同步 OTA 版本清单入口行为
- [ ] `specs/wifi-manager.md`
  - [ ] 同步 `start()` 的 BLE 停用前置条件和失败路径
- [ ] `CHANGELOG.md`
  - [ ] 新增本批修复条目
  - [ ] 记录测试报告

## 验证清单

### 代码级检查

- [ ] `py_compile` 相关 `.py` 文件通过
- [ ] `GetDiagnostics` 无新增问题
- [ ] 搜索确认 `ota_updater.py` 已导入 `const`
- [ ] 搜索确认 `WiFiManager.start()` 不再无条件设置 `ble_disabled = True`

### 设备链路验证

- [ ] BLE 正常启动
- [ ] 长按进入确认窗口后，再按一次可以进入配网模式
- [ ] 进入配网模式前 BLE 已停用
- [ ] WiFi AP 正常启动
- [ ] OTA 检查请求可访问稳定版本清单

## 提交拆分建议

### Commit 1

- 范围：`ota_updater.py` + `config.py`
- 类型：`fix(ota): 修复OTA导入和版本清单入口`

### Commit 2

- 范围：`wifi_manager.py` + 相关 `specs/README/CHANGELOG`
- 类型：`fix(wifi): 校验BLE停用后再启动配网`

## 完成标准

- OTA 主链路不再因模块导入或版本地址策略失效
- WiFi/BLE 互斥路径不再依赖错误状态标记
- 本批所有改动都能独立编译、验证、提交、push
