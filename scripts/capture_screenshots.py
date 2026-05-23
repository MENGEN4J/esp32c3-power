#!/usr/bin/env python3
"""
生成 BikePower 网页配置预览资源。

运行环境: CPython 3.x（本地文档/截图生成）
"""

import html
import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
WEB_DIR = PROJECT_ROOT / "web"
IMAGES_DIR = PROJECT_ROOT / "images"
WEB_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

if "micropython" not in sys.modules:
    micropython = types.ModuleType("micropython")
    micropython.const = lambda value: value
    sys.modules["micropython"] = micropython

sys.path.insert(0, str(PROJECT_ROOT))
import config  # noqa: E402
import web_pages  # noqa: E402


def _pages():
    """返回手册截图使用的页面 HTML。"""
    version = config.FIRMWARE_VERSION
    return [
        ("page1_home", "首页配置表单", web_pages.build_config_page(
            200, 90, 140, config.RIDE_MODE_STEADY, False, None, version
        )),
        ("page2_wifi_scan", "WiFi 扫描选择", web_pages.build_wifi_setup_page()),
        ("page3_config", "WiFi 已连接配置页", web_pages.build_config_page(
            200, 90, 140, config.RIDE_MODE_ROAD, True, {"has_update": False}, version
        )),
        ("page4_update_available", "有更新提示", web_pages.build_config_page(
            200, 90, 140, config.RIDE_MODE_STEADY, True,
            {"has_update": True, "version": "2.0.0", "changelog": "新增: 支持更多骑行 App；优化: 配网页面体验；修复: 连接稳定性问题"},
            version
        )),
        ("page5_success", "保存成功页", web_pages.build_success_page(200, 90, 140, config.RIDE_MODE_ROAD)),
        ("page6_update_progress", "固件更新页", web_pages.build_update_page({
            "completed": 6,
            "total": 9,
            "percent": 67,
            "downloaded_bytes": 323584,
            "total_bytes": 479232
        })),
    ]


def create_html_previews():
    """创建单独的预览 HTML 文件，每个页面一个文件。"""
    html_files = []
    for filename, title, content in _pages():
        filepath = WEB_DIR / (filename + ".html")
        filepath.write_text(content, encoding="utf-8")
        html_files.append((filename, title, filepath))
        print("创建: %s" % filepath.name)
    return html_files


def _iframe(content):
    return '<iframe srcdoc="%s"></iframe>' % html.escape(content, quote=True)


def write_config_preview():
    """生成普通网格预览页。"""
    cards = []
    for _, title, content in _pages():
        cards.append('<div class="preview-card"><h2>%s</h2><div class="iframe-box">%s</div></div>' % (html.escape(title), _iframe(content)))
    body = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BikePower 配置界面预览</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#f6f8fb;padding:24px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;color:#172033}
