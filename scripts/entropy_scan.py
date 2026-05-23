#!/usr/bin/env python3
"""
Entropy 治理扫描脚本 + Harness Hooks 自动检查

模式:
  python3 scripts/entropy_scan.py          全量 Entropy 扫描（5 项）
  python3 scripts/entropy_scan.py --hooks  Hooks 快速检查（H1~H23）
  python3 scripts/entropy_scan.py --all    全量 Entropy + Hooks
"""

import os
import py_compile
import re
import sys

BIZ_MODULES = [
    'app.py', 'config.py', 'logger.py', 'utils.py',
    'ble_service.py', 'power_data.py', 'wifi_manager.py',
    'web_pages.py', 'ota_updater.py', 'event_bus.py'
]

CORE_MODULES = [
    'config', 'logger', 'utils', 'ble_service',
    'power_data', 'wifi_manager', 'web_pages',
    'ota_updater', 'app'
]

SPEC_TO_MODULE = {
    'ble-service.md': 'ble_service.py',
    'power-engine.md': 'power_data.py',
    'wifi-manager.md': 'wifi_manager.py',
    'ota-updater.md': 'ota_updater.py',
    'button-handler.md': 'app.py',
}

CPYTHON_IMPORTS = [
    'requests', 'asyncio', 'threading', 'http',
    'urllib', 'concurrent', 'multiprocessing',
    'xml.etree', 'csv', 'sqlite3',
]

TRADITIONAL_CHINESE_RANGES = [
    (0x4E00, 0x9FFF),
]

TRADITIONAL_CHARS = set(
    '裡著說與會這裡製運網點個為來過還裝當於對開經關將從時沒樣問種話長區業導師歷書幾機東車歷'
    '準據斷語現證識議適規設請產階際額預導驗證讀變點該論認證據權際標準範圍運營區域設備'
)


def _read_file(path):
    if not os.path.exists(path):
        return ''
    with open(path) as f:
        return f.read()


# ============================================================
# Entropy 治理扫描（5 项）
# ============================================================

def scan_doc_drift():
    """检查 specs/ 与代码实际行为是否一致"""
    issues = []

    specs_dir = 'specs'
    if not os.path.exists(specs_dir):
        return ['specs/ 目录不存在']

    for spec_file in os.listdir(specs_dir):
        if not spec_file.endswith('.md'):
            continue
        py_file = SPEC_TO_MODULE.get(spec_file)
        if not py_file:
            continue
        if py_file not in os.listdir('.'):
            issues.append('specs/%s 对应的 %s 不存在' % (spec_file, py_file))
            continue

        with open(os.path.join(specs_dir, spec_file)) as f:
            spec_content = f.read()

        with open(py_file) as f:
            py_content = f.read()

        spec_methods = set(re.findall(r'`?(\w+)`?(?:\(|\s*[—\-:]|\s*$)', spec_content, re.MULTILINE))
        spec_methods |= set(re.findall(r'`(\w+)`', spec_content))
        py_methods = set(re.findall(r'def (\w+)\(', py_content))
        public_py = {m for m in py_methods if not m.startswith('_')}
        public_py |= set(re.findall(r'(\w+)\s*=\s*(?:property|attribute)', py_content))

        missing_in_spec = public_py - spec_methods
        if missing_in_spec and len(public_py) > 3:
            for m in sorted(missing_in_spec):
                if m not in ('__init__',):
                    module_name = py_file.replace('.py', '')
                    issues.append('specs/%s 缺少 %s.%s 描述' % (spec_file, module_name, m))

    return issues


