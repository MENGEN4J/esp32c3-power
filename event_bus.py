"""
轻量事件总线模块
职责：模块间解耦通信，发布/订阅模式，零依赖

运行环境：MicroPython v1.28
"""

from logger import get_logger

log = get_logger("EVENT")


class EventBus:
    """轻量级同步事件总线，支持发布/订阅模式"""

    def __init__(self):
        self._subscribers = {}

    def subscribe(self, event_type, handler):
        """
        订阅事件

        Args:
            event_type: 事件类型字符串
            handler: 回调函数，接收 event_type 和 **kwargs
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def publish(self, event_type, **kwargs):
        """
        发布事件，同步调用所有订阅者

        Args:
            event_type: 事件类型字符串
            **kwargs: 事件数据
        """
        handlers = self._subscribers.get(event_type)
        if not handlers:
            return
        for handler in handlers:
            try:
                handler(event_type, **kwargs)
            except Exception as e:
                log.error("事件处理异常[%s]: %s" % (event_type, e))

    def unsubscribe(self, event_type, handler):
        """
        取消订阅

        Args:
            event_type: 事件类型字符串
            handler: 要移除的回调函数
        """
        handlers = self._subscribers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)
            if not handlers:
                del self._subscribers[event_type]


bus = EventBus()

EVENT_POWER_CHANGED = "power_changed"
EVENT_CADENCE_CHANGED = "cadence_changed"
EVENT_MODE_CHANGED = "mode_changed"
EVENT_HEARTRATE_CHANGED = "heartrate_changed"
EVENT_ERG_TARGET = "erg_target"
EVENT_BLE_CONNECTED = "ble_connected"
EVENT_BLE_DISCONNECTED = "ble_disconnected"
EVENT_WIFI_START = "wifi_start"
EVENT_OTA_STATUS = "ota_status"
EVENT_CONFIG_DIRTY = "config_dirty"