.container{max-width:1280px;margin:0 auto}
h1{text-align:center;margin-bottom:8px;font-size:28px}
.subtitle{text-align:center;color:#667085;margin-bottom:24px}
.preview-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:22px}
.preview-card{background:#fff;border-radius:18px;padding:16px;box-shadow:0 8px 28px rgba(16,24,40,.08)}
.preview-card h2{font-size:16px;color:#344054;margin-bottom:12px;text-align:center}
.iframe-box{background:#f8fafc;border-radius:14px;overflow:hidden;display:flex;justify-content:center;border:1px solid #e4e7ec}
iframe{border:none;width:500px;height:844px;background:#fff;transform:scale(.64);transform-origin:top center;margin-bottom:-304px}
</style>
</head>
<body><div class="container"><h1>BikePower 网页配置界面预览</h1><p class="subtitle">与 web_pages.py 实际页面保持一致</p><div class="preview-grid">__CARDS__</div></div></body></html>""".replace("__CARDS__", "\n".join(cards))
    (WEB_DIR / "config-preview.html").write_text(body, encoding="utf-8")


def write_screenshots_page():
    """生成手机框架展示页。"""
    cards = []
    for idx, (_, title, content) in enumerate(_pages(), 1):
        cards.append('<div class="card"><h2><span>%d</span>%s</h2><div class="phone"><div class="notch"></div><div class="screen">%s</div></div></div>' % (idx, html.escape(title), _iframe(content)))
    body = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BikePower 网页配置界面截图</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#f0f2f5;padding:28px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;color:#172033}
.container{max-width:1380px;margin:0 auto}
h1{text-align:center;margin-bottom:8px;font-size:28px}.subtitle{text-align:center;color:#667085;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px}.card{background:#fff;border-radius:18px;padding:16px;box-shadow:0 8px 28px rgba(16,24,40,.08)}
.card h2{text-align:center;font-size:16px;margin-bottom:12px;color:#344054}.card h2 span{display:inline-block;background:#d64560;color:#fff;border-radius:50%;width:28px;height:28px;line-height:28px;margin-right:8px}
.phone{background:#1f2937;border-radius:32px;padding:12px;box-shadow:0 8px 24px rgba(16,24,40,.18)}.notch{width:120px;height:24px;background:#111827;border-radius:0 0 14px 14px;margin:0 auto 10px}
.screen{background:#fff;border-radius:20px;overflow:hidden;height:560px;display:flex;justify-content:center}iframe{border:none;width:500px;height:844px;transform:scale(.66);transform-origin:top center}
@media print{body{background:#fff}.card{break-inside:avoid;box-shadow:none;border:1px solid #ddd}}
</style>
</head><body><div class="container"><h1>BikePower 网页配置界面</h1><p class="subtitle">用于用户手册配图和页面快速校对</p><div class="grid">__CARDS__</div></div></body></html>""".replace("__CARDS__", "\n".join(cards))
    (WEB_DIR / "screenshots.html").write_text(body, encoding="utf-8")


def write_screenshot_tool():
    """生成截图辅助说明页。"""
    rows = []
    for filename, title, _ in _pages():
        rows.append('<tr><td>%s</td><td><code>images/%s.png</code></td></tr>' % (html.escape(title), filename))
    body = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BikePower 网页截图工具</title>
<style>
body{margin:0;background:#f6f8fb;color:#172033;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;padding:32px}.box{max-width:900px;margin:0 auto;background:#fff;border-radius:20px;padding:28px;box-shadow:0 8px 28px rgba(16,24,40,.08)}
h1{margin:0 0 8px}.muted{color:#667085;line-height:1.7}.actions{display:flex;gap:12px;flex-wrap:wrap;margin:22px 0}.btn{display:inline-block;padding:12px 18px;border-radius:12px;text-decoration:none;font-weight:700}.primary{background:#d64560;color:#fff}.secondary{background:#fff;color:#d64560;border:2px solid #d64560}table{width:100%;border-collapse:collapse;margin-top:18px}th,td{border:1px solid #e4e7ec;padding:10px;text-align:left}th{background:#f8fafc}code{background:#eef2ff;padding:2px 6px;border-radius:6px}
</style>
</head><body><div class="box"><h1>BikePower 网页截图工具</h1><p class="muted">预览页面由 <code>scripts/capture_screenshots.py</code> 从 <code>web_pages.py</code> 自动生成。正式截图建议按 MEMORY.md 中的 DevTools 协议流程生成，避免 Chrome 截到已有浏览器窗口。</p><div class="actions"><a class="btn primary" href="config-preview.html">查看网格预览</a><a class="btn secondary" href="screenshots.html">查看手机框架</a></div><table><thead><tr><th>页面</th><th>输出图片</th></tr></thead><tbody>__ROWS__</tbody></table></div></body></html>""".replace("__ROWS__", "\n".join(rows))
    (WEB_DIR / "screenshot_tool.html").write_text(body, encoding="utf-8")


def generate_manual_assets():
    """生成手册配图相关 HTML 资源。"""
    print("BikePower 网页界面资源生成")
    html_files = create_html_previews()
    write_config_preview()
    write_screenshots_page()
    write_screenshot_tool()
    print("完成，共生成 %d 个临时页面和 3 个预览页面" % len(html_files))
    print("截图完成后请删除 web/page*.html，避免提交临时文件")


if __name__ == "__main__":
    generate_manual_assets()