def scan_naming_drift():
    """检查命名是否符合 code_style.md"""
    issues = []

    with open('config.py') as f:
        for i, line in enumerate(f, 1):
            stripped = line.strip()
            if stripped.startswith('#') or not stripped:
                continue
            m = re.match(r'^([A-Z_]+)\s*=\s*(\d+)', stripped)
            if m and 'const(' not in stripped:
                name = m.group(1)
                if name not in ('FIRMWARE_VERSION',):
                    issues.append('config.py L%d: %s 未用 const() 包装' % (i, name))

    for f in BIZ_MODULES:
        if not os.path.exists(f):
            continue
        with open(f) as fh:
            content = fh.read()
            m = re.search(r'get_logger\("([^"]+)"\)', content)
            if m and m.group(1) != m.group(1).upper():
                issues.append('%s: get_logger("%s") 非大写' % (f, m.group(1)))

    for f in BIZ_MODULES:
        if not os.path.exists(f):
            continue
        with open(f) as fh:
            for i, line in enumerate(fh, 1):
                m = re.match(r'^class\s+(\w+)', line.strip())
                if m and not re.match(r'^[A-Z]', m.group(1)):
                    issues.append('%s L%d: class %s 非 PascalCase' % (f, i, m.group(1)))

    return issues


def scan_dead_code():
    """检查死代码：未引用的 import、函数、常量"""
    issues = []

    with open('config.py') as f:
        content = f.read()
        all_consts = re.findall(r'^([A-Z_]+)\s*=', content, re.MULTILINE)

    for const in all_consts:
        found = False
        for f in BIZ_MODULES:
            if f == 'config.py':
                continue
            if not os.path.exists(f):
                continue
            with open(f) as fh:
                if const in fh.read():
                    found = True
                    break
        if not found and content.count(const) <= 1:
            issues.append('config.py: %s 未被其他模块引用' % const)

    all_calls = set()
    all_defs = {}
    for f in BIZ_MODULES:
        if not os.path.exists(f):
            continue
        with open(f) as fh:
            content = fh.read()
            for m in re.finditer(r'def\s+(\w+)\(', content):
                all_defs.setdefault(f, []).append(m.group(1))
            for m in re.finditer(r'(\w+)\(', content):
                all_calls.add(m.group(1))

    skip_methods = {'main', '__init__', '_irq', '_server_thread',
                    '_wifi_shutdown_timer', '_scan_wifi_thread',
                    '_connect_wifi_thread', '_ota_check_thread',
                    '_ota_download_thread', '_async_save_config',
                    '_create_wifi_manager', 'close_wifi_later'}
    for f, methods in all_defs.items():
        for m in methods:
            if m.startswith('__') and m.endswith('__'):
                continue
            if m in skip_methods:
                continue
            if m not in all_calls:
                issues.append('%s: %s() 未被调用' % (f, m))

    return issues


def scan_rule_rot():
    """检查 .trae/rules/ 是否过时"""
    issues = []

    pr_path = '.trae/rules/project_rules.md'
    if os.path.exists(pr_path):
        with open(pr_path) as f:
            pr = f.read()
        for mod in BIZ_MODULES:
            if mod not in pr:
                issues.append('project_rules.md 文件结构缺少 %s' % mod)
        for spec in os.listdir('specs'):
            if spec not in pr:
                issues.append('project_rules.md 文件结构缺少 specs/%s' % spec)

    hc_path = '.trae/rules/hardware_constraints.md'
    if os.path.exists(hc_path):
        with open(hc_path) as f:
            hc = f.read()
        with open('config.py') as f:
            cfg = f.read()
        config_consts = re.findall(r'^([A-Z_]+)\s*=\s*const\((\d+)\)', cfg, re.MULTILINE)
        for name, val in config_consts:
            if name in hc:
                if val not in hc:
                    issues.append('hardware_constraints.md: %s 值与 config.py 不一致' % name)

    templates_dir = '.trae/rules/templates'
    if os.path.exists(templates_dir):
        for spec in os.listdir('specs'):
            if not spec.endswith('.md'):
                continue
            template = spec
            if template not in os.listdir(templates_dir):
                module_name = spec.replace('.md', '').replace('-', '_')
                py_file = module_name + '.py'
                if py_file in BIZ_MODULES:
                    issues.append('templates/ 缺少 %s（specs/ 有对应规格）' % template)

    return issues


