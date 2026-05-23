#!/usr/bin/env python3
"""
power_data / config 一致性单元测试

运行环境: CPython 3.8+（通过 mock 模拟 MicroPython 模块）
运行方式: python3 test/test_power_data.py
"""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

sys.modules['micropython'] = MagicMock()
sys.modules['micropython'].const = lambda x: x
sys.modules['logger'] = MagicMock()
sys.modules['logger'].get_logger = lambda name: MagicMock()

import config
import power_data


class TestConfigConstants(unittest.TestCase):
    """config.py 常量完整性检查"""

    def test_power_range(self):
        self.assertEqual(config.POWER_MIN, 0)
        self.assertEqual(config.POWER_MAX, 2000)

    def test_cadence_range(self):
        self.assertEqual(config.CADENCE_MIN, 20)
        self.assertEqual(config.CADENCE_MAX, 120)

    def test_hr_range(self):
        self.assertEqual(config.HR_MIN, 60)
        self.assertEqual(config.HR_MAX, 200)

    def test_default_values_in_range(self):
        self.assertTrue(config.POWER_MIN <= config.DEFAULT_POWER <= config.POWER_MAX)
        self.assertTrue(config.CADENCE_MIN <= config.DEFAULT_CADENCE <= config.CADENCE_MAX)
        self.assertTrue(config.HR_MIN <= config.DEFAULT_HEARTRATE <= config.HR_MAX)

    def test_ride_modes_tuple(self):
        self.assertIn(config.RIDE_MODE_STEADY, config.RIDE_MODES)
        self.assertIn(config.RIDE_MODE_ROAD, config.RIDE_MODES)
        self.assertIn(config.RIDE_MODE_INTERVAL, config.RIDE_MODES)
        self.assertIn(config.RIDE_MODE_RANDOM, config.RIDE_MODES)

    def test_button_thresholds_positive(self):
        self.assertGreater(config.SHORT_PRESS_MS, 0)
        self.assertGreater(config.WIFI_BTN_HOLD_MS, config.SHORT_PRESS_MS)

    def test_wifi_shutdown_positive(self):
        self.assertGreater(config.WIFI_SHUTDOWN_MS, 0)

    def test_ota_chunk_positive(self):
        self.assertGreater(config.OTA_DOWNLOAD_CHUNK, 0)

    def test_firmware_version_format(self):
        parts = config.FIRMWARE_VERSION.split('.')
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertTrue(part.isdigit())


class TestPowerEngineClamping(unittest.TestCase):
    """PowerEngine 范围限制测试"""

    def setUp(self):
        with patch('builtins.open', mock_open(read_data='{}')):
            self.engine = power_data.PowerEngine()

    def test_clamp_power_min(self):
        self.assertEqual(power_data.PowerEngine._clamp_power(-100), config.POWER_MIN)

    def test_clamp_power_max(self):
        self.assertEqual(power_data.PowerEngine._clamp_power(9999), config.POWER_MAX)

    def test_clamp_power_normal(self):
        self.assertEqual(power_data.PowerEngine._clamp_power(200), 200)

    def test_clamp_cadence_min(self):
        self.assertEqual(power_data.PowerEngine._clamp_cadence(0), config.CADENCE_MIN)

    def test_clamp_cadence_max(self):
        self.assertEqual(power_data.PowerEngine._clamp_cadence(999), config.CADENCE_MAX)

    def test_clamp_cadence_normal(self):
        self.assertEqual(power_data.PowerEngine._clamp_cadence(90), 90)

    def test_clamp_heartrate_min(self):
        self.assertEqual(power_data.PowerEngine._clamp_heartrate(0), config.HR_MIN)

    def test_clamp_heartrate_max(self):
        self.assertEqual(power_data.PowerEngine._clamp_heartrate(999), config.HR_MAX)

    def test_clamp_heartrate_normal(self):
        self.assertEqual(power_data.PowerEngine._clamp_heartrate(140), 140)


