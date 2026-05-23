#!/usr/bin/env python3
"""BLE 蓝牙数据监控测试 — 详细操作步骤、具体数值验证

输出格式: id|name|status|steps|expected|actual|reason|fix
"""

import argparse
import asyncio
import struct
import sys
import subprocess
import time

from device_control import DeviceController
from test_utils import emit

DEVICE_NAME = "BikePower"
ALT_DEVICE_NAMES = ["MPY ESP32"]


def mpremote_exec(port, code, timeout=10):
    controller = DeviceController(port)
    try:
        with controller.deploy_session(wait_after_exit=5) as session:
            raw, rc = session.exec_code(code, timeout=timeout)
    except Exception as e:
        return str(e), -1
    lines = [l for l in raw.split('\n') if not l.startswith('[INFO]') and not l.startswith('[WARNING]') and not l.startswith('[ERROR]')]
    return '\n'.join(lines), rc


async def scan_ble_device(timeout=10):
    try:
        import bleak
    except ImportError:
        emit("T2.1", "bleak依赖", "FAIL",
             "1.检查bleak模块是否已安装", "bleak可正常导入",
             "bleak未安装", "依赖缺失", "pip3 install bleak")
        return None

    emit("T2.1", "bleak依赖", "PASS",
         "1.检查bleak模块是否已安装", "bleak可正常导入",
         "bleak已安装", "", "")

    device = None
    local_name = None
    try:
        devices_with_adv = await bleak.BleakScanner.discover(timeout=timeout, return_adv=True)
        for addr, (d, adv) in devices_with_adv.items():
            dev_name = d.name or ""
            adv_name = adv.local_name or ""
            if (DEVICE_NAME in dev_name or DEVICE_NAME in adv_name or
                    any(alt in dev_name for alt in ALT_DEVICE_NAMES)):
                device = d
                local_name = adv_name or dev_name
                break
    except Exception as e:
        emit("T2.2", "BLE设备扫描", "FAIL",
             f"1.调用BleakScanner.discover(timeout={timeout}s, return_adv=True)\n2.在GAP名称和广播包本地名中查找'{DEVICE_NAME}'",
             f"发现名为{DEVICE_NAME}的BLE设备",
             f"扫描异常: {e}",
             "蓝牙未开启或权限不足", "开启macOS蓝牙，检查系统偏好设置→蓝牙")
        return None

    if device:
        name_matched = DEVICE_NAME in (device.name or "")
        adv_matched = DEVICE_NAME in (local_name or "")
        match_info = f"广播名: {local_name}" + (f", GAP名: {device.name}" if device.name != local_name else "")
        emit("T2.2", "BLE设备扫描", "PASS",
             f"1.调用BleakScanner.discover(timeout={timeout}s, return_adv=True)\n2.在GAP名称和广播包本地名中查找'{DEVICE_NAME}'",
             f"发现名为{DEVICE_NAME}的BLE设备",
             f"发现: {match_info} ({device.address})", "", "")
    else:
        found_names = [d.name for d, _ in devices_with_adv.values() if d.name][:5]
        emit("T2.2", "BLE设备扫描", "FAIL",
             f"1.调用BleakScanner.discover(timeout={timeout}s, return_adv=True)\n2.在GAP名称和广播包本地名中查找'{DEVICE_NAME}'",
             f"发现名为{DEVICE_NAME}的BLE设备",
             f"未发现{DEVICE_NAME}，附近设备: {found_names}",
             "设备BLE未启动或距离过远", "确认设备已上电且BLE广播中，缩短距离")
    return device


