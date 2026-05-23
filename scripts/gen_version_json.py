#!/usr/bin/env python3
"""
OTA 发版脚本：编译 .mpy + 生成 version.json

用法:
  python3 scripts/gen_version_json.py --version 1.9.0 --min-version 1.8.0 \
    --mpy-version v1.28 --gitee-user user --gitee-repo esp32-power

选项:
  --version       目标版本号 (必填)
  --min-version   最低可升级版本 (默认 1.8.0)
  --mpy-version   MicroPython 版本 (默认 v1.28)
  --gitee-user    Gitee 用户名 (必填)
  --gitee-repo    Gitee 仓库名 (默认 esp32-power)
  --mpy-cross     mpy-cross 路径 (默认自动查找)
  --output-dir    version.json 输出目录 (默认 releases/latest)
  --files         要包含的文件列表 (默认自动检测变更)
"""

import argparse
import binascii
import json
import os
import shutil
import subprocess
import sys


BIZ_MODULES = [
    'app.py', 'config.py', 'logger.py', 'utils.py',
    'ble_service.py', 'power_data.py', 'wifi_manager.py',
    'web_pages.py', 'ota_updater.py', 'event_bus.py'
]


def find_mpy_cross():
    candidates = [
        'micropython/mpy-cross/build/mpy-cross',
        'micropython/mpy-cross/build/mpy-cross.exe',
        os.path.expanduser('~/.local/bin/mpy-cross'),
        '/usr/local/bin/mpy-cross',
        'mpy-cross',
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
        try:
            result = subprocess.run([c, '--version'], capture_output=True, timeout=5)
            if result.returncode == 0:
                return c
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def compile_mpy(mpy_cross_path, py_file, output_dir):
    mpy_file = os.path.splitext(os.path.basename(py_file))[0] + '.mpy'
    out_path = os.path.join(output_dir, mpy_file)
    result = subprocess.run(
        [mpy_cross_path, '-o', out_path, py_file],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("ERROR: 编译失败 %s: %s" % (py_file, result.stderr))
        return None
    return out_path


def crc32_file(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    return '%08x' % (binascii.crc32(data) & 0xFFFFFFFF)


def main():
    parser = argparse.ArgumentParser(description='OTA 发版脚本')
    parser.add_argument('--version', required=True, help='目标版本号')
    parser.add_argument('--min-version', default='1.8.0', help='最低可升级版本')
    parser.add_argument('--mpy-version', default='v1.28', help='MicroPython 版本')
    parser.add_argument('--gitee-user', required=True, help='Gitee 用户名')
    parser.add_argument('--gitee-repo', default='esp32-power', help='Gitee 仓库名')
    parser.add_argument('--mpy-cross', default=None, help='mpy-cross 路径')
    parser.add_argument('--output-dir', default=None, help='输出目录')
    parser.add_argument('--files', nargs='*', default=None, help='要包含的文件')
    args = parser.parse_args()

    version_tag = 'v' + args.version
    version_dir = os.path.join('releases', 'ota', version_tag)
    output_dir = args.output_dir or os.path.join('releases', 'latest')

    mpy_cross = args.mpy_cross or find_mpy_cross()
    if not mpy_cross:
        print("ERROR: 未找到 mpy-cross，请指定 --mpy-cross 路径")
        sys.exit(1)
    print("mpy-cross: %s" % mpy_cross)

    os.makedirs(version_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    files_to_process = args.files or BIZ_MODULES

    version_json = {
        'version': args.version,
        'min_version': args.min_version,
        'mpy_version': args.mpy_version,
        'changelog': '',
        'files': []
    }

    for py_file in files_to_process:
        if not os.path.isfile(py_file):
            print("WARN: 文件不存在，跳过: %s" % py_file)
            continue

        mpy_path = compile_mpy(mpy_cross, py_file, version_dir)
        if not mpy_path:
            continue

        mpy_name = os.path.basename(mpy_path)
        file_hash = crc32_file(mpy_path)
        file_size = os.path.getsize(mpy_path)
        gitee_url = 'https://gitee.com/%s/%s/raw/v%s/releases/ota/v%s/%s' % (
            args.gitee_user, args.gitee_repo, args.version, args.version, mpy_name
        )

        version_json['files'].append({
            'name': mpy_name,
            'hash': file_hash,
            'size': file_size,
            'url': gitee_url
        })

        src_size = os.path.getsize(py_file)
        ratio = (1 - file_size / src_size) * 100 if src_size > 0 else 0
        print("  %s -> %s (%d -> %d bytes, -%.0f%%)" % (
            py_file, mpy_name, src_size, file_size, ratio
        ))

    version_json_path = os.path.join(output_dir, 'version.json')
    with open(version_json_path, 'w') as f:
        json.dump(version_json, f, indent=2, ensure_ascii=False)

    print()
    print("version.json 已生成: %s" % version_json_path)
    print("版本: %s" % version_json['version'])
    print("MPY: %s" % version_json['mpy_version'])
    print("文件数: %d" % len(version_json['files']))
    total_size = sum(f['size'] for f in version_json['files'])
    print("总大小: %d bytes" % total_size)
    print()
    print("下一步:")
    print("  1. git add %s/ %s" % (version_dir, output_dir))
    print("  2. git commit -m \"release: v%s\"" % args.version)
    print("  3. git tag v%s" % args.version)
    print("  4. git push origin main --tags")


if __name__ == '__main__':
    main()
