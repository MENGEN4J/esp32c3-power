#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/common.sh"

TARGET_DIR="${PROJECT_DIR}/target"
SERIAL_PORT=""
ERASE=false
UPLOAD_MAIN=true
SKIP_VERIFY=false
MONITOR_SECONDS=10

usage() {
    cat <<EOF
ESP32-C3 固件烧录脚本

用法: $(basename "$0") [选项]

选项:
  -p, --port PORT     指定串口地址（不指定则自动扫描 ESP32-C3）
  -e, --erase         擦除 Flash 后再烧录（首次烧录时使用）
  -n, --no-main       不上传 main.py 启动入口
  -s, --skip-verify   跳过烧录后验证
  -m, --monitor SECS  烧录后监控日志秒数（默认10秒，0=不监控）
  -h, --help          显示帮助信息

示例:
  $(basename "$0")                          # 自动扫描 ESP32-C3 串口并烧录
  $(basename "$0") -e                       # 擦除 Flash 后烧录（首次）
  $(basename "$0") -p /dev/cu.usbmodem1101  # 指定串口
  $(basename "$0") -n                       # 仅烧录固件，不上传 main.py

串口扫描:
  脚本通过 USB VID/PID 智能识别 ESP32-C3 设备
  支持识别: Espressif USB(0x303A) / CP210x(0x10C4) / CH340(0x1A86)

常见问题:
  1. 设备启动失败（overlaps bootloader stack）:
     原因: 使用了 micropython.bin（仅应用部分）而非 firmware.bin（合并固件）
     修复: 必须使用 firmware.bin 写入地址 0x0，不能分段烧录

  2. esptool 未找到:
     脚本会自动搜索 ESP-IDF 虚拟环境中的 esptool
     也可手动安装: pip3 install esptool

  3. mpremote 连接失败:
     设备重启需要时间，脚本会自动重试
     如持续失败，请手动重插 USB 后执行:
     python3 -m mpremote connect <PORT> cp main.py :main.py

EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -p|--port)        SERIAL_PORT="$2"; shift 2 ;;
        -e|--erase)       ERASE=true; shift ;;
        -n|--no-main)     UPLOAD_MAIN=false; shift ;;
        -s|--skip-verify) SKIP_VERIFY=true; shift ;;
        -m|--monitor)     MONITOR_SECONDS="$2"; shift 2 ;;
        -h|--help)        usage ;;
        *)                log_error "未知参数: $1"; usage ;;
    esac
done

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║      ESP32-C3 固件烧录工具               ║"
echo "╚══════════════════════════════════════════╝"
echo ""

log_info "当前系统: ${_OS_DISPLAY}"

# ============================================================
#  检查固件文件
# ============================================================
log_step "步骤 1/6: 检查固件文件"

FIRMWARE_BIN="${TARGET_DIR}/firmware.bin"
MAIN_PY="${PROJECT_DIR}/main.py"

if [[ ! -f "$FIRMWARE_BIN" ]]; then
    log_error "固件文件不存在: $FIRMWARE_BIN"
    log_error "请先执行 ./scripts/build_firmware.sh 编译固件"
    exit 1
fi

FIRMWARE_SIZE=$(file_size_bytes "$FIRMWARE_BIN")
if [[ "$FIRMWARE_SIZE" -lt 100000 ]]; then
    log_error "固件文件异常: 大小仅 $FIRMWARE_SIZE 字节（正常应 >1MB）"
    log_error "可能误用了 micropython.bin（仅应用部分），请确认使用 firmware.bin（合并固件）"
    exit 1
fi

log_info "合并固件: $(file_size_human "$FIRMWARE_BIN")  $FIRMWARE_BIN"
log_info "文件大小: $FIRMWARE_SIZE 字节"

if [[ "$UPLOAD_MAIN" == true ]] && [[ ! -f "$MAIN_PY" ]]; then
    log_error "main.py 不存在: $MAIN_PY"
    exit 1
fi

# ============================================================
#  智能扫描 ESP32-C3 串口
# ============================================================
log_step "步骤 2/6: 扫描 ESP32-C3 串口"

find_esp32_port "$SERIAL_PORT" || exit 1

