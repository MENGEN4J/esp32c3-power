"""
功率数据引擎模块
职责：生成骑行模式功率/心率/踏频数据，支持参数调整与配置持久化

运行环境：MicroPython v1.28
"""

import json
import random
import time
import config
from logger import get_logger
from event_bus import bus, EVENT_POWER_CHANGED, EVENT_CADENCE_CHANGED, EVENT_MODE_CHANGED, EVENT_HEARTRATE_CHANGED, EVENT_ERG_TARGET, EVENT_CONFIG_DIRTY

log = get_logger("ENGINE")

_ROAD_STATE_COAST = "coast"
_ROAD_STATE_CRUISE = "cruise"
_ROAD_STATE_CLIMB = "climb"
_ROAD_STATE_SURGE = "surge"
_ROAD_STATE_RECOVER = "recover"


class PowerEngine:
    """骑行模式数据生成器，含功率/心率/踏频，支持按钮与Web调整"""

    def __init__(self):
        self.base_power = config.DEFAULT_POWER
        self.cadence_base = config.DEFAULT_CADENCE
        self.last_heartrate = config.DEFAULT_HEARTRATE
        self.user_heartrate = None
        self.mode = config.DEFAULT_RIDE_MODE
        self._last_power = config.DEFAULT_POWER
        self._last_cadence = config.DEFAULT_CADENCE
        self._road_state = _ROAD_STATE_CRUISE
        self._state_until = 0
        self._interval_start = 0
        self._snapshot = {
            'power': config.DEFAULT_POWER,
            'cadence': config.DEFAULT_CADENCE,
            'heartrate': config.DEFAULT_HEARTRATE,
            'mode': config.DEFAULT_RIDE_MODE
        }
        self._dirty = False
        self._saving = False

        self._load_config()
        self.reset_mode_state()

    def _load_config(self):
        """从 JSON 文件恢复上次配置，支持版本迁移"""
        try:
            with open(config.POWER_CONFIG_FILE, 'r') as f:
                cfg = json.load(f)
            version = cfg.get('v', 1)
            if version < config.CONFIG_VERSION:
                cfg = self._migrate_config(cfg, version)
            self.base_power = cfg.get('p', config.DEFAULT_POWER)
            self.cadence_base = cfg.get('c', config.DEFAULT_CADENCE)
            mode = cfg.get('m', config.DEFAULT_RIDE_MODE)
            if self._is_valid_mode(mode):
                self.mode = mode
            else:
                self.mode = config.DEFAULT_RIDE_MODE
                log.warning("骑行模式无效，已回退固定功率模式")
            if 'h' in cfg:
                hr = cfg['h']
                if config.HR_MIN <= hr <= config.HR_MAX:
                    self.user_heartrate = hr
                    self.last_heartrate = hr
            log.info("配置已恢复(v%d): %dW/%dRPM/%s" % (version, self.base_power, self.cadence_base, self.mode))
        except OSError:
            pass
        except Exception as e:
            log.error("JSON配置读取失败: %s" % e)

    @staticmethod
    def _migrate_config(cfg, from_version):
        """
        配置版本迁移：将旧版本配置升级到当前版本

        Args:
            cfg: 旧版本配置字典
            from_version: 旧版本号

        Returns:
            dict: 迁移后的配置字典
        """
        if from_version < 2:
            if 'm' not in cfg:
                cfg['m'] = config.DEFAULT_RIDE_MODE
        cfg['v'] = config.CONFIG_VERSION
        log.info("配置已从 v%d 迁移到 v%d" % (from_version, config.CONFIG_VERSION))
        return cfg

    def _build_config(self):
        """
        构建当前持久化配置快照

        Returns:
            dict: 待保存配置
        """
        return {
            'v': config.CONFIG_VERSION,
            'p': self.base_power,
            'c': self.cadence_base,
            'h': self.user_heartrate if self.user_heartrate is not None else self.last_heartrate,
            'm': self.mode
        }

    def _save_config(self, cfg):
        """
        将当前配置写入 JSON 文件

        Args:
            cfg: 配置快照

        Returns:
            bool: 是否保存成功
        """
        try:
            with open(config.POWER_CONFIG_FILE, 'w') as f:
                json.dump(cfg, f)
            log.info("配置已保存: %dW/%dRPM/%dBPM/%s" % (cfg['p'], cfg['c'], cfg['h'], cfg['m']))
            return True
        except Exception as e:
            log.error("保存配置失败: %s" % e)
            return False

    def adjust_power(self, delta):
        """
        固定功率模式下调整基准功率，标记待持久化（由主循环异步保存）

        Args:
            delta: 功率变化量 (W)

        Returns:
            int: 调整后的基准功率
        """
        if self.mode != config.RIDE_MODE_STEADY:
            log.info("当前模式不支持按钮调功率: %s" % self.mode)
            return self.base_power
        old_power = self.base_power
        self.base_power = max(config.POWER_MIN, min(self.base_power + delta, config.POWER_MAX))
        log.info("基准功率调整为: %dW" % self.base_power)
        if old_power != self.base_power:
            self._dirty = True
            bus.publish(EVENT_POWER_CHANGED, power=self.base_power)
            bus.publish(EVENT_CONFIG_DIRTY)
        return self.base_power

    def set_power(self, value):
        """
        固定功率模式下直接设置基准功率，标记待持久化

        Args:
            value: 目标功率值 (W)

        Returns:
            bool: 是否发生变化
        """
        if self.mode != config.RIDE_MODE_STEADY:
            return False
        if not (config.POWER_MIN <= value <= config.POWER_MAX):
            return False
        if self.base_power == value:
            return False
        self.base_power = value
        self._last_power = value
        self._dirty = True
        bus.publish(EVENT_POWER_CHANGED, power=value)
        bus.publish(EVENT_CONFIG_DIRTY)
        log.info("功率已设置: %dW" % value)
        return True

    def adjust_cadence(self, delta):
        """
        固定功率模式下调整基准踏频，标记待持久化（由主循环异步保存）

        Args:
            delta: 踏频变化量 (RPM)

        Returns:
            int: 调整后的基准踏频
        """
        if self.mode != config.RIDE_MODE_STEADY:
            return self.cadence_base
        old_cadence = self.cadence_base
        self.cadence_base = max(config.CADENCE_MIN, min(self.cadence_base + delta, config.CADENCE_MAX))
        log.info("基准踏频调整为: %dRPM" % self.cadence_base)
        if old_cadence != self.cadence_base:
            self._dirty = True
            bus.publish(EVENT_CADENCE_CHANGED, cadence=self.cadence_base)
            bus.publish(EVENT_CONFIG_DIRTY)
        return self.cadence_base

    def set_cadence(self, value):
        """
        固定功率模式下直接设置基准踏频，标记待持久化

        Args:
            value: 目标踏频值 (RPM)

        Returns:
            bool: 是否发生变化
        """
        if self.mode != config.RIDE_MODE_STEADY:
            return False
        if not (config.CADENCE_MIN <= value <= config.CADENCE_MAX):
            return False
        if self.cadence_base == value:
            return False
        self.cadence_base = value
        self._last_cadence = value
        self._dirty = True
        bus.publish(EVENT_CADENCE_CHANGED, cadence=value)
        bus.publish(EVENT_CONFIG_DIRTY)
        log.info("踏频已设置: %dRPM" % value)
        return True

    def set_heartrate(self, value):
        """
        固定功率模式下直接设置用户心率，标记待持久化

        Args:
            value: 目标心率值 (BPM)

        Returns:
            bool: 是否发生变化
        """
        if self.mode != config.RIDE_MODE_STEADY:
            return False
        if not (config.HR_MIN <= value <= config.HR_MAX):
            return False
        self.user_heartrate = value
        self.last_heartrate = value
        self._dirty = True
        bus.publish(EVENT_HEARTRATE_CHANGED, heartrate=value)
        bus.publish(EVENT_CONFIG_DIRTY)
        log.info("心率已设置: %dBPM" % value)
        return True

    def set_mode(self, mode):
        """
        设置骑行模式，标记待持久化

        Args:
            mode: 目标骑行模式 ID

        Returns:
            bool: 是否发生变化
        """
        if not self._is_valid_mode(mode):
            return False
        if self.mode == mode:
            return False
        self.mode = mode
        self.reset_mode_state()
        self._dirty = True
        bus.publish(EVENT_MODE_CHANGED, mode=mode)
        bus.publish(EVENT_CONFIG_DIRTY)
        log.info("骑行模式已设置: %s" % mode)
        return True

    def get_mode(self):
        """
        获取当前骑行模式

        Returns:
            str: 当前骑行模式 ID
        """
        return self.mode

    def reset_mode_state(self):
        """重置骑行模式内部状态，避免切换模式后状态污染"""
        if self.mode == config.RIDE_MODE_RANDOM:
            self._last_power = config.RANDOM_START_POWER
            self._last_cadence = config.RANDOM_START_CADENCE
        elif self.mode == config.RIDE_MODE_ROAD:
            self._last_power = config.ROAD_CRUISE_POWER[0]
            self._last_cadence = config.ROAD_CRUISE_CADENCE[0]
        elif self.mode == config.RIDE_MODE_INTERVAL:
            self._last_power = config.INTERVAL_RECOVERY_POWER[0]
            self._last_cadence = config.INTERVAL_RECOVERY_CADENCE[0]
        else:
            self._last_power = self.base_power
            self._last_cadence = self.cadence_base
        self._road_state = _ROAD_STATE_CRUISE
        self._state_until = 0
        self._interval_start = 0

    @staticmethod
    def _is_valid_mode(mode):
        """
        判断骑行模式是否有效

        Args:
            mode: 骑行模式 ID

        Returns:
            bool: 是否有效
        """
        return mode in config.RIDE_MODES

    @property
    def power(self):
        """返回带随机波动的功率值"""
        return self.base_power + random.randint(*config.POWER_FLUCTUATION)

    @property
    def heartrate(self):
        """返回当前心率值（无副作用，需先调用 update_heartrate 更新平滑值）"""
        return max(config.HR_MIN, min(config.HR_MAX, self.last_heartrate + random.randint(*config.HR_FLUCTUATION)))

    def update_heartrate(self):
        """更新心率平滑值（应在每次 BLE 通知前调用一次）"""
        if self.user_heartrate is not None:
            base_hr = self.user_heartrate
        else:
            base_hr = int(0.45 * self.power + 45)
        self.last_heartrate = int(self.last_heartrate * 0.8 + base_hr * 0.2)

    @property
    def cadence(self):
        """返回带随机波动的踏频值"""
        return max(config.CADENCE_MIN, min(config.CADENCE_MAX, self.cadence_base + random.randint(*config.CADENCE_FLUCTUATION)))

    def get_snapshot(self, now_ms):
        """
        生成当前 BLE 应广播的数据快照

        Args:
            now_ms: 当前毫秒时间戳

        Returns:
            dict: 包含 power/cadence/heartrate/mode 的快照
        """
        if self.mode == config.RIDE_MODE_ROAD:
            power, cadence, heartrate = self._build_road_snapshot(now_ms)
        elif self.mode == config.RIDE_MODE_INTERVAL:
            power, cadence, heartrate = self._build_interval_snapshot(now_ms)
        elif self.mode == config.RIDE_MODE_RANDOM:
            power, cadence, heartrate = self._build_random_snapshot()
        else:
            power, cadence, heartrate = self._build_steady_snapshot()

        self._last_power = power
        self._last_cadence = cadence
        self.last_heartrate = heartrate
        self._snapshot['power'] = power
        self._snapshot['cadence'] = cadence
        self._snapshot['heartrate'] = heartrate
        self._snapshot['mode'] = self.mode
        return self._snapshot

    def _build_steady_snapshot(self):
        """
        构建固定功率模式快照

        Returns:
            tuple: power, cadence, heartrate
        """
        power = self._clamp_power(self.base_power + random.randint(*config.STEADY_POWER_FLUCTUATION))
        cadence = self._clamp_cadence(self.cadence_base + random.randint(*config.STEADY_CADENCE_FLUCTUATION))
        target_hr = self._target_heartrate(power)
        heartrate = self._smooth_heartrate(target_hr, config.STEADY_HR_SMOOTH_PERCENT)
        heartrate = self._clamp_heartrate(heartrate + random.randint(*config.STEADY_HR_FLUCTUATION))
        return power, cadence, heartrate

    def _build_random_snapshot(self):
        """
        构建随机巡航模式快照

        Returns:
            tuple: power, cadence, heartrate
        """
        power = self._last_power + random.randint(-config.RANDOM_POWER_STEP, config.RANDOM_POWER_STEP)
        power = max(config.RANDOM_POWER_RANGE[0], min(config.RANDOM_POWER_RANGE[1], power))
        cadence = self._last_cadence + random.randint(-config.RANDOM_CADENCE_STEP, config.RANDOM_CADENCE_STEP)
        cadence = max(config.RANDOM_CADENCE_RANGE[0], min(config.RANDOM_CADENCE_RANGE[1], cadence))
        heartrate = self._smooth_heartrate(self._target_heartrate(power), config.RANDOM_HR_SMOOTH_PERCENT)
        heartrate = self._clamp_heartrate(heartrate + random.randint(*config.HR_FLUCTUATION))
        return power, cadence, heartrate

    def _build_road_snapshot(self, now_ms):
        """
        构建真实路骑模式快照

        Args:
            now_ms: 当前毫秒时间戳

        Returns:
            tuple: power, cadence, heartrate
        """
        if self._state_until == 0 or time.ticks_diff(now_ms, self._state_until) >= 0:
            self._road_state = self._next_road_state()
            duration = self._road_state_duration(self._road_state)
            self._state_until = time.ticks_add(now_ms, duration)

        state = self._road_state
        if state == _ROAD_STATE_COAST:
            power = random.randint(*config.ROAD_COAST_POWER)
            cadence = random.randint(*config.ROAD_COAST_CADENCE)
        elif state == _ROAD_STATE_CLIMB:
            power = random.randint(*config.ROAD_CLIMB_POWER)
            cadence = random.randint(*config.ROAD_CLIMB_CADENCE)
        elif state == _ROAD_STATE_SURGE:
            power = random.randint(*config.ROAD_SURGE_POWER)
            cadence = random.randint(*config.ROAD_SURGE_CADENCE)
        elif state == _ROAD_STATE_RECOVER:
            power = random.randint(*config.ROAD_RECOVER_POWER)
            cadence = random.randint(*config.ROAD_RECOVER_CADENCE)
        else:
            power = random.randint(*config.ROAD_CRUISE_POWER)
            cadence = random.randint(*config.ROAD_CRUISE_CADENCE)

        power = self._clamp_power(power)
        cadence = self._clamp_cadence(cadence)
        heartrate = self._smooth_heartrate(self._target_heartrate(power), config.ROAD_HR_SMOOTH_PERCENT)
        heartrate = self._clamp_heartrate(heartrate + random.randint(*config.HR_FLUCTUATION))
        return power, cadence, heartrate

    @staticmethod
    def _road_state_duration(state):
        """
        读取真实路骑状态持续时间

        Args:
            state: 真实路骑状态 ID

        Returns:
            int: 状态持续毫秒数
        """
        if state == _ROAD_STATE_COAST:
            return random.randint(*config.ROAD_COAST_DURATION_MS)
        if state == _ROAD_STATE_CLIMB:
            return random.randint(*config.ROAD_CLIMB_DURATION_MS)
        if state == _ROAD_STATE_SURGE:
            return random.randint(*config.ROAD_SURGE_DURATION_MS)
        if state == _ROAD_STATE_RECOVER:
            return random.randint(*config.ROAD_RECOVER_DURATION_MS)
        return random.randint(*config.ROAD_CRUISE_DURATION_MS)

    def _build_interval_snapshot(self, now_ms):
        """
        构建间歇训练模式快照

        Args:
            now_ms: 当前毫秒时间戳

        Returns:
            tuple: power, cadence, heartrate
        """
        if self._interval_start == 0:
            self._interval_start = now_ms
        cycle = config.INTERVAL_WORK_MS + config.INTERVAL_RECOVERY_MS
        elapsed = time.ticks_diff(now_ms, self._interval_start) % cycle
        if elapsed < config.INTERVAL_WORK_MS:
            power = random.randint(*config.INTERVAL_WORK_POWER)
            cadence = random.randint(*config.INTERVAL_WORK_CADENCE)
        else:
            power = random.randint(*config.INTERVAL_RECOVERY_POWER)
            cadence = random.randint(*config.INTERVAL_RECOVERY_CADENCE)
        power = self._clamp_power(power)
        cadence = self._clamp_cadence(cadence)
        heartrate = self._smooth_heartrate(self._target_heartrate(power), config.INTERVAL_HR_SMOOTH_PERCENT)
        heartrate = self._clamp_heartrate(heartrate + random.randint(*config.HR_FLUCTUATION))
        return power, cadence, heartrate

    def _next_road_state(self):
        """
        根据当前真实路骑状态选择下一个状态

        Returns:
            str: 下一个状态 ID
        """
        r = random.randint(1, 100)
        state = self._road_state
        if state == _ROAD_STATE_SURGE:
            return _ROAD_STATE_RECOVER if r <= 80 else _ROAD_STATE_CRUISE
        if state == _ROAD_STATE_CLIMB:
            if r <= 45:
                return _ROAD_STATE_RECOVER
            if r <= 85:
                return _ROAD_STATE_CRUISE
            return _ROAD_STATE_SURGE
        if state == _ROAD_STATE_RECOVER:
            if r <= 65:
                return _ROAD_STATE_CRUISE
            if r <= 85:
                return _ROAD_STATE_COAST
            return _ROAD_STATE_CLIMB
        if state == _ROAD_STATE_COAST:
            return _ROAD_STATE_CRUISE if r <= 80 else _ROAD_STATE_RECOVER
        if r <= 10:
            return _ROAD_STATE_COAST
        if r <= 30:
            return _ROAD_STATE_CLIMB
        if r <= 40:
            return _ROAD_STATE_SURGE
        return _ROAD_STATE_CRUISE

    def _target_heartrate(self, power):
        """
        根据当前功率计算目标心率

        Args:
            power: 当前功率

        Returns:
            int: 目标心率
        """
        if self.user_heartrate is not None and self.mode == config.RIDE_MODE_STEADY:
            return self.user_heartrate
        if self.mode == config.RIDE_MODE_INTERVAL:
            base_hr = config.INTERVAL_WORK_HR_TARGET if power >= config.INTERVAL_WORK_POWER[0] else config.INTERVAL_RECOVERY_HR_TARGET
        elif self.mode == config.RIDE_MODE_ROAD:
            if power <= config.ROAD_COAST_POWER[1]:
                base_hr = config.ROAD_COAST_HR_TARGET
            elif power >= config.ROAD_SURGE_POWER[0]:
                base_hr = config.ROAD_SURGE_HR_TARGET
            elif power >= config.ROAD_CLIMB_POWER[0]:
                base_hr = config.ROAD_CLIMB_HR_TARGET
            elif power <= config.ROAD_RECOVER_POWER[1]:
                base_hr = config.ROAD_RECOVER_HR_TARGET
            else:
                base_hr = config.ROAD_CRUISE_HR_TARGET
        elif self.mode == config.RIDE_MODE_RANDOM:
            base_hr = 135 + int((power - config.RANDOM_POWER_RANGE[0]) / 6)
        else:
            base_hr = int(0.45 * power + 45)
        return self._clamp_heartrate(base_hr)

    def _smooth_heartrate(self, target, keep_percent):
        """
        平滑更新心率

        Args:
            target: 目标心率
            keep_percent: 保留上次心率的百分比

        Returns:
            int: 平滑后的心率
        """
        return int((self.last_heartrate * keep_percent + target * (100 - keep_percent)) / 100)

    @staticmethod
    def _clamp_power(value):
        """
        限制功率范围

        Args:
            value: 待限制功率

        Returns:
            int: 合法功率
        """
        return max(config.POWER_MIN, min(config.POWER_MAX, value))

    @staticmethod
    def _clamp_cadence(value):
        """
        限制踏频范围

        Args:
            value: 待限制踏频

        Returns:
            int: 合法踏频
        """
        return max(config.CADENCE_MIN, min(config.CADENCE_MAX, value))

    @staticmethod
    def _clamp_heartrate(value):
        """
        限制心率范围

        Args:
            value: 待限制心率

        Returns:
            int: 合法心率
        """
        return max(config.HR_MIN, min(config.HR_MAX, value))

    def set_erg_target(self, target_power):
        """
        设置 ERG 模式目标功率（由 FTMS 控制点下发）

        Args:
            target_power: 目标功率值 (W)
        """
        if not (config.POWER_MIN <= target_power <= config.POWER_MAX):
            log.warning("ERG目标功率超出范围: %dW" % target_power)
            return
        self.base_power = target_power
        self._last_power = target_power
        self._dirty = True
        bus.publish(EVENT_ERG_TARGET, power=target_power)
        bus.publish(EVENT_CONFIG_DIRTY)
        log.info("ERG目标功率已设置: %dW" % target_power)

    def flush_if_dirty(self):
        """
        若配置已变更，立即保存到文件

        Returns:
            bool: 是否执行并成功保存
        """
        if not self._dirty or self._saving:
            return False
        self._saving = True
        try:
            cfg = self._build_config()
            if self._save_config(cfg):
                if self._build_config() == cfg:
                    self._dirty = False
                return True
            return False
        finally:
            self._saving = False
