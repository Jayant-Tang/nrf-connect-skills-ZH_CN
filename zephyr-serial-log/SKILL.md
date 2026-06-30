---
name: zephyr-serial-log
description: >-
  读取 nRF 设备串口输出并验证启动 / 运行日志：用 nrfutil device list 识别 VCOM/COM，按 DK 和 shield
  选择端口，使用 Nordic UART monitor 脚本限时读取，处理 DTR、先打开串口再复位捕获 boot log，并对乱码、
  截断和替换符做防幻觉处理。当需要验证固件输出、选择 COM/VCOM、读 UART 日志，或用户提到 boot log、DTR、
  nRF54L15 无输出、串口乱码时使用；烧录见 zephyr-flash。
---

# 串口与日志验证（NCS / Zephyr）

目标：用明确端口、固定时长和复位时序捕获日志，证明固件已按预期运行。

## 串口前 Gate

1. **确认设备**：先运行 `nrfutil device list`，读取设备 SN、traits、Ports、vcom index。多设备或多端口不明确时停止询问。
2. **确认 console 路由**：优先读应用 overlay 的 `chosen { zephyr,console = ...; }` 和 UART pinctrl；没有改动时使用 DK 默认映射。
3. **设置读取边界**：串口读取默认是持续流，自动验证必须使用 `--duration <seconds>`。
4. **先打开串口再复位**：boot log 在启动瞬间输出。先打开端口并让 DTR 生效，再复位设备。

## 开发板 VCOM / 串口端口映射

不同 DK 的 VCOM 映射不同，选错端口会无输出。Serial Terminal 按 VCOM index 升序显示端口；Windows 为 COM，Linux 多为 `/dev/ttyACM*`，macOS 为 `/dev/tty.*`。

| DK / 场景 | 默认应用日志端口 | UART / 引脚 | 备注 |
|---------|---------------|-------------|------|
| nRF52 DK（nrf52840dk、nrf52833dk、nrf52dk） | VCOM0 / 第一个端口 | `uart0` | 单核默认端口 |
| nRF5340 DK v2.0.0 | 第二个端口 | app core log | 第一个端口为 network core log |
| nRF5340 DK v1.0.0 | 第三个端口 | app core log | 第二个端口接 P24 |
| nRF54L15 / nRF54LM20 DK（无 shield） | VCOM1 / 第二个端口 | app core `UART20`，P1.04/P1.05 | VCOM0 对应 P0.00/P0.01 |
| nRF54L15 / nRF54LM20 DK + nRF7002 EB II shield | VCOM0 / 第一个端口 | app console reroute 到 `UART30` | VCOM1 与 shield 冲突，需在 Board Configurator 禁用 |
| nRF91 DK | VCOM0 / 第一个端口 | `uart0` | 默认 115200 8N1 |

应用 overlay 改了 `zephyr,console` 或 UART pinctrl 时，以实际 Devicetree 为准。

## DTR 与 nRF54L 注意事项

- **关键机制**：调试器 UART 引脚默认高阻态（tri-stated），**必须由终端软件发送 DTR 信号才能激活**。
- **自动行为**：pyserial 打开端口通常会拉高 DTR；无输出时手动执行 `DTR=False` → 等 200ms → `DTR=True` → 等 200ms。
- **nRF54L 硬件**：VCOM0 为 P0.00/P0.01，VCOM1 为 P1.04/P1.05；UART 信号经 DK 模拟开关连接到 debugger。
- **Board Configurator**：端口和 DTR 正确仍无输出时，让用户确认对应 VCOM 未被禁用；使用 nRF7002 EB II shield 时必须禁用 VCOM1。

## 查端口

```bash
nrfutil device list
```

关注输出中的 `serialNumber`、`Ports`、`vcom` index。PowerShell 备选：

```powershell
[System.IO.Ports.SerialPort]::GetPortNames()
```

## Nordic UART Monitor 脚本

读取 MCP resource `resource://nordicsemi/nordicsemi_uart_monitor.py`，保存为 `nordicsemi_uart_monitor.py`。脚本提供 `read`、`write`、`monitor` 三个子命令，依赖 `pyserial`，可用 `uv run`、`pipx run` 或已安装依赖的 `python` 执行。

```bash
uv run nordicsemi_uart_monitor.py read --port <COM-or-tty> --baud 115200 --duration 10
uv run nordicsemi_uart_monitor.py write --port <COM-or-tty> --baud 115200 --message "help"
uv run nordicsemi_uart_monitor.py monitor --port <COM-or-tty> --baud 115200
```

没有 `uv` 或 `pipx` 时：

```bash
python nordicsemi_uart_monitor.py read --port COM8 --baud 115200 --duration 15
```

## 捕获 boot log

步骤固定：

1. 用 `nrfutil device list` 选 SN 和端口。
2. 启动限时读取进程。
3. 等待读取进程打开端口。
4. 执行 `nrfutil device reset --serial-number <SN>`。
5. 回收读取输出并比对预期。

Windows PowerShell 模板：

```powershell
$rd = @('nordicsemi_uart_monitor.py','read','--port','COM8','--baud','115200','--duration','15')
$p = Start-Process python -ArgumentList $rd -RedirectStandardOutput uart.log -RedirectStandardError uart.err -PassThru -NoNewWindow
Start-Sleep -Seconds 2
nrfutil device reset --serial-number <SN>
$p.WaitForExit()
Get-Content uart.log
```

## 验证标准

- 看到完整 boot banner、应用预期日志、shell prompt、测试 PASS 或业务输出，才判定通过。
- nRF54L15 DK + hello_world 常见输出形态：

```text
*** Booting nRF Connect SDK ...
Hello World! nrf54l15dk/nrf54l15/cpuapp
```

无输出时按顺序检查：SN → 端口/VCOM → `zephyr,console` → 波特率 115200 8N1 → DTR → 复位时序 → Board Configurator → shield 冲突 → 供电和线缆 → 改走 RTT。

## 防幻觉（串口日志）

读到乱码、不可见字符或半截字节时，**先排查物理/编码原因，绝不脑补出有意义的字符串或结论**：

- 乱码常见原因是波特率不符、选错 VCOM、DTR 未生效或复位时序错误。
- 输出含 `�`、截断行、半个 UTF-8 字节、二进制 dump 时，该片段不可靠；提高 duration、保存原始 bytes、换 RTT 或按 hex 重读。
- 只引用完整、可解释、可复现的日志作为结论依据。