def scan_config_consistency():
    """检查配置一致性"""
    issues = []

    with open('config.py') as f:
        cfg = f.read()

    config_ranges = {
        'MIN_POWER': ('MAX_POWER', 'power_data.py'),
        'MIN_CADENCE': ('MAX_CADENCE', 'power_data.py'),
        'MIN_HEARTRATE': ('MAX_HEARTRATE', 'power_data.py'),
    }

    for min_name, (max_name, check_file) in config_ranges.items():
        min_m = re.search(r'%s\s*=\s*const\((\d+)\)' % min_name, cfg)
        max_m = re.search(r'%s\s*=\s*const\((\d+)\)' % max_name, cfg)
        if min_m and max_m:
            min_val = int(min_m.group(1))
            max_val = int(max_m.group(1))
            if os.path.exists(check_file):
                with open(check_file) as f:
                    content = f.read()
                if str(min_val) not in content or str(max_val) not in content:
                    issues.append('%s: %s/%s 范围与 config.py 不一致' % (check_file, min_name, max_name))

    return issues


# ============================================================
# Harness Hooks 自动检查（H1~H23）
# ============================================================

def hook_syntax_check():
    """H1: 语法正确"""
    issues = []
    for f in BIZ_MODULES:
        if not os.path.exists(f):
            continue
        try:
            py_compile.compile(f, doraise=True)
        except py_compile.PyCompileError as e:
            issues.append('H1: %s 语法错误: %s' % (f, str(e)))
    return issues


def hook_no_cpython_imports():
    """H2: 禁止 CPython 专有库"""
    issues = []
    for f in BIZ_MODULES:
        if not os.path.exists(f):
            continue
        content = _read_file(f)
        for lib in CPYTHON_IMPORTS:
            pattern = r'^\s*import\s+%s|^\s*from\s+%s' % (lib, lib)
            if re.search(pattern, content, re.MULTILINE):
                issues.append('H2: %s 引入 CPython 专有库: %s' % (f, lib))
    return issues


def hook_no_print():
    """H3: 禁止 print()（boot.py/logger.py 例外）"""
    issues = []
    whitelist = {'boot.py', 'logger.py'}
    for f in BIZ_MODULES:
        if not os.path.exists(f):
            continue
        if f in whitelist:
            continue
        content = _read_file(f)
        matches = re.findall(r'print\s*\(', content)
        if matches:
            issues.append('H3: %s 包含 %d 处 print() 调用' % (f, len(matches)))
    return issues


def hook_const_wrapper():
    """H4: 模块常量 const() 包装"""
    issues = []
    content = _read_file('config.py')
    if not content:
        return issues
    for i, line in enumerate(content.split('\n'), 1):
        stripped = line.strip()
        if stripped.startswith('#') or not stripped:
            continue
        m = re.match(r'^([A-Z_]+)\s*=\s*(\d+)', stripped)
        if m and 'const(' not in stripped:
            name = m.group(1)
            if name not in ('FIRMWARE_VERSION',):
                issues.append('H4: config.py L%d: %s 未用 const() 包装' % (i, name))
    return issues


def hook_logger_uppercase():
    """H5: 日志器大写简称"""
    issues = []
    for f in BIZ_MODULES:
        if not os.path.exists(f):
            continue
        content = _read_file(f)
        m = re.search(r'get_logger\("([^"]+)"\)', content)
        if m and m.group(1) != m.group(1).upper():
            issues.append('H5: %s: get_logger("%s") 非大写' % (f, m.group(1)))
    return issues


def hook_no_traditional_chinese():
    """H6: 禁止繁体中文"""
    issues = []
    for f in BIZ_MODULES:
        if not os.path.exists(f):
            continue
        content = _read_file(f)
        found = [ch for ch in TRADITIONAL_CHARS if ch in content]
        if found:
            issues.append('H6: %s 包含繁体字: %s' % (f, ''.join(found[:5])))
    return issues


def hook_docstring_exists():
    """H7: 模块/类/公开方法 docstring"""
    issues = []
    for f in BIZ_MODULES:
        if not os.path.exists(f):
            continue
        content = _read_file(f)
        stripped = content.strip()
        if not stripped.startswith('"""') and not stripped.startswith("'''"):
            issues.append('H7: %s 缺少模块级 docstring' % f)
        class_defs = re.finditer(r'^class\s+(\w+)', content, re.MULTILINE)
        for cd in class_defs:
            class_name = cd.group(1)
            after = content[cd.end():]
            next_20_lines = after[:200]
            if '"""' not in next_20_lines and "'''" not in next_20_lines:
                issues.append('H7: %s: class %s 缺少 docstring' % (f, class_name))
    return issues


