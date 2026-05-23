"""
BikePower 自定义 MicroPython 固件 manifest
将项目 Python 模块冻结（freeze）到固件中

用法:
  make BOARD=ESP32_GENERIC_C3 FROZEN_MANIFEST=/path/to/esp32-power/manifest.py

冻结模块的优势:
  - 代码预编译为字节码，启动更快
  - 字节码直接从 Flash 执行，节省 RAM
  - 源代码不可直接访问，保护知识产权
  - 无需文件系统即可运行
"""

include("$(PORT_DIR)/boards/manifest.py")

freeze("$(MPY_DIR)/..", "boot.py")
freeze("$(MPY_DIR)/..", "config.py")
freeze("$(MPY_DIR)/..", "logger.py")
freeze("$(MPY_DIR)/..", "utils.py")
freeze("$(MPY_DIR)/..", "ble_service.py")
freeze("$(MPY_DIR)/..", "power_data.py")
freeze("$(MPY_DIR)/..", "wifi_manager.py")
freeze("$(MPY_DIR)/..", "web_pages.py")
freeze("$(MPY_DIR)/..", "ota_updater.py")
freeze("$(MPY_DIR)/..", "event_bus.py")
freeze("$(MPY_DIR)/..", "app.py")
