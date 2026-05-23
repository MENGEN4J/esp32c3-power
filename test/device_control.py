#!/usr/bin/env python3
"""
测试设备控制辅助模块

职责：在 BLE 主程序运行时，通过部署模式安全执行 mpremote 命令，再恢复设备主程序。

运行环境: CPython 3.x
"""

import argparse
import subprocess
import sys
import time
from contextlib import contextmanager

import serial


def _run_command(command, timeout):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        raw = (result.stdout or "") + (result.stderr or "")
        return raw, result.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", -1
    except Exception as exc:
        return str(exc), -1


class DeviceController:
    """测试期间控制 ESP32 进入/退出部署模式。"""

    def __init__(self, port):
        self.port = port

    def _mpremote_ls(self, timeout=5):
        _, rc = _run_command(
            ["python3", "-m", "mpremote", "connect", self.port, "ls"],
            timeout,
        )
        return rc == 0

    def _mpremote_exec_probe(self, timeout=5):
        raw, rc = _run_command(
            ["python3", "-m", "mpremote", "connect", self.port, "exec", "print('READY')"],
            timeout,
        )
        return rc == 0 and "READY" in raw

    def _write_deploy_flag(self):
        serial_conn = serial.Serial(self.port, 115200, timeout=2)
        try:
            time.sleep(0.1)
            serial_conn.write(b"\x03\x03")
            time.sleep(0.5)
            serial_conn.write(b"\x01")
            time.sleep(0.5)
            serial_conn.read(serial_conn.in_waiting or 4096)
            serial_conn.write(b'f=open(".deploy","w");f.flush();f.close()\x04')
            time.sleep(0.5)
            serial_conn.read(serial_conn.in_waiting or 4096)
            serial_conn.write(b"\x02")
            time.sleep(0.3)
            serial_conn.read(serial_conn.in_waiting or 4096)
            serial_conn.write(b"\x04")
            time.sleep(3)
            serial_conn.read(serial_conn.in_waiting or 8192)
            serial_conn.dtr = False
            serial_conn.rts = False
        finally:
            serial_conn.close()

    def _hardware_reset(self):
        serial_conn = serial.Serial(self.port, 115200, timeout=2)
        try:
            serial_conn.dtr = False
            serial_conn.rts = True
            time.sleep(0.1)
            serial_conn.rts = False
            time.sleep(0.5)
            serial_conn.dtr = True
        finally:
            serial_conn.close()

    def enter_deploy_mode(self, retries=5, wait_s=2):
        if self._mpremote_ls() and self._mpremote_exec_probe():
            return True

        self._write_deploy_flag()
        self._hardware_reset()
        time.sleep(wait_s)

        for _ in range(retries):
            if self._mpremote_ls() and self._mpremote_exec_probe():
                return True
            time.sleep(wait_s)
        return False

    def exit_deploy_mode(self, wait_s=5):
        _run_command(
            ["python3", "-m", "mpremote", "connect", self.port, "rm", ":.deploy"],
            5,
        )
        self._hardware_reset()
        time.sleep(wait_s)
        return True

    def exec_code(self, code, timeout=10):
        return _run_command(
            ["python3", "-m", "mpremote", "connect", self.port, "exec", code],
            timeout,
        )

    @contextmanager
    def deploy_session(self, wait_after_exit=5):
        if not self.enter_deploy_mode():
            raise RuntimeError("无法进入部署模式")
        try:
            yield self
        finally:
            self.exit_deploy_mode(wait_s=wait_after_exit)


def _cmd_enter(args):
    controller = DeviceController(args.port)
    if controller.enter_deploy_mode(retries=args.retries, wait_s=args.wait):
        print("DEPLOY_MODE_READY")
        return 0
    print("DEPLOY_MODE_FAILED", file=sys.stderr)
    return 1


def _cmd_exit(args):
    controller = DeviceController(args.port)
    controller.exit_deploy_mode(wait_s=args.wait)
    print("APP_MODE_READY")
    return 0


def _cmd_exec(args):
    controller = DeviceController(args.port)
    if not controller.enter_deploy_mode(retries=args.retries, wait_s=args.wait):
        print("DEPLOY_MODE_FAILED", file=sys.stderr)
        return 1

    raw, rc = controller.exec_code(args.code, timeout=args.timeout)
    if raw:
        print(raw, end="" if raw.endswith("\n") else "\n")

    if not args.keep_deploy:
        controller.exit_deploy_mode(wait_s=args.resume_wait)

    return 0 if rc == 0 else 1


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    enter_parser = subparsers.add_parser("enter-deploy")
    enter_parser.add_argument("--port", required=True)
    enter_parser.add_argument("--retries", type=int, default=5)
    enter_parser.add_argument("--wait", type=int, default=2)
    enter_parser.set_defaults(handler=_cmd_enter)

    exit_parser = subparsers.add_parser("exit-deploy")
    exit_parser.add_argument("--port", required=True)
    exit_parser.add_argument("--wait", type=int, default=5)
    exit_parser.set_defaults(handler=_cmd_exit)

    exec_parser = subparsers.add_parser("exec")
    exec_parser.add_argument("--port", required=True)
    exec_parser.add_argument("--code", required=True)
    exec_parser.add_argument("--timeout", type=int, default=10)
    exec_parser.add_argument("--retries", type=int, default=5)
    exec_parser.add_argument("--wait", type=int, default=2)
    exec_parser.add_argument("--resume-wait", type=int, default=5)
    exec_parser.add_argument("--keep-deploy", action="store_true")
    exec_parser.set_defaults(handler=_cmd_exec)

    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
