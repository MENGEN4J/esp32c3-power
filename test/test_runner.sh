#!/bin/bash
# BikePower 自动化测试 — 5分钟内完成，异步执行，详细报告
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEST_DIR="${PROJECT_DIR}/test"
REPORT_DIR="${PROJECT_DIR}/test/reports"
SERIAL_PORT=""
MAX_RETRY=1
SKIP_BLE=false
SKIP_WIFI=false
START_TIME=$(date +%s)
TIMEOUT_TOTAL=280
DEVICE_HELPER="${TEST_DIR}/device_control.py"
MOCK_PID=""

source "${PROJECT_DIR}/scripts/common.sh"

_timeout() { perl -e 'alarm shift; exec @ARGV' "$@"; }

for arg in "$@"; do
    case "$arg" in
        -p=*) SERIAL_PORT="${arg#-p=}" ;;
        -r=*) MAX_RETRY="${arg#-r=}" ;;
        --skip-ble)  SKIP_BLE=true ;;
        --skip-wifi) SKIP_WIFI=true ;;
    esac
done

if [[ -z "$SERIAL_PORT" ]]; then
    find_esp32_port "" || { log_error "未找到 ESP32-C3 设备"; exit 1; }
fi

mkdir -p "$REPORT_DIR"
RESULT_FILE="${REPORT_DIR}/result_$$.json"
> "$RESULT_FILE"

elapsed() { echo $(( $(date +%s) - START_TIME )); }
check_timeout() {
    if [[ $(elapsed) -gt $TIMEOUT_TOTAL ]]; then
        echo "⏰ 超时(${TIMEOUT_TOTAL}s)，终止测试"
        exit 0
    fi
}

log() { echo -e "\033[0;32m[$(elapsed)s]\033[0m $*"; }
warn() { echo -e "\033[0;33m[$(elapsed)s] ⚠️\033[0m $*"; }
fail() { echo -e "\033[0;31m[$(elapsed)s] ❌\033[0m $*"; }

cleanup() {
    if [[ -n "$MOCK_PID" ]] && kill -0 "$MOCK_PID" 2>/dev/null; then
        kill "$MOCK_PID" 2>/dev/null || true
        wait "$MOCK_PID" 2>/dev/null || true
    fi
}

enter_deploy_mode() {
    python3 "$DEVICE_HELPER" enter-deploy --port "$SERIAL_PORT" >/dev/null
}

exit_deploy_mode() {
    python3 "$DEVICE_HELPER" exit-deploy --port "$SERIAL_PORT" --wait 5 >/dev/null
}

trap cleanup EXIT

add_result() {
    local id="$1" name="$2" status="$3" steps="$4" expected="$5" actual="$6" reason="$7" fix="$8"
    steps=$(echo "$steps" | tr '\n' '\\n')
    printf '%s\n' "$id" "$name" "$status" "$steps" "$expected" "$actual" "$reason" "$fix" >> "$RESULT_FILE"
    case "$status" in
        PASS)  echo "  ✅ [$id] $name" ;;
        FAIL)  echo "  ❌ [$id] $name — $reason" ;;
        SKIP)  echo "  ⏭️  [$id] $name — $reason" ;;
    esac
}

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║    BikePower 自动化测试 (≤5分钟)        ║"
echo "╚══════════════════════════════════════════╝"
echo "串口: $SERIAL_PORT | 超时: ${TIMEOUT_TOTAL}s | 重试: $MAX_RETRY"
echo ""

# ============================================================
#  T1: 串口连接与设备状态
# ============================================================
log "T1: 验证设备连接"
if enter_deploy_mode; then
    log "设备已进入部署模式"
else
    log "设备未能进入部署模式，继续记录失败项..."
fi
check_timeout

T1_OUT=$(_timeout 10 python3 -m mpremote connect "$SERIAL_PORT" exec "print('OK')" 2>&1 || true)
if echo "$T1_OUT" | grep -q "OK"; then
    add_result "T1.1" "串口连接" "PASS" \
        "1.通过测试辅助脚本让设备进入.deploy部署模式\n2.使用mpremote exec执行print('OK')验证通信" \
        "设备响应 OK" "设备响应 OK" "" ""
