# 合宙 CORE ESP32-C3 开发板硬件参考

> 本文档介绍 BikePower 项目所使用的硬件平台——合宙 CORE ESP32-C3 开发板（经典款），包含资源规格、引脚定义、供电方式、LED/按钮使用说明。

---

## 一、开发板概述

CORE ESP32-C3 核心板是基于乐鑫 ESP32-C3 设计的紧凑型开发板，尺寸仅 **21mm × 51mm**，板边采用邮票孔设计，可直接焊接嵌入产品。核心板支持 UART、GPIO、SPI、I2C、ADC、PWM 等接口。

![合宙 CORE ESP32-C3 开发板正面](../images/esp32c3-front.jpg)

![合宙 CORE ESP32-C3 引脚功能及分布](../images/esp32c3-pinout.jpg)

### 型号说明

| 版本 | USB 接口 | 驱动 | 刷机方式 |
|------|---------|------|---------|
| **经典款**（本项目所用） | Type-C + CH343 USB 转 TTL | 需安装 CH343 驱动 | UART0 串口烧录 |
| 新款（USB 直连） | Type-C 直连 ESP32-C3 USB | Win8+ 免驱 | 需选 USB 字样固件，GPIO18/19 被占用 |

> **本项目使用经典款**。经典款需安装 [CH343 驱动](http://www.wch.cn/downloads/CH343SER_EXE.html) 后才能正常下载固件。默认 CDC 驱动只能打印日志，速率太慢会导致下载失败。

---

## 二、硬件资源

| 资源 | 规格 |
|------|------|
| 主芯片 | ESP32-C3 (RISC-V 32 位单核, 最高 160MHz) |
| ROM | 384 KB |
| SRAM | 400 KB（其中 16 KB 用于 Cache） |
| Flash | 板载 4 MB SPI Flash（DIO 模式，最大支持 16 MB） |
| WiFi | 802.11b/g/n (2.4 GHz)，最高 150 Mbps |
| 蓝牙 | Bluetooth LE 5.0，支持 125Kbps/500Kbps/1Mbps/2Mbps |
| USB | Type-C 接口，CH343 USB 转 UART0 |
| 天线 | 2.4G PCB 板载天线 |
| 尺寸 | 21 mm × 51 mm |
| 工作温度 | -40°C ~ 85°C |

### 外设接口

| 接口 | 数量 | 说明 |
|------|------|------|
| UART | 2 路 | UART0（下载/日志）、UART1 |
| SPI | 1 路 | SPI2，支持主模式 |
| I2C | 1 路 | I2C 控制器 |
| ADC | 5 路 | 12 位 SAR ADC，最高 100 KSPS |
| PWM | 4 路 | 任意 GPIO 可复用，同时最多 4 路 |
| GPIO | 15 路 | 可用外部管脚，可复用 |
| LED | 2 路 | 贴片 LED：D4(GPIO12)、D5(GPIO13) |
| 按钮 | 2 个 | BOOT(GPIO9) + RESET |

---

## 三、引脚定义

### 完整引脚表

| 编号 | 名称 | 复位后默认功能 | 复用功能 | 电源域 | 上下拉 |
|------|------|--------------|---------|--------|--------|
| 01 | GND | 接地 | — | — | — |
| 02 | IO00 | GPIO00, 输入/输出/高阻 | UART1_TX / ADC_0 | VDD3P3_CPU | UP/DOWN |
| 03 | IO01 | GPIO01, 输入/输出/高阻 | UART1_RX / ADC_1 | VDD3P3_CPU | UP/DOWN |
| 04 | IO12 | GPIO12, 输入/输出/高阻 | SPIHD (Flash) | VDD3P3_CPU | UP/DOWN |
| 05 | IO18 | GPIO18, 输入/输出/高阻 | USB_D- | VDD3P3_CPU | UP/DOWN |
| 06 | IO19 | GPIO19, 输入/输出/高阻 | USB_D+ | VDD3P3_CPU | UP/DOWN |
| 07 | GND | 接地 | — | — | — |
| 08 | U0_RX | GPIO20, 输入/输出/高阻 | UART0_RX | VDD3P3_CPU | UP/DOWN |
| 09 | U0_TX | GPIO21, 输入/输出/高阻 | UART0_TX | VDD3P3_CPU | UP/DOWN |
| 10 | IO13 | GPIO13, 输入/输出/高阻 | — | VDD3P3_CPU | UP/DOWN |
| 11 | NC | 未连接 | — | — | — |
| 12 | RESET | 芯片复位 | — | VDD3P3_RTC | — |
| 13 | 3.3V | 芯片电源 3.3V | — | — | — |
| 14 | GND | 接地 | — | — | — |
| 15 | PWB | 3.3V 供电控制，高有效，不用可悬空 | — | — | — |
| 16 | 5V | 5V 电源，与 USB VBUS 相连 | — | — | — |
| 17 | GND | 接地 | — | — | — |
| 18 | 3.3V | 芯片电源 3.3V | — | — | — |
| 19 | IO02 | GPIO02, 输入/输出/高阻 | SPI2_CK / ADC_2 | VDD3P3_CPU | UP/DOWN |
| 20 | IO03 | GPIO03, 输入/输出/高阻 | SPI2_MOSI / ADC_3 | VDD3P3_RTC | UP/DOWN |
| 21 | IO10 | GPIO10, 输入/输出/高阻 | SPI2_MISO | VDD3P3_CPU | UP/DOWN |
| 22 | IO06 | GPIO06, 输入/输出/高阻 | — | VDD3P3_CPU | UP/DOWN |
| 23 | IO07 | GPIO07, 输入/输出/高阻 | SPI2_CS | VDD3P3_CPU | UP/DOWN |
| 24 | PB_11 | GPIO11, 输入/输出/高阻 | VDD_SPI | VDD3P3_CPU | UP/DOWN |
| 25 | GND | 接地 | — | — | — |
| 26 | 3.3V | 芯片电源 3.3V | — | — | — |
| 27 | IO05 | GPIO05, 输入/输出/高阻 | I2C_SCL / ADC_5 | VDD3P3_RTC | UP/DOWN |
| 28 | IO04 | GPIO04, 输入/输出/高阻 | I2C_SDA / ADC_4 | VDD3P3_RTC | UP/DOWN |
| 29 | IO08 | GPIO08, 输入/输出/高阻 | — | VDD3P3_CPU | UP/DOWN |
| 30 | BOOT | GPIO09, 输入 | BOOTMODE | VDD3P3_CPU | UP/DOWN |
| 31 | 5V | 5V 电源，与 USB VBUS 相连 | — | — | — |
| 32 | GND | 接地 | — | — | — |

---

## 四、BikePower 项目 GPIO 使用

| GPIO | 功能 | 说明 |
|------|------|------|
| GPIO9 | BOOT 按钮 | 内部上拉，按下为低电平。短按调节功率、长按触发配网 |
| GPIO12 | D4 LED | 高电平有效，LED 状态指示灯 |
| GPIO13 | D5 LED | 高电平有效，板载第二颗 LED（本项目中保留未用） |

### Flash 模式注意事项

本项目使用 **DIO Flash 模式**（MicroPython 默认），GPIO12/13 在 DIO 模式下可作为普通 GPIO 使用。**禁止使用 QSPI 模式**，否则 GPIO12~17 被 Flash 占用，LED 不可用。

### Strapping 引脚

ESP32-C3 启动时 GPIO2、GPIO8、GPIO9 的状态影响启动模式：

| GPIO | Strapping 功能 | 本项目中用途 |
|------|---------------|-------------|
| GPIO2 | 启动时需为高电平或悬空 | 未使用 |
| GPIO8 | 启动时需为高电平或悬空 | 未使用 |
| GPIO9 | 启动时内部上拉，低电平进入下载模式 | BOOT 按钮 |

---

## 五、供电方式

| 方式 | 说明 |
|------|------|
| Type-C USB 供电 | 调试首选，5V 输入经 LDO 降压至 3.3V |
| 5V + GND 排针 | 从 5V 和 GND 引脚供电 |
| 3.3V + GND 排针 | 直接给 3.3V 引脚供电 |

> ⚠️ 所有 I/O 为 3.3V 电平，**不兼容 5V**。仅 5V 引脚可直接接 5V 电源。

---

## 六、版本辨别

市面上存在盗版合宙开发板，正版特征如下：

1. Flash 芯片为**紫光**或**普冉**品牌，盗版使用劣质二手芯片
2. PCB 丝印清晰明显，盗版丝印细且模糊
3. PCB 背面有板厂正规生产批次号
4. 背面网址完整（`luatos.com`）
5. 背面 Pin 脚丝印使用白底黑字
6. 沉金工艺精致

---

## 七、相关链接

- [合宙 Wiki — ESP32C3-CORE 开发板](https://wiki.luatos.com/chips/esp32c3/board.html)
- [CH343 驱动下载](http://www.wch.cn/downloads/CH343SER_EXE.html)
- [乐鑫 ESP32-C3 技术规格书](https://www.espressif.com/sites/default/files/documentation/esp32-c3_datasheet_cn.pdf)
- [合宙 ESP32-C3 产品页](https://luatos.com/t/esp32c3)