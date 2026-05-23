"""
硬件初始化 + OTA 更新校验与安全回滚

运行环境：MicroPython v1.28
"""

import gc
import machine
import os
import time

gc.threshold(4096)
machine.freq(160000000)


def _cleanup_tmp_files():
    """清理 OTA 下载中断残留的 .tmp 文件"""
    try:
        for f in os.listdir():
            if f.endswith('.tmp'):
                try:
                    os.remove(f)
                    print("[INFO][BOOT] 已清理残留临时文件: %s" % f)
                except OSError:
                    pass
    except OSError:
        pass


def _check_ota_integrity():
    """检查 OTA 更新完整性，失败则自动从 .bak 回滚"""
    try:
        files = os.listdir()
    except OSError:
        return

    if '.update_pending' not in files:
        return

    print("[INFO][BOOT] 检测到更新待校验标志，开始完整性校验...")

    core_modules = [
        'config', 'logger', 'utils', 'ble_service',
        'power_data', 'wifi_manager', 'web_pages',
        'ota_updater', 'app'
    ]

    all_ok = True
    for mod in core_modules:
        try:
            __import__(mod)
        except Exception as e:
            print("[INFO][BOOT] 模块校验失败: %s (%s)" % (mod, e))
            all_ok = False
            break

    if all_ok:
        print("[INFO][BOOT] OTA更新校验通过，清理备份文件...")
        for f in files:
            if f.endswith('.bak'):
                try:
                    os.remove(f)
                except OSError:
                    pass
        for f in os.listdir():
            if f.endswith('.mpy'):
                py_name = f[:-4] + '.py'
                if py_name in os.listdir():
                    try:
                        os.remove(py_name)
                        print("[INFO][BOOT] 已删除旧源码: %s" % py_name)
                    except OSError:
                        pass
        try:
            os.remove('.update_pending')
        except OSError:
            pass
        print("[INFO][BOOT] OTA更新成功")
    else:
        print("[INFO][BOOT] OTA更新校验失败，开始回滚...")
        for f in os.listdir():
            if f.endswith('.bak'):
                original = f[:-4]
                try:
                    if original in os.listdir():
                        os.remove(original)
                    os.rename(f, original)
                    print("[INFO][BOOT] 已回滚: %s" % original)
                except OSError as e:
                    print("[INFO][BOOT] 回滚失败: %s (%s)" % (original, e))
        for f in os.listdir():
            if f.endswith('.mpy'):
                try:
                    os.remove(f)
                    print("[INFO][BOOT] 已删除字节码: %s" % f)
                except OSError:
                    pass
        try:
            os.remove('.update_pending')
        except OSError:
            pass
        try:
            os.remove('ota_version.json')
        except OSError:
            pass
        print("[INFO][BOOT] 回滚完成，使用旧版本启动")


_cleanup_tmp_files()
_check_ota_integrity()

if '.deploy' in os.listdir():
    print("[INFO][BOOT] 部署模式：跳过主程序")
else:
    time.sleep_ms(500)
    import app
    app.main()
