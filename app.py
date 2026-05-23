"""
BikePower 蓝牙功率计 — 主程序入口
职责：初始化各模块、按钮事件检测与功率调整循环、LED 状态指示

硬件约束详见 .trae/rules/hardware_constraints.md

运行环境：MicroPython v1.28
"""

import gc
import time
from machine import Pin, WDT, reset
from micropython import const
import config
from logger import get_logger
from utils import start_thread
from ble_service import SimpleBLEPowerMeter
from power_data import PowerEngine
from wifi_manager import WiFiManager
from ota_updater import OTAUpdater

log = get_logger("MAIN")

LED_STATE_IDLE_NO_CONN = const(0)
LED_STATE_CONNECTED = const(1)
LED_STATE_CONFIRM_WAIT = const(2)
LED_STATE_WIFI_MODE = const(3)
LED_STATE_OTA_DOWNLOAD = const(4)

_BLINK_INTERVALS = {
    LED_STATE_IDLE_NO_CONN: config.LED_BLINK_SLOW_MS,
    LED_STATE_CONFIRM_WAIT: config.LED_BLINK_FAST_MS,
    LED_STATE_WIFI_MODE: config.LED_BLINK_WIFI_MS,
}


def _create_wifi_manager(power_engine, ble_meter, ota_updater, wifi_holder):
    """后台线程：异步创建 WiFiManager（不阻塞主循环）"""
    try:
        wifi_holder['mgr'] = WiFiManager(power_engine, ble_meter, ota_updater)
        log.info("WiFiManager 异步创建完成")
    except Exception as e:
        log.error("WiFiManager 创建失败: %s" % e)


def _async_save_config(power_engine):
    """后台线程：异步保存配置到文件"""
    try:
        power_engine.flush_if_dirty()
    except Exception as e:
        log.error("异步保存配置失败: %s" % e)


def _update_led(led, led_state, led_on, led_toggle_time, current_time, confirm_start_time, ble_paused, ble_meter, wifi_mgr):
    """
    LED 状态机：处理闪烁、状态切换、确认窗口超时

    Returns:
        tuple: (led_state, led_on, led_toggle_time, confirm_start_time, enter_wifi)
    """
    enter_wifi = False

    if led_state == LED_STATE_CONFIRM_WAIT:
        if time.ticks_diff(current_time, confirm_start_time) >= config.CONFIRM_WINDOW_MS:
            led_state = LED_STATE_IDLE_NO_CONN
            led.value(0)
            led_on = False
            log.info("确认窗口超时，取消进入配网模式")

    if led_state != LED_STATE_CONFIRM_WAIT:
        if ble_paused and wifi_mgr is not None and getattr(wifi_mgr, '_ota_downloading', False):
            new_led_state = LED_STATE_OTA_DOWNLOAD
        elif ble_paused:
            new_led_state = LED_STATE_WIFI_MODE
        elif ble_meter is not None and ble_meter.conn_count > 0:
            new_led_state = LED_STATE_CONNECTED
        else:
            new_led_state = LED_STATE_IDLE_NO_CONN
        if new_led_state != led_state:
            led_state = new_led_state
            if led_state == LED_STATE_CONNECTED:
                led.value(1)
                led_on = True
            elif led_state == LED_STATE_WIFI_MODE:
                led.value(0)
                led_on = False
                led_toggle_time = current_time

    interval = _BLINK_INTERVALS.get(led_state)
    if led_state == LED_STATE_OTA_DOWNLOAD:
        phase = time.ticks_diff(current_time, led_toggle_time) % 1000
        should_on = phase < 100 or (200 <= phase < 300)
        if should_on != led_on:
            led_on = should_on
            led.value(1 if led_on else 0)
    elif interval is not None:
        if time.ticks_diff(current_time, led_toggle_time) >= interval:
            led_on = not led_on
            led.value(1 if led_on else 0)
            led_toggle_time = current_time

    return led_state, led_on, led_toggle_time, confirm_start_time, enter_wifi