else
    add_result "T1.1" "串口连接" "FAIL" \
        "1.通过测试辅助脚本让设备进入.deploy部署模式\n2.使用mpremote exec执行print('OK')验证通信" \
        "设备响应 OK" "无响应: $(echo "$T1_OUT" | head -2)" \
        "部署模式不可达或mpremote执行失败" "检查USB连接，确认boot.py部署模式逻辑正常"
fi

T1_CFG=$(_timeout 8 python3 -m mpremote connect "$SERIAL_PORT" exec "
import config
print('DN:', config.DEVICE_NAME)
print('BP:', config.DEFAULT_POWER)
print('BC:', config.DEFAULT_CADENCE)
print('BH:', config.DEFAULT_HEARTRATE)
" 2>&1 || true)

if echo "$T1_CFG" | grep -q "BikePower"; then
    DN=$(echo "$T1_CFG" | grep "DN:" | cut -d' ' -f2)
    BP=$(echo "$T1_CFG" | grep "BP:" | cut -d' ' -f2)
    BC=$(echo "$T1_CFG" | grep "BC:" | cut -d' ' -f2)
    BH=$(echo "$T1_CFG" | grep "BH:" | cut -d' ' -f2)
    add_result "T1.2" "设备配置" "PASS" \
        "1.通过mpremote读取config模块常量\n2.验证DEVICE_NAME/BASE_POWER等" \
        "DEVICE_NAME=BikePower" "DN=$DN BP=${BP}W BC=${BC}RPM BH=${BH}BPM" "" ""
else
    add_result "T1.2" "设备配置" "FAIL" \
        "1.通过mpremote读取config模块常量" \
        "DEVICE_NAME=BikePower" "读取失败" \
        "config模块未正确部署" "重新部署代码: ./scripts/deploy.sh"
fi

check_timeout

# ============================================================
#  恢复主程序并准备 BLE 测试
# ============================================================
DEVICE_MODE="unknown"
if exit_deploy_mode; then
    DEVICE_MODE="ble"
    log "已退出部署模式，等待主程序恢复 BLE 广播"
else
    log "退出部署模式失败，继续测试..."
fi

# ============================================================
#  T4-T8: WiFi 网页测试（本地Mock服务器模式）
# ============================================================
WIFI_RESULT_FILE="${REPORT_DIR}/wifi_result_$$.txt"
> "$WIFI_RESULT_FILE"
MOCK_SERVER_LOG="${REPORT_DIR}/mock_server_$$.log"

if [[ "$SKIP_WIFI" != true ]]; then
    log "T4-T8: 启动本地Mock服务器测试WiFi网页"
    python3 "${TEST_DIR}/mock_server.py" 18080 > "$MOCK_SERVER_LOG" 2>&1 &
    MOCK_PID=$!
    sleep 3
    python3 "${TEST_DIR}/test_wifi.py" --ip 127.0.0.1 --port 18080 --timeout 15 > "$WIFI_RESULT_FILE" 2>&1 &
    WIFI_PID=$!
else
    echo "SKIP|WiFi测试|SKIP|用户跳过||||" > "$WIFI_RESULT_FILE"
    WIFI_PID=""
fi

# ============================================================
#  等待WiFi测试完成
# ============================================================
if [[ -n "$WIFI_PID" ]]; then
    log "等待WiFi测试完成 (PID: $WIFI_PID)..."
    wait "$WIFI_PID" 2>/dev/null || true
    log "WiFi测试完成"
fi
cleanup
MOCK_PID=""
check_timeout

# ============================================================
#  解析WiFi测试结果
# ============================================================
if [[ -f "$WIFI_RESULT_FILE" ]]; then
    while IFS='|' read -r id name status steps expected actual reason fix; do
        add_result "$id" "$name" "$status" "$steps" "$expected" "$actual" "$reason" "$fix"
    done < "$WIFI_RESULT_FILE"
fi

# ============================================================
#  T2-T3: BLE 蓝牙测试（WiFi测试完成后，关闭WiFi启用BLE）
# ============================================================
BLE_RESULT_FILE="${REPORT_DIR}/ble_result_$$.txt"
> "$BLE_RESULT_FILE"

if [[ "$SKIP_BLE" != true ]]; then
    if [[ "$DEVICE_MODE" == "wifi" ]]; then
        log "T2-T3: 关闭WiFi，启用BLE..."
        BLE_SWITCH=$(_timeout 15 python3 -m mpremote connect "$SERIAL_PORT" exec "
import network, time
ap = network.WLAN(network.AP_IF)
if ap.active():
    ap.active(False)
    time.sleep(1)
    print('WIFI_CLOSED')
else:
    print('WIFI_ALREADY_OFF')
" 2>&1 || true)
        if echo "$BLE_SWITCH" | grep -q "WIFI_CLOSED\|WIFI_ALREADY_OFF"; then
            log "WiFi已关闭，激活BLE..."
        else
            log "WiFi关闭可能失败: $(echo "$BLE_SWITCH" | head -2)"
        fi

        BLE_ACTIVATE=$(_timeout 30 python3 -m mpremote connect "$SERIAL_PORT" exec "
import network, time, gc
ap = network.WLAN(network.AP_IF)
if ap.active():
    ap.active(False)
    time.sleep(1)
try:
    import ble_service as _bm
    import config as _cfg
    _bm._global_meter = _bm.SimpleBLEPowerMeter(_cfg.DEVICE_NAME)
    _bm._global_meter.ble.config(gap_name=_cfg.DEVICE_NAME)
    _bm._global_meter.ble.gap_advertise(None)
    time.sleep_ms(500)
    _bm._global_meter._start_advertising()
    pwr_buf = bytearray(8)
    pwr_buf[0] = 0x20; pwr_buf[1] = 0x00
    pwr_buf[2] = _cfg.DEFAULT_POWER & 0xFF; pwr_buf[3] = (_cfg.DEFAULT_POWER >> 8) & 0xFF
    hr_buf = bytearray(2)
    hr_buf[0] = 0x00; hr_buf[1] = _cfg.DEFAULT_HEARTRATE
    _bm._global_meter.ble.gatts_write(_bm._global_meter.power_handle, pwr_buf)
    _bm._global_meter.ble.gatts_write(_bm._global_meter.hr_handle, hr_buf)
    gc.collect()
    time.sleep(2)
    print('BLE_METER_STARTED:', _bm._global_meter.ble.active(), 'GAP:', _bm._global_meter.ble.config('gap_name'))
except Exception as e:
    print('BLE_METER_ERROR:', e)
" 2>&1 || true)
        if echo "$BLE_ACTIVATE" | grep -q "BLE_METER_STARTED: True"; then
            log "BLE功率计已启动，等待广播..."
            sleep 3
        else
            log "BLE启动结果: $(echo "$BLE_ACTIVATE" | grep -E "BLE_METER|Error" | head -3)"
            sleep 3
        fi
    fi
    log "T2-T3: 启动BLE测试（后台异步）"
    python3 "${TEST_DIR}/test_ble.py" --port "$SERIAL_PORT" --timeout 20 > "$BLE_RESULT_FILE" 2>&1 &
    BLE_PID=$!
else
    echo "SKIP|BLE测试|SKIP|用户跳过||||" > "$BLE_RESULT_FILE"
    BLE_PID=""
fi

# ============================================================
#  等待BLE测试完成
# ============================================================
if [[ -n "$BLE_PID" ]]; then
    log "等待BLE测试完成 (PID: $BLE_PID)..."
    wait "$BLE_PID" 2>/dev/null || true
    log "BLE测试完成"
fi
check_timeout

# ============================================================
#  解析BLE测试结果
# ============================================================
if [[ -f "$BLE_RESULT_FILE" ]]; then
    while IFS='|' read -r id name status steps expected actual reason fix; do
        add_result "$id" "$name" "$status" "$steps" "$expected" "$actual" "$reason" "$fix"
    done < "$BLE_RESULT_FILE"
fi

check_timeout

# ============================================================
#  自修复重试（仅重试BLE相关失败项，WiFi需手动连接热点）
# ============================================================
BLE_FAIL_COUNT=0
if [[ -f "$BLE_RESULT_FILE" ]]; then
    BLE_FAIL_COUNT=$(grep -c "|FAIL|" "$BLE_RESULT_FILE" 2>/dev/null || true)
    BLE_FAIL_COUNT=${BLE_FAIL_COUNT:-0}
fi
WIFI_FAIL_COUNT=0
if [[ -f "$WIFI_RESULT_FILE" ]]; then
    WIFI_FAIL_COUNT=$(grep -c "|FAIL|" "$WIFI_RESULT_FILE" 2>/dev/null || true)
    WIFI_FAIL_COUNT=${WIFI_FAIL_COUNT:-0}
fi
RETRY_BLE=false

if [[ "$BLE_FAIL_COUNT" -gt 0 ]] && [[ "$MAX_RETRY" -gt 0 ]]; then
    RETRY_BLE=true
fi

if [[ "$RETRY_BLE" == true ]]; then
    warn "BLE存在 ${BLE_FAIL_COUNT} 项失败，尝试自修复重试..."
    if exit_deploy_mode; then
        log "已通过硬件重置恢复主程序，准备重试BLE测试"
        sleep 3
        > "$BLE_RESULT_FILE"
        python3 "${TEST_DIR}/test_ble.py" --port "$SERIAL_PORT" --timeout 15 > "$BLE_RESULT_FILE" 2>&1 &
        wait $! 2>/dev/null || true
        while IFS='|' read -r id name status steps expected actual reason fix; do
            add_result "${id}R" "${name}(重试)" "$status" "$steps" "$expected" "$actual" "$reason" "$fix"
        done < "$BLE_RESULT_FILE"
    else
        warn "BLE重试激活失败: 无法恢复主程序"
    fi
fi

# ============================================================
#  生成 HTML 测试报告
# ============================================================
log "生成测试报告"

REPORT_FILE="${REPORT_DIR}/report_$(date +%Y%m%d_%H%M%S).html"
TOTAL=$(awk 'NR%8==3' "$RESULT_FILE" 2>/dev/null | wc -l | tr -d ' \n')
PASSED=$(awk 'NR%8==3' "$RESULT_FILE" 2>/dev/null | grep -c "^PASS$" 2>/dev/null || true)
PASSED=$(echo "$PASSED" | tr -d ' \n')
FAILED=$(awk 'NR%8==3' "$RESULT_FILE" 2>/dev/null | grep -c "^FAIL$" 2>/dev/null || true)
FAILED=$(echo "$FAILED" | tr -d ' \n')
SKIPPED=$(awk 'NR%8==3' "$RESULT_FILE" 2>/dev/null | grep -c "^SKIP$" 2>/dev/null || true)
SKIPPED=$(echo "$SKIPPED" | tr -d ' \n')
ELAPSED=$(elapsed)

{
cat <<HDR
<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BikePower 测试报告</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"SF Pro Text","Helvetica Neue",sans-serif;background:#f0f2f5;color:#1a1a2e;padding:20px}
.container{max-width:1200px;margin:0 auto}
.header{background:linear-gradient(135deg,#2c3e50,#3498db);color:#fff;border-radius:12px;padding:20px 28px;display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;box-shadow:0 4px 15px rgba(52,152,219,.25)}
.header h1{font-size:20px;font-weight:600;white-space:nowrap}
.header-meta{font-size:13px;opacity:.85;text-align:right;line-height:1.6}
.stats{display:flex;gap:12px;margin-bottom:16px}
.stat{flex:1;background:#fff;border-radius:10px;padding:14px 16px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.stat .num{font-size:28px;font-weight:700;line-height:1}
.stat .label{font-size:12px;color:#888;margin-top:4px}
.stat.pass .num{color:#27ae60}.stat.fail .num{color:#e74c3c}.stat.skip .num{color:#f39c12}.stat.time .num{color:#3498db}
table{width:100%;border-collapse:separate;border-spacing:0;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.06);font-size:13px}
thead th{background:#2c3e50;color:#fff;padding:10px 10px;text-align:left;font-weight:600;font-size:12px;white-space:nowrap}
tbody td{padding:8px 10px;border-bottom:1px solid #f0f0f0;vertical-align:middle;line-height:1.5}
tbody tr:hover{background:#f8faff}
tbody tr:last-child td{border-bottom:none}
.col-id{width:52px;text-align:center;font-weight:600;color:#2c3e50}
.col-name{width:130px;font-weight:500;white-space:nowrap}
.col-status{width:60px;text-align:center}
.col-steps{min-width:160px;max-width:220px}
.col-expected{min-width:100px;max-width:160px}
.col-actual{min-width:100px;max-width:180px}
.col-reason{max-width:140px}
.col-fix{max-width:140px}
.badge{display:inline-block;padding:2px 10px;border-radius:10px;color:#fff;font-size:11px;font-weight:600;white-space:nowrap}
.b-pass{background:#27ae60}.b-fail{background:#e74c3c}.b-skip{background:#f39c12}
.cell-text{word-break:break-word;overflow-wrap:break-word}
.cell-text.short{white-space:nowrap}
.steps-text{color:#555;font-size:12px;line-height:1.5}
.expected-text{color:#2980b9;font-weight:500}
.actual-text{color:#27ae60;font-weight:500}
.reason-text{color:#e74c3c;font-weight:500}
.fix-text{color:#e67e22;font-style:italic}
.footer{text-align:center;color:#bbb;margin:20px 0;font-size:11px}
</style></head><body>
<div class="container">
<div class="header">
  <h1>🧪 BikePower 自动化测试报告</h1>
  <div class="header-meta">📅 $(date '+%Y-%m-%d %H:%M:%S')<br>🔌 ${SERIAL_PORT} &nbsp; ⏱️ ${ELAPSED}s</div>
</div>
<div class="stats">
  <div class="stat pass"><div class="num">${PASSED}</div><div class="label">通过</div></div>
  <div class="stat fail"><div class="num">${FAILED}</div><div class="label">失败</div></div>
  <div class="stat skip"><div class="num">${SKIPPED}</div><div class="label">跳过</div></div>
  <div class="stat time"><div class="num">${ELAPSED}s</div><div class="label">耗时</div></div>
</div>
<table>
<thead><tr>
<th class="col-id">编号</th><th class="col-name">测试项</th><th class="col-status">结果</th>
<th class="col-steps">操作步骤</th><th class="col-expected">预期结果</th><th class="col-actual">实际结果</th><th class="col-reason">失败原因</th><th class="col-fix">解决方案</th>
</tr></thead><tbody>
HDR

while IFS= read -r id && IFS= read -r name && IFS= read -r status && IFS= read -r steps && IFS= read -r expected && IFS= read -r actual && IFS= read -r reason && IFS= read -r fix; do
    STEPS=$(echo "$steps" | sed 's/\\n/<br>/g')

    case "$status" in
        PASS)  BC="b-pass"; BT="✅ 通过" ;;
        FAIL)  BC="b-fail"; BT="❌ 失败" ;;
        SKIP)  BC="b-skip"; BT="⏭️ 跳过" ;;
        *)     BC="b-skip"; BT="❓ 未知" ;;
    esac

    echo "<tr><td class=\"col-id\">${id}</td><td class=\"col-name\">${name}</td><td class=\"col-status\"><span class=\"badge ${BC}\">${BT}</span></td><td class=\"col-steps\"><div class=\"steps-text\">${STEPS}</div></td><td class=\"col-expected\"><div class=\"expected-text cell-text\">${expected}</div></td><td class=\"col-actual\"><div class=\"actual-text cell-text\">${actual}</div></td><td class=\"col-reason\"><div class=\"reason-text cell-text\">${reason}</div></td><td class=\"col-fix\"><div class=\"fix-text cell-text\">${fix}</div></td></tr>"
done < "$RESULT_FILE"

cat <<FTR
</tbody></table>
<div class="footer">总计 ${TOTAL} 项 · 通过 ${PASSED} · 失败 ${FAILED} · 跳过 ${SKIPPED} · 耗时 ${ELAPSED}s</div>
</div></body></html>
FTR
} > "$REPORT_FILE"

# 清理临时文件
rm -f "$BLE_RESULT_FILE" "$WIFI_RESULT_FILE"

log "报告: $REPORT_FILE"
[[ "$(uname)" == "Darwin" ]] && open "$REPORT_FILE" 2>/dev/null || true

echo ""
if [[ "$FAILED" -eq 0 ]]; then
    echo -e "\033[0;32m🎉 全部通过！(${PASSED}/${TOTAL}, ${ELAPSED}s)\033[0m"
else
    echo -e "\033[0;31m⚠️ ${FAILED}项失败 (${PASSED}/${TOTAL}通过, ${ELAPSED}s)\033[0m"
fi
echo ""
