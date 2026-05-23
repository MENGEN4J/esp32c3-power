#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/common.sh"

TARGET_DIR="${PROJECT_DIR}/target"
MICROPYTHON_DIR="${PROJECT_DIR}/micropython"
ESP_IDF_DIR="${PROJECT_DIR}/esp-idf"
BOARD="ESP32_GENERIC_C3"
ESP_IDF_VERSION="v5.5.1"
MICROPYTHON_VERSION="v1.28.0"
CLEAN_BUILD=false
KEEP_FIRMWARE_COUNT=3

while getopts "ch" opt; do
    case $opt in
        c) CLEAN_BUILD=true ;;
        h)
            echo "用法: ./build_firmware.sh [-c] [-h]"
            echo "  -c  清理构建缓存后重新编译"
            echo "  -h  显示帮助信息"
            exit 0
            ;;
        *)
            echo "未知选项: -$opt"
            exit 1
            ;;
    esac
done

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   BikePower MicroPython 固件编译打包     ║"
echo "╚══════════════════════════════════════════╝"
echo ""

log_info "当前系统: ${_OS_DISPLAY}"

log_step "步骤 1/7: 检查 MicroPython 源码"

if [[ ! -d "$MICROPYTHON_DIR" ]]; then
    log_info "克隆 MicroPython 仓库 (${MICROPYTHON_VERSION})..."
    git clone -b "${MICROPYTHON_VERSION}" --depth 1 https://github.com/micropython/micropython.git "$MICROPYTHON_DIR"
    cd "$MICROPYTHON_DIR"
    git submodule update --init --recursive --depth 1
    log_info "MicroPython 克隆完成"
else
    log_info "MicroPython 仓库已存在: $MICROPYTHON_DIR"
    CURRENT_TAG=$(cd "$MICROPYTHON_DIR" && git describe --tags 2>/dev/null || echo "unknown")
    log_info "当前版本: $CURRENT_TAG"
fi

log_step "步骤 2/7: 检查 ESP-IDF"

if [[ ! -d "$ESP_IDF_DIR" ]]; then
    log_info "克隆 ESP-IDF (${ESP_IDF_VERSION})..."
    git clone -b "${ESP_IDF_VERSION}" --depth 1 https://github.com/espressif/esp-idf.git "$ESP_IDF_DIR"
    cd "$ESP_IDF_DIR"
    log_info "初始化 ESP-IDF 子模块（浅克隆）..."
    git submodule update --init --recursive --depth 1
    log_info "安装 ESP-IDF 工具链（首次安装较慢，请耐心等待）..."
    if is_macos; then
        ./install.sh esp32c3
    elif is_linux || is_wsl; then
        ./install.sh esp32c3
    else
        log_error "ESP-IDF 编译仅支持 macOS 和 Linux"
        log_error "Windows 用户请使用 WSL 或 Git Bash"
        exit 1
    fi
    log_info "ESP-IDF 安装完成"
else
    log_info "ESP-IDF 已存在: $ESP_IDF_DIR"
    EMPTY_SUBMODULES=$(cd "$ESP_IDF_DIR" && git submodule foreach --recursive 'if [ -z "$(ls -A . 2>/dev/null | grep -v .git)" ]; then echo "EMPTY: $path"; fi' 2>&1 | grep -c "^EMPTY:" || true)
    if [[ "$EMPTY_SUBMODULES" -gt 0 ]]; then
        log_warn "发现 ${EMPTY_SUBMODULES} 个空子模块，正在修复..."
        cd "$ESP_IDF_DIR"
        git submodule update --init --recursive --depth 1
        log_info "子模块修复完成"
    fi
    IDF_VENV=""
    if is_macos; then
        IDF_VENV="$HOME/.espressif/python_env/idf5.5_py3.9_env/bin/python"
    elif is_linux || is_wsl; then
        IDF_VENV="$HOME/.espressif/python_env/idf5.5_py3.$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')_env/bin/python"
    fi
    if [[ -n "$IDF_VENV" ]] && [[ ! -f "$IDF_VENV" ]]; then
        log_info "ESP-IDF Python 环境未安装，正在安装..."
        cd "$ESP_IDF_DIR"
        ./install.sh esp32c3
    fi
fi

log_step "步骤 3/7: 设置编译环境"

if is_macos; then
    source "$ESP_IDF_DIR/export.sh" 2>/dev/null
elif is_linux || is_wsl; then
    source "$ESP_IDF_DIR/export.sh" 2>/dev/null
else
    log_error "不支持当前系统编译 ESP-IDF 固件"
    exit 1
