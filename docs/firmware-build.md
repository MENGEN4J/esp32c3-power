# ESP32-C3 MicroPython 固件编译打包指南

> 将 BikePower 项目 Python 代码冻结（freeze）到 MicroPython 固件中，生成可直接烧录的 `firmware.bin`。

---

## 1. 一键编译与烧录

```bash
# 编译固件
bash scripts/build_firmware.sh
bash scripts/build_firmware.sh -c        # 清理后重新编译

# 烧录固件（首次需擦除）
bash scripts/flash_firmware.sh -e
bash scripts/flash_firmware.sh -p /dev/cu.usbmodem1101  # 指定串口
```

编译成功后，固件文件位于 `target/firmware.bin`。

---

## 2. 冻结（Freeze）说明

MicroPython 支持将 Python 代码预编译为字节码并嵌入固件镜像中：

- **启动更快** — 代码已预编译，无需运行时编译
- **节省 RAM** — 字节码直接从 Flash 执行，不占用 RAM
- **代码保护** — 源代码不可直接访问

### Manifest 文件

`scripts/manifest.py` 定义了要冻结的 Python 模块：

```python
include("$(PORT_DIR)/boards/manifest.py")

freeze("$(MPY_DIR)/..", "boot.py")
freeze("$(MPY_DIR)/..", "config.py")
freeze("$(MPY_DIR)/..", "logger.py")
freeze("$(MPY_DIR)/..", "utils.py")
freeze("$(MPY_DIR)/..", "ble_service.py")
freeze("$(MPY_DIR)/..", "power_data.py")
freeze("$(MPY_DIR)/..", "wifi_manager.py")
freeze("$(MPY_DIR)/..", "web_pages.py")
freeze("$(MPY_DIR)/..", "ota_updater.py")
freeze("$(MPY_DIR)/..", "app.py")
```

> ⚠️ `$(MPY_DIR)/..` 已经是项目根目录，不要再加 `esp32c3-power`。

---

## 3. 环境准备（手动步骤）

### 3.1 系统依赖

```bash
# macOS
brew install cmake ninja python3

# Ubuntu/Debian
sudo apt-get install build-essential cmake git python3 python3-pip ninja-build
```

### 3.2 克隆 MicroPython

```bash
git clone -b v1.28.0 --depth 1 https://github.com/micropython/micropython.git
cd micropython && git submodule update --init --recursive --depth 1
```

### 3.3 安装 ESP-IDF

```bash
git clone -b v5.5.1 --depth 1 https://github.com/espressif/esp-idf.git
cd esp-idf && git submodule update --init --recursive --depth 1
./install.sh esp32c3
```

> ⚠️ ESP-IDF 子模块较多，网络不稳定时可能部分克隆失败，重新执行 `git submodule update --init --recursive --depth 1` 即可。

### 3.4 编译 mpy-cross

```bash
cd micropython && make -C mpy-cross
```

---

## 4. 手动编译步骤

```bash
source /path/to/esp-idf/export.sh
cd micropython && make -C mpy-cross
cd ports/esp32
make BOARD=ESP32_GENERIC_C3 submodules
make BOARD=ESP32_GENERIC_C3 FROZEN_MANIFEST=/path/to/esp32c3-power/scripts/manifest.py -j$(nproc)
```

> ⚠️ `make submodules` 必须指定 `BOARD=ESP32_GENERIC_C3`，否则默认使用 ESP32（Xtensa）会编译失败。

---

## 5. 烧录方式

### 合并固件烧录（推荐）

使用 `firmware.bin`（包含 bootloader + partition-table + app），写入地址 `0x0`：

```bash
# 示例串口，实际请使用 bash scripts/common.sh scan 自动扫描
esptool.py --chip esp32c3 --port /dev/cu.usbmodem1101 erase_flash
esptool.py --chip esp32c3 --port /dev/cu.usbmodem1101 --baud 460800 write_flash 0x0 target/firmware.bin
```

> ⚠️ 必须使用 `firmware.bin`（合并固件），不能使用 `micropython.bin`（仅应用部分）分段烧录，否则设备无法启动。

### 烧录后上传项目文件

固件烧录后设备不会自动运行，需上传项目文件：

```bash
# 示例串口，实际请使用 bash scripts/common.sh scan 自动扫描
# 推荐使用一键部署脚本
bash scripts/deploy.sh
```

---

## 6. 冻结模块 vs 文件系统部署

| 对比项 | 冻结模块（固件） | 文件系统部署 |
|--------|-----------------|-------------|
| RAM 占用 | 更少（字节码从 Flash 执行） | 更多（需加载到 RAM） |
| 启动速度 | 更快（预编译） | 较慢（运行时编译） |
| 更新方式 | 重新编译+烧录固件 | mpremote cp 上传文件 |
| 开发效率 | 低（每次修改需重编译） | 高（秒级更新） |
| 适用场景 | 生产发布 | 开发调试 |

**建议**：开发阶段使用 `deploy.sh`，发布阶段使用 `build_firmware.sh` + `flash_firmware.sh`。

---

## 7. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `idf.py: command not found` | ESP-IDF 环境未加载 | `source esp-idf/export.sh` |
| `xtensa-esp32-elf-gcc: not found` | 未指定 BOARD | `make BOARD=ESP32_GENERIC_C3 submodules` |
| `Missing esp-mqtt submodule` | 子模块克隆不完整 | `git submodule update --init --recursive --depth 1` |
| 固件太大无法烧录 | 冻结模块过多 | 减少 manifest.py 中的模块或使用 `opt=3` |
| 设备启动报 `overlaps bootloader` | 使用了 micropython.bin | 改用 firmware.bin（合并固件）写入 0x0 |

---

## 8. 编译产物

| 文件 | 路径 | 大小 | 说明 |
|------|------|------|------|
| `firmware.bin` | `target/` | ~1.7MB | 合并固件（烧录到 0x0） |
| `firmware-{timestamp}.bin` | `target/` | ~1.7MB | 带时间戳的备份，自动保留最新 3 个 |
| `bootloader.bin` | MicroPython 构建目录 | ~17KB | 引导加载程序（已包含在合并固件中） |
| `partition-table.bin` | MicroPython 构建目录 | ~3KB | 分区表（已包含在合并固件中） |
| `*.mpy` | `releases/ota/vX.Y.Z/` | ~51KB | OTA 字节码包，每个版本独立目录 |
| `version.json` | `releases/latest/` | <10KB | OTA 当前版本清单，设备固定读取稳定入口 |