def hook_config_specs_consistency():
    """H8: specs/ 常量值一致"""
    issues = []
    cfg = _read_file('config.py')
    if not cfg:
        return issues
    specs_dir = 'specs'
    if not os.path.exists(specs_dir):
        return ['H8: specs/ 目录不存在']
    config_values = re.findall(r'([A-Z_]+)\s*=\s*const\((\d+)\)', cfg)
    for name, val in config_values:
        for spec_file in os.listdir(specs_dir):
            if not spec_file.endswith('.md'):
                continue
            spec_content = _read_file(os.path.join(specs_dir, spec_file))
            if name in spec_content and val not in spec_content:
                issues.append('H8: specs/%s 引用 %s 但值 %s 不存在' % (spec_file, name, val))
    return issues


def hook_power_data_ranges():
    """H9: power_data.py 范围校验一致"""
    issues = []
    cfg = _read_file('config.py')
    pd = _read_file('power_data.py')
    if not cfg or not pd:
        return issues
    ranges = {
        'MIN_POWER': 'MAX_POWER',
        'MIN_CADENCE': 'MAX_CADENCE',
        'MIN_HEARTRATE': 'MAX_HEARTRATE',
    }
    for min_name, max_name in ranges.items():
        min_m = re.search(r'%s\s*=\s*const\((\d+)\)' % min_name, cfg)
        max_m = re.search(r'%s\s*=\s*const\((\d+)\)' % max_name, cfg)
        if min_m and max_m:
            if min_m.group(1) not in pd or max_m.group(1) not in pd:
                issues.append('H9: power_data.py 缺少 %s/%s 范围校验' % (min_name, max_name))
    return issues


def hook_wifi_form_ranges():
    """H10: wifi_manager.py 表单范围一致"""
    issues = []
    cfg = _read_file('config.py')
    wp = _read_file('web_pages.py')
    if not cfg or not wp:
        return issues
    ranges = {
        'MIN_POWER': 'MAX_POWER',
        'MIN_CADENCE': 'MAX_CADENCE',
        'MIN_HEARTRATE': 'MAX_HEARTRATE',
    }
    for min_name, max_name in ranges.items():
        min_m = re.search(r'%s\s*=\s*const\((\d+)\)' % min_name, cfg)
        max_m = re.search(r'%s\s*=\s*const\((\d+)\)' % max_name, cfg)
        if min_m and max_m:
            if min_m.group(1) not in wp or max_m.group(1) not in wp:
                issues.append('H10: web_pages.py 表单缺少 %s/%s 范围' % (min_name, max_name))
    return issues


def hook_hardware_constraints_params():
    """H11: hardware_constraints.md 参数一致"""
    issues = []
    cfg = _read_file('config.py')
    hc = _read_file('.trae/rules/hardware_constraints.md')
    if not cfg or not hc:
        return issues
    config_consts = re.findall(r'^([A-Z_]+)\s*=\s*const\((\d+)\)', cfg, re.MULTILINE)
    for name, val in config_consts:
        if name in hc and val not in hc:
            issues.append('H11: hardware_constraints.md: %s 值 %s 与 config.py 不一致' % (name, val))
    return issues


def hook_ble_no_new_objects_in_irq():
    """H12: 通知回调无新对象"""
    issues = []
    content = _read_file('ble_service.py')
    if not content:
        return issues
    irq_match = re.search(r'def\s+_irq\(.*?\n(.*?)(?=\n    def |\nclass |\Z)', content, re.DOTALL)
    if irq_match:
        irq_body = irq_match.group(1)
        if re.search(r'bytearray\s*\(', irq_body):
            issues.append('H12: ble_service.py _irq 中创建 bytearray')
        if re.search(r'bytes\s*\(', irq_body):
            issues.append('H12: ble_service.py _irq 中创建 bytes')
    return issues


