"""
WiFi 配置管理模块
职责：AP热点创建、Web服务器、一键配网、表单参数解析、自动关闭、WiFi/蓝牙互斥

运行环境：MicroPython v1.28
"""

import gc
import machine
import time
import socket
import network
from micropython import const
import config
from logger import get_logger
from utils import start_thread, DEFAULT_STACK
from ota_updater import get_firmware_version
from event_bus import bus, EVENT_WIFI_START, EVENT_OTA_STATUS

log = get_logger("WIFI")

HTTP_RECV_CHUNK = const(512)
HTTP_REQUEST_MAX = const(4096)


class WiFiManager:
    """WiFi AP 热点 + Web 配置页面，支持一键配网，提交后自动关闭"""

    def __init__(self, power_engine, ble_meter=None, ota_updater=None):
        """
        初始化 WiFi 管理器

        Args:
            power_engine: PowerEngine 实例，用于读写配置
            ble_meter: SimpleBLEPowerMeter 实例，用于蓝牙互斥管理
            ota_updater: OTAUpdater 实例，用于固件更新
        """
        self.power_engine = power_engine
        self.ble_meter = ble_meter
        self.ota_updater = ota_updater
        self.wlan = None
        self.sta_if = None
        self.server = None
        self._wifi_close_event = False
        self._start_time = 0
        self._submitted = False
        self.ble_disabled = False
        self._wifi_configured = False
        self._connect_result = None
        self._scan_result = None
        self._ota_check_result = None
        self._ota_downloading = False
        self._config_cache = None

    def _get_sta_if(self):
        """
        延迟创建 STA 接口，避免 BLE 运行时内存不足

        Returns:
            WLAN: STA 接口实例
        """
        if self.sta_if is None:
            self.sta_if = network.WLAN(network.STA_IF)
        return self.sta_if

    @staticmethod
    def _url_decode(s):
        """
        解码 URL 编码字符串

        Args:
            s: URL 编码的字符串

        Returns:
            str: 解码后的字符串
        """
        s = s.replace('+', ' ')
        parts = s.split('%')
        result = parts[0]
        for part in parts[1:]:
            if len(part) >= 2:
                try:
                    result += chr(int(part[:2], 16)) + part[2:]
                except ValueError:
                    result += '%' + part
            else:
                result += '%' + part
        return result

    @staticmethod
    def _json_escape(s):
        """
        转义 JSON 字符串值

        Args:
            s: 原始字符串

        Returns:
            str: 可安全放入 JSON 字符串的内容
        """
        if s is None:
            return ''
        return str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')

    def _scan_wifi(self):
        """
        扫描附近 WiFi 网络，按信号强度排序取前10

        Returns:
            list: WiFi 网络信息列表，每项含 ssid/rssi/encrypted
        """
        try:
            sta = self._get_sta_if()
            was_active = sta.active()
            if not was_active:
                sta.active(True)
                time.sleep(1)
            networks = sta.scan()
            if not was_active:
                sta.active(False)
                log.info("WiFi扫描完成，STA接口已关闭")
            networks.sort(key=lambda x: x[3], reverse=True)
            result = []
            seen = set()
            for net in networks[:20]:
                ssid = net[0]
                if isinstance(ssid, bytes):
                    try:
                        ssid = ssid.decode('utf-8')
                    except UnicodeDecodeError:
                        ssid = ssid.decode('latin-1')
                if not ssid or ssid in seen:
                    continue
                seen.add(ssid)
                rssi = net[3]
                authmode = net[4]
                encrypted = authmode != 0
                result.append({'ssid': ssid, 'rssi': rssi, 'encrypted': encrypted})
                if len(result) >= 10:
                    break
            return result
        except Exception as e:
            log.error("WiFi扫描失败: %s" % e)
            return []

    def _connect_wifi(self, ssid, password):
        """
        连接指定 WiFi 网络

        Args:
            ssid: WiFi 名称
            password: WiFi 密码

        Returns:
            tuple: (成功标志, IP地址或错误信息)
        """
        try:
            sta = self._get_sta_if()
            if not sta.active():
                sta.active(True)
                time.sleep(1)
            if sta.isconnected():
                sta.disconnect()
                time.sleep(1)
            sta.connect(ssid, password)
            for _ in range(30):
                time.sleep(0.5)
                if sta.isconnected():
                    ip = sta.ifconfig()[0]
                    log.info("WiFi连接成功: %s, IP: %s" % (ssid, ip))
                    self._save_wifi_config(ssid, password)
                    self._wifi_configured = True
                    self._config_cache = None
                    self._auto_check_ota()
                    return True, ip
            log.warning("WiFi连接超时: %s" % ssid)
            try:
                sta.disconnect()
            except OSError:
                pass
            return False, "连接超时，请检查密码"
        except Exception as e:
            log.error("WiFi连接失败: %s" % e)
            return False, str(e)

    def _save_wifi_config(self, ssid, password):
        """
        保存 WiFi 凭据到文件系统

        Args:
            ssid: WiFi 名称
            password: WiFi 密码
        """
        try:
            with open(config.WIFI_CONFIG_FILE, 'w') as f:
                f.write(ssid + '\n' + password)
            log.info("WiFi配置已保存: %s" % ssid)
        except Exception as e:
            log.error("保存WiFi配置失败: %s" % e)

    def _auto_check_ota(self):
        """STA 连接成功后自动检查 OTA 更新（后台线程）"""
        if self.ota_updater is None:
            return
        if self._ota_check_result is not None:
            return
        self._ota_check_result = "pending"
        start_thread(self._ota_check_thread, stack=DEFAULT_STACK)

    def _ota_check_thread(self):
        """后台线程：执行 OTA 版本检查"""
        try:
            result = self.ota_updater.check_update()
            self._ota_check_result = result
            self._config_cache = None
            if result.get('has_update'):
                log.info("发现新版本: %s" % result.get('version', ''))
            else:
                log.info("OTA检查完成，无可用更新")
        except Exception as e:
            log.error("OTA检查线程异常: %s" % e)
            self._ota_check_result = {'has_update': False, 'error': str(e)}
            self._config_cache = None

    def _handle_check_update(self):
        """处理 OTA 更新检查请求"""
        if self.ota_updater is None:
            body = '{"has_update":false,"error":"OTA不可用"}'
            return self._json_response(body)
        if not self._wifi_configured:
            body = '{"has_update":false,"error":"需先配网连接WiFi"}'
            return self._json_response(body)
        if self._ota_check_result == "pending":
            body = '{"status":"checking"}'
            return self._json_response(body)
        if self._ota_check_result is not None:
            result = self._ota_check_result
            if result.get('has_update'):
                body = '{"has_update":true,"version":"' + self._json_escape(result.get('version', '')) + '","changelog":"' + self._json_escape(result.get('changelog', '')) + '","file_count":' + str(result.get('file_count', 0)) + ',"total_size":' + str(result.get('total_size', 0)) + '}'
            elif result.get('error'):
                body = '{"has_update":false,"error":"' + self._json_escape(result.get('error', '')) + '"}'
            else:
                body = '{"has_update":false,"current":"' + self._json_escape(self.ota_updater.current_version) + '"}'
            return self._json_response(body)
        self._auto_check_ota()
        body = '{"status":"checking"}'
        return self._json_response(body)

    def _handle_start_update(self):
        """处理开始 OTA 更新请求"""
        if self.ota_updater is None:
            body = '{"ok":false,"msg":"OTA不可用"}'
            return self._json_response(body)
        if self._ota_downloading:
            body = '{"ok":false,"msg":"正在更新中，请稍候"}'
            return self._json_response(body)
        if not self.ota_updater.check_result or not self.ota_updater.check_result.get('has_update'):
            body = '{"ok":false,"msg":"请先检查更新"}'
            return self._json_response(body)
        self._ota_downloading = True
        self._config_cache = None
        bus.publish(EVENT_OTA_STATUS, status="downloading")
        start_thread(self._ota_download_thread, stack=DEFAULT_STACK)
        body = '{"ok":true,"msg":"downloading"}'
        return self._json_response(body)

    def _ota_download_thread(self):
        """后台线程：执行 OTA 文件下载，期间暂停 WiFi 关闭计时器"""
        try:
            self._ota_downloading = True
            ok = self.ota_updater.start_download()
            if ok:
                log.info("OTA下载完成，即将重启")
                bus.publish(EVENT_OTA_STATUS, status="success")
                time.sleep_ms(2000)
                machine.reset()
            else:
                log.error("OTA下载失败")
                bus.publish(EVENT_OTA_STATUS, status="failed")
                self._ota_downloading = False
        except Exception as e:
            log.error("OTA下载线程异常: %s" % e)
            bus.publish(EVENT_OTA_STATUS, status="error")
            self._ota_downloading = False

    def _handle_update_status(self):
        """处理 OTA 更新状态查询"""
        if self.ota_updater is None:
            body = '{"status":"idle"}'
            return self._json_response(body)
        state = self.ota_updater.download_state
        if state is None:
            body = '{"status":"idle"}'
        elif state.get('status') == 'downloading':
            body = (
                '{"status":"downloading","completed":' + str(state.get('completed', 0)) +
                ',"total":' + str(state.get('total', 0)) +
                ',"percent":' + str(state.get('percent', 0)) +
                ',"downloaded_bytes":' + str(state.get('downloaded_bytes', 0)) +
                ',"total_bytes":' + str(state.get('total_bytes', 0)) +
                ',"current_file_bytes":' + str(state.get('current_file_bytes', 0)) +
                ',"current_file_total":' + str(state.get('current_file_total', 0)) + '}'
            )
        elif state.get('status') == 'done':
            body = '{"status":"done","msg":"更新完成，设备即将重启"}'
        elif state.get('status') == 'failed':
            body = (
                '{"status":"failed","msg":"' + self._json_escape(state.get('error', '未知错误')) +
                '","completed":' + str(state.get('completed', 0)) +
                ',"total":' + str(state.get('total', 0)) +
                ',"downloaded_bytes":' + str(state.get('downloaded_bytes', 0)) +
                ',"total_bytes":' + str(state.get('total_bytes', 0)) + '}'
            )
        else:
            body = '{"status":"idle"}'
        return self._json_response(body)

    def _disable_ble(self):
        """
        关闭蓝牙，释放射频资源

        Returns:
            tuple: (成功标志, 提示信息)
        """
        if not self.ble_meter:
            return True, "无蓝牙模块"
        if self.ble_disabled:
            return True, "蓝牙已停用"
        if self.ble_meter.connections:
            return False, "蓝牙有活跃连接，请先断开所有蓝牙设备"
        ok = self.ble_meter.deactivate()
        if ok:
            self.ble_disabled = True
            return True, "蓝牙已停用"
        return False, "蓝牙停用失败"

    def start(self):
        """启动 WiFi AP 热点与 Web 服务器

        ESP32-C3 硬件限制：WiFi 与 BLE 共用射频，无法同时运行。
        必须先关闭 BLE 才能启动 WiFi AP。
        此方法仅在用户主动长按2秒触发配网模式时调用，符合蓝牙优先规则。

        Returns:
            bool: 是否成功启动 WiFi AP 和 Web 服务器
        """
        try:
            if self.ble_meter and not self.ble_disabled:
                ok, msg = self._disable_ble()
                if not ok:
                    log.error("WiFi启动前关闭BLE失败: %s" % msg)
                    return False
                log.info("已关闭BLE（用户主动进入配网模式，ESP32-C3 WiFi/BLE互斥）")

            bus.publish(EVENT_WIFI_START)
            gc.collect()

            self.wlan = network.WLAN(network.AP_IF)
            self.wlan.active(False)
            time.sleep(1)

            self.wlan.active(True)
            self.wlan.config(essid=config.WIFI_SSID, authmode=network.AUTH_OPEN)
            time.sleep(2)

            self.wlan.ifconfig((
                config.WIFI_IP, config.WIFI_SUBNET,
                config.WIFI_GATEWAY, config.WIFI_DNS
            ))

            ip = self.wlan.ifconfig()[0]
            log.info("WiFi热点已启动，ESSID: %s" % config.WIFI_SSID)
            log.info("IP地址: %s" % ip)
            log.info("%d秒后将自动关闭WiFi并重启恢复蓝牙" % (config.WIFI_SHUTDOWN_MS // 1000))

            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind(("0.0.0.0", config.WIFI_PORT))
            self.server.listen(3)
            log.info("Web服务器已启动，监听端口%d" % config.WIFI_PORT)

            self._start_time = time.ticks_ms()

            self._config_cache = None

            start_thread(self._server_thread, stack=DEFAULT_STACK)
            start_thread(self._wifi_shutdown_timer)
            self._auto_connect_saved_wifi()
            return True
        except Exception as e:
            log.error("WiFi启动失败: %s" % e)
            if self.ble_disabled:
                log.error("WiFi启动失败且BLE已停用，重启设备恢复蓝牙")
                time.sleep_ms(1000)
                machine.reset()
            return False

    def _auto_connect_saved_wifi(self):
        """AP 启动后自动尝试连接已保存的 WiFi 凭据（后台线程）"""
        try:
            with open(config.WIFI_CONFIG_FILE, 'r') as f:
                lines = f.read().split('\n')
            ssid = lines[0].strip() if len(lines) > 0 else ''
            password = lines[1].strip() if len(lines) > 1 else ''
            if not ssid:
                return
            log.info("发现已保存WiFi: %s，自动连接中..." % ssid)
            start_thread(self._auto_connect_thread, (ssid, password), stack=DEFAULT_STACK)
        except OSError:
            pass
        except Exception as e:
            log.error("读取WiFi凭据失败: %s" % e)

    def _auto_connect_thread(self, ssid, password):
        """后台线程：自动连接已保存的 WiFi"""
        try:
            ok, result = self._connect_wifi(ssid, password)
            if ok:
                log.info("自动连接WiFi成功: %s" % ssid)
            else:
                log.info("自动连接WiFi失败: %s" % result)
        except Exception as e:
            log.error("自动连接WiFi异常: %s" % e)

    def _wifi_shutdown_timer(self):
        """WiFi 自动关闭计时线程，OTA 下载期间暂停关闭计时"""
        while not self._wifi_close_event:
            if self._ota_downloading:
                time.sleep(1)
                continue
            if config.WIFI_SHUTDOWN_MS > 0 and time.ticks_diff(time.ticks_ms(), self._start_time) >= config.WIFI_SHUTDOWN_MS:
                self._shutdown_wifi()
                break
            time.sleep(1)

    def get_remaining_time(self):
        """
        获取 WiFi 自动关闭剩余秒数

        Returns:
            int: 剩余秒数
        """
        if self._wifi_close_event or self._start_time == 0:
            return 0
        if self._ota_downloading:
            return 0
        elapsed = time.ticks_diff(time.ticks_ms(), self._start_time)
        remaining = config.WIFI_SHUTDOWN_MS - elapsed
        return max(0, int(remaining / 1000))

    def _shutdown_wifi(self):
        """关闭 WiFi AP 和 STA，如蓝牙已关闭则重启恢复"""
        log.info("正在关闭WiFi...")
        try:
            self._wifi_close_event = True
            if self.server:
                try:
                    self.server.close()
                except OSError:
                    pass
            try:
                if self.sta_if is not None and self.sta_if.active():
                    if self.sta_if.isconnected():
                        self.sta_if.disconnect()
                    self.sta_if.active(False)
                    log.info("WiFi STA已关闭")
            except OSError:
                pass
            if self.wlan:
                self.wlan.active(False)
                log.info("WiFi AP已关闭")
            if self.ble_disabled:
                log.info("蓝牙已关闭，设备即将重启以恢复蓝牙...")
                time.sleep_ms(1000)
                machine.reset()
            else:
                log.info("WiFi已关闭，蓝牙保持运行")
        except Exception as e:
            log.error("关闭WiFi失败: %s" % e)

    def _server_thread(self):
        """Web 服务器主循环线程"""
        while True:
            try:
                conn, _addr = self.server.accept()
                conn.settimeout(5.0)

                try:
                    request = self._recv_request(conn)
                    if request:
                        response = self._handle_request(request)
                        if isinstance(response, str):
                            data = response.encode('utf-8')
                        else:
                            data = response
                        try:
                            conn.sendall(data)
                        except OSError:
                            pass
                except OSError as e:
                    estr = str(e)
                    if "ETIMEDOUT" not in estr and "ECONNRESET" not in estr and "ECONNABORTED" not in estr:
                        log.warning("请求处理错误: %s" % e)
                except Exception as e:
                    log.warning("请求处理错误: %s" % e)
                finally:
                    try:
                        conn.close()
                    except OSError:
                        pass
            except OSError:
                if self._wifi_close_event:
                    break
                time.sleep(1)
            except Exception:
                if self._wifi_close_event:
                    break
                time.sleep(1)

    def _recv_request(self, conn):
        """
        读取完整 HTTP 请求，确保 POST body 按 Content-Length 收齐

        Args:
            conn: 客户端 socket 连接

        Returns:
            str: HTTP 请求文本
        """
        data = bytearray()
        expected_len = 0
        while len(data) < HTTP_REQUEST_MAX:
            chunk = conn.recv(HTTP_RECV_CHUNK)
            if not chunk:
                break
            data.extend(chunk)
            header_end = data.find(b"\r\n\r\n")
            if header_end < 0:
                continue
            if expected_len == 0:
                content_len = 0
                try:
                    header_text = bytes(data[:header_end]).decode()
                    for line in header_text.split("\r\n"):
                        lower = line.lower()
                        if lower.startswith("content-length:"):
                            content_len = int(line.split(":", 1)[1].strip())
                            break
                except (ValueError, UnicodeError):
                    content_len = 0
                expected_len = header_end + 4 + content_len
            if len(data) >= expected_len:
                break
        try:
            return bytes(data).decode()
        except UnicodeError:
            return ""

    def _handle_request(self, request):
        """
        解析 HTTP 请求并路由到对应处理方法

        Args:
            request: 原始 HTTP 请求字符串

        Returns:
            str: HTTP 响应字符串
        """
        path = "/"
        method = "GET"
        try:
            first_line = request.split("\r\n")[0]
            parts = first_line.split()
            method = parts[0] if len(parts) > 0 else "GET"
            path = parts[1] if len(parts) > 1 else "/"
        except (IndexError, ValueError):
            pass

        if "?" in path:
            path = path.split("?")[0]

        if method == "POST" and path == "/wifi_connect":
            return self._handle_wifi_connect(request)
        if path == "/wifi_status":
            return self._handle_wifi_status()
        if path == "/check_update":
            return self._handle_check_update()
        if method == "POST" and path == "/start_update":
            return self._handle_start_update()
        if path == "/update_status":
            return self._handle_update_status()
        if path == "/update_page":
            import web_pages
            return self._html_response(web_pages.build_update_page())
        if method == "POST" and path == "/config":
            return self._handle_config_submit(request)
        if path == "/scan":
            return self._handle_scan()
        if path == "/disable_bt":
            return self._handle_disable_bt()
        if path == "/time":
            remaining = self.get_remaining_time()
            return self._text_response(str(remaining), "text/plain")
        if path == "/success":
            if not self._submitted:
                return "HTTP/1.1 302 Found\r\nLocation: /\r\n\r\n"
            self._submitted = False
            return self._html_response(self._build_success_page())
        if path == "/wifi_setup":
            return self._html_response(self._build_wifi_setup_page())
        if path == "/" or path == "/config":
            if self._config_cache is not None:
                return self._config_cache
            self._config_cache = self._html_response(self._build_config_page())
            return self._config_cache

        return self._html_response(self._build_config_page())

    def _text_response(self, body, content_type="text/plain"):
        """构造纯文本 HTTP 响应"""
        data = body.encode('utf-8')
        return ("HTTP/1.1 200 OK\r\nContent-Type: " + content_type + "; charset=utf-8\r\n"
                "Cache-Control: no-cache\r\n"
                "Content-Length: " + str(len(data)) + "\r\n\r\n").encode('utf-8') + data

    def _html_response(self, body):
        """构造 HTML HTTP 响应"""
        data = body.encode('utf-8')
        return ("HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
                "Cache-Control: no-cache\r\nConnection: close\r\n"
                "Content-Length: " + str(len(data)) + "\r\n\r\n").encode('utf-8') + data

    def _json_response(self, body):
        """构造 JSON HTTP 响应"""
        data = body.encode('utf-8')
        return ("HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\n"
                "Cache-Control: no-cache\r\nAccess-Control-Allow-Origin: *\r\n"
                "Content-Length: " + str(len(data)) + "\r\n\r\n").encode('utf-8') + data

    def _scan_wifi_thread(self):
        """后台线程：执行 WiFi 扫描，结果写入 _scan_result"""
        try:
            nets = self._scan_wifi()
            items = []
            for n in nets:
                ssid_escaped = n['ssid'].replace('\\', '\\\\').replace('"', '\\"')
                items.append('{"ssid":"' + ssid_escaped + '","rssi":' + str(n['rssi']) + ',"enc":' + ('true' if n['encrypted'] else 'false') + '}')
            self._scan_result = '[' + ','.join(items) + ']'
        except Exception as e:
            log.error("WiFi扫描线程异常: %s" % e)
            self._scan_result = '[]'

    def _handle_scan(self):
        """处理 WiFi 扫描请求（异步，首次触发启动后台线程，后续返回结果）"""
        if not self.ble_disabled:
            body = '{"error":"请先关闭蓝牙"}'
        elif self._scan_result is None:
            self._scan_result = "pending"
            start_thread(self._scan_wifi_thread, stack=DEFAULT_STACK)
            body = '{"status":"scanning"}'
        elif self._scan_result == "pending":
            body = '{"status":"scanning"}'
        else:
            result = self._scan_result
            self._scan_result = None
            body = result
        return self._json_response(body)

    def _handle_disable_bt(self):
        """处理关闭蓝牙请求"""
        ok, msg = self._disable_ble()
        body = '{"ok":' + ('true' if ok else 'false') + ',"msg":"' + self._json_escape(msg) + '"}'
        return self._json_response(body)

    def _handle_wifi_connect(self, request):
        """处理 WiFi 连接 POST 请求（异步，后台线程执行连接）"""
        ssid = ""
        password = ""
        try:
            if "\r\n\r\n" in request:
                _, body = request.split("\r\n\r\n", 1)
                params = self._parse_form_data(body)
                ssid = params.get("ssid", "")
                password = params.get("password", "")
        except Exception as e:
            log.error("解析WiFi连接参数失败: %s" % e)

        if not ssid:
            body = '{"ok":false,"msg":"缺少SSID"}'
        elif not self.ble_disabled:
            body = '{"ok":false,"msg":"请先关闭蓝牙再连接WiFi"}'
        elif self._wifi_configured:
            sta = self._get_sta_if()
            if sta.isconnected():
                current_ssid = ''
                try:
                    current_ssid = sta.config('essid')
                except (OSError, ValueError):
                    pass
                if current_ssid == ssid:
                    ip = sta.ifconfig()[0]
                    body = '{"ok":true,"msg":"already_connected","ip":"' + self._json_escape(ip) + '"}'
                else:
                    self._connect_result = "pending"
                    start_thread(self._connect_wifi_thread, (ssid, password), stack=DEFAULT_STACK)
                    body = '{"ok":true,"msg":"connecting"}'
            else:
                if self._connect_result is not None and self._connect_result != "pending":
                    self._connect_result = None
                elif self._connect_result == "pending":
                    body = '{"ok":false,"msg":"正在连接中，请稍候"}'
                    return self._json_response(body)
                self._connect_result = "pending"
                start_thread(self._connect_wifi_thread, (ssid, password), stack=DEFAULT_STACK)
                body = '{"ok":true,"msg":"connecting"}'
        elif self._connect_result is not None:
            body = '{"ok":false,"msg":"正在连接中，请稍候"}'
        else:
            self._connect_result = "pending"
            start_thread(self._connect_wifi_thread, (ssid, password), stack=DEFAULT_STACK)
            body = '{"ok":true,"msg":"connecting"}'

        return self._json_response(body)

    def _connect_wifi_thread(self, ssid, password):
        """后台线程：执行 WiFi 连接，结果写入 _connect_result"""
        try:
            ok, result = self._connect_wifi(ssid, password)
            if ok:
                self._connect_result = "ok:" + result
            else:
                self._connect_result = "fail:" + result
        except Exception as e:
            log.error("WiFi连接线程异常: %s" % e)
            self._connect_result = "fail:" + str(e)

    def _handle_wifi_status(self):
        """处理 WiFi 连接状态查询（原子化读写，防止状态丢失）"""
        result = self._connect_result
        if result is None:
            body = '{"status":"idle"}'
        elif result == "pending":
            body = '{"status":"connecting"}'
        else:
            self._connect_result = None
            if result.startswith("ok:"):
                ip = result[3:]
                body = '{"status":"connected","ip":"' + self._json_escape(ip) + '"}'
            else:
                msg = result[5:] if result.startswith("fail:") else result
                body = '{"status":"failed","msg":"' + self._json_escape(msg) + '"}'
        return self._json_response(body)

    def _handle_config_submit(self, request):
        """处理配置表单 POST 请求"""
        log.info("检测到配置表单POST请求")
        try:
            if "\r\n\r\n" in request:
                _, body = request.split("\r\n\r\n", 1)
                params = self._parse_form_data(body)
                log.info("POST参数: %s" % str(params))
                self._apply_config(params)
                self.power_engine.flush_if_dirty()
        except Exception as e:
            log.error("POST处理错误: %s" % e)

        self._submitted = True
        self._config_cache = None

        def close_wifi_later():
            time.sleep(5)
            self._shutdown_wifi()
        start_thread(close_wifi_later)

        return "HTTP/1.1 302 Found\r\nLocation: /success\r\n\r\n"

    def _parse_form_data(self, body):
        """
        解析 URL 编码的表单数据

        Args:
            body: 表单原始字符串

        Returns:
            dict: 参数键值对
        """
        params = {}
        for pair in body.split("&"):
            if "=" in pair:
                key, value = pair.split("=", 1)
                params[key] = self._url_decode(value)
        return params

    def _apply_config(self, params):
        """
        将表单参数应用到功率引擎（通过公共方法，与按钮路径一致）

        Args:
            params: 表单参数字典
        """
        if "mode" in params:
            if not self.power_engine.set_mode(params["mode"]):
                log.warning("骑行模式未变更或无效: %s" % params["mode"])

        if self.power_engine.get_mode() != config.RIDE_MODE_STEADY:
            log.info("非固定功率模式使用内置规则，忽略功率/踏频/心率表单")
            return

        if "power" in params:
            try:
                self.power_engine.set_power(int(params["power"]))
            except ValueError as e:
                log.error("功率更新失败: %s" % e)

        if "cadence" in params:
            try:
                self.power_engine.set_cadence(int(params["cadence"]))
            except ValueError as e:
                log.error("踏频更新失败: %s" % e)

        if "heartrate" in params:
            try:
                self.power_engine.set_heartrate(int(params["heartrate"]))
            except ValueError as e:
                log.error("心率更新失败: %s" % e)

    def _build_landing_page(self):
        return self._build_config_page()

    def _build_wifi_setup_page(self):
        import web_pages
        return web_pages.build_wifi_setup_page()

    def _build_config_page(self):
        import web_pages
        ota_info = None
        if self.ota_updater and self._ota_check_result and self._ota_check_result != "pending":
            ota_info = self._ota_check_result
        return web_pages.build_config_page(
            self.power_engine.base_power,
            self.power_engine.cadence_base,
            self.power_engine.last_heartrate,
            self.power_engine.get_mode(),
            self._wifi_configured,
            ota_info,
            self.ota_updater.current_version if self.ota_updater else get_firmware_version()
        )

    def _build_success_page(self):
        import web_pages
        return web_pages.build_success_page(
            self.power_engine.base_power,
            self.power_engine.cadence_base,
            self.power_engine.last_heartrate,
            self.power_engine.get_mode()
        )
