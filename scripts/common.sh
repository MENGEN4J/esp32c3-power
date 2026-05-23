#!/usr/bin/env bash
# ============================================================
#  BikePower 跨平台公共函数库
#  提供 OS 检测、ESP32-C3 串口智能扫描、跨平台兼容工具
#  使用方式: source "$(dirname "$0")/common.sh"
# ============================================================

_BIKEPOWER_COMMON_LOADED=true

# ---- 颜色定义 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()  { echo -e "\n${CYAN}==== $1 ====${NC}"; }

# ============================================================
#  OS 检测
# ============================================================
detect_os() {
    case "$(uname -s)" in
        Darwin)
            _OS_TYPE="macos"
            _OS_DISPLAY="macOS $(sw_vers -productVersion 2>/dev/null || echo 'Unknown')"
            ;;
        Linux)
            if grep -qi microsoft /proc/version 2>/dev/null; then
                _OS_TYPE="wsl"
                _OS_DISPLAY="WSL ($(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d'"' -f2 || echo 'Linux'))"
            else
                _OS_TYPE="linux"
                _OS_DISPLAY="Linux ($(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d'"' -f2 || echo 'Unknown'))"
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*)
            _OS_TYPE="windows_git_bash"
            _OS_DISPLAY="Windows (Git Bash)"
            ;;
        *)
            _OS_TYPE="unknown"
            _OS_DISPLAY="Unknown ($(uname -s))"
            ;;
    esac
    export _OS_TYPE _OS_DISPLAY
}

is_macos() { [[ "${_OS_TYPE:-}" == "macos" ]]; }
is_linux() { [[ "${_OS_TYPE:-}" == "linux" ]]; }
is_wsl()   { [[ "${_OS_TYPE:-}" == "wsl" ]]; }
is_windows_git_bash() { [[ "${_OS_TYPE:-}" == "windows_git_bash" ]]; }

# ============================================================
#  跨平台文件大小获取
# ============================================================
file_size_bytes() {
    local file="$1"
    if is_macos; then
        stat -f%z "$file" 2>/dev/null || echo 0
    else
        stat -c%s "$file" 2>/dev/null || echo 0
    fi
}

file_size_human() {
    du -h "$1" | cut -f1
}

# ============================================================
#  跨平台 CPU 核心数
# ============================================================
cpu_count() {
    if is_macos; then
        sysctl -n hw.ncpu 2>/dev/null || echo 4
    else
        nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo 2>/dev/null || echo 4
    fi
}

# ============================================================
#  跨平台超时执行
# ============================================================
run_with_timeout() {
    local seconds=$1
    shift

    if command -v timeout >/dev/null 2>&1; then
        timeout "${seconds}s" "$@"
    elif command -v gtimeout >/dev/null 2>&1; then
        gtimeout "${seconds}s" "$@"
    else
        "$@" &
        local pid=$!
        local elapsed=0
        while kill -0 "$pid" 2>/dev/null && [[ $elapsed -lt $seconds ]]; do
            sleep 1
            elapsed=$((elapsed + 1))
        done
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            wait "$pid" 2>/dev/null || true
        else
            wait "$pid" 2>/dev/null || true
        fi
    fi
}

# ============================================================
#  跨平台打开浏览器
# ============================================================
open_url() {
    local url="$1"
    if is_macos; then
        open "$url" 2>/dev/null || true
    elif is_linux || is_wsl; then
        xdg-open "$url" 2>/dev/null || true
    elif is_windows_git_bash; then
        start "$url" 2>/dev/null || true
    fi
}

# ============================================================
#  ESP32-C3 串口智能扫描
#  优先使用 pyserial list_ports（可获取 VID/PID 识别芯片型号）
#  回退到系统工具（ls /dev/...）
# ============================================================

_ESP_VIDS="0x303a 0x10c4 0x1a86 0x0403"

_esp_vid_matches() {
    local vid="$1"
    for v in $_ESP_VIDS; do
        if [[ "$vid" == "$v" ]]; then
            return 0
        fi
    done
    return 1
}

_esp_chip_hint() {
    local vid="$1"
    local pid="$2"
    case "$vid" in
        0x303a)
            echo "ESP32-C3/S2/S3 (Espressif USB)"
            ;;
        0x10c4)
            echo "CP210x (Silicon Labs USB-UART)"
            ;;
        0x1a86)
            echo "CH340/CH341 (USB-UART)"
            ;;
        0x0403)
            echo "FTDI FT232 (USB-UART)"
            ;;
        *)
            echo "Unknown USB device"
            ;;
    esac
}