def hook_ble_params_from_config():
    """H13: MTU/广播/通知间隔从 config 读取"""
    issues = []
    content = _read_file('ble_service.py')
    if not content:
        return issues
    hardcoded = re.findall(r'(?:mtu|MTU)\s*=\s*(\d+)', content)
    for val in hardcoded:
        if val not in ('69',):
            issues.append('H13: ble_service.py 硬编码 MTU=%s' % val)
    return issues


def hook_ble_init_reset():
    """H14: BLE 初始化失败 machine.reset()"""
    issues = []
    content = _read_file('ble_service.py')
    if not content:
        return issues
    if 'machine.reset()' not in content:
        issues.append('H14: ble_service.py 缺少 machine.reset() 异常恢复')
    return issues


def hook_wifi_ble_mutex():
    """H15: WiFi 启动前确认 BLE 已关闭"""
    issues = []
    content = _read_file('wifi_manager.py')
    if not content:
        return issues
    if 'deactivate' not in content and 'ble_disabled' not in content:
        issues.append('H15: wifi_manager.py 缺少 BLE 关闭检查')
    return issues


def hook_socket_close():
    """H16: Socket 及时关闭"""
    issues = []
    content = _read_file('wifi_manager.py')
    if not content:
        return issues
    conn_closes = len(re.findall(r'conn\.close\(\)', content))
    finally_closes = len(re.findall(r'finally:.*?conn\.close\(\)', content, re.DOTALL))
    if conn_closes > 0 and finally_closes == 0:
        issues.append('H16: wifi_manager.py conn.close() 不在 finally 中')
    return issues


def hook_listen_backlog():
    """H17: listen(3) 而非 listen(5)"""
    issues = []
    content = _read_file('wifi_manager.py')
    if not content:
        return issues
    listens = re.findall(r'\.listen\((\d+)\)', content)
    for val in listens:
        if int(val) > 3:
            issues.append('H17: wifi_manager.py listen(%s) 超过 3' % val)
    return issues


def hook_ota_protected_files():
    """H18: WiFi 凭据文件受 OTA 保护"""
    issues = []
    content = _read_file('ota_updater.py')
    if not content:
        return issues
    if 'wifi_config.txt' not in content:
        issues.append('H18: ota_updater.py _PROTECTED_FILE_NAMES 缺少 wifi_config.txt')
    if 'power_config.json' not in content:
        issues.append('H18: ota_updater.py _PROTECTED_FILE_NAMES 缺少 power_config.json')
    return issues


def hook_ota_wifi_timer_pause():
    """H19: 下载期间暂停 WiFi 关闭计时器"""
    issues = []
    wm = _read_file('wifi_manager.py')
    if not wm:
        return issues
    if '_ota_downloading' not in wm:
        issues.append('H19: wifi_manager.py 缺少 _ota_downloading 标志')
    return issues


def hook_ota_backup_before_replace():
    """H20: 文件替换前备份 .bak"""
    issues = []
    content = _read_file('ota_updater.py')
    if not content:
        return issues
    if '.bak' not in content:
        issues.append('H20: ota_updater.py 缺少 .bak 备份逻辑')
    return issues


def hook_ota_crc32_check():
    """H21: CRC32 校验下载文件"""
    issues = []
    content = _read_file('ota_updater.py')
    if not content:
        return issues
    if '_file_crc32' not in content and '_crc32' not in content:
        issues.append('H21: ota_updater.py 缺少 CRC32 校验')
    return issues


def hook_button_thresholds():
    """H22: 按钮时长阈值与 config.py 一致"""
    issues = []
    cfg = _read_file('config.py')
    app = _read_file('app.py')
    if not cfg or not app:
        return issues
    btn_consts = re.findall(r'(BTN_\w+_MS)\s*=\s*const\((\d+)\)', cfg)
    for name, val in btn_consts:
        if name not in app and val not in app:
            issues.append('H22: app.py 未引用 %s=%s' % (name, val))
    return issues


def hook_led_gpio():
    """H23: LED GPIO 与 config.py 一致"""
    issues = []
    cfg = _read_file('config.py')
    app = _read_file('app.py')
    if not cfg or not app:
        return issues
    led_m = re.search(r'LED_PIN\s*=\s*const\((\d+)\)', cfg)
    if led_m:
        led_name = 'LED_PIN'
        if led_name not in app:
            issues.append('H23: app.py 未使用 %s' % led_name)
    return issues


