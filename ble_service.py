"""
BLE 蓝牙功率计模块
职责：蓝牙广播、设备连接/断开管理、5 服务 GATT 通知、ERG 模式功率目标接收、停用/恢复

运行环境：MicroPython v1.28
"""

import time
import bluetooth
import config
from logger import get_logger
from event_bus import bus, EVENT_BLE_CONNECTED, EVENT_BLE_DISCONNECTED

log = get_logger("BLE")

_IRQ_GATTS_WRITE = const(3)


class SimpleBLEPowerMeter:
    """BLE 5 服务广播器：Cycling Power + Heart Rate + CSC + FTMS + Device Information"""

    def __init__(self, device_name):
        """
        初始化蓝牙功率计

        Args:
            device_name: BLE 广播设备名称
        """
        log.info("初始化蓝牙功率计...")
        self.device_name = device_name

        self.crank_revolutions = 0
        self.last_crank_time = 0
        self.last_rev_count = 0
        self.last_time_stamp = 0

        self._power_buf = bytearray(8)
        self._hr_buf = bytearray(2)
        self._csc_buf = bytearray(5)
        self._ftms_feature_buf = bytearray(8)
        self._ftms_power_buf = bytearray(2)
        self._ftms_status_buf = bytearray(7)
        self._failed_conns = bytearray(config.MAX_CONNECTIONS)

        self._last_notify_time = 0
        self._min_notify_interval = config.BLE_NOTIFY_INTERVAL
        self._conn_notify_times = {}

        self.erg_target_power = None
        self._on_erg_target = None

        self._init_ftms_feature()
        self._init_ftms_status()

        self._adv_data = self._build_adv_data(device_name)

        try:
            self.ble = bluetooth.BLE()
            log.info("蓝牙对象创建成功")

            ble_activated = False
            for attempt in range(3):
                try:
                    self.ble.active(False)
                    time.sleep_ms(200)
                    self.ble.active(True)
                    ble_activated = True
                    log.info("蓝牙激活成功")
                    break
                except OSError as e:
                    log.warning("蓝牙激活重试 %d/3: %s" % (attempt + 1, e))
                    time.sleep_ms(500)

            if not ble_activated:
                raise OSError("BLE硬件未就绪，请断电重启设备")

            try:
                self.ble.config(gap_name=self.device_name)
                self.ble.config(mtu=69)
                log.info("GAP名称已设置: %s, MTU=69" % self.device_name)
            except (AttributeError, OSError) as e:
                log.warning("GAP名称设置失败(将使用广播包名称): %s" % e)

            self.ble.irq(self._irq)
            log.info("中断处理函数设置成功")

            self.connections = []
            self.conn_count = 0

            self._register_services()
            self._start_advertising()

            log.info("蓝牙功率计已启动，设备名称: %s" % device_name)
            log.info("最大连接数: %d, 服务: CPS+HRS+CSCS+FTMS+DIS" % config.MAX_CONNECTIONS)
        except Exception as e:
            log.error("蓝牙初始化失败: %s，3秒后重启设备" % e)
            time.sleep(3)
            machine.reset()

    def _init_ftms_feature(self):
        """初始化 FTMS Feature 特征值（支持功率控制 + ERG 模式）"""
        self._ftms_feature_buf[0] = 0x04
        self._ftms_feature_buf[1] = 0x00
        self._ftms_feature_buf[2] = 0x00
        self._ftms_feature_buf[3] = 0x00
        self._ftms_feature_buf[4] = 0x08
        self._ftms_feature_buf[5] = 0x00
        self._ftms_feature_buf[6] = 0x00
        self._ftms_feature_buf[7] = 0x00

    def _init_ftms_status(self):
        """初始化 FTMS Status 特征值（空闲状态）"""
        self._ftms_status_buf[0] = 0x00
        for i in range(1, 7):
            self._ftms_status_buf[i] = 0x00

    def set_erg_callback(self, callback):
        """
        设置 ERG 功率目标回调函数

        Args:
            callback: 回调函数，接收功率目标值 (int)，返回 None
        """
        self._on_erg_target = callback

    def _irq(self, event, data):
        """BLE 中断回调，处理连接/断开/写入事件"""
        if event == config.IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            if len(self.connections) < config.MAX_CONNECTIONS:
                self.connections.append(conn_handle)
                self.conn_count = len(self.connections)
                self._conn_notify_times[conn_handle] = 0
                role = "主连接" if len(self.connections) == 1 else "从连接"
                log.info("设备已连接: %d(%s), 当前连接数: %d" % (conn_handle, role, len(self.connections)))
                bus.publish(EVENT_BLE_CONNECTED, conn_handle=conn_handle, role=role, count=len(self.connections))
            else:
                log.warning("连接数已达上限(%d)，拒绝: %d" % (config.MAX_CONNECTIONS, conn_handle))
                try:
                    self.ble.gap_disconnect(conn_handle)
                except OSError:
                    pass
        elif event == config.IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            if conn_handle in self.connections:
                self.connections.remove(conn_handle)
                self.conn_count = len(self.connections)
            if conn_handle in self._conn_notify_times:
                del self._conn_notify_times[conn_handle]
            log.info("设备已断开: %d, 当前连接数: %d" % (conn_handle, len(self.connections)))
            bus.publish(EVENT_BLE_DISCONNECTED, conn_handle=conn_handle, count=len(self.connections))
            self._start_advertising()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            self._handle_write(conn_handle, value_handle)

    def _handle_write(self, conn_handle, value_handle):
        """
        处理 GATT 写入事件（FTMS 控制点）

        Args:
            conn_handle: 连接句柄
            value_handle: 特征值句柄
        """
        if not hasattr(self, 'ftms_control_handle'):
            return
        if value_handle != self.ftms_control_handle:
            return
        try:
            value = self.ble.gatts_read(value_handle)
            if len(value) < 1:
                return
            op_code = value[0]
            if op_code == 0x00 and len(value) >= 3:
                self._handle_set_target_power(value)
            elif op_code == 0x01:
                self._handle_ftms_start()
            elif op_code == 0x02:
                self._handle_ftms_stop()
            elif op_code == 0x04:
                self._handle_ftms_reset()
        except Exception as e:
            log.error("FTMS写入处理失败: %s" % e)

    def _handle_set_target_power(self, value):
        """
        处理 FTMS 设置目标功率请求

        Args:
            value: 写入的原始字节数据
        """
        target = value[1] | (value[2] << 8)
        self.erg_target_power = target
        log.info("ERG目标功率: %dW" % target)
        if self._on_erg_target is not None:
            try:
                self._on_erg_target(target)
            except Exception as e:
                log.error("ERG回调异常: %s" % e)
        self._send_ftms_response(0x80, 0x01, 0x01)

    def _handle_ftms_start(self):
        """处理 FTMS 开始训练请求"""
        self._ftms_status_buf[0] = 0x01
        self._send_ftms_response(0x80, 0x02, 0x01)
        log.info("FTMS训练已开始")

    def _handle_ftms_stop(self):
        """处理 FTMS 停止训练请求"""
        self._ftms_status_buf[0] = 0x02
        self._send_ftms_response(0x80, 0x02, 0x02)
        log.info("FTMS训练已停止")

    def _handle_ftms_reset(self):
        """处理 FTMS 重置请求"""
        self.erg_target_power = None
        self._ftms_status_buf[0] = 0x00
        self._send_ftms_response(0x80, 0x02, 0x04)
        log.info("FTMS已重置")

    def _send_ftms_response(self, op_code, request_op, result):
        """
        发送 FTMS 控制点响应

        Args:
            op_code: 响应操作码
            request_op: 请求操作码
            result: 结果代码
        """
        if not self.connections:
            return
        resp = bytearray([op_code, request_op, result])
        try:
            self.ble.gatts_write(self.ftms_control_handle, resp)
            for conn_handle in self.connections:
                try:
                    self.ble.gatts_notify(conn_handle, self.ftms_control_handle)
                except OSError:
                    pass
        except Exception as e:
            log.error("FTMS响应发送失败: %s" % e)

    def _register_services(self):
        """注册 5 个 GATT 服务：CPS + HRS + CSCS + FTMS + DIS"""
        services = [
            (bluetooth.UUID(config.POWER_SERVICE_UUID),
             [(bluetooth.UUID(config.POWER_CHAR_UUID), bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY)]),
            (bluetooth.UUID(config.HR_SERVICE_UUID),
             [(bluetooth.UUID(config.HR_CHAR_UUID), bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY)]),
            (bluetooth.UUID(config.CSC_SERVICE_UUID),
             [(bluetooth.UUID(config.CSC_CHAR_UUID), bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY)]),
            (bluetooth.UUID(config.FTMS_SERVICE_UUID),
             [(bluetooth.UUID(config.FTMS_FEATURE_CHAR_UUID), bluetooth.FLAG_READ),
              (bluetooth.UUID(config.FTMS_CONTROL_POINT_CHAR_UUID), bluetooth.FLAG_WRITE | bluetooth.FLAG_WRITE_NO_RESPONSE | bluetooth.FLAG_NOTIFY),
              (bluetooth.UUID(config.FTMS_POWER_CHAR_UUID), bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY),
              (bluetooth.UUID(config.FTMS_STATUS_CHAR_UUID), bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY)]),
            (bluetooth.UUID(config.DIS_SERVICE_UUID),
             [(bluetooth.UUID(config.DIS_MANUFACTURER_CHAR_UUID), bluetooth.FLAG_READ),
              (bluetooth.UUID(config.DIS_MODEL_CHAR_UUID), bluetooth.FLAG_READ),
              (bluetooth.UUID(config.DIS_FIRMWARE_CHAR_UUID), bluetooth.FLAG_READ)])
        ]
        try:
            handles = self.ble.gatts_register_services(services)
            (self.power_handle,) = handles[0]
            (self.hr_handle,) = handles[1]
            (self.csc_handle,) = handles[2]
            self.ftms_feature_handle = handles[3][0]
            self.ftms_control_handle = handles[3][1]
            self.ftms_power_handle = handles[3][2]
            self.ftms_status_handle = handles[3][3]
            self.dis_manufacturer_handle = handles[4][0]
            self.dis_model_handle = handles[4][1]
            self.dis_firmware_handle = handles[4][2]
            self._init_dis_values()
            self._init_ftms_values()
            log.info("5服务注册成功: CPS+HRS+CSCS+FTMS+DIS")
        except Exception as e:
            log.error("服务注册失败: %s" % e)
            raise

    def _init_dis_values(self):
        """写入 Device Information Service 静态特征值"""
        try:
            manufacturer = config.DEVICE_MANUFACTURER.encode('utf-8')
            model = config.DEVICE_MODEL.encode('utf-8')
            firmware = config.FIRMWARE_VERSION.encode('utf-8')
            self.ble.gatts_write(self.dis_manufacturer_handle, manufacturer)
            self.ble.gatts_write(self.dis_model_handle, model)
            self.ble.gatts_write(self.dis_firmware_handle, firmware)
        except Exception as e:
            log.warning("DIS特征值写入失败: %s" % e)

    def _init_ftms_values(self):
        """写入 FTMS 静态特征值"""
        try:
            self.ble.gatts_write(self.ftms_feature_handle, self._ftms_feature_buf)
            self.ble.gatts_write(self.ftms_status_handle, self._ftms_status_buf)
        except Exception as e:
            log.warning("FTMS特征值写入失败: %s" % e)

    def _build_adv_data(self, name):
        """构造 BLE 广播包数据（含 5 个服务 UUID）"""
        adv_data = bytearray()
        adv_data += bytes([0x02, 0x01, 0x06])
        name_encoded = name.encode()
        name_length = min(len(name_encoded), 22)
        if len(name_encoded) > 22:
            name_encoded = name_encoded[:22]
        adv_data += bytes([name_length + 1, 0x09]) + name_encoded
        adv_data += bytes([0x05, 0x03, 0x18, 0x18, 0x0D, 0x18])
        return adv_data

    def _start_advertising(self):
        """开始 BLE 广播（使用预构建广播包）"""
        try:
            self.ble.gap_advertise(config.BLE_ADVERTISING_INTERVAL, self._adv_data, connectable=True)
            try:
                self.ble.gap_connect_params(
                    min_conn_interval=20, max_conn_interval=40,
                    latency=0, supervision_timeout=400
                )
            except (AttributeError, OSError):
                pass
            log.info("开始广播... (间隔%dms)" % config.BLE_ADVERTISING_INTERVAL)
        except Exception as e:
            log.error("广播失败: %s" % e)

    def update_data(self, power, heartrate, cadence):
        """
        将功率/心率/踏频写入 GATT 特征值并按优先级通知已连接设备

        主连接（第一个）1s 间隔，从连接 2s 间隔

        Args:
            power: 功率值 (W)
            heartrate: 心率值 (BPM)
            cadence: 踏频值 (RPM)
        """
        current_time = time.ticks_ms()

        if time.ticks_diff(current_time, self._last_notify_time) < self._min_notify_interval:
            return
        self._last_notify_time = current_time

        power = max(config.POWER_MIN, min(power, config.POWER_MAX))
        heartrate = max(config.HR_MIN, min(heartrate, config.HR_MAX))
        cadence = max(1, min(cadence, config.CADENCE_MAX))

        if self.last_crank_time == 0:
            time_diff = 1000
        else:
            time_diff = time.ticks_diff(current_time, self.last_crank_time)

        rev_increment = 2
        target_time_diff = (rev_increment * 60 * 1000) / cadence

        self.crank_revolutions += rev_increment
        current_rev_count = self.crank_revolutions % 65536

        if self.last_crank_time == 0:
            adjusted_time = current_time
        else:
            adjusted_time = int(self.last_crank_time + target_time_diff)

        current_time_1024 = int(adjusted_time * 1024 / 1000) % 65536

        flags = 0x0020
        self._power_buf[0] = flags & 0xFF
        self._power_buf[1] = (flags >> 8) & 0xFF
        self._power_buf[2] = power & 0xFF
        self._power_buf[3] = (power >> 8) & 0xFF
        self._power_buf[4] = current_rev_count & 0xFF
        self._power_buf[5] = (current_rev_count >> 8) & 0xFF
        self._power_buf[6] = current_time_1024 & 0xFF
        self._power_buf[7] = (current_time_1024 >> 8) & 0xFF

        self.last_rev_count = current_rev_count
        self.last_time_stamp = current_time_1024
        self.last_crank_time = adjusted_time

        self._hr_buf[0] = 0x00
        self._hr_buf[1] = heartrate

        csc_flags = 0x02
        self._csc_buf[0] = csc_flags
        self._csc_buf[1] = current_rev_count & 0xFF
        self._csc_buf[2] = (current_rev_count >> 8) & 0xFF
        self._csc_buf[3] = current_time_1024 & 0xFF
        self._csc_buf[4] = (current_time_1024 >> 8) & 0xFF

        self._ftms_power_buf[0] = power & 0xFF
        self._ftms_power_buf[1] = (power >> 8) & 0xFF

        if not self.connections:
            return

        try:
            self.ble.gatts_write(self.power_handle, self._power_buf)
            self.ble.gatts_write(self.hr_handle, self._hr_buf)
            self.ble.gatts_write(self.csc_handle, self._csc_buf)
            self.ble.gatts_write(self.ftms_power_handle, self._ftms_power_buf)
        except Exception as e:
            log.error("写入特征值失败: %s" % e)
            return

        failed_count = 0
        for idx, conn_handle in enumerate(self.connections):
            is_primary = (idx == 0)
            interval = config.BLE_NOTIFY_INTERVAL_PRIMARY if is_primary else config.BLE_NOTIFY_INTERVAL_SECONDARY
            last_time = self._conn_notify_times.get(conn_handle, 0)
            if time.ticks_diff(current_time, last_time) < interval:
                continue
            self._conn_notify_times[conn_handle] = current_time
            try:
                self.ble.gatts_notify(conn_handle, self.power_handle)
                self.ble.gatts_notify(conn_handle, self.hr_handle)
                self.ble.gatts_notify(conn_handle, self.csc_handle)
                self.ble.gatts_notify(conn_handle, self.ftms_power_handle)
            except Exception as e:
                log.warning("通知发送失败(conn=%d): %s" % (conn_handle, e))
                if failed_count < len(self._failed_conns):
                    self._failed_conns[failed_count] = conn_handle
                failed_count += 1

        for i in range(failed_count):
            if i < len(self._failed_conns):
                conn_handle = self._failed_conns[i]
                if conn_handle in self.connections:
                    self.connections.remove(conn_handle)
                    if conn_handle in self._conn_notify_times:
                        del self._conn_notify_times[conn_handle]
                    log.info("已移除失效连接: %d" % conn_handle)

    def deactivate(self):
        """
        停用蓝牙，释放资源供WiFi使用

        Returns:
            bool: 是否成功停用
        """
        try:
            self.ble.gap_advertise(None)
            log.info("已停止蓝牙广播")
            for conn_handle in list(self.connections):
                try:
                    self.ble.gap_disconnect(conn_handle)
                except OSError:
                    pass
            self.connections.clear()
            self._conn_notify_times.clear()
            self.conn_count = 0
            time.sleep_ms(200)
            self.ble.active(False)
            log.info("蓝牙已停用")
            return True
        except Exception as e:
            log.error("蓝牙停用失败: %s" % e)
            return False