class TestPowerEngineAdjust(unittest.TestCase):
    """PowerEngine 调整操作测试"""

    def setUp(self):
        with patch('builtins.open', mock_open(read_data='{}')):
            self.engine = power_data.PowerEngine()
        self.engine.mode = config.RIDE_MODE_STEADY

    def test_adjust_power_up(self):
        old = self.engine.base_power
        result = self.engine.adjust_power(10)
        self.assertEqual(result, min(old + 10, config.POWER_MAX))

    def test_adjust_power_down(self):
        old = self.engine.base_power
        result = self.engine.adjust_power(-10)
        self.assertEqual(result, max(old - 10, config.POWER_MIN))

    def test_adjust_power_clamp_max(self):
        self.engine.base_power = config.POWER_MAX
        result = self.engine.adjust_power(10)
        self.assertEqual(result, config.POWER_MAX)

    def test_adjust_power_clamp_min(self):
        self.engine.base_power = config.POWER_MIN
        result = self.engine.adjust_power(-10)
        self.assertEqual(result, config.POWER_MIN)

    def test_set_power_valid(self):
        self.assertTrue(self.engine.set_power(500))
        self.assertEqual(self.engine.base_power, 500)

    def test_set_power_out_of_range(self):
        self.assertFalse(self.engine.set_power(config.POWER_MAX + 1))
        self.assertFalse(self.engine.set_power(config.POWER_MIN - 1))

    def test_set_power_same_value(self):
        self.engine.base_power = 200
        self.assertFalse(self.engine.set_power(200))

    def test_set_cadence_valid(self):
        self.assertTrue(self.engine.set_cadence(80))
        self.assertEqual(self.engine.cadence_base, 80)

    def test_set_cadence_out_of_range(self):
        self.assertFalse(self.engine.set_cadence(config.CADENCE_MAX + 1))
        self.assertFalse(self.engine.set_cadence(config.CADENCE_MIN - 1))

    def test_set_heartrate_valid(self):
        self.assertTrue(self.engine.set_heartrate(150))
        self.assertEqual(self.engine.user_heartrate, 150)

    def test_set_heartrate_out_of_range(self):
        self.assertFalse(self.engine.set_heartrate(config.HR_MAX + 1))
        self.assertFalse(self.engine.set_heartrate(config.HR_MIN - 1))


class TestPowerEngineMode(unittest.TestCase):
    """PowerEngine 模式切换测试"""

    def setUp(self):
        with patch('builtins.open', mock_open(read_data='{}')):
            self.engine = power_data.PowerEngine()

    def test_set_mode_valid(self):
        for mode in config.RIDE_MODES:
            self.engine.mode = '__none__'
            self.assertTrue(self.engine.set_mode(mode))

    def test_set_mode_invalid(self):
        self.assertFalse(self.engine.set_mode("nonexistent"))

    def test_set_mode_same(self):
        self.engine.mode = config.RIDE_MODE_STEADY
        self.assertFalse(self.engine.set_mode(config.RIDE_MODE_STEADY))

    def test_is_valid_mode(self):
        for mode in config.RIDE_MODES:
            self.assertTrue(power_data.PowerEngine._is_valid_mode(mode))
        self.assertFalse(power_data.PowerEngine._is_valid_mode("invalid"))

    def test_non_steady_mode_rejects_power_adjust(self):
        self.engine.set_mode(config.RIDE_MODE_ROAD)
        result = self.engine.adjust_power(10)
        self.assertEqual(result, self.engine.base_power)

    def test_non_steady_mode_rejects_set_power(self):
        self.engine.set_mode(config.RIDE_MODE_ROAD)
        self.assertFalse(self.engine.set_power(500))