def hook_no_auto_wifi_start():
    """H24: 禁止开机自动启动 WiFi"""
    issues = []
    content = _read_file('app.py')
    if not content:
        return issues
    main_match = re.search(r'def\s+main\s*\(', content)
    if not main_match:
        return issues
    main_body = content[main_match.start():]
    while_match = re.search(r'while\s+True\s*:', main_body)
    if not while_match:
        return issues
    init_section = main_body[:while_match.start()]
    if re.search(r'\.start\(\)', init_section):
        issues.append('H24: app.py main() 初始化阶段调用了 .start()，禁止开机自动启动 WiFi')
    return issues


def hook_critical_has_hook():
    """H25: CRITICAL 踩坑项必须有对应 Hook"""
    issues = []
    memory = _read_file('MEMORY.md')
    if not memory:
        return issues
    critical_lines = re.findall(r'\[CRITICAL\].*', memory)
    for line in critical_lines:
        if '→' not in line and '升级' not in line:
            module_hint = ''
            if 'BLE' in line or 'ble' in line:
                module_hint = ' (建议升级为 H12~H14)'
            elif 'WiFi' in line or 'wifi' in line:
                module_hint = ' (建议升级为 H15~H17)'
            elif 'OTA' in line or 'ota' in line:
                module_hint = ' (建议升级为 H18~H21)'
            issues.append('H25: MEMORY.md CRITICAL 项未标注 Hook 升级: %s%s' % (line.strip()[:80], module_hint))
    return issues


def hook_template_source_consistency():
    """H26: 模板中引用的函数名/类名在源码中存在"""
    issues = []
    template_dir = os.path.join('.trae', 'rules', 'templates')
    if not os.path.isdir(template_dir):
        return issues
    template_map = {
        'ble-service.md': 'ble_service.py',
        'wifi-manager.md': 'wifi_manager.py',
        'wifi-handler.md': 'wifi_manager.py',
        'ota-updater.md': 'ota_updater.py',
        'config-persist.md': 'power_data.py',
    }
    for tpl_name, src_name in template_map.items():
        tpl_path = os.path.join(template_dir, tpl_name)
        src_path = src_name
        if not os.path.isfile(tpl_path) or not os.path.isfile(src_path):
            continue
        tpl_content = _read_file(os.path.join('.trae', 'rules', 'templates', tpl_name))
        src_content = _read_file(src_name)
        if not tpl_content or not src_content:
            continue
        def_names = set(re.findall(r'\bdef\s+(\w+)', src_content))
        class_names = set(re.findall(r'\bclass\s+(\w+)', src_content))
        all_names = def_names | class_names
        tpl_refs = set(re.findall(r'`(\w+)`', tpl_content))
        for ref in tpl_refs:
            if ref.startswith('_') or ref.isupper() or ref in ('self', 'cls', 'True', 'False', 'None'):
                continue
            if ref in ('bytearray', 'bytes', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple',
                       'finally', 'except', 'with', 'for', 'while', 'if', 'else', 'elif', 'try',
                       'return', 'yield', 'raise', 'import', 'from', 'class', 'def', 'async', 'await',
                       'print', 'len', 'range', 'open', 'type', 'super', 'property', 'staticmethod',
                       'classmethod', 'isinstance', 'hasattr', 'getattr', 'setattr', 'delattr'):
                continue
            if ref not in all_names and len(ref) > 3:
                issues.append('H26: %s 引用 `%s` 在 %s 中不存在' % (tpl_name, ref, src_name))
    return issues


def hook_event_bus_usage():
    """H27: 事件总线使用规范检查"""
    issues = []
    event_bus_path = 'event_bus.py'
    if not os.path.exists(event_bus_path):
        return issues
    event_constants = set()
    with open(event_bus_path) as f:
        for line in f:
            m = re.match(r'^EVENT_\w+\s*=\s*"(\w+)"', line.strip())
            if m:
                event_constants.add(m.group(1))
    for mod in BIZ_MODULES:
        if not os.path.exists(mod):
            continue
        content = _read_file(mod)
        if 'event_bus' not in content:
            continue
        for m in re.finditer(r'from event_bus import\s+(.+)', content):
            imported = m.group(1)
            for name in re.findall(r'EVENT_\w+', imported):
                if name.replace('EVENT_', '').lower() not in event_constants:
                    issues.append('H27: %s 引用不存在的事件常量 %s' % (mod, name))
    return issues


