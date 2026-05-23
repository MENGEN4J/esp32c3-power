"""
轻量级日志模块
替代 print()，支持日志级别过滤，统一日志格式

运行环境：MicroPython v1.28
"""

DEBUG = 0
INFO = 1
WARNING = 2
ERROR = 3

_level_names = {DEBUG: "DEBUG", INFO: "INFO", WARNING: "WARN", ERROR: "ERROR"}

class Logger:
    """轻量级日志器，替代 print 输出"""

    def __init__(self, name, level=INFO):
        """
        初始化日志器

        Args:
            name: 模块名称，用于日志前缀
            level: 最低日志级别，低于此级别的日志不输出
        """
        self.name = name
        self.level = level

    def _log(self, level, msg):
        if level >= self.level:
            print("[%s][%s] %s" % (_level_names.get(level, "????"), self.name, msg))

    def debug(self, msg):
        """输出 DEBUG 级别日志"""
        self._log(DEBUG, msg)

    def info(self, msg):
        """输出 INFO 级别日志"""
        self._log(INFO, msg)

    def warning(self, msg):
        """输出 WARNING 级别日志"""
        self._log(WARNING, msg)

    def error(self, msg):
        """输出 ERROR 级别日志"""
        self._log(ERROR, msg)


_loggers = {}

def get_logger(name, level=INFO):
    """
    获取或创建命名日志器

    Args:
        name: 模块名称
        level: 最低日志级别

    Returns:
        Logger 实例
    """
    if name not in _loggers:
        _loggers[name] = Logger(name, level)
    return _loggers[name]
