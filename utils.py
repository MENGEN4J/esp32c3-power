"""
工具函数模块
职责：跨模块共享的工具函数

运行环境: MicroPython v1.28
"""

import _thread

DEFAULT_STACK = 8192


def start_thread(func, args=(), stack=4096):
    """安全启动线程：设置栈大小 → 启动 → 恢复默认，避免全局副作用"""
    _thread.stack_size(stack)
    _thread.start_new_thread(func, args)
    _thread.stack_size(DEFAULT_STACK)