def hook_ble_uuid_conflict():
    """H28: BLE UUID 冲突检查"""
    issues = []
    config_path = 'config.py'
    if not os.path.exists(config_path):
        return issues
    uuids = {}
    with open(config_path) as f:
        for line in f:
            m = re.match(r'^(\w+_UUID)\s*=\s*const\((0x[0-9A-Fa-f]+)\)', line.strip())
            if not m:
                m = re.match(r'^(\w+_UUID)\s*=\s*(0x[0-9A-Fa-f]+)', line.strip())
            if m:
                name, value = m.group(1), m.group(2)
                int_val = int(value, 16)
                if int_val in uuids:
                    issues.append('H28: UUID 冲突: %s 和 %s 均为 %s' % (name, uuids[int_val], value))
                else:
                    uuids[int_val] = name
    return issues


def hook_file_size_limit():
    """H29: 业务模块文件大小上限检查（单文件不超过 900 行）"""
    issues = []
    for mod in BIZ_MODULES:
        if not os.path.exists(mod):
            continue
        with open(mod) as f:
            line_count = sum(1 for _ in f)
        if line_count > 900:
            issues.append('H29: %s 超过 900 行限制（当前 %d 行）' % (mod, line_count))
    return issues


def hook_traditional_chinese_extended():
    """H30: 繁体中文扩展检查（含注释和字符串）"""
    issues = []
    traditional_chars = set('裡著說與會這製運網點個為來過還裝當於對開經關將從時沒樣問種話長區業導師歷書幾機東車準據斷語現證識議適規設請產階際額預驗證讀變該論認權標準範圍運營區域設備體係資訊數據處開發環境測試部署維護優化整合配置管理系統網絡節點監控')
    simplified_map = {
        '裡': '里', '著': '着', '說': '说', '與': '与', '會': '会',
        '這': '这', '製': '制', '運': '运', '網': '网', '點': '点',
        '個': '个', '為': '为', '來': '来', '過': '过', '還': '还',
        '裝': '装', '當': '当', '於': '于', '對': '对', '開': '开',
        '經': '经', '關': '关', '將': '将', '從': '从', '時': '时',
        '沒': '没', '樣': '样', '問': '问', '種': '种', '話': '话',
        '長': '长', '區': '区', '業': '业', '導': '导', '師': '师',
        '歷': '历', '書': '书', '幾': '几', '機': '机', '東': '东',
        '車': '车', '準': '准', '據': '据', '斷': '断', '語': '语',
        '現': '现', '證': '证', '識': '识', '議': '议', '適': '适',
        '規': '规', '設': '设', '請': '请', '產': '产', '階': '阶',
        '際': '际', '額': '额', '預': '预', '驗': '验', '讀': '读',
        '變': '变', '該': '该', '論': '论', '認': '认', '權': '权',
        '標': '标', '範': '范', '圍': '围', '營': '营', '域': '域',
        '體': '体', '係': '系', '資': '资', '訊': '讯', '數': '数',
        '據': '据', '處': '处', '發': '发', '環': '环', '境': '境',
        '測': '测', '試': '试', '部署': '部署', '維': '维', '護': '护',
        '優': '优', '化': '化', '整': '整', '合': '合', '配': '配',
        '置': '置', '管': '管', '理': '理', '網': '网', '絡': '络',
        '節': '节', '點': '点', '監': '监', '控': '控',
    }
    real_traditional = set()
    for ch in traditional_chars:
        if ch in simplified_map and simplified_map[ch] != ch:
            real_traditional.add(ch)
    for mod in BIZ_MODULES:
        if not os.path.exists(mod):
            continue
        with open(mod) as f:
            for i, line in enumerate(f, 1):
                for ch in line:
                    if ch in real_traditional:
                        issues.append('H30: %s:%d 包含繁体字 "%s"（简体: "%s"）' % (mod, i, ch, simplified_map.get(ch, ch)))
                        break
    return issues


