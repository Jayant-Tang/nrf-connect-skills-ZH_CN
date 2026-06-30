---
name: ble-dtm
description: >-
  BLE Direct Test Mode (DTM) 射频测试：通过 2-wire UART（19200 8N1、16-bit MSB-first 帧）控制 DUT 做
  TX / RX / PER 等 PHY 合规与产线射频测试。先给 DUT 烧 DTM 固件，再用串口下发命令。当用户做 RF / 射频
  认证、BLE PHY 测试、产线射频校验，或提到 DTM、Direct Test Mode、PRBS9、transmitter / receiver test、
  packet error rate、19200 baud、射频测试、蓝牙认证时使用。构建烧录见 zephyr-build / zephyr-flash，端口选择见 zephyr-serial-log。
---

# BLE Direct Test Mode (DTM)

目标：用 2-wire UART 控制 DUT 跑射频 PHY 测试（TX 连续发包、RX 收包计数 / PER），用于射频合规认证与产线校验。

## 前置（DUT 必须先跑 DTM 固件）

DTM 不是普通固件自带的功能，先把 DUT 切到 DTM：

1. **烧 DTM 固件**：构建并烧录 NCS 的 DTM sample（如 `nrf/samples/bluetooth/direct_test_mode`，**确切路径以 SDK 版本为准，查 Nordic MCP / 本地 SDK 确认**）。构建见 [zephyr-build](../zephyr-build/SKILL.md)，烧录见 [zephyr-flash](../zephyr-flash/SKILL.md)。
2. **确认控制接口**：DTM 有 2-wire UART（本指南）和 HCI / over-UART 两种控制方式；引脚、波特率以 sample 的 `prj.conf` / board overlay 为准，不要假设。
3. **选串口**：DTM 的 2-wire UART 往往不是默认 console 口。端口 / VCOM 识别见 [zephyr-serial-log](../zephyr-serial-log/SKILL.md)。

## 串口与帧格式

- **串口**：19200 baud，8N1。
- **帧**：16-bit，**MSB first**；命令 2 字节、响应 2 字节。
- **命令编码**（高 2 位 bits[15:14]）：`00`=SETUP，`01`=RX，`10`=TX，`11`=END；低 14 位是参数（频道 freq、length、packet type）。

## 命令集（示例编码，实际按 spec 计算 / 查证）

下表为常见操作的示例帧，**不同 freq / length / packet type 对应的位编码须按 Bluetooth Core《DTM》spec 或 Nordic 文档计算**，不要把示例值套到其他参数：

| 操作 | 命令 (MSB first) | 响应 |
|---|---|---|
| Reset | `0x0000` | `0x0000` |
| TX（ch37, PRBS9, len=37） | `0xA594` | `0x0000` |
| RX（ch37） | `0x6500` | `0x0000` |
| End | `0xC000` | `0x8000` + packet count（仅 RX 有计数） |

## Python 快测（限时、errors='replace'）

```python
import serial, time

def dtm_cmd(ser, cmd: bytes) -> str:
    ser.write(cmd)
    time.sleep(0.5)
    resp = ser.read(2)                        # 限时由 serial timeout 控制
    return "0x" + resp.hex().upper() if resp else "NO RESPONSE"

def dtm_test(port: str, baud: int = 19200):
    with serial.Serial(port, baud, timeout=2) as ser:
        # 同步：连发 Reset 直到有 ACK
        for _ in range(5):
            if dtm_cmd(ser, b"\x00\x00") != "NO RESPONSE":
                break
        for name, cmd in [("Reset", b"\x00\x00"),
                          ("TX",    b"\xA5\x94"),
                          ("End",   b"\xC0\x00")]:
            print(f"{name}: {dtm_cmd(ser, cmd)}")
```

## 防幻觉（DTM）

- 响应只按收到的**原始 2 字节 hex** 解读，不脑补含义；`NO RESPONSE` 先排查波特率(19200)、接线(2-wire)、DUT 是否真在 DTM 固件，不要臆测成「测试通过 / 失败」。
- END 的 packet count 只有 RX 测试才有；TX 的 End 响应不带计数。
- 命令字编码、sample 路径、引脚波特率以实际 SDK 版本与 Nordic 文档为准；拿不准就查 Nordic MCP，**不编造编码值**。