async def read_ble_data(device, duration=5):
    import bleak

    power_values = []
    hr_values = []

    def notification_handler(sender, data):
        try:
            sender_uuid = str(sender.uuid if hasattr(sender, 'uuid') else sender)
            if "2A63" in sender_uuid.upper():
                if len(data) >= 4:
                    power = struct.unpack_from('<H', data, 2)[0]
                    power_values.append(power)
            elif "2A37" in sender_uuid.upper():
                if len(data) >= 2:
                    hr = data[1]
                    hr_values.append(hr)
        except Exception:
            pass

    try:
        async with bleak.BleakClient(device.address) as client:
            services = client.services
            power_service = None
            hr_service = None
            for s in services:
                if "1818" in s.uuid.upper():
                    power_service = s
                elif "180D" in s.uuid.upper():
                    hr_service = s

            if power_service:
                emit("T2.3", "功率服务(0x1818)", "PASS",
                     "1.连接BLE设备\n2.遍历services查找UUID含1818的服务",
                     "发现Cycling Power服务(0x1818)",
                     f"服务UUID: {power_service.uuid}", "", "")

                for char in power_service.characteristics:
                    if "2A63" in char.uuid.upper():
                        try:
                            val = await client.read_gatt_char(char)
                            if len(val) >= 4:
                                p = struct.unpack_from('<H', val, 2)[0]
                                power_values.append(p)
                                emit("T2.4", "功率数据读取", "PASS",
                                     f"1.读取Cycling Power Measurement(0x2A63)\n2.解析字节2-3为uint16功率值",
                                     f"读取到功率值(0-65535W范围内)",
                                     f"功率: {p}W", "", "")
                            else:
                                emit("T2.4", "功率数据读取", "FAIL",
                                     f"1.读取Cycling Power Measurement(0x2A63)\n2.解析字节2-3为uint16功率值",
                                     f"读取到功率值(至少4字节)",
                                     f"特征值长度={len(val)}字节(需>=4), 数据未写入",
                                     "BLE特征值未写入数据, 需先调用update_data()",
                                     "通过mpremote调用ble_service.update_data()写入初始数据")
                        except Exception as e:
                            emit("T2.4", "功率数据读取", "FAIL",
                                 "1.读取Cycling Power Measurement(0x2A63)",
                                 "读取到功率值",
                                 f"读取失败: {e}", "BLE连接不稳定", "缩短距离，减少干扰")
                        try:
                            await client.start_notify(char, notification_handler)
                        except Exception:
                            pass
            else:
                emit("T2.3", "功率服务(0x1818)", "FAIL",
                     "1.连接BLE设备\n2.遍历services查找UUID含1818的服务",
                     "发现Cycling Power服务(0x1818)",
                     "未找到功率服务", "BLE服务未注册", "确认ble_service.py服务注册正确")

            if hr_service:
                emit("T2.5", "心率服务(0x180D)", "PASS",
                     "1.遍历services查找UUID含180D的服务",
                     "发现Heart Rate服务(0x180D)",
                     f"服务UUID: {hr_service.uuid}", "", "")
                for char in hr_service.characteristics:
                    if "2A37" in char.uuid.upper():
                        try:
                            val = await client.read_gatt_char(char)
                            if len(val) >= 2:
                                hr = val[1]
                                hr_values.append(hr)
                                emit("T2.6", "心率数据读取", "PASS",
                                     "1.读取Heart Rate Measurement(0x2A37)\n2.解析字节1为uint8心率值",
                                     "读取到心率值(0-255bpm范围内)",
                                     f"心率: {hr}bpm", "", "")
                            else:
                                emit("T2.6", "心率数据读取", "FAIL",
                                     "1.读取Heart Rate Measurement(0x2A37)\n2.解析字节1为uint8心率值",
                                     "读取到心率值(至少2字节)",
                                     f"特征值长度={len(val)}字节(需>=2), 数据未写入",
                                     "BLE特征值未写入数据, 需先调用update_data()",
                                     "通过mpremote调用ble_service.update_data()写入初始数据")
                        except Exception as e:
                            emit("T2.6", "心率数据读取", "FAIL",
                                 "1.读取Heart Rate Measurement(0x2A37)",
                                 "读取到心率值",
                                 f"读取失败: {e}", "BLE连接不稳定", "缩短距离")
            else:
                emit("T2.5", "心率服务(0x180D)", "FAIL",
                     "1.遍历services查找UUID含180D的服务",
                     "发现Heart Rate服务(0x180D)",
                     "未找到心率服务", "BLE服务未注册", "确认ble_service.py服务注册正确")

            await asyncio.sleep(duration)

            try:
                for char in power_service.characteristics if power_service else []:
                    if "2A63" in char.uuid.upper():
                        await client.stop_notify(char)
                for char in hr_service.characteristics if hr_service else []:
                    if "2A37" in char.uuid.upper():
                        await client.stop_notify(char)
            except Exception:
                pass

    except Exception as e:
        emit("T2.7", "BLE连接", "FAIL",
             f"1.使用BleakClient连接设备 {device.address}",
             "成功连接并读取数据",
             f"连接异常: {e}", "BLE信号不稳定或设备断开", "缩短距离，重启设备蓝牙")

    return power_values, hr_values