# ============================================================
#  检查 esptool
# ============================================================
log_step "步骤 3/6: 检查工具"

ESPTOOL=""
if command -v esptool.py >/dev/null 2>&1; then
    ESPTOOL="esptool.py"
elif python3 -m esptool --help >/dev/null 2>&1; then
    ESPTOOL="python3 -m esptool"
fi

if [[ -z "$ESPTOOL" ]]; then
    for idf_env in "$HOME/.espressif/python_env"/idf*_py*_env; do
        if [[ -f "$idf_env/bin/esptool.py" ]]; then
            ESPTOOL="$idf_env/bin/esptool.py"
            break
        fi
    done
fi

if [[ -z "$ESPTOOL" ]]; then
    log_error "esptool 未安装"
    log_error "请执行以下任一命令安装:"
    log_error "  pip3 install esptool"
    log_error "  或安装 ESP-IDF: ./scripts/build_firmware.sh（会自动安装）"
    exit 1
fi

log_info "esptool: $ESPTOOL"

# ============================================================
#  擦除 Flash
# ============================================================
if [[ "$ERASE" == true ]]; then
    log_step "步骤 4/6: 擦除 Flash"
    log_warn "此操作将清除设备上所有数据！"
    $ESPTOOL --chip esp32c3 --port "$SERIAL_PORT" erase_flash
    log_info "Flash 擦除完成"
else
    log_step "步骤 4/6: 烧录固件（跳过擦除，如遇问题请使用 -e 参数）"
fi

# ============================================================
#  烧录固件
# ============================================================
log_info "正在烧录固件..."
log_info "  合并固件 -> 0x0 (包含 bootloader + partition-table + app)"
log_info ""
log_info "  ⚠️  重要: 必须使用 firmware.bin（合并固件）写入地址 0x0"
log_info "  ⚠️  不能使用 micropython.bin 分段烧录，否则设备无法启动"
log_info "  ⚠️  错误现象: 'overlaps bootloader stack' / 'not bootable'"

FLASH_OK=false
if $ESPTOOL --chip esp32c3 --port "$SERIAL_PORT" --baud 460800 \
    write_flash 0 "$FIRMWARE_BIN" 2>&1; then
    FLASH_OK=true
else
    log_error "固件烧录失败！"
    log_warn "尝试降低波特率重新烧录..."
    if $ESPTOOL --chip esp32c3 --port "$SERIAL_PORT" \
        write_flash 0 "$FIRMWARE_BIN" 2>&1; then
        FLASH_OK=true
    else
        log_error "降低波特率后仍然失败，尝试擦除 Flash 后重烧..."
        $ESPTOOL --chip esp32c3 --port "$SERIAL_PORT" erase_flash 2>&1 || true
        sleep 2
        if $ESPTOOL --chip esp32c3 --port "$SERIAL_PORT" --baud 460800 \
            write_flash 0 "$FIRMWARE_BIN" 2>&1; then
            FLASH_OK=true
        fi
    fi
fi

if [[ "$FLASH_OK" != true ]]; then
    log_error "固件烧录失败，请检查:"
    log_error "  1. USB 连接是否正常"
    log_error "  2. 设备是否进入下载模式（按住 BOOT 键再按 RST）"
    log_error "  3. 串口是否被其他程序占用"
    exit 1
fi

log_info "固件烧录完成"

# ============================================================
#  验证设备启动
# ============================================================
log_step "步骤 5/6: 验证设备启动"

if [[ "$SKIP_VERIFY" == true ]]; then
    log_info "跳过验证（-s 参数）"
