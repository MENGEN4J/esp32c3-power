#!/usr/bin/env bash
# ============================================================
#  ESP32-C3 MicroPython 一键部署脚本
#  用法: ./deploy.sh [选项]
#  适用于 macOS / Linux，Windows 请使用 deploy.ps1
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/common.sh"

MAIN_FILE="${PROJECT_DIR}/app.py"
REMOTE_NAME="app.py"
MODULE_FILES=("config.py" "logger.py" "utils.py" "web_pages.py" "ble_service.py" "power_data.py" "wifi_manager.py" "ota_updater.py")
BOOT_FILE="${PROJECT_DIR}/boot.py"
SERIAL_PORT=""
AUTO_FIX=true
MONITOR_SECONDS=8
MAX_RETRIES=2

usage() {
    cat <<EOF
ESP32-C3 MicroPython 一键部署脚本

用法: $(basename "$0") [选项]

选项:
  -p, --port PORT       指定串口地址（不指定则自动扫描 ESP32-C3）
  -f, --file FILE       指定本地主程序文件（默认: app.py）
  -n, --no-fix          禁用自动修复（遇到异常直接退出）
  -m, --monitor SEC     日志监控时长，秒（默认: 8）
  -r, --retries N       最大重试次数（默认: 2）
  -h, --help            显示帮助信息

示例:
  ./deploy.sh                          # 自动扫描 ESP32-C3 串口并部署
  ./deploy.sh -p /dev/cu.usbmodem1101  # 指定串口
  ./deploy.sh -f myCode.py             # 指定文件
  ./deploy.sh -n                       # 禁用自动修复

串口扫描:
  脚本通过 USB VID/PID 智能识别 ESP32-C3 设备
  支持识别: Espressif USB(0x303A) / CP210x(0x10C4) / CH340(0x1A86)
  也可单独运行扫描: bash scripts/common.sh scan

EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -p|--port)    SERIAL_PORT="$2"; shift 2 ;;
        -f|--file)    MAIN_FILE="${PROJECT_DIR}/$2"; REMOTE_NAME="$(basename "$2")"; shift 2 ;;
        -n|--no-fix)  AUTO_FIX=false; shift ;;
        -m|--monitor) MONITOR_SECONDS="$2"; shift 2 ;;
        -r|--retries) MAX_RETRIES="$2"; shift 2 ;;
        -h|--help)    usage ;;
        *)            log_error "未知参数: $1"; usage ;;
    esac
done

# ============================================================
#  步骤 1: 智能扫描 ESP32-C3 串口
# ============================================================
detect_port() {
    log_step "步骤 1/7: 扫描 ESP32-C3 串口"

    log_info "当前系统: ${_OS_DISPLAY}"

    find_esp32_port "$SERIAL_PORT" || exit 1
}

# ============================================================
#  步骤 2: 释放串口占用
# ============================================================
check_and_release_port() {
    log_step "步骤 2/7: 检查串口占用"

    release_port "$SERIAL_PORT" || exit 1
}

# ============================================================
#  步骤 3: 验证连接
# ============================================================
verify_connection() {
    log_step "步骤 3/7: 验证设备连接"

    wait_for_mpremote_ready() {
        local retries=5
        local i
        for ((i = 1; i <= retries; i++)); do
            if python3 -m mpremote connect "$SERIAL_PORT" exec "print('READY')" 2>/dev/null | grep -q "READY"; then
                return 0
            fi
            log_warn "等待 mpremote exec 就绪，第 $i/$retries 次重试..."
            sleep 2
        done
        return 1
    }

    if python3 -m mpremote connect "$SERIAL_PORT" ls >/dev/null 2>&1; then
        if wait_for_mpremote_ready; then
            log_info "设备连接成功"
            return 0
        fi
    fi

    log_warn "mpremote 无法连接（设备可能正在运行 BLE 程序）"
    log_info "尝试进入部署模式（创建 .deploy 标志文件后重启）..."

    python3 -c "
import serial, time
try:
    s = serial.Serial('$SERIAL_PORT', 115200, timeout=2)
    time.sleep(0.1)
    s.write(b'\x03\x03')
    time.sleep(0.5)
    s.write(b'\x01')
    time.sleep(0.5)
    s.read(s.in_waiting or 4096)
    s.write(b'f=open(\".deploy\",\"w\");f.flush();f.close()\x04')
    time.sleep(0.5)
    s.read(s.in_waiting or 4096)
    s.write(b'\x02')
    time.sleep(0.3)
    s.read(s.in_waiting or 4096)
    s.write(b'\x04')
    time.sleep(3)
    s.read(s.in_waiting or 8192)
    s.dtr = False
    s.rts = True
    time.sleep(0.1)
    s.rts = False
    time.sleep(0.5)
    s.dtr = True
    s.close()
    del s
except Exception:
    pass
" 2>/dev/null || true

    sleep 2

    local retries=5
    local i
    for ((i = 1; i <= retries; i++)); do
        if python3 -m mpremote connect "$SERIAL_PORT" ls >/dev/null 2>&1; then
            if wait_for_mpremote_ready; then
                log_info "设备连接成功（部署模式）"
                return 0
            fi
        fi
        log_warn "连接失败，第 $i/$retries 次重试..."
        sleep 2
    done

    log_error "无法连接设备 ($SERIAL_PORT)，请检查："
    log_error "  1. USB 线是否连接（需支持数据传输，非仅充电线）"
    log_error "  2. 尝试物理重插 USB 后重新部署"
    exit 1
}