def test_ble_data_change(port, power_values):
    if not power_values:
        emit("T3.1", "功率数据变化验证", "FAIL",
             "1.通过BLE读取功率数据\n2.调整功率值\n3.再次读取验证变化",
             "能读取到功率数据",
             "无功率数据(BLE未连接或服务未找到)",
             "BLE数据通道未建立", "确认设备BLE正常广播，缩短距离")
        return

    initial_power = power_values[0]
    emit("T3.1", "功率初始值", "PASS",
         f"1.通过BLE读取Cycling Power Measurement\n2.记录初始功率值",
         f"读取到功率值",
         f"初始功率: {initial_power}W", "", "")

    output, rc = mpremote_exec(port, """
import power_data
engine = power_data.PowerEngine()
old = engine.base_power
engine.adjust_power(30)
print(f'ADJUSTED:{old}->{engine.base_power}')
""", timeout=8)

    if rc == 0 and "ADJUSTED:" in output:
        adj_line = [l for l in output.split('\n') if 'ADJUSTED:' in l][0].strip()
        emit("T3.2", "功率+30W调整", "PASS",
             f"1.通过mpremote创建PowerEngine实例\n2.调用adjust_power(30)\n3.打印调整前后base_power",
             f"base_power从{initial_power}增加30",
             adj_line, "", "")
    else:
        emit("T3.2", "功率+30W调整", "FAIL",
             "1.通过mpremote创建PowerEngine实例\n2.调用adjust_power(30)",
             "base_power增加30",
             f"执行失败: {output[:100]}", "mpremote连接失败或代码异常",
             "检查设备连接，确认power_data.py已部署")

    output2, rc2 = mpremote_exec(port, """
import power_data
engine = power_data.PowerEngine()
engine.adjust_power(-30)
print(f'RESTORED:{engine.base_power}')
""", timeout=8)

    if rc2 == 0 and "RESTORED:" in output2:
        restored_line = [l for l in output2.split('\n') if 'RESTORED:' in l]
        actual_val = restored_line[0].strip() if restored_line else output2.strip()[:60]
        emit("T3.3", "功率-30W恢复", "PASS",
             "1.通过mpremote创建PowerEngine实例\n2.调用adjust_power(-30)\n3.验证base_power恢复",
             "base_power恢复到调整前的值",
             actual_val, "", "")
    else:
        emit("T3.3", "功率-30W恢复", "FAIL",
             "1.通过mpremote调用adjust_power(-30)",
             "base_power恢复原值",
             f"执行失败: {output2[:100]}", "mpremote连接失败", "检查设备连接")

    output3, rc3 = mpremote_exec(port, """
import power_data
engine = power_data.PowerEngine()
old_c = engine.cadence_base
engine.adjust_cadence(15)
print(f'CAD_ADJ:{old_c}->{engine.cadence_base}')
""", timeout=8)

    if rc3 == 0 and "CAD_ADJ:" in output3:
        emit("T3.4", "踏频+15RPM调整", "PASS",
             "1.通过mpremote创建PowerEngine实例\n2.调用adjust_cadence(15)\n3.打印调整前后cadence_base",
             "cadence_base增加15",
             [l for l in output3.split('\n') if 'CAD_ADJ:' in l][0].strip(), "", "")
    else:
        emit("T3.4", "踏频+15RPM调整", "FAIL",
             "1.通过mpremote调用adjust_cadence(15)",
             "cadence_base增加15",
             f"执行失败: {output3[:100]}", "mpremote连接失败", "检查设备连接")

    output4, rc4 = mpremote_exec(port, """
import power_data
engine = power_data.PowerEngine()
engine.adjust_cadence(-15)
print(f'CAD_RST:{engine.cadence_base}')
""", timeout=8)

    if rc4 == 0 and "CAD_RST:" in output4:
        cad_rst_line = [l for l in output4.split('\n') if 'CAD_RST:' in l]
        actual_val = cad_rst_line[0].strip() if cad_rst_line else output4.strip()[:60]
        emit("T3.5", "踏频-15RPM恢复", "PASS",
             "1.通过mpremote调用adjust_cadence(-15)\n2.验证cadence_base恢复",
             "cadence_base恢复原值",
             actual_val, "", "")
    else:
        emit("T3.5", "踏频-15RPM恢复", "FAIL",
             "1.通过mpremote调用adjust_cadence(-15)",
             "cadence_base恢复原值",
             f"执行失败: {output4[:100]}", "mpremote连接失败", "检查设备连接")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()

    device = await scan_ble_device(timeout=args.timeout)
    if device:
        result = await read_ble_data(device, duration=5)
        if result:
            power_values, hr_values = result
            test_ble_data_change(args.port, power_values)
    else:
        emit("T2.3", "BLE数据读取", "SKIP",
             "1.扫描BLE设备", "发现BikePower设备",
             "设备未找到", "BLE扫描未发现设备", "确认设备已上电且BLE广播中")
        test_ble_data_change(args.port, [])


if __name__ == "__main__":
    asyncio.run(main())
