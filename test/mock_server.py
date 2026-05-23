"""
ESP32 本地 Mock 环境
模拟 bluetooth / network / machine / micropython 模块，
在 macOS 上启动 Web 服务器测试配网流程

用法: python3 mock_server.py
访问: http://localhost:8080
"""

import sys
import os
import types
import time as _real_time
import socket as _real_socket
import threading as _real_threading
import random as _random

# 强制 stdout 无缓冲
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

# ============================================================
#  Mock 模块注入
# ============================================================

class _MockBLE:
    FLAG_READ = 2
    FLAG_NOTIFY = 16

    def __init__(self):
        self._active = False
        self._irq_cb = None
        self._advertising = False

    def active(self, val=None):
        if val is not None:
            self._active = val
            print(f"[Mock] BLE.active({val})")
        return self._active

    def irq(self, cb):
        self._irq_cb = cb
        print("[Mock] BLE.irq() 已设置")

    def gap_advertise(self, interval, adv_data=None, connectable=None):
        self._advertising = adv_data is not None
        if adv_data is not None:
            print(f"[Mock] BLE 开始广播, 数据长度={len(adv_data)}")
        else:
            print("[Mock] BLE 停止广播")

    def gap_disconnect(self, handle):
        print(f"[Mock] BLE 断开连接: {handle}")

    def gap_connect_params(self, **kw):
        pass

    def gatts_register_services(self, services):
        print(f"[Mock] BLE 注册 {len(services)} 个服务")
        return ((99,), (100,))

    def gatts_write(self, handle, data):
        pass

    def gatts_notify(self, handle, char_handle):
        pass

    def config(self, **kw):
        if 'gap_name' in kw:
            print(f"[Mock] BLE.config(gap_name={kw['gap_name']})")
        return kw.get('gap_name', 'BikePower')


class _MockBluetooth:
    UUID = type('UUID', (), {'__init__': lambda self, v: setattr(self, 'val', v)})
    BLE = _MockBLE
    FLAG_READ = 2
    FLAG_NOTIFY = 16


class _MockWLAN:
    AP_IF = 1
    STA_IF = 0
    AUTH_OPEN = 0

    _MOCK_NETWORKS = [
        (b"HomeWiFi-5G", b"xx:xx:xx:xx:xx:01", 1, -35, 3, False),
        (b"HomeWiFi-2.4G", b"xx:xx:xx:xx:xx:02", 1, -42, 3, False),
        (b"Office-Network", b"xx:xx:xx:xx:xx:03", 6, -55, 4, False),
        (b"StarBucks-Free", b"xx:xx:xx:xx:xx:04", 11, -62, 0, False),
        (b"Neighbor_5F", b"xx:xx:xx:xx:xx:05", 6, -68, 3, False),
        (b"TP-LINK_A8F2", b"xx:xx:xx:xx:xx:06", 1, -71, 3, False),
        (b"ChinaNet-Kx8m", b"xx:xx:xx:xx:xx:07", 11, -75, 4, False),
        (b"Guest-WiFi", b"xx:xx:xx:xx:xx:08", 6, -78, 0, False),
        (b"HUAWEI-B2E3", b"xx:xx:xx:xx:xx:09", 1, -82, 3, False),
        (b"Mi-Router", b"xx:xx:xx:xx:xx:0a", 11, -85, 3, False),
        (b"WeakSignal", b"xx:xx:xx:xx:xx:0b", 6, -90, 3, False),
    ]

    def __init__(self, if_id):
        self._if_id = if_id
        self._active = False
        self._connected = False
        self._ssid = ""
        self._password = ""
        self._ap_config = ("192.168.4.1", "255.255.255.0", "192.168.4.1", "8.8.8.8")
        self._essid = ""

    def active(self, val=None):
        if val is not None:
            self._active = val
            mode = "AP" if self._if_id == 1 else "STA"
            print(f"[Mock] WLAN({mode}).active({val})")
        return self._active

    def config(self, **kw):
        if "essid" in kw:
            self._essid = kw["essid"]
            print(f"[Mock] AP ESSID={kw['essid']}")
        if "authmode" in kw:
            print(f"[Mock] AP authmode={kw['authmode']}")

    def ifconfig(self, config=None):
        if config is not None:
            self._ap_config = config
            print(f"[Mock] AP ifconfig={config}")
        if self._if_id == 1:
            return self._ap_config
        if self._connected:
            return ("192.168.1.42", "255.255.255.0", "192.168.1.1", "8.8.8.8")
        return ("0.0.0.0", "0.0.0.0", "0.0.0.0", "0.0.0.0")

    def scan(self):
        print(f"[Mock] WiFi 扫描，返回 {len(self._MOCK_NETWORKS)} 个网络")
        return self._MOCK_NETWORKS

    def connect(self, ssid, password=""):
        self._ssid = ssid
        self._password = password
        print(f"[Mock] STA 连接: ssid={ssid}, password={'*' * len(password) if password else '(空)'}")

        def _do_connect():
            _real_time.sleep(1.5)
            if password and len(password) >= 4:
                self._connected = True
                print(f"[Mock] STA 连接成功: {ssid}")
            else:
                self._connected = False
                print(f"[Mock] STA 连接失败: 密码错误或为空")

        _real_threading.Thread(target=_do_connect, daemon=True).start()

    def disconnect(self):
        self._connected = False
        print("[Mock] STA 断开连接")

    def isconnected(self):
        return self._connected


class _MockNetwork:
    AP_IF = 1
    STA_IF = 0
    AUTH_OPEN = 0
    WLAN = _MockWLAN


