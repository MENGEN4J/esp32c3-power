#!/usr/bin/env python3
"""
使用 Gitee API 创建 Release 并上传文件
"""

import os
import re
import sys
from pathlib import Path

GITEE_TOKEN = os.environ.get("GITEE_TOKEN", "")

def _load_env():
    env_path = Path(__file__).parent.parent / ".env"
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
if not GITEE_TOKEN:
    GITEE_TOKEN = os.environ.get("GITEE_TOKEN", "")
GITEE_OWNER = "mengen4jv"
GITEE_REPO = "esp32-power"

PROJECT_DIR = Path(__file__).parent.parent
API_BASE = "https://gitee.com/api/v5/repos/%s/%s" % (GITEE_OWNER, GITEE_REPO)


def create_release(tag, name, description):
    url = "%s/releases" % API_BASE
    headers = {"Authorization": "token %s" % GITEE_TOKEN}
    data = {
        "tag_name": tag,
        "name": name,
        "body": description,
        "prerelease": False,
        "target_commitish": "main",
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print("❌ 创建 Release 失败: %s" % e)
        if hasattr(e, "response") and e.response is not None:
            print("响应: %s" % e.response.text)
        return None


def get_release(tag):
    url = "%s/releases/tags/%s" % (API_BASE, tag)
    headers = {"Authorization": "token %s" % GITEE_TOKEN}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None


def update_release(release_id, tag, name, description):
    url = "%s/releases/%s" % (API_BASE, release_id)
    headers = {"Authorization": "token %s" % GITEE_TOKEN}
    data = {
        "tag_name": tag,
        "name": name,
        "body": description,
        "prerelease": False,
    }
    try:
        response = requests.patch(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print("❌ 更新 Release 说明失败: %s" % e)
        if hasattr(e, "response") and e.response is not None:
            print("响应: %s" % e.response.text)
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
        print("❌ CHANGELOG.md 中未找到 %s 条目，禁止创建简短 Release" % tag)
        return None
    if "### 测试报告" not in changelog_body:
        print("❌ CHANGELOG.md 的 %s 条目缺少测试报告，禁止创建 Release" % tag)
        return None

    file_lines = []
    for fp in files_to_upload:
        size_kb = fp.stat().st_size / 1024
        if fp.name == "firmware.bin":
            desc = "USB 全量烧录固件，适合首次刷机、OTA 失败恢复和全量升级"
        elif fp.name == "version.json":
            desc = "OTA 当前版本清单，设备联网检查更新时读取"
        elif fp.name.endswith("-ota.zip"):
            desc = "OTA 字节码压缩包，包含本版本 9 个 `.mpy` 文件"
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

测试结论以 `CHANGELOG.md` 中 `%s` 条目为准。本版本已记录语法检查、Shell 检查、HTML 解析、Entropy 扫描、OTA 字节码打包、固件编译和真机部署结果。

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
- OTA 依赖家庭 WiFi 和 Gitee Raw 下载地址可访问
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
            print("❌ Release 正文缺少章节: %s" % section)
            return None
    return body


def upload_asset(release_id, file_path):
    url = "%s/releases/%s/attach_files" % (API_BASE, release_id)
    headers = {"Authorization": "token %s" % GITEE_TOKEN}
    file_name = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        files = {"file": (file_name, f)}
        try:
            print("📤 正在上传: %s..." % file_name)
            response = requests.post(url, headers=headers, files=files, timeout=120)
            response.raise_for_status()
            print("✅ 上传成功: %s" % file_name)
            return response.json()
        except requests.exceptions.RequestException as e:
            print("❌ 上传失败: %s - %s" % (file_name, e))
            if hasattr(e, "response") and e.response is not None:
                print("响应: %s" % e.response.text[:200])
            return None


def main():
    if len(sys.argv) < 2:
        print("用法: python3 create_gitee_release.py <version>")
        print("示例: python3 create_gitee_release.py 1.9.2")
        return 1
    if not GITEE_TOKEN:
        print("ERROR: 请先设置环境变量 GITEE_TOKEN")
        return 1
    global requests
    import requests

    version = sys.argv[1]
    tag = "v%s" % version

    print("=" * 70)
    print("  Gitee Release 创建与上传: %s" % tag)
    print("=" * 70)
    print()

    ota_dir = PROJECT_DIR / "releases/ota" / tag
    ota_zip = PROJECT_DIR / "releases/ota" / ("%s-ota.zip" % tag)
    version_json = PROJECT_DIR / "releases/latest/version.json"
    firmware_bin = PROJECT_DIR / "target/firmware.bin"

    if not ota_dir.exists():
        print("❌ OTA 目录不存在: %s（请先执行 scripts/gen_version_json.py）" % ota_dir)
        return 1

    if not ota_zip.exists():
        print("📦 打包 OTA 文件...")
        import subprocess
        ota_zip.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["zip", "-r", str(ota_zip), str(ota_dir.relative_to(PROJECT_DIR))], cwd=str(PROJECT_DIR), check=True)

    files_to_upload = [ota_zip, version_json]

    if firmware_bin.exists():
        files_to_upload.append(firmware_bin)
    else:
        print("⚠️ 固件文件不存在: %s（请先执行 bash scripts/build_firmware.sh）" % firmware_bin)

    for fp in files_to_upload:
        if not fp.exists():
            print("❌ 文件不存在: %s" % fp)
            return 1
        print("✅ 找到文件: %s (%.1f KB)" % (fp.name, fp.stat().st_size / 1024))
    print()

    description = build_release_description(version, files_to_upload)
    if description is None:
        return 1

    release = get_release(tag)
    if release:
        print("ℹ️ Release 已存在: %s" % release.get("name"))
        release_id = release.get("id")
        print("📝 更新 Release 说明...")
        release = update_release(release_id, tag, tag, description)
        if not release:
            return 1
        print("✅ Release 说明已更新")
    else:
        print("✨ 创建 Release...")
        release = create_release(tag, tag, description)
        if not release:
            return 1
        release_id = release.get("id")
        print("✅ Release 创建成功: %s" % release.get("name"))
    print()

    print("📤 开始上传文件...")
    for fp in files_to_upload:
        upload_asset(release_id, str(fp))
    print()

    print("=" * 70)
    print("🎉 完成！访问: https://gitee.com/%s/%s/releases" % (GITEE_OWNER, GITEE_REPO))
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