# ============================================================
#  步骤 3.5: 清理设备旧文件
# ============================================================
remove_legacy_files() {
    log_step "步骤 3.5/7: 清理设备旧文件"
    for f in main.py; do
        if python3 -m mpremote connect "$SERIAL_PORT" rm :"$f" 2>/dev/null; then
            log_info "已删除设备上的 $f"
        fi
    done
    log_info "旧文件清理完成"
}

# ============================================================
#  步骤 4: BOM 检查与语法检查
# ============================================================
check_file() {
    log_step "步骤 4/7: 文件检查"

    local all_files=("$MAIN_FILE" "$BOOT_FILE")
    for mod in "${MODULE_FILES[@]}"; do
        all_files+=("${PROJECT_DIR}/$mod")
    done
    for f in "${all_files[@]}"; do
        if [[ ! -f "$f" ]]; then
            log_error "文件不存在: $f"
            exit 1
        fi

        local bom_bytes
        bom_bytes=$(xxd -l 3 -p "$f" 2>/dev/null || true)
        if [[ "$bom_bytes" == "efbbbf" ]]; then
            log_warn "检测到 UTF-8 BOM ($f)，正在移除..."
            python3 -c "
with open('$f', 'rb') as fh:
    data = fh.read()
if data[:3] == b'\xef\xbb\xbf':
    data = data[3:]
with open('$f', 'wb') as fh:
    fh.write(data)
"
            log_info "BOM 已移除: $f"
        fi
    done

    log_info "BOM 检查通过 (${#all_files[@]} 个文件)"

    if python3 -c "import py_compile; py_compile.compile('$MAIN_FILE', doraise=True)" 2>/dev/null; then
        log_info "语法检查通过"
    else
        log_error "语法检查失败！"
        python3 -c "import py_compile; py_compile.compile('$MAIN_FILE', doraise=True)"
        exit 1
    fi
}

# ============================================================
#  步骤 5: 上传文件
# ============================================================
upload_file() {
    log_step "步骤 5/7: 上传文件"

    for mod in "${MODULE_FILES[@]}"; do
        local src="${PROJECT_DIR}/$mod"
        local local_size
        local_size=$(file_size_bytes "$src")
        log_info "上传模块: $mod ($local_size bytes)"
        if ! python3 -m mpremote connect "$SERIAL_PORT" cp "$src" :"$mod"; then
            log_error "上传失败: $mod"
            exit 1
        fi
    done

    local local_size
    local_size=$(file_size_bytes "$MAIN_FILE")
    log_info "上传主程序: $REMOTE_NAME ($local_size bytes)"

    if ! python3 -m mpremote connect "$SERIAL_PORT" cp "$MAIN_FILE" :"$REMOTE_NAME"; then
        log_error "上传主程序失败"
        exit 1
    fi

    local_size=$(file_size_bytes "$BOOT_FILE")
    log_info "上传启动入口: boot.py ($local_size bytes)"
    if ! python3 -m mpremote connect "$SERIAL_PORT" cp "$BOOT_FILE" :boot.py; then
        log_error "上传 boot.py 失败"
        exit 1
    fi

    log_info "全部上传成功 (${#MODULE_FILES[@]} 个模块 + app.py + boot.py)"
}

