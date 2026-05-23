# BikePower Agent Instructions

This file is the cross-tool entry point for AI coding agents. Keep it short and link to the canonical project rules instead of duplicating them.

## Must Read First

- `MEMORY.md` records user preferences, verified decisions, credentials handling notes, and repeated pitfalls.
- `.trae/rules/project_rules.md` records project structure, module boundaries, release rules, and commit rules.
- `.trae/rules/code_style.md` records MicroPython code style and ESP32-C3 runtime limits.
- `.trae/rules/hardware_constraints.md` records WiFi/BLE mutual exclusion, memory, sockets, buttons, LEDs, OTA, and deployment constraints.
- `.trae/rules/optimization-review.md` records the project-wide optimization checklist.
- `docs/agent-governance.md` records memory, rules, testing, reports, and conflict-governance procedures.

## Hard Rules

- Communicate with the user in Chinese unless explicitly asked otherwise.
- Do not start WiFi unless BLE has been stopped; ESP32-C3 WiFi and BLE are mutually constrained in this project.
- Do not auto-start WiFi at boot; WiFi config mode requires user long-press plus confirmation.
- Do not introduce CPython-only libraries such as `requests`, `asyncio`, or `threading` into device code.
- Do not use `print()` in business code; use `logger.get_logger()`.
- Do not add inline comments unless explicitly requested; keep required docstrings accurate.
- Do not hardcode ports, IPs, pins, UUIDs, or thresholds outside `config.py`.

## Workflow

- Before editing, run `git status --short` and identify the exact files affected by the current task.
- Before committing, run the relevant tests and record the real result in `CHANGELOG.md` or the commit handoff.
- Split commits by function: one bug fix, one feature, one script change, one release artifact update, or one documentation/rule topic per commit.
- Never mix unrelated code, screenshots, release artifacts, and governance docs into one commit.
- After each successful commit requested by the user, push immediately.
- Do not rewrite pushed history or amend commits unless the user explicitly requests it.

## Validation

- For MicroPython code, run at least `python3 -m py_compile` on affected Python files.
- For shell scripts, run `bash -n` on affected scripts.
- For release or OTA changes, validate `releases/latest/version.json`, `releases/ota/vX.Y.Z/`, and `target/firmware.bin` expectations.
- For project-wide optimization or release readiness, run `python3 scripts/entropy_scan.py`.
- For device behavior changes, run deployment or `bash test/test_runner.sh -p=<port>` when hardware is available.

## Memory Policy

- Write long-term user preferences and verified solutions to `MEMORY.md`.
- Write enforceable rules to `.trae/rules/`.
- Write long workflows and explanations to `docs/`.
- Do not store one-off task details, guesses, or content that can be inferred from source code.