class TestPowerEnginePersistence(unittest.TestCase):
    """PowerEngine 配置持久化测试"""

    def test_build_config_keys(self):
        with patch('builtins.open', mock_open(read_data='{}')):
            engine = power_data.PowerEngine()
        cfg = engine._build_config()
        self.assertIn('p', cfg)
        self.assertIn('c', cfg)
        self.assertIn('h', cfg)
        self.assertIn('m', cfg)

    def test_build_config_values_in_range(self):
        with patch('builtins.open', mock_open(read_data='{}')):
            engine = power_data.PowerEngine()
        cfg = engine._build_config()
        self.assertTrue(config.POWER_MIN <= cfg['p'] <= config.POWER_MAX)
        self.assertTrue(config.CADENCE_MIN <= cfg['c'] <= config.CADENCE_MAX)
        self.assertTrue(config.HR_MIN <= cfg['h'] <= config.HR_MAX)
        self.assertIn(cfg['m'], config.RIDE_MODES)

    def test_save_config_success(self):
        with patch('builtins.open', mock_open(read_data='{}')):
            engine = power_data.PowerEngine()
        cfg = engine._build_config()
        with patch('builtins.open', mock_open()):
            with patch('json.dump'):
                self.assertTrue(engine._save_config(cfg))

    def test_load_config_valid(self):
        saved = json.dumps({'p': 300, 'c': 85, 'h': 150, 'm': 'steady'})
        with patch('builtins.open', mock_open(read_data=saved)):
            engine = power_data.PowerEngine()
        self.assertEqual(engine.base_power, 300)
        self.assertEqual(engine.cadence_base, 85)
        self.assertEqual(engine.user_heartrate, 150)
        self.assertEqual(engine.mode, 'steady')

    def test_load_config_invalid_mode_fallback(self):
        saved = json.dumps({'p': 200, 'c': 90, 'h': 140, 'm': 'invalid'})
        with patch('builtins.open', mock_open(read_data=saved)):
            engine = power_data.PowerEngine()
        self.assertEqual(engine.mode, config.DEFAULT_RIDE_MODE)

    def test_load_config_hr_out_of_range_ignored(self):
        saved = json.dumps({'p': 200, 'c': 90, 'h': 999, 'm': 'steady'})
        with patch('builtins.open', mock_open(read_data=saved)):
            engine = power_data.PowerEngine()
        self.assertIsNone(engine.user_heartrate)

    def test_dirty_flag_set_on_adjust(self):
        with patch('builtins.open', mock_open(read_data='{}')):
            engine = power_data.PowerEngine()
        engine.mode = config.RIDE_MODE_STEADY
        engine._dirty = False
        engine.adjust_power(10)
        self.assertTrue(engine._dirty)

    def test_flush_if_dirty(self):
        with patch('builtins.open', mock_open(read_data='{}')):
            engine = power_data.PowerEngine()
        engine.mode = config.RIDE_MODE_STEADY
        engine._dirty = True
        with patch.object(engine, '_save_config', return_value=True):
            with patch.object(engine, '_build_config', return_value={'p': 1, 'c': 1, 'h': 1, 'm': 'steady'}):
                result = engine.flush_if_dirty()
                self.assertTrue(result)


class TestPowerEngineSnapshot(unittest.TestCase):
    """PowerEngine 快照数据范围测试"""

    def setUp(self):
        with patch('builtins.open', mock_open(read_data='{}')):
            self.engine = power_data.PowerEngine()

    def test_steady_snapshot_range(self):
        self.engine.mode = config.RIDE_MODE_STEADY
        for _ in range(50):
            snap = self.engine._build_steady_snapshot()
            self.assertTrue(config.POWER_MIN <= snap[0] <= config.POWER_MAX)
            self.assertTrue(config.CADENCE_MIN <= snap[1] <= config.CADENCE_MAX)
            self.assertTrue(config.HR_MIN <= snap[2] <= config.HR_MAX)

    def test_random_snapshot_range(self):
        self.engine.mode = config.RIDE_MODE_RANDOM
        self.engine.reset_mode_state()
        for _ in range(50):
            snap = self.engine._build_random_snapshot()
            self.assertTrue(config.POWER_MIN <= snap[0] <= config.POWER_MAX)
            self.assertTrue(config.CADENCE_MIN <= snap[1] <= config.CADENCE_MAX)
            self.assertTrue(config.HR_MIN <= snap[2] <= config.HR_MAX)

    def test_get_snapshot_keys(self):
        self.engine.mode = config.RIDE_MODE_STEADY
        snap = self.engine.get_snapshot(0)
        self.assertIn('power', snap)
        self.assertIn('cadence', snap)
        self.assertIn('heartrate', snap)
        self.assertIn('mode', snap)


if __name__ == '__main__':
    unittest.main()