else
    BOOT_OK=false
    for attempt in $(seq 1 5); do
        sleep $((attempt * 2))

        SERIAL_OUTPUT=$(python3 -m mpremote connect "$SERIAL_PORT" exec "print('BOOT_OK')" 2>&1 || true)

        if echo "$SERIAL_OUTPUT" | grep -q "BOOT_OK"; then
            BOOT_OK=true
            break
        fi

        if echo "$SERIAL_OUTPUT" | grep -qi "overlaps bootloader\|not bootable\|invalid.*segment"; then
            log_error "检测到启动失败: 固件格式不正确"
            log_error "根因: 可能使用了 micropython.bin（仅应用部分）而非 firmware.bin（合并固件）"
            log_error "修复: 请重新执行 ./scripts/build_firmware.sh 编译固件"
            log_error "      确认 target/firmware.bin 是合并固件而非 micropython.bin"
            exit 1
        fi

        log_warn "设备未响应，等待重试 ($attempt/5)..."
    done

    if [[ "$BOOT_OK" == true ]]; then
        log_info "设备启动验证通过"
    else
        log_warn "设备未在 30 秒内响应，可能需要手动重插 USB"
        log_warn "如果设备持续重启（串口输出 'not bootable'），说明固件格式错误"
        log_warn "请使用 -e 参数擦除 Flash 后重新烧录: $0 -e"
    fi
fi

# ============================================================
#  上传 main.py
# ============================================================
log_step "步骤 6/6: 上传 main.py"

if [[ "$UPLOAD_MAIN" == true ]]; then
    UPLOAD_OK=false
    for attempt in $(seq 1 3); do
        if python3 -m mpremote connect "$SERIAL_PORT" cp "$MAIN_PY" :main.py 2>&1; then
            UPLOAD_OK=true
            break
        fi
        log_warn "上传失败，重试 ($attempt/3)..."
        sleep 3
    done

    if [[ "$UPLOAD_OK" == true ]]; then
        log_info "main.py 上传完成"
        log_info "设备上电后将自动运行 app.main()"
    else
        log_warn "无法上传 main.py（设备可能需要手动重插 USB）"
        log_warn "请手动执行以下命令："
        echo ""
        echo "  python3 -m mpremote connect $SERIAL_PORT cp main.py :main.py"
        echo ""
    fi
else
    log_info "跳过 main.py 上传（-n 参数）"
    log_warn "设备上电后不会自动运行，需手动上传 main.py："
    echo ""
    echo "  python3 -m mpremote connect $SERIAL_PORT cp main.py :main.py"
    echo ""
fi

# ============================================================
#  监控串口日志
# ============================================================
if [[ "$MONITOR_SECONDS" -gt 0 ]] 2>/dev/null; then
    log_step "监控串口日志 (${MONITOR_SECONDS}秒)"
    log_info "实时输出设备日志，Ctrl+C 可提前退出..."

    run_with_timeout "$MONITOR_SECONDS" python3 -m mpremote connect "$SERIAL_PORT" 2>&1 || true

    log_info "监控结束"
else
    log_info "跳过日志监控（-m 0）"
fi

# ============================================================
#  完成
# ============================================================
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║          固件烧录完成!                   ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "串口: $SERIAL_PORT"
echo "固件: $FIRMWARE_BIN ($FIRMWARE_SIZE 字节)"
echo ""
echo "后续操作:"
echo "  - 重启设备后程序将自动运行"
echo "  - 如需查看日志: python3 -m mpremote connect $SERIAL_PORT"
echo "  - 如需重新部署代码（不刷固件）: ./scripts/deploy.sh"
echo "  - 如设备无法启动: $0 -e  # 擦除后重烧"
echo "  - 持续监控日志: python3 -m mpremote connect $SERIAL_PORT"

# ============================================================
#  启动本地监控页面
# ============================================================
MONITOR_PORT=8765
WEB_DIR="${PROJECT_DIR}/web"

if ! lsof -i :${MONITOR_PORT} >/dev/null 2>&1; then
    log_info "启动本地监控服务器 (端口 ${MONITOR_PORT})..."
    python3 -m http.server ${MONITOR_PORT} --directory "$WEB_DIR" >/dev/null 2>&1 &
    server_pid=$!
    sleep 1

    if kill -0 "$server_pid" 2>/dev/null; then
        log_info "监控服务器已启动 (PID: $server_pid)"
    else
        log_warn "监控服务器启动失败，可手动执行:"
        log_warn "  cd web && python3 -m http.server ${MONITOR_PORT}"
    fi
else
    log_info "监控服务器已在运行 (端口 ${MONITOR_PORT})"
fi

monitor_url="http://localhost:${MONITOR_PORT}/monitor.html"
log_info "在默认浏览器中打开监控页面..."
open_url "$monitor_url"
log_info "监控页面: $monitor_url"
