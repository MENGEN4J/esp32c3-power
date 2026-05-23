#!/usr/bin/env python3
"""
使用 GitHub API 创建 Release 并上传文件。
"""

import json
import mimetypes
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).parent.parent
API_BASE = "https://api.github.com"


def _load_env():
    env_path = PROJECT_DIR / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


_load_env()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "MENGEN4J")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "esp32c3-power")


def _headers(extra=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "BikePower-release-script",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = "Bearer %s" % GITHUB_TOKEN
    if extra:
        headers.update(extra)
    return headers


def _request(method, url, data=None, expected=(200,), timeout=30, not_found_none=False, headers=None):
    body = None
    req_headers = _headers(headers)
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=req_headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            content = response.read()
            if response.status not in expected:
                print("ERROR: GitHub API 返回 HTTP %d: %s" % (response.status, url))
                return None
            if not content:
                return {}
            text = content.decode("utf-8")
            return json.loads(text) if text else {}
    except HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        if e.code == 404 and not_found_none:
            return None
        print("ERROR: GitHub API 请求失败 HTTP %d: %s" % (e.code, url))
        if text:
            print("响应: %s" % text[:500])
        return None
    except URLError as e:
        print("ERROR: GitHub API 网络请求失败: %s" % e)
        return None


def _api_url(path):
    return "%s/repos/%s/%s%s" % (API_BASE, GITHUB_OWNER, GITHUB_REPO, path)


def get_release(tag):
    return _request("GET", _api_url("/releases/tags/%s" % tag), not_found_none=True)


def create_release(tag, name, description):
    data = {
        "tag_name": tag,
        "target_commitish": "main",
        "name": name,
        "body": description,
        "draft": False,
        "prerelease": False,
    }
    return _request("POST", _api_url("/releases"), data=data, expected=(201,))


def update_release(release_id, tag, name, description):
    data = {
        "tag_name": tag,
        "target_commitish": "main",
        "name": name,
        "body": description,
        "draft": False,
        "prerelease": False,
    }
    return _request("PATCH", _api_url("/releases/%s" % release_id), data=data)


def list_assets(release_id):
    result = _request("GET", _api_url("/releases/%s/assets?per_page=100" % release_id))
    return result or []


def delete_asset(asset_id):
    return _request("DELETE", _api_url("/releases/assets/%s" % asset_id), expected=(204,))


def upload_asset(release, file_path):
    fp = Path(file_path)
    release_id = release.get("id")
    for asset in list_assets(release_id):
        if asset.get("name") == fp.name:
            print("INFO: 删除同名旧附件: %s" % fp.name)
            delete_asset(asset.get("id"))
            break

    upload_url = release.get("upload_url", "").split("{", 1)[0]
    if not upload_url:
        print("ERROR: Release 缺少 upload_url，无法上传: %s" % fp.name)
        return None

    data = fp.read_bytes()
    content_type = mimetypes.guess_type(str(fp))[0] or "application/octet-stream"
    url = "%s?%s" % (upload_url, urlencode({"name": fp.name}))
    headers = {
        "Content-Type": content_type,
        "Content-Length": str(len(data)),
    }
    request = Request(url, data=data, headers=_headers(headers), method="POST")
    try:
        print("上传附件: %s" % fp.name)
        with urlopen(request, timeout=120) as response:
            content = response.read().decode("utf-8")
            if response.status != 201:
                print("ERROR: 上传失败 HTTP %d: %s" % (response.status, fp.name))
                return None
            print("上传成功: %s" % fp.name)
            return json.loads(content)
    except HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        print("ERROR: 上传失败 HTTP %d: %s" % (e.code, fp.name))
        if text:
            print("响应: %s" % text[:500])
        return None
    except URLError as e:
        print("ERROR: 上传网络请求失败: %s" % e)
        return None


def extract_changelog_section(tag):
    changelog = PROJECT_DIR / "CHANGELOG.md"
    if not changelog.exists():
        return ""
    content = changelog.read_text(encoding="utf-8")
    pattern = r"^## %s(?:\s+[^\n]*)?\n(?P<body>.*?)(?=^##\s+v|\Z)" % re.escape(tag)
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if not match:
        return ""
    return match.group("body").strip()


def build_release_description(version, files_to_upload):
    tag = "v%s" % version
    changelog_body = extract_changelog_section(tag)
    if not changelog_body:
        print("ERROR: CHANGELOG.md 中未找到 %s 条目，禁止创建简短 Release" % tag)
        return None
    if "### 测试报告" not in changelog_body:
        print("ERROR: CHANGELOG.md 的 %s 条目缺少测试报告，禁止创建 Release" % tag)
        return None

    file_lines = []
    for fp in files_to_upload:
        size_kb = fp.stat().st_size / 1024
        if fp.name == "firmware.bin":
            desc = "USB 全量烧录固件，适合首次刷机、OTA 失败恢复和全量升级"
        elif fp.name == "version.json":
            desc = "OTA 当前版本清单，设备联网检查更新时读取"
        elif fp.name.endswith("-ota.zip"):
            desc = "OTA 字节码压缩包，包含本版本 `.mpy` 文件"
        else:
            desc = "发布附件"
        file_lines.append("- **`%s`**：%s，大小 %.1f KB" % (fp.name, desc, size_kb))

    required_sections = [
        "## 版本概览",
        "## 本版重点",
        "## 详细变更",
        "## 测试报告",
        "## 下载文件说明",
        "## 使用说明",
        "## 兼容性说明",
        "## 已知限制",
        "## 回滚说明",
        "## 附件清单",
    ]

    body = """## 版本概览

- **版本号**：%s
- **版本类型**：Release
- **适用硬件**：合宙 CORE ESP32-C3
- **适用环境**：MicroPython v1.28
- **升级方式**：USB 全量刷机 / OTA 更新

## 本版重点

%s

## 详细变更

%s

## 测试报告

测试结论以 `CHANGELOG.md` 中 `%s` 条目为准。本版本已记录语法检查、Shell 检查、HTML 解析、Entropy 扫描、OTA 字节码打包、固件编译和未验证项。

## 下载文件说明

%s

## 使用说明

### USB 全量刷机

1. 下载 `firmware.bin`
2. 连接 ESP32-C3 设备到电脑
3. 使用 `bash scripts/flash_firmware.sh -e` 或烧录工具写入固件
4. 重启设备，按用户手册连接 `BikePower`

### OTA 更新

1. 长按 BOOT 进入配网确认窗口
2. 二次确认后连接 `BikePower` 热点
3. 打开 `http://192.168.4.1` 并连接家庭 WiFi
4. 检查更新并点击“立即更新”
5. 等待下载完成和设备自动重启

## 兼容性说明

- **最低升级版本**：v1.8.0
- **MicroPython 版本**：v1.28
- **配置兼容性**：保持现有配置文件格式，OTA 版本字段兼容 `v` 与旧字段 `current_version`

## 已知限制

- ESP32-C3 上 WiFi 与 BLE 互斥，进入配网和 OTA 流程时 BLE 会暂停
- OTA 依赖家庭 WiFi 和 GitHub Raw 下载地址可访问
- WiFi 热点默认无密码，仅建议在短时间可信环境中使用

## 回滚说明

- OTA 更新失败时系统保留 `.bak` 文件并尝试自动回滚
- 若设备无法恢复，可使用 `firmware.bin` 进行 USB 全量刷机

## 附件清单

- [x] `firmware.bin`
- [x] `version.json`
- [x] `%s-ota.zip`
""" % (
        tag,
        "\n".join(line for line in changelog_body.splitlines() if line.startswith("- **")) or "- 详见下方详细变更",
        changelog_body,
        tag,
        "\n".join(file_lines),
        tag,
    )

    for section in required_sections:
        if section not in body:
            print("ERROR: Release 正文缺少章节: %s" % section)
            return None
    return body


def ensure_ota_zip(tag):
    ota_dir = PROJECT_DIR / "releases/ota" / tag
    ota_zip = PROJECT_DIR / "releases/ota" / ("%s-ota.zip" % tag)
    if not ota_dir.exists():
        print("ERROR: OTA 目录不存在: %s（请先执行 scripts/gen_version_json.py）" % ota_dir)
        return None
    if ota_zip.exists():
        ota_zip.unlink()
    print("打包 OTA 文件: %s" % ota_zip.name)
    subprocess.run(
        ["zip", "-r", "-q", str(ota_zip), str(ota_dir.relative_to(PROJECT_DIR))],
        cwd=str(PROJECT_DIR),
        check=True,
    )
    return ota_zip


def main():
    if len(sys.argv) < 2:
        print("用法: python3 scripts/create_github_release.py <version>")
        print("示例: python3 scripts/create_github_release.py 2.0.2")
        return 1
    if not GITHUB_TOKEN:
        print("ERROR: 请先设置 GITHUB_TOKEN 或 GH_TOKEN")
        return 1

    version = sys.argv[1][1:] if sys.argv[1].startswith("v") else sys.argv[1]
    tag = "v%s" % version

    print("=" * 70)
    print("  GitHub Release 创建与上传: %s" % tag)
    print("=" * 70)
    print()

    ota_zip = ensure_ota_zip(tag)
    if ota_zip is None:
        return 1

    version_json = PROJECT_DIR / "releases/latest/version.json"
    firmware_bin = PROJECT_DIR / "target/firmware.bin"
    files_to_upload = [firmware_bin, ota_zip, version_json]

    for fp in files_to_upload:
        if not fp.exists():
            print("ERROR: 文件不存在: %s" % fp)
            return 1
        print("找到文件: %s (%.1f KB)" % (fp.name, fp.stat().st_size / 1024))
    print()

    description = build_release_description(version, files_to_upload)
    if description is None:
        return 1

    release = get_release(tag)
    if release:
        print("Release 已存在: %s" % release.get("name"))
        print("更新 Release 说明...")
        release = update_release(release.get("id"), tag, tag, description)
        if not release:
            return 1
        print("Release 说明已更新")
    else:
        print("创建 Release...")
        release = create_release(tag, tag, description)
        if not release:
            return 1
        print("Release 创建成功: %s" % release.get("name"))
    print()

    print("开始上传文件...")
    for fp in files_to_upload:
        if not upload_asset(release, str(fp)):
            return 1
    print()

    print("=" * 70)
    print("完成: https://github.com/%s/%s/releases/tag/%s" % (GITHUB_OWNER, GITHUB_REPO, tag))
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