class _MockPin:
    IN = 1
    PULL_UP = 1

    def __init__(self, id, mode=-1, pull=-1):
        self._id = id
        print(f"[Mock] Pin({id}) 初始化")

    def value(self, val=None):
        return 1


class _MockWDT:
    def __init__(self, timeout=5000):
        self._timeout = timeout

    def feed(self):
        pass


class _MockMachine:
    Pin = _MockPin
    WDT = _MockWDT

    @staticmethod
    def freq(hz=None):
        return 160000000

    @staticmethod
    def reset():
        print("[Mock] machine.reset()")


class _MockMicropython:
    @staticmethod
    def const(x):
        return x

    @staticmethod
    def mem_free():
        return 80000

    @staticmethod
    def mem_alloc():
        return 50000


# 注入 Mock 模块到 sys.modules
sys.modules['bluetooth'] = _MockBluetooth()
sys.modules['network'] = _MockNetwork()

_machine_mod = types.ModuleType('machine')
_machine_mod.Pin = _MockPin
_machine_mod.WDT = _MockWDT
_machine_mod.freq = _MockMachine.freq
_machine_mod.reset = _MockMachine.reset
sys.modules['machine'] = _machine_mod

_mp_mod = types.ModuleType('micropython')
_mp_mod.const = lambda x: x
_mp_mod.mem_free = lambda: 80000
_mp_mod.mem_alloc = lambda: 50000
_mp_mod.__path__ = []
_mp_mod.__package__ = 'micropython'
_mp_mod.__spec__ = None
_mp_mod.__loader__ = None
sys.modules['micropython'] = _mp_mod

# Mock _thread.start_new_thread -> 使用 threading
import _thread as _real_thread_mod

def _mock_start_new_thread(func, args=()):
    _real_threading.Thread(target=func, args=args, daemon=True).start()

_real_thread_mod.start_new_thread = _mock_start_new_thread
_real_thread_mod.stack_size = lambda size=None: 0

# Mock time.sleep_ms
import time as _time
_original_sleep = _time.sleep

def _sleep_ms(ms):
    _original_sleep(ms / 1000.0)

_time.sleep_ms = _sleep_ms

# Mock time.ticks_ms / ticks_diff
_ticks_origin = _real_time.time() * 1000

def _ticks_ms():
    return int(_real_time.time() * 1000 - _ticks_origin)

def _ticks_diff(t1, t2):
    return t1 - t2

_time.ticks_ms = _ticks_ms
_time.ticks_diff = _ticks_diff

# ============================================================
#  导入实际代码
# ============================================================

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

for mod in list(sys.modules.keys()):
    if mod.startswith('app') or mod in ('ble_service', 'power_data', 'wifi_manager', 'logger', 'config', 'micropython', 'machine'):
        del sys.modules[mod]

sys.modules['micropython'] = _mp_mod
sys.modules['machine'] = _machine_mod

from ble_service import SimpleBLEPowerMeter
from power_data import PowerEngine
from wifi_manager import WiFiManager

# ============================================================
#  启动本地 Mock 服务器
# ============================================================

def main():
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    print("=" * 50)
    print("  ESP32 一键配网 Mock 测试环境")
    print(f"  访问: http://localhost:{port}")
    print("=" * 50)
    print()

    power_engine = PowerEngine()
    ble_meter = SimpleBLEPowerMeter("BikePower")

    wifi_mgr = WiFiManager(power_engine, ble_meter)

    # 替换 socket 绑定地址为 localhost:8080
    original_start = wifi_mgr.start

    def mock_start():
        try:
            if wifi_mgr.ble_meter and not wifi_mgr.ble_disabled:
                wifi_mgr.ble_meter.deactivate()
                wifi_mgr.ble_disabled = True
                print("已关闭BLE（Mock）", flush=True)

            import gc; gc.collect()

            wifi_mgr.wlan = _MockWLAN(_MockNetwork.AP_IF)
            wifi_mgr.wlan.active(False)
            _time.sleep(0.1)
            wifi_mgr.wlan.active(True)
            wifi_mgr.wlan.config(essid="BikePower", authmode=0)
            _time.sleep(0.1)
            wifi_mgr.wlan.ifconfig(("192.168.4.1", "255.255.255.0", "192.168.4.1", "8.8.8.8"))

            wifi_mgr.server = _real_socket.socket(_real_socket.AF_INET, _real_socket.SOCK_STREAM)
            wifi_mgr.server.setsockopt(_real_socket.SOL_SOCKET, _real_socket.SO_REUSEADDR, 1)
            wifi_mgr.server.bind(("127.0.0.1", port))
            wifi_mgr.server.listen(3)
            print(f"Mock Web 服务器已启动，监听 http://localhost:{port}", flush=True)

            wifi_mgr._start_time = _time.ticks_ms()

            _real_threading.Thread(target=wifi_mgr._server_thread, daemon=True).start()
            print(f"Mock WiFi自动关闭计时器已禁用(测试模式)", flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Mock 启动失败: {e}", flush=True)

    wifi_mgr.start = mock_start

    original_shutdown = wifi_mgr._shutdown_wifi
    def mock_shutdown():
        print("[Mock] WiFi关闭已拦截(测试模式，保持服务器运行)", flush=True)
        wifi_mgr._wifi_close_event = True
    wifi_mgr._shutdown_wifi = mock_shutdown

    wifi_mgr.start()

    # 保持主线程运行
    try:
        while True:
            _time.sleep(1)
    except KeyboardInterrupt:
        print("\nMock 服务器已停止")


if __name__ == "__main__":
    main()