scan_esp32_ports() {
    local verbose=false
    [[ "${1:-}" == "-v" || "${1:-}" == "--verbose" ]] && verbose=true

    echo "============================================================"
    echo "  ESP32-C3 串口智能扫描"
    echo "  系统: ${_OS_DISPLAY:-Unknown}"
    echo "============================================================"
    echo ""

    local esp_ports=()
    local other_ports=()

    if python3 -c "from serial.tools import list_ports" 2>/dev/null; then
        log_info "使用 pyserial 扫描串口设备..."
        echo ""

        local port_data
        port_data=$(python3 -c "
from serial.tools import list_ports
import sys
ports = list(list_ports.comports())
for p in sorted(ports, key=lambda x: x.device):
    vid = f'{p.vid:#06x}' if p.vid else '0x0000'
    pid = f'{p.pid:#06x}' if p.pid else '0x0000'
    print(f'{p.device}|{vid}|{pid}|{p.description}|{p.manufacturer or \"\"}|{p.hwid}')
" 2>/dev/null)

        if [[ -z "$port_data" ]]; then
            log_warn "pyserial 未检测到任何串口"
        else
            while IFS='|' read -r dev vid pid desc mfr hwid; do
                [[ -z "$dev" ]] && continue

                if _esp_vid_matches "$vid"; then
                    local chip_hint
                    chip_hint=$(_esp_chip_hint "$vid" "$pid")
                    esp_ports+=("$dev")
                    echo -e "  ${GREEN}[ESP32]${NC} $dev"
                    echo -e "          VID=$vid PID=$pid | $chip_hint"
                    echo -e "          描述: $desc | 厂商: ${mfr:-N/A}"
                    if $verbose; then
                        echo -e "          HWID: $hwid"
                    fi
                    echo ""
                else
                    other_ports+=("$dev")
                    if $verbose; then
                        echo -e "  ${YELLOW}[其他]${NC}  $dev"
                        echo -e "          VID=$vid PID=$pid | $desc"
                        echo ""
                    fi
                fi
            done <<< "$port_data"
        fi
    else
        log_warn "pyserial 未安装，使用系统工具扫描..."
        echo ""

        local candidates=()
        if is_macos; then
            while IFS= read -r line; do
                [[ -n "$line" ]] && candidates+=("$line")
            done < <(ls /dev/cu.usbmodem* /dev/tty.usbmodem* /dev/cu.SLAB_USBtoUART* /dev/cu.wchusbserial* /dev/cu.usbserial* 2>/dev/null || true)
        elif is_linux || is_wsl; then
            while IFS= read -r line; do
                [[ -n "$line" ]] && candidates+=("$line")
            done < <(ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true)
        fi

        for dev in "${candidates[@]}"; do
            esp_ports+=("$dev")
            local chip_hint="可能为 ESP32 设备"
            if [[ "$dev" == *usbmodem* ]]; then
                chip_hint="ESP32-C3/S2/S3 (Espressif USB)"
            elif [[ "$dev" == *SLAB* ]]; then
                chip_hint="CP210x (Silicon Labs USB-UART)"
            elif [[ "$dev" == *wchusbserial* ]] || [[ "$dev" == *ch340* ]]; then
                chip_hint="CH340/CH341 (USB-UART)"
            fi
            echo -e "  ${GREEN}[ESP32?]${NC} $dev"
            echo -e "           $chip_hint"
            echo ""
        done
    fi

    echo "------------------------------------------------------------"
    if [[ ${#esp_ports[@]} -eq 0 ]]; then
        echo -e "  ${RED}未找到 ESP32-C3 设备${NC}"
        echo ""
        echo "  排查建议:"
        echo "    1. 检查 USB 数据线是否连接（需支持数据传输，非仅充电线）"
        echo "    2. 确认设备已上电（LED 指示灯亮起）"
        echo "    3. macOS: 系统偏好设置 → 安全性与隐私 → 允许 USB 设备"
        echo "    4. Linux: 确认用户在 dialout 组 (sudo usermod -aG dialout \$USER)"
        echo "    5. 安装 pyserial 获取更精确的扫描: pip3 install pyserial"
    else
        echo -e "  ${GREEN}找到 ${#esp_ports[@]} 个 ESP32 设备${NC}"
        local i=1
        for dev in "${esp_ports[@]}"; do
            echo "    [$i] $dev"
            i=$((i + 1))
        done
    fi
    echo "------------------------------------------------------------"

    _SCANNED_ESP_PORTS=("${esp_ports[@]+"${esp_ports[@]}"}")
    _SCANNED_OTHER_PORTS=("${other_ports[@]+"${other_ports[@]}"}")
}

find_esp32_port() {
    local prefer="$1"

    if [[ -n "$prefer" ]]; then
        if [[ -e "$prefer" ]] || [[ "$prefer" == COM* ]]; then
            log_info "使用指定串口: $prefer"
            SERIAL_PORT="$prefer"
            return 0
        else
            log_warn "指定串口不存在: $prefer，尝试自动扫描..."
        fi
    fi

    scan_esp32_ports

    if [[ ${#_SCANNED_ESP_PORTS[@]} -eq 0 ]]; then
        log_error "未找到 ESP32-C3 设备，请检查 USB 连接"
        log_error "可运行详细扫描: bash scripts/common.sh scan -v"
        return 1
    fi

    if [[ ${#_SCANNED_ESP_PORTS[@]} -eq 1 ]]; then
        SERIAL_PORT="${_SCANNED_ESP_PORTS[0]}"
        log_info "自动选择串口: $SERIAL_PORT"
        return 0
    fi

    echo ""
    log_warn "发现 ${#_SCANNED_ESP_PORTS[@]} 个 ESP32 设备，请选择:"
    local i=1
    for dev in "${_SCANNED_ESP_PORTS[@]}"; do
        echo "  [$i] $dev"
        i=$((i + 1))
    done
    echo ""

    read -rp "请输入序号 [1-${#_SCANNED_ESP_PORTS[@]}]: " choice
    if [[ "$choice" =~ ^[0-9]+$ ]] && [[ "$choice" -ge 1 ]] && [[ "$choice" -le ${#_SCANNED_ESP_PORTS[@]} ]]; then
        SERIAL_PORT="${_SCANNED_ESP_PORTS[$((choice - 1))]}"
        log_info "已选择串口: $SERIAL_PORT"
        return 0
    else
        log_error "无效选择"
        return 1
    fi
}

# ============================================================
#  串口占用检测与释放
# ============================================================
check_port_busy() {
    local port="$1"

    if is_macos; then
        local pids
        pids=$(lsof 2>/dev/null | grep "$(basename "$port")" | awk '{print $2}' | sort -u || true)
        if [[ -n "$pids" ]]; then
            log_warn "串口 $port 被以下进程占用:"
            while IFS= read -r pid; do
                local cmd
                cmd=$(ps -p "$pid" -o command= 2>/dev/null || echo "unknown")
                echo "  PID $pid: $cmd"
            done <<< "$pids"
            return 1
        fi
    elif is_linux || is_wsl; then
        if command -v lsof >/dev/null 2>&1; then
            if lsof "$port" >/dev/null 2>&1; then
                log_warn "串口 $port 被占用，请手动释放"
                lsof "$port" 2>/dev/null || true
                return 1
            fi
        elif command -v fuser >/dev/null 2>&1; then
            if fuser "$port" >/dev/null 2>&1; then
                log_warn "串口 $port 被占用，请手动释放"
                fuser -v "$port" 2>/dev/null || true
                return 1
            fi
        fi
    fi

    log_info "串口未被占用"
    return 0
}

release_port() {
    local port="$1"

    if check_port_busy "$port"; then
        return 0
    fi

    echo ""
    read -rp "是否终止占用进程？[y/N] " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        if is_macos; then
            local pids
            pids=$(lsof 2>/dev/null | grep "$(basename "$port")" | awk '{print $2}' | sort -u || true)
            while IFS= read -r pid; do
                kill "$pid" 2>/dev/null && log_info "已终止 PID $pid" || log_warn "终止 PID $pid 失败"
            done <<< "$pids"
        elif is_linux || is_wsl; then
            if command -v fuser >/dev/null 2>&1; then
                fuser -k "$port" 2>/dev/null && log_info "已释放串口" || log_warn "释放失败"
            fi
        fi
        sleep 2
        return 0
    else
        log_error "串口仍被占用，无法继续"
        return 1
    fi
}

# ============================================================
#  初始化（自动检测 OS）
# ============================================================
detect_os

# ============================================================
#  独立运行入口（bash scripts/common.sh scan [-v]）
# ============================================================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [[ $# -eq 0 ]]; then
        echo "用法: bash scripts/common.sh <命令> [选项]"
        echo ""
        echo "命令:"
        echo "  scan [-v]   智能扫描 ESP32-C3 串口设备（-v 详细输出）"
        echo "  os          显示当前操作系统信息"
        exit 0
    fi

    case "$1" in
        scan)
            shift
            scan_esp32_ports "$@"
            ;;
        os)
            echo "系统类型: $_OS_TYPE"
            echo "系统信息: $_OS_DISPLAY"
            echo "CPU 核心: $(cpu_count)"
            ;;
        *)
            log_error "未知命令: $1"
            echo "可用命令: scan, os"
            exit 1
            ;;
    esac
fi
