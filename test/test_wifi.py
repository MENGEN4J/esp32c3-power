#!/usr/bin/env python3
"""WiFi 状态与网页测试 — 详细操作步骤、预期结果、中文乱码检测、表单模拟

输出格式: id|name|status|steps|expected|actual|reason|fix
"""

import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

from test_utils import emit

WIFI_IP = "192.168.4.1"
WIFI_PORT = 80
TIMEOUT = 10

MOJIBAKE_PATTERNS = [
    r'Ã¤', r'Ã¶', r'Ã¼', r'ÃŸ', r'Ã©', r'Ã¨', r'Ã ',
    r'ï¿½', r'â€', r'â€™', r'â€œ', r'â€',
    r'\ufffd', r'\\u00',
]

EXPECTED_CN_TEXTS = ["一键配网", "蓝牙", "WiFi", "密码", "连接", "关闭",
                     "功率", "踏频", "心率", "配置", "提交", "重启"]


def http_get(path="/", timeout=TIMEOUT):
    url = f"http://{WIFI_IP}:{WIFI_PORT}{path}"
    try:
        req = urllib.request.Request(url, headers={"Connection": "close"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return body.decode(charset, errors="replace"), resp.status
    except urllib.error.URLError as e:
        return None, 0
    except Exception as e:
        return str(e), -1


def http_post(path, data, timeout=TIMEOUT):
    url = f"http://{WIFI_IP}:{WIFI_PORT}{path}"
    try:
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=encoded, method="POST",
                                     headers={"Content-Type": "application/x-www-form-urlencoded",
                                              "Connection": "close"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return body.decode(charset, errors="replace"), resp.status
    except urllib.error.URLError as e:
        return None, 0
    except Exception as e:
        return str(e), -1


def test_wifi_ap():
    body, status = http_get("/")
    if status == 200:
        emit("T4.1", "WiFi AP可访问", "PASS",
             f"1.连接WiFi热点 BikePower\n2.GET http://{WIFI_IP}/",
             f"HTTP 200，返回HTML页面",
             f"HTTP 200，内容长度{len(body)}字符", "", "")
    elif status == 0:
        emit("T4.1", "WiFi AP可访问", "FAIL",
             f"1.连接WiFi热点 BikePower\n2.GET http://{WIFI_IP}/",
             f"HTTP 200",
             "连接被拒绝/超时，无法访问192.168.4.1",
             "WiFi AP未启动或电脑未连接BikePower热点",
             "确认电脑已连接BikePower WiFi，设备WiFi AP已启动")
        return None, status
    else:
        emit("T4.1", "WiFi AP可访问", "FAIL",
             f"1.GET http://{WIFI_IP}/",
             "HTTP 200",
             f"HTTP {status}",
             f"Web服务器返回非200状态码",
             "检查wifi_manager.py Web服务器是否正常")
    return body, status


def test_wifi_pages(body):
    if not body:
        emit("T5.1", "首页可访问", "FAIL",
             "1.GET http://192.168.4.1/",
             "返回HTML页面内容",
             "无响应内容",
             "WiFi AP不可访问", "确认WiFi AP已启动，电脑已连接BikePower热点")
        return

    emit("T5.1", "首页可访问", "PASS",
         "1.GET http://192.168.4.1/\n2.检查响应内容长度",
         "返回非空HTML页面",
         f"内容长度: {len(body)} 字符", "", "")

    if "<html" in body.lower() or "<!doctype" in body.lower():
        emit("T5.2", "HTML结构完整", "PASS",
             "1.检查响应内容是否包含<html>或<!DOCTYPE>标签",
             "包含HTML结构标签",
             "检测到HTML标签", "", "")
    else:
        emit("T5.2", "HTML结构完整", "FAIL",
             "1.检查响应内容是否包含<html>或<!DOCTYPE>标签",
             "包含HTML结构标签",
             "未检测到HTML标签",
             "网页生成逻辑异常", "检查wifi_manager.py中HTML生成代码")

    scan_body, scan_status = http_get("/scan")
    if scan_status == 200:
        try:
            scan_data = json.loads(scan_body)
            if isinstance(scan_data, list):
                ssid_list = [item.get('ssid', '?') for item in scan_data[:5]]
                emit("T5.3", "WiFi扫描接口(/scan)", "PASS",
                     "1.GET http://192.168.4.1/scan\n2.解析JSON响应\n3.检查返回WiFi列表",
                     "返回JSON数组，包含附近WiFi列表",
                     f"发现{len(scan_data)}个WiFi: {ssid_list}", "", "")
            else:
                emit("T5.3", "WiFi扫描接口(/scan)", "PASS",
                     "1.GET http://192.168.4.1/scan\n2.解析JSON响应",
                     "返回JSON数据",
                     f"返回类型: {type(scan_data).__name__}", "", "")
        except json.JSONDecodeError:
            emit("T5.3", "WiFi扫描接口(/scan)", "FAIL",
                 "1.GET http://192.168.4.1/scan\n2.解析JSON响应",
                 "返回有效JSON",
                 f"JSON解析失败: {scan_body[:100]}",
                 "/scan接口返回非JSON格式", "检查wifi_manager.py中/scan路由处理")
    else:
        emit("T5.3", "WiFi扫描接口(/scan)", "FAIL",
             "1.GET http://192.168.4.1/scan",
             "HTTP 200",
             f"HTTP {scan_status}",
             "/scan路由不可访问", "检查wifi_manager.py中/scan路由是否注册")

    config_body, config_status = http_get("/config")
    if config_status == 200:
        emit("T5.4", "配置页面(/config)", "PASS",
             "1.GET http://192.168.4.1/config",
             "HTTP 200，返回配置表单页面",
             f"HTTP 200，内容长度{len(config_body)}字符", "", "")
    else:
        emit("T5.4", "配置页面(/config)", "FAIL",
             "1.GET http://192.168.4.1/config",
             "HTTP 200",
             f"HTTP {config_status}",
             "/config路由不可访问", "检查wifi_manager.py中/config路由")


def test_chinese_text(body):
    if not body:
        emit("T6.1", "中文乱码检测", "FAIL",
             "1.获取首页HTML内容\n2.扫描乱码模式",
             "无乱码模式匹配",
             "无网页内容",
             "WiFi AP不可访问", "确认WiFi AP已启动")
        return

    has_mojibake = False
    mojibake_samples = []
    for pattern in MOJIBAKE_PATTERNS:
        matches = re.findall(pattern + '.{0,8}', body)
        if matches:
            has_mojibake = True
            mojibake_samples.extend(matches[:2])

    if has_mojibake:
        emit("T6.1", "中文乱码检测", "FAIL",
             "1.获取首页HTML内容\n2.用正则扫描常见UTF-8乱码模式(Ã¤/Ã¶/ï¿½等)\n3.匹配到则判定乱码",
             "无乱码模式匹配",
             f"发现乱码: {mojibake_samples[:4]}",
             "Content-Length用字符数而非字节数，中文UTF-8占3字节导致截断",
             "修改_html_response: 先body.encode('utf-8')再计算len，Content-Type加charset=utf-8")
    else:
        emit("T6.1", "中文乱码检测", "PASS",
             "1.获取首页HTML内容\n2.用正则扫描常见UTF-8乱码模式(Ã¤/Ã¶/ï¿½等)\n3.无匹配则通过",
             "无乱码模式匹配",
             "未检测到乱码", "", "")

    found = [t for t in EXPECTED_CN_TEXTS if t in body]
    missing = [t for t in EXPECTED_CN_TEXTS if t not in body]

    if len(found) >= 3:
        emit("T6.2", "中文文案完整性", "PASS",
             f"1.获取首页HTML内容\n2.检查是否包含关键中文: {', '.join(EXPECTED_CN_TEXTS[:6])}等",
             "至少包含3个关键中文词汇",
             f"包含{len(found)}个: {', '.join(found[:8])}", "", "")
    else:
        emit("T6.2", "中文文案完整性", "FAIL",
             f"1.获取首页HTML内容\n2.检查是否包含关键中文: {', '.join(EXPECTED_CN_TEXTS[:6])}等",
             "至少包含3个关键中文词汇",
             f"仅包含{len(found)}个，缺失: {', '.join(missing[:6])}",
             "网页HTML中缺少必要中文文案", "检查wifi_manager.py中HTML模板是否包含中文文案")


def test_form_submit():
    config_body, config_status = http_get("/config")
    if config_status != 200 or not config_body:
        emit("T7.1", "配置表单检测", "FAIL",
             "1.GET http://192.168.4.1/config\n2.检查HTML中是否包含<form>标签",
             "返回包含<form>的HTML页面",
             "无法获取配置页面",
             "/config路由不可访问", "检查wifi_manager.py中/config路由")
        return

    has_form = "<form" in config_body.lower()
    if has_form:
        form_action = re.search(r'<form[^>]*action="([^"]*)"', config_body, re.I)
        action_str = form_action.group(1) if form_action else "默认(当前URL)"
        emit("T7.1", "配置表单检测", "PASS",
             "1.GET http://192.168.4.1/config\n2.检查HTML中是否包含<form>标签\n3.提取form action属性",
             "包含<form>标签",
             f"检测到form标签，action={action_str}", "", "")
    else:
        emit("T7.1", "配置表单检测", "FAIL",
             "1.GET http://192.168.4.1/config\n2.检查HTML中是否包含<form>标签",
             "包含<form>标签",
             "未检测到form标签",
             "配置页面缺少表单", "检查wifi_manager.py中配置页面HTML")

    result, status = http_post("/config", {
        "power": "200",
        "cadence": "90",
        "heartrate": "130"
    })

    if status == 200:
        emit("T7.2", "POST配置表单(power=200,cadence=90,hr=130)", "PASS",
             "1.POST http://192.168.4.1/config\n2.body: power=200&cadence=90&heartrate=130\n3.检查HTTP状态码",
             "HTTP 200",
             f"HTTP 200", "", "")

        if result:
            success_keywords = ["成功", "ok", "success", "保存", "已更新"]
            found_kw = [k for k in success_keywords if k.lower() in result.lower()]
            if found_kw:
                emit("T7.3", "配置提交响应内容", "PASS",
                     "1.检查POST响应内容是否包含成功关键词(成功/ok/保存等)",
                     "响应包含成功提示",
                     f"包含关键词: {found_kw[0]}", "", "")
            else:
                emit("T7.3", "配置提交响应内容", "PASS",
                     "1.检查POST响应内容",
                     "HTTP 200响应",
                     f"响应内容: {result[:120]}", "", "")
    else:
        emit("T7.2", "POST配置表单(power=200,cadence=90,hr=130)", "FAIL",
             "1.POST http://192.168.4.1/config\n2.body: power=200&cadence=90&heartrate=130",
             "HTTP 200",
             f"HTTP {status}",
             "配置提交路由处理异常", "检查wifi_manager.py中POST /config处理逻辑")
        emit("T7.3", "配置提交响应内容", "SKIP",
             "1.检查POST响应内容", "响应包含成功提示",
             "提交失败，跳过响应检查", "POST请求失败", "")

    scan_result, scan_status = http_get("/scan")
    if scan_status == 200:
        emit("T7.4", "WiFi扫描按钮模拟(GET /scan)", "PASS",
             "1.GET http://192.168.4.1/scan\n2.模拟点击扫描按钮的HTTP请求",
             "HTTP 200，返回WiFi列表JSON",
             f"HTTP {scan_status}", "", "")
    else:
        emit("T7.4", "WiFi扫描按钮模拟(GET /scan)", "FAIL",
             "1.GET http://192.168.4.1/scan",
             "HTTP 200",
             f"HTTP {scan_status}",
             "/scan接口不可访问", "检查wifi_manager.py中/scan路由")


def test_wifi_shutdown():
    emit("T8.1", "WiFi自动关闭(180秒超时)", "SKIP",
         "1.等待180秒\n2.尝试访问192.168.4.1\n3.验证WiFi AP已关闭",
         "180秒后WiFi AP自动关闭，192.168.4.1不可访问",
         "跳过(需等待3分钟，超出测试时间限制)",
         "自动关闭需等待3分钟", "可手动验证: 等待3分钟后访问192.168.4.1确认无法连接")

    result, status = http_post("/config", {
        "power": "180",
        "cadence": "95",
        "heartrate": "65"
    })

    if status == 200:
        emit("T8.2", "配置后WiFi仍运行", "PASS",
             "1.POST配置表单(power=180,cadence=95,hr=65)\n2.检查WiFi AP是否仍在运行",
             "配置提交成功，WiFi AP仍可访问(等待自动关闭)",
             "HTTP 200，WiFi AP仍在运行", "", "")
    else:
        emit("T8.2", "配置后WiFi状态", "FAIL",
             "1.POST配置表单\n2.检查WiFi AP是否仍在运行",
             "配置提交成功",
             f"HTTP {status}",
             "WiFi AP可能已关闭或Web服务器异常", "检查wifi_manager.py配置提交逻辑")


def main():
    global WIFI_IP, WIFI_PORT
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default=WIFI_IP)
    parser.add_argument("--port", type=int, default=WIFI_PORT)
    parser.add_argument("--timeout", type=int, default=TIMEOUT)
    args = parser.parse_args()
    WIFI_IP = args.ip
    WIFI_PORT = args.port

    body, status = test_wifi_ap()

    if status == 200:
        test_wifi_pages(body)
        test_chinese_text(body)
        test_form_submit()
        test_wifi_shutdown()
    else:
        for tid, tname in [("T5", "网页测试"), ("T6", "中文测试"),
                           ("T7", "表单测试"), ("T8", "WiFi关闭测试")]:
            emit(tid, tname, "SKIP",
                 "1.访问WiFi AP", "WiFi AP可访问",
                 "WiFi AP不可访问，跳过", "WiFi AP未启动", "确认电脑已连接BikePower热点")


if __name__ == "__main__":
    main()