# ============================================================
#  步骤 6: 启动运行
# ============================================================
run_program() {
    log_step "步骤 6/7: 启动程序"

    log_info "删除部署模式标志，重启设备..."
    python3 -m mpremote connect "$SERIAL_PORT" rm :.deploy 2>/dev/null || true

    python3 -c "
import serial, time
try:
    s = serial.Serial('$SERIAL_PORT', 115200, timeout=2)
    s.dtr = False
    s.rts = True
    time.sleep(0.1)
    s.rts = False
    time.sleep(0.5)
    s.dtr = True
    s.close()
    del s
except Exception:
    pass
" 2>/dev/null || true

    sleep 5

    log_info "验证程序启动（通过串口读取启动日志）..."
    local log_output
    log_output=$(python3 -c "
import serial, time
try:
    s = serial.Serial('$SERIAL_PORT', 115200, timeout=8)
    time.sleep(0.1)
    output = s.read(s.in_waiting or 8192)
    if not output:
        time.sleep(5)
        output = s.read(s.in_waiting or 8192)
    text = output.decode('utf-8', errors='replace') if isinstance(output, bytes) else str(output)
    print(text)
    s.close()
except Exception as e:
    print(f'serial read error: {e}')
" 2>&1 || true)

    if [[ -n "$log_output" ]]; then
        echo "$log_output"
        analyze_log "$log_output"
    else
        log_info "串口无输出，设备可能已正常启动 BLE 程序"
        log_info "🎉 部署成功！程序运行正常"
    fi
}

# ============================================================
#  步骤 7: 日志分析与自修复
# ============================================================
analyze_log() {
    log_step "步骤 7/7: 日志分析"

    local log_data="$1"
    local has_error=false
    local error_type=""

    local ble_ok=false
    local wifi_ok=false
    local web_ok=false

    if echo "$log_data" | grep -q "蓝牙功率计已启动\|BikePower"; then
        ble_ok=true
        log_info "✅ 蓝牙启动正常"
    fi

    if echo "$log_data" | grep -q "WiFi热点已启动"; then
        wifi_ok=true
        log_info "✅ WiFi 启动正常"
    fi

    if echo "$log_data" | grep -q "Web服务器已启动"; then
        web_ok=true
        log_info "✅ Web 服务器启动正常"
    fi

    if echo "$log_data" | grep -q "Traceback" && ! echo "$log_data" | grep -q "mpremote\|TransportError\|runpy.py"; then
        has_error=true
        error_type="Traceback"
        log_error "❌ 检测到运行时异常 (Traceback)"
    fi

    if echo "$log_data" | grep -q "NameError"; then
        has_error=true
        error_type="NameError"
        log_error "❌ 检测到 NameError（可能由 BOM 或语法错误引起）"
    fi

    if echo "$log_data" | grep -q "ImportError"; then
        has_error=true
        error_type="ImportError"
        log_error "❌ 检测到 ImportError（缺少模块）"
    fi

    if echo "$log_data" | grep -q "OSError.*ENOMEM"; then
        has_error=true
        error_type="ENOMEM"
        log_error "❌ 检测到内存不足错误"
    fi

    if echo "$log_data" | grep -q "初始化失败\|启动失败"; then
        has_error=true
        error_type="InitFailed"
        log_error "❌ 检测到初始化失败"
    fi

    if [[ "$has_error" == false ]] && [[ "$ble_ok" == true ]]; then
        log_info "🎉 部署成功！程序运行正常"
        return 0
    fi

    if [[ "$AUTO_FIX" == true ]] && [[ $RETRY_COUNT -lt $MAX_RETRIES ]]; then
        log_warn "尝试自动修复 (第 $((RETRY_COUNT + 1))/$MAX_RETRIES 次)..."

        case "$error_type" in
            NameError)
                log_info "修复策略: 重新检查 BOM 并重新上传"
                verify_connection
                upload_file
                ;;
            ENOMEM)
                log_info "修复策略: 重新部署"
                verify_connection
                upload_file
                ;;
            ImportError|Traceback|InitFailed)
                log_info "修复策略: 重新进入部署模式并部署"
                verify_connection
                upload_file
                ;;
            *)
                log_warn "未知异常类型，尝试重新部署"
                verify_connection
                upload_file
                ;;
        esac

        RETRY_COUNT=$((RETRY_COUNT + 1))
        run_program
        return $?
    fi

    log_error "部署失败，请手动检查日志"
    return 1
}

# ============================================================
#  主流程
# ============================================================
RETRY_COUNT=0

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   ESP32-C3 MicroPython 一键部署      ║"
echo "╚══════════════════════════════════════╝"
echo ""

detect_port
check_and_release_port
verify_connection
remove_legacy_files
check_file
upload_file
run_program

echo ""
log_info "完成！设备 $SERIAL_PORT 运行中"

# ============================================================
#  启动本地监控页面
# ============================================================
start_monitor_server() {
    local WEB_DIR="${PROJECT_DIR}/web"
    local MONITOR_PORT=8765

    if ! lsof -i :${MONITOR_PORT} >/dev/null 2>&1; then
        log_info "启动本地监控服务器 (端口 ${MONITOR_PORT})..."
        python3 -m http.server ${MONITOR_PORT} --directory "$WEB_DIR" >/dev/null 2>&1 &
        local server_pid=$!
        sleep 1

        if kill -0 "$server_pid" 2>/dev/null; then
            log_info "监控服务器已启动 (PID: $server_pid)"
        else
            log_warn "监控服务器启动失败，可手动执行:"
            log_warn "  cd web && python3 -m http.server ${MONITOR_PORT}"
            return
        fi
    else
        log_info "监控服务器已在运行 (端口 ${MONITOR_PORT})"
    fi

    local monitor_url="http://localhost:${MONITOR_PORT}/monitor.html"
    log_info "在默认浏览器中打开监控页面..."
    open_url "$monitor_url"
    log_info "监控页面: $monitor_url"
}

start_monitor_server