def _handle_button(btn, current_time, btn_press_time, last_btn_state, led_state, confirm_start_time, led_toggle_time, led_on, led, wifi_mgr, power_engine):
    """
    按钮事件检测：按下/释放判断、功率调整、确认窗口管理

    Returns:
        tuple: (led_state, led_on, led_toggle_time, confirm_start_time, btn_press_time, last_btn_state, enter_wifi)
    """
    enter_wifi = False
    btn_state = btn.value()

    if btn_state == 0 and last_btn_state == 1:
        btn_press_time = current_time

        if led_state == LED_STATE_CONFIRM_WAIT:
            if wifi_mgr is not None:
                led.value(0)
                led_on = False
                led_state = LED_STATE_WIFI_MODE
                led_toggle_time = current_time
                confirm_start_time = 0
                enter_wifi = True
                log.info("二次确认，进入WiFi配网模式")
            else:
                log.warning("WiFiManager 尚未就绪，请稍后重试")
                led_state = LED_STATE_IDLE_NO_CONN
                confirm_start_time = 0
            btn_press_time = 0
            last_btn_state = btn_state
            return led_state, led_on, led_toggle_time, confirm_start_time, btn_press_time, last_btn_state, enter_wifi

    if btn_state == 1 and last_btn_state == 0 and btn_press_time > 0:
        press_duration = time.ticks_diff(current_time, btn_press_time)

        if press_duration >= config.WIFI_BTN_HOLD_MS:
            led_state = LED_STATE_CONFIRM_WAIT
            confirm_start_time = current_time
            led_toggle_time = current_time
            led_on = True
            led.value(1)
            log.info("长按2秒，LED快闪等待二次确认...")
        elif press_duration >= config.SHORT_PRESS_MS:
            power_engine.adjust_power(10)
        else:
            power_engine.adjust_power(-10)

        btn_press_time = 0

    last_btn_state = btn_state
    return led_state, led_on, led_toggle_time, confirm_start_time, btn_press_time, last_btn_state, enter_wifi


def main():
    """主程序入口：初始化各模块，进入按钮事件循环

    按钮操作（释放时判断）：
      - 短按(<300ms): 功率-10W
      - 中按(300ms~2s): 功率+10W
      - 长按(>=2s): 进入二次确认窗口（LED快闪3秒）
        - 确认窗口内再按一次: 进入WiFi配网模式（关闭蓝牙）
        - 确认窗口超时: 取消，恢复正常
    """
    power_engine = PowerEngine()

    ble_meter = None
    try:
        ble_meter = SimpleBLEPowerMeter(config.DEVICE_NAME)
        ble_meter.set_erg_callback(power_engine.set_erg_target)
    except OSError as e:
        log.warning("BLE初始化失败，重启设备恢复: %s" % e)
        time.sleep_ms(1000)
        reset()

    ota_updater = OTAUpdater()

    wifi_holder = {'mgr': None}
    start_thread(_create_wifi_manager, (power_engine, ble_meter, ota_updater, wifi_holder))

    gc.collect()
    gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())
    log.info("内存: free=%d alloc=%d" % (gc.mem_free(), gc.mem_alloc()))

    btn = Pin(config.BTN_PIN, Pin.IN, Pin.PULL_UP)
    led = Pin(config.LED_PIN, Pin.OUT)
    led.value(0)

    last_btn_state = 1
    btn_press_time = 0
    loop_count = 0

    led_state = LED_STATE_IDLE_NO_CONN
    led_toggle_time = 0
    led_on = False

    confirm_start_time = 0

    wdt = WDT(timeout=config.WDT_TIMEOUT_MS)

    log.info("主循环已启动，等待按钮操作...")

    while True:
        current_time = time.ticks_ms()
        wifi_mgr = wifi_holder['mgr']
        ble_paused = wifi_mgr is not None and wifi_mgr.ble_disabled

        if ble_meter is not None and not ble_paused:
            try:
                snapshot = power_engine.get_snapshot(current_time)
                ble_meter.update_data(snapshot['power'], snapshot['heartrate'], snapshot['cadence'])
            except Exception as e:
                log.error("BLE通知异常: %s" % e)

        led_state, led_on, led_toggle_time, confirm_start_time, _ = _update_led(
            led, led_state, led_on, led_toggle_time, current_time,
            confirm_start_time, ble_paused, ble_meter, wifi_mgr
        )

        led_state, led_on, led_toggle_time, confirm_start_time, btn_press_time, last_btn_state, enter_wifi = _handle_button(
            btn, current_time, btn_press_time, last_btn_state,
            led_state, confirm_start_time, led_toggle_time, led_on,
            led, wifi_mgr, power_engine
        )

        if enter_wifi and wifi_mgr is not None:
            wifi_mgr.start()

        loop_count += 1
        if loop_count % 200 == 0:
            gc.collect()
            if power_engine._dirty:
                start_thread(_async_save_config, (power_engine,))
        wdt.feed()
        time.sleep_ms(50)


if __name__ == "__main__":
    main()