fi
log_info "ESP-IDF 环境已加载"

log_step "步骤 4/7: 编译 mpy-cross 交叉编译器"

cd "$MICROPYTHON_DIR"
NPROC=$(cpu_count)
if [[ "$CLEAN_BUILD" == true ]] || [[ ! -f "mpy-cross/build/mpy-cross" ]]; then
    make -C mpy-cross clean 2>/dev/null || true
fi
make -C mpy-cross -j"$NPROC"
log_info "mpy-cross 编译完成"

log_step "步骤 5/7: 编译 ESP32-C3 固件"

cd "$MICROPYTHON_DIR/ports/esp32"

make BOARD="$BOARD" submodules

if [[ "$CLEAN_BUILD" == true ]]; then
    log_info "清理构建缓存..."
    make BOARD="$BOARD" clean
fi

MANIFEST_PATH="${SCRIPT_DIR}/manifest.py"
log_info "使用 manifest: $MANIFEST_PATH"
log_info "目标板型: $BOARD"
log_info "正在编译固件（首次编译较慢，约5-15分钟）..."

make BOARD="$BOARD" FROZEN_MANIFEST="$MANIFEST_PATH" -j"$NPROC"

log_info "固件编译完成"

log_step "步骤 6/7: 打包固件到 target 目录"

mkdir -p "$TARGET_DIR"

BUILD_DIR="$MICROPYTHON_DIR/ports/esp32/build-${BOARD}"

FIRMWARE_BIN="${BUILD_DIR}/firmware.bin"

if [[ -f "$FIRMWARE_BIN" ]]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    TARGET_APP="${TARGET_DIR}/firmware-${TIMESTAMP}.bin"
    LATEST_APP="${TARGET_DIR}/firmware.bin"

    cp "$FIRMWARE_BIN" "$TARGET_APP"
    cp "$FIRMWARE_BIN" "$LATEST_APP"

    FILE_SIZE=$(file_size_human "$FIRMWARE_BIN")
    log_info "固件已复制到: $TARGET_APP ($FILE_SIZE)"
    log_info "最新固件链接: $LATEST_APP"

    OLD_FIRMWARE=$(ls -1t "$TARGET_DIR"/firmware-*.bin 2>/dev/null | tail -n +$((KEEP_FIRMWARE_COUNT + 1)) || true)
    if [[ -n "$OLD_FIRMWARE" ]]; then
        while IFS= read -r old_file; do
            [[ -z "$old_file" ]] && continue
            rm -f "$old_file"
            log_info "已清理旧固件: $old_file"
        done <<< "$OLD_FIRMWARE"
    fi

    log_info "注意: 使用合并固件(firmware.bin)，烧录到地址 0x0 即可"
else
    log_error "固件文件未找到: $FIRMWARE_BIN"
    log_error "编译可能失败，请检查上方日志"
    exit 1
fi

log_step "步骤 7/7: 烧录指南"

DETECTED_PORT="未检测到"
if is_macos; then
    DETECTED_PORT=$(ls /dev/cu.usbmodem* 2>/dev/null | head -1 || echo "未检测到")
elif is_linux || is_wsl; then
    DETECTED_PORT=$(ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | head -1 || echo "未检测到")
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║          固件编译打包完成!               ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "固件文件: $TARGET_APP"
echo "文件大小: $FILE_SIZE"
echo "检测串口: $DETECTED_PORT"
echo ""
echo "烧录命令:"
echo ""
echo "  # 擦除 Flash（首次烧录时需要）"
echo "  esptool.py --chip esp32c3 --port ${DETECTED_PORT} erase_flash"
echo ""
echo "  # 烧录固件（合并固件，写入地址 0x0）"
echo "  esptool.py --chip esp32c3 --port ${DETECTED_PORT} --baud 460800 \\"
echo "    write_flash 0 ${LATEST_APP}"
echo ""
echo "  # 使用烧录脚本（自动扫描串口）"
echo "  bash scripts/flash_firmware.sh -e"
echo ""
echo "  # 使用 mpremote"
echo "  mpremote connect ${DETECTED_PORT} flash ${LATEST_APP}"
echo ""
echo "冻结模块列表:"
echo "  - boot.py"
echo "  - config.py"
echo "  - logger.py"
echo "  - utils.py"
echo "  - ble_service.py"
echo "  - power_data.py"
echo "  - wifi_manager.py"
echo "  - web_pages.py"
echo "  - ota_updater.py"
echo "  - app.py"
echo ""
echo "设备上电后将自动运行 app.main()"
