"""
OTA 固件更新模块
职责：版本检查、文件差量下载、CRC32 校验、原子替换、安全回滚

运行环境：MicroPython v1.28
"""

import gc
import json
import os
import socket
import ssl
from micropython import const
import config
from logger import get_logger

log = get_logger("OTA")

try:
    _ssl_mod = ssl
except NameError:
    _ssl_mod = None


def get_firmware_version():
    """
    获取当前固件版本号，优先读取 ota_version.json，回退到 config.FIRMWARE_VERSION

    Returns:
        str: 当前固件版本号
    """
    try:
        with open(config.OTA_VERSION_FILE, 'r') as f:
            data = json.loads(f.read())
        return data.get('v', data.get('current_version', config.FIRMWARE_VERSION))
    except (OSError, ValueError, KeyError):
        return config.FIRMWARE_VERSION


class OTAUpdater:
    """文件级差量 OTA 更新器，支持 CRC32 校验和 .bak 安全回滚"""

    _MAX_RESPONSE_SIZE = const(10240)

    def __init__(self):
        self._current_version = config.FIRMWARE_VERSION
        self._load_ota_version()
        self._version_info = None
        self._check_result = None
        self._download_state = None

    def _load_ota_version(self):
        try:
            with open(config.OTA_VERSION_FILE, 'r') as f:
                cfg = json.load(f)
            v = cfg.get('v', '')
            if v:
                self._current_version = v
                log.info("OTA版本: %s" % v)
        except OSError:
            pass
        except Exception as e:
            log.error("OTA版本读取失败: %s" % e)

    @property
    def current_version(self):
        return self._current_version

    @property
    def check_result(self):
        return self._check_result

    @property
    def download_state(self):
        return self._download_state

    @staticmethod
    def _crc32(data):
        """
        计算 CRC32 校验值

        Args:
            data: bytes 数据

        Returns:
            str: 8位十六进制 CRC32 字符串
        """
        crc = 0xFFFFFFFF
        for b in data:
            crc ^= b
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xEDB88320
                else:
                    crc >>= 1
        return '%08x' % (crc ^ 0xFFFFFFFF)

    @staticmethod
    def _file_crc32(filepath):
        """
        计算文件 CRC32（流式读取，低内存）

        Args:
            filepath: 文件路径

        Returns:
            str: CRC32 十六进制字符串，失败返回空字符串
        """
        try:
            crc = 0xFFFFFFFF
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(config.OTA_DOWNLOAD_CHUNK)
                    if not chunk:
                        break
                    for b in chunk:
                        crc ^= b
                        for _ in range(8):
                            if crc & 1:
                                crc = (crc >> 1) ^ 0xEDB88320
                            else:
                                crc >>= 1
            return '%08x' % (crc ^ 0xFFFFFFFF)
        except OSError:
            return ''

    @staticmethod
    def _parse_url(url):
        """
        解析 HTTP URL

        Args:
            url: 完整 URL 字符串

        Returns:
            tuple: (host, path, port)
        """
        if url.startswith('https://'):
            host_part = url[8:]
            port = 443
        elif url.startswith('http://'):
            host_part = url[7:]
            port = 80
        else:
            host_part = url
            port = 80
        slash_idx = host_part.find('/')
        if slash_idx >= 0:
            host = host_part[:slash_idx]
            path = host_part[slash_idx:]
        else:
            host = host_part
            path = '/'
        colon_idx = host.find(':')
        if colon_idx >= 0:
            port = int(host[colon_idx + 1:])
            host = host[:colon_idx]
        return host, path, port

    @staticmethod
    def _ssl_wrap(sock):
        """
        为 socket 包装 SSL/TLS（HTTPS 连接用）

        Args:
            sock: 已连接的原始 socket

        Returns:
            SSL 包装后的 socket，SSL 不可用时返回原 socket
        """
        if _ssl_mod is not None:
            try:
                return _ssl_mod.wrap_socket(sock)
            except Exception as e:
                log.error("SSL握手失败: %s" % e)
                raise
        raise OSError("SSL不可用，无法连接HTTPS")

    @staticmethod
    def _extract_content_length(headers):
        """从 HTTP 响应头中提取 Content-Length。"""
        for line in headers.split('\r\n'):
            if line.lower().startswith('content-length:'):
                try:
                    return int(line.split(':', 1)[1].strip())
                except ValueError:
                    return 0
        return 0

    @staticmethod
    def _update_stream_progress(progress, bytes_received, content_length):
        """根据当前流式下载进度刷新下载状态。"""
        if not progress:
            return
        state = progress.get('state')
        if not state:
            return
        total = progress.get('total', 0)
        completed = progress.get('completed', 0)
        total_bytes = progress.get('total_bytes', 0)
        base_downloaded = progress.get('base_downloaded', 0)
        expected_size = progress.get('expected_size', 0)
        file_total = content_length if content_length > 0 else expected_size
        downloaded_bytes = base_downloaded + bytes_received
        if total_bytes > 0:
            if downloaded_bytes > total_bytes:
                downloaded_bytes = total_bytes
            percent = int(downloaded_bytes * 100 / total_bytes)
        else:
            percent = int(completed * 100 / total) if total > 0 else 0
        state['completed'] = completed
        state['total'] = total
        state['downloaded_bytes'] = downloaded_bytes
        state['total_bytes'] = total_bytes
        state['current_file_bytes'] = bytes_received
        state['current_file_total'] = file_total
        state['percent'] = percent

    @staticmethod
    def _http_request(url, dest_path=None, progress=None):
        """
        统一 HTTP GET 请求：支持返回响应体（dest_path=None）或流式写入文件

        Args:
            url: 请求 URL
            dest_path: 若指定则流式写入此文件路径，否则返回响应体

        Returns:
            dest_path=None 时返回 bytes 或 None（失败）
            dest_path 指定时返回 True/False/None（成功/失败/异常）
        """
        for _ in range(config.OTA_MAX_REDIRECTS + 1):
            try:
                host, path, port = OTAUpdater._parse_url(url)
                addr = socket.getaddrinfo(host, port)[0][-1]
                sock = socket.socket()
                sock.settimeout(config.OTA_HTTP_TIMEOUT)
                sock.connect(addr)
                if port == 443:
                    sock = OTAUpdater._ssl_wrap(sock)
                req = 'GET %s HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n' % (path, host)
                sock.send(req.encode())

                if dest_path is None:
                    response = b''
                    while True:
                        try:
                            chunk = sock.recv(1024)
                            if not chunk:
                                break
                            response += chunk
                            if len(response) > OTAUpdater._MAX_RESPONSE_SIZE:
                                log.error("响应过大(>%d字节)" % OTAUpdater._MAX_RESPONSE_SIZE)
                                sock.close()
                                return None
                        except OSError:
                            break
                    sock.close()
                    header_end = response.find(b'\r\n\r\n')
                    if header_end < 0:
                        return None
                    headers = response[:header_end].decode('utf-8', errors='replace')
                    status_line = headers.split('\r\n')[0]
                    status_code = int(status_line.split()[1]) if len(status_line.split()) > 1 else 0
                    if status_code in (301, 302, 307, 308):
                        url = OTAUpdater._extract_redirect(headers)
                        if url:
                            continue
                    if status_code != 200:
                        log.error("HTTP %d: %s" % (status_code, url))
                        return None
                    return response[header_end + 4:]
                else:
                    headers_done = False
                    headers_buf = b''
                    redirect_url = None
                    content_length = 0
                    bytes_received = 0
                    f = None
                    try:
                        while True:
                            try:
                                chunk = sock.recv(config.OTA_DOWNLOAD_CHUNK)
                                if not chunk:
                                    break
                                if not headers_done:
                                    headers_buf += chunk
                                    header_end_h = headers_buf.find(b'\r\n\r\n')
                                    if header_end_h >= 0:
                                        headers = headers_buf[:header_end_h].decode('utf-8', errors='replace')
                                        body_start = headers_buf[header_end_h + 4:]
                                        status_line = headers.split('\r\n')[0]
                                        status_code = int(status_line.split()[1]) if len(status_line.split()) > 1 else 0
                                        if status_code in (301, 302, 307, 308):
                                            redirect_url = OTAUpdater._extract_redirect(headers)
                                            break
                                        if status_code != 200:
                                            log.error("HTTP %d: %s" % (status_code, url))
                                            break
                                        content_length = OTAUpdater._extract_content_length(headers)
                                        f = open(dest_path, 'wb')
                                        if body_start:
                                            f.write(body_start)
                                            bytes_received += len(body_start)
                                            OTAUpdater._update_stream_progress(progress, bytes_received, content_length)
                                        headers_done = True
                                else:
                                    f.write(chunk)
                                    bytes_received += len(chunk)
                                    OTAUpdater._update_stream_progress(progress, bytes_received, content_length)
                            except OSError:
                                break
                    finally:
                        if f:
                            f.close()
                        sock.close()
                    if redirect_url:
                        url = redirect_url
                        continue
                    return headers_done
            except Exception as e:
                log.error("HTTP请求失败: %s" % e)
                try:
                    sock.close()
                except OSError:
                    pass
                return None
        log.error("重定向次数超限")
        return None

    @staticmethod
    def _extract_redirect(headers):
        """从 HTTP 响应头中提取重定向 Location"""
        for line in headers.split('\r\n'):
            if line.lower().startswith('location:'):
                return line.split(':', 1)[1].strip()
        return None

    @staticmethod
    def _version_cmp(v1, v2):
        """
        比较两个语义化版本号（支持预发布标识如 1.9.0-beta.1）

        Args:
            v1: 版本字符串 (如 "1.8.0" 或 "1.9.0-beta.1")
            v2: 版本字符串 (如 "1.9.0")

        Returns:
            int: v1 > v2 返回正数，v1 < v2 返回负数，相等返回 0
        """
        def _parse(ver):
            base = ver.split('-', 1)[0]
            try:
                return [int(x) for x in base.split('.')]
            except ValueError:
                return [0]
        parts1 = _parse(v1)
        parts2 = _parse(v2)
        for a, b in zip(parts1, parts2):
            if a != b:
                return a - b
        return len(parts1) - len(parts2)

    def check_update(self):
        """
        检查是否有可用更新

        Returns:
            dict: 检查结果
                has_update: bool
                version: str (新版本号)
                changelog: str
                file_count: int
                total_size: int
                error: str (失败时)
        """
        try:
            body = self._http_request(config.OTA_VERSION_URL)
            if body is None:
                self._check_result = {'has_update': False, 'error': '网络请求失败'}
                return self._check_result

            if isinstance(body, bytes):
                info = json.loads(body.decode('utf-8'))
            else:
                info = json.loads(body)

            remote_version = info.get('version', '')
            min_version = info.get('min_version', '0.0.0')
            mpy_version = info.get('mpy_version', '')

            if self._version_cmp(remote_version, self._current_version) <= 0:
                self._check_result = {
                    'has_update': False,
                    'current': self._current_version
                }
                return self._check_result

            if self._version_cmp(self._current_version, min_version) < 0:
                self._check_result = {
                    'has_update': False,
                    'error': '当前版本过低，需USB升级（最低%s）' % min_version
                }
                return self._check_result

            if mpy_version and mpy_version != config.MPY_VERSION:
                self._check_result = {
                    'has_update': False,
                    'error': 'MicroPython版本不匹配（需%s 当前%s）' % (mpy_version, config.MPY_VERSION)
                }
                return self._check_result

            files = info.get('files', [])
            total_size = sum(f.get('size', 0) for f in files)

            self._version_info = info
            self._check_result = {
                'has_update': True,
                'version': remote_version,
                'changelog': info.get('changelog', ''),
                'file_count': len(files),
                'total_size': total_size
            }
            log.info("发现新版本: %s (%d个文件, %d字节)" % (remote_version, len(files), total_size))
            return self._check_result

        except Exception as e:
            log.error("检查更新失败: %s" % e)
            self._check_result = {'has_update': False, 'error': '检查失败: %s' % str(e)}
            return self._check_result

    _PROTECTED_FILES = const(0)

    _PROTECTED_FILE_NAMES = frozenset([
        'wifi_config.txt',
        'power_config.json',
        'ota_version.json',
        '.update_pending',
    ])

    def start_download(self):
        """
        开始下载更新（后台线程调用）

        Returns:
            bool: 是否成功完成所有文件下载和替换
        """
        if not self._version_info:
            return False

        files = self._version_info.get('files', [])
        plan = []
        total_bytes = 0

        for f_info in files:
            fname = f_info.get('name', '')
            expected_hash = f_info.get('hash', '')
            download_url = f_info.get('url', '')
            if not fname or not download_url:
                log.warning("跳过无效文件条目: %s" % fname)
                continue
            if fname in self._PROTECTED_FILE_NAMES:
                log.warning("跳过受保护文件: %s" % fname)
                continue
            local_hash = self._file_crc32(fname)
            if local_hash == expected_hash:
                log.info("文件未变更，跳过: %s" % fname)
                continue
            plan.append(f_info)
            try:
                size = int(f_info.get('size', 0) or 0)
            except (TypeError, ValueError):
                size = 0
            if size > 0:
                total_bytes += size

        total = len(plan)
        completed = 0
        downloaded_bytes = 0

        self._download_state = {
            'status': 'downloading',
            'completed': 0,
            'total': total,
            'percent': 0,
            'downloaded_bytes': 0,
            'total_bytes': total_bytes,
            'current_file_bytes': 0,
            'current_file_total': 0,
            'error': ''
        }

        for f_info in plan:
            fname = f_info.get('name', '')
            expected_hash = f_info.get('hash', '')
            download_url = f_info.get('url', '')
            try:
                expected_size = int(f_info.get('size', 0) or 0)
            except (TypeError, ValueError):
                expected_size = 0

            self._download_state['completed'] = completed
            self._download_state['downloaded_bytes'] = downloaded_bytes
            self._download_state['current_file_bytes'] = 0
            self._download_state['current_file_total'] = expected_size
            if total_bytes > 0:
                self._download_state['percent'] = int(downloaded_bytes * 100 / total_bytes)
            else:
                self._download_state['percent'] = int(completed * 100 / total) if total > 0 else 0

            tmp_path = fname + config.OTA_TEMP_SUFFIX
            bak_path = fname + config.OTA_BACKUP_SUFFIX

            is_mpy = fname.endswith(config.OTA_MPY_SUFFIX)
            py_name = fname[:-len(config.OTA_MPY_SUFFIX)] + '.py' if is_mpy else ''

            try:
                if fname in os.listdir():
                    if bak_path in os.listdir():
                        os.remove(bak_path)
                    os.rename(fname, bak_path)
                    log.info("已备份: %s -> %s" % (fname, bak_path))
                if is_mpy and py_name and py_name in os.listdir():
                    py_bak = py_name + config.OTA_BACKUP_SUFFIX
                    if py_bak in os.listdir():
                        os.remove(py_bak)
                    os.rename(py_name, py_bak)
                    log.info("已备份旧源码: %s -> %s" % (py_name, py_bak))
            except OSError as e:
                log.error("备份失败: %s" % e)
                self._download_state = {
                    'status': 'failed',
                    'error': '准备更新失败，请重试',
                    'completed': completed,
                    'total': total,
                    'downloaded_bytes': downloaded_bytes,
                    'total_bytes': total_bytes
                }
                return False

            log.info("正在下载: %s" % fname)
            ok = self._http_request(download_url, tmp_path, {
                'state': self._download_state,
                'completed': completed,
                'total': total,
                'base_downloaded': downloaded_bytes,
                'total_bytes': total_bytes,
                'expected_size': expected_size
            })
            if not ok:
                log.error("下载失败: %s" % fname)
                if bak_path in os.listdir():
                    try:
                        os.rename(bak_path, fname)
                        log.info("已回滚: %s" % fname)
                    except OSError:
                        pass
                if is_mpy and py_name:
                    py_bak = py_name + config.OTA_BACKUP_SUFFIX
                    if py_bak in os.listdir():
                        try:
                            os.rename(py_bak, py_name)
                            log.info("已回滚旧源码: %s" % py_name)
                        except OSError:
                            pass
                if tmp_path in os.listdir():
                    os.remove(tmp_path)
                self._download_state = {
                    'status': 'failed',
                    'error': '下载失败，请检查网络后重试',
                    'completed': completed,
                    'total': total,
                    'downloaded_bytes': downloaded_bytes,
                    'total_bytes': total_bytes
                }
                return False

            actual_hash = self._file_crc32(tmp_path)
            if actual_hash != expected_hash:
                log.error("校验失败: %s (期望%s 实际%s)" % (fname, expected_hash, actual_hash))
                if tmp_path in os.listdir():
                    os.remove(tmp_path)
                if bak_path in os.listdir():
                    try:
                        os.rename(bak_path, fname)
                    except OSError:
                        pass
                if is_mpy and py_name:
                    py_bak = py_name + config.OTA_BACKUP_SUFFIX
                    if py_bak in os.listdir():
                        try:
                            os.rename(py_bak, py_name)
                        except OSError:
                            pass
                self._download_state = {
                    'status': 'failed',
                    'error': '下载校验失败，请重试',
                    'completed': completed,
                    'total': total,
                    'downloaded_bytes': downloaded_bytes,
                    'total_bytes': total_bytes
                }
                return False

            try:
                os.rename(tmp_path, fname)
                log.info("已替换: %s" % fname)
                if is_mpy and py_name:
                    py_bak = py_name + config.OTA_BACKUP_SUFFIX
                    if py_bak in os.listdir():
                        os.remove(py_bak)
                        log.info("已删除旧源码备份: %s" % py_bak)
            except OSError as e:
                log.error("替换失败: %s" % e)
                if bak_path in os.listdir():
                    try:
                        os.rename(bak_path, fname)
                    except OSError:
                        pass
                if is_mpy and py_name:
                    py_bak = py_name + config.OTA_BACKUP_SUFFIX
                    if py_bak in os.listdir():
                        try:
                            os.rename(py_bak, py_name)
                        except OSError:
                            pass
                self._download_state = {
                    'status': 'failed',
                    'error': '写入失败，请重试',
                    'completed': completed,
                    'total': total,
                    'downloaded_bytes': downloaded_bytes,
                    'total_bytes': total_bytes
                }
                return False

            file_bytes = self._download_state.get('current_file_bytes', 0)
            if file_bytes <= 0:
                file_bytes = expected_size
            downloaded_bytes += file_bytes
            if total_bytes > 0 and downloaded_bytes > total_bytes:
                downloaded_bytes = total_bytes
            completed += 1
            self._download_state['completed'] = completed
            self._download_state['downloaded_bytes'] = downloaded_bytes
            self._download_state['current_file_bytes'] = 0
            self._download_state['current_file_total'] = 0
            if total_bytes > 0:
                self._download_state['percent'] = int(downloaded_bytes * 100 / total_bytes)
            else:
                self._download_state['percent'] = int(completed * 100 / total) if total > 0 else 100
            gc.collect()

        try:
            new_version = self._version_info.get('version', '')
            with open(config.OTA_VERSION_FILE, 'w') as f:
                json.dump({'v': new_version}, f)
            log.info("版本号已更新: %s" % new_version)
        except Exception as e:
            log.error("保存版本号失败: %s" % e)

        try:
            with open(config.OTA_PENDING_FLAG, 'w') as f:
                f.write('1')
            log.info("已设置更新待校验标志")
        except Exception as e:
            log.error("设置更新标志失败: %s" % e)

        self._download_state = {
            'status': 'done',
            'completed': total,
            'total': total,
            'percent': 100,
            'downloaded_bytes': total_bytes,
            'total_bytes': total_bytes,
            'current_file_bytes': 0,
            'current_file_total': 0
        }
        log.info("OTA下载完成，即将重启校验")
        return True