def run_hooks():
    """运行所有 Hooks 检查"""
    hooks = [
        ('H1  语法检查', hook_syntax_check),
        ('H2  CPython 专有库', hook_no_cpython_imports),
        ('H3  print() 禁止', hook_no_print),
        ('H4  const() 包装', hook_const_wrapper),
        ('H5  日志器大写', hook_logger_uppercase),
        ('H6  繁体中文', hook_no_traditional_chinese),
        ('H7  docstring', hook_docstring_exists),
        ('H8  specs 常量一致', hook_config_specs_consistency),
        ('H9  power_data 范围', hook_power_data_ranges),
        ('H10 web_pages 表单范围', hook_wifi_form_ranges),
        ('H11 硬件约束参数', hook_hardware_constraints_params),
        ('H12 BLE 回调无新对象', hook_ble_no_new_objects_in_irq),
        ('H13 BLE 参数从 config', hook_ble_params_from_config),
        ('H14 BLE reset 恢复', hook_ble_init_reset),
        ('H15 WiFi/BLE 互斥', hook_wifi_ble_mutex),
        ('H16 Socket 关闭', hook_socket_close),
        ('H17 listen(3)', hook_listen_backlog),
        ('H18 OTA 保护文件', hook_ota_protected_files),
        ('H19 OTA 暂停计时器', hook_ota_wifi_timer_pause),
        ('H20 OTA 备份', hook_ota_backup_before_replace),
        ('H21 OTA CRC32', hook_ota_crc32_check),
        ('H22 按钮阈值', hook_button_thresholds),
        ('H23 LED GPIO', hook_led_gpio),
        ('H24 禁止开机自启WiFi', hook_no_auto_wifi_start),
        ('H25 CRITICAL有对应Hook', hook_critical_has_hook),
        ('H26 模板源码一致性', hook_template_source_consistency),
        ('H27 事件总线规范', hook_event_bus_usage),
        ('H28 BLE UUID冲突', hook_ble_uuid_conflict),
        ('H29 文件大小上限', hook_file_size_limit),
        ('H30 繁体中文扩展', hook_traditional_chinese_extended),
    ]

    total_issues = 0
    for name, hook_fn in hooks:
        issues = hook_fn()
        if issues:
            for issue in issues:
                print("  ❌ %s" % issue)
            total_issues += len(issues)
        else:
            print("  ✅ %s" % name)

    return total_issues


def run_entropy():
    """运行 Entropy 治理扫描"""
    scans = [
        ('文档 Drift', scan_doc_drift),
        ('命名漂移', scan_naming_drift),
        ('死代码', scan_dead_code),
        ('规则腐烂', scan_rule_rot),
        ('配置一致性', scan_config_consistency),
    ]

    total_issues = 0
    for name, scan_fn in scans:
        print()
        print("### %s" % name)
        issues = scan_fn()
        if issues:
            for issue in issues:
                print("  ❌ %s" % issue)
            total_issues += len(issues)
        else:
            print("  ✅ 无问题")

    return total_issues


def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    mode = sys.argv[1] if len(sys.argv) > 1 else ''

    if mode == '--hooks':
        print("=" * 60)
        print("  Harness Hooks 自动检查 (H1~H23)")
        print("=" * 60)
        total = run_hooks()
    elif mode == '--all':
        print("=" * 60)
        print("  Entropy 治理扫描 + Harness Hooks")
        print("=" * 60)
        e = run_entropy()
        print()
        print("=" * 60)
        print("  Harness Hooks 自动检查 (H1~H23)")
        print("=" * 60)
        h = run_hooks()
        total = e + h
    else:
        print("=" * 60)
        print("  Entropy 治理扫描")
        print("=" * 60)
        total = run_entropy()

    print()
    print("=" * 60)
    if total == 0:
        print("  扫描完成: 全部通过 ✅")
    else:
        print("  扫描完成: 发现 %d 个问题 ❌" % total)
    print("=" * 60)

    return 0 if total == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
