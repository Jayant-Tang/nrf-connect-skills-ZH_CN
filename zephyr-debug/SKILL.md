---
name: zephyr-debug
description: >-
  调试与诊断 NCS / Zephyr 固件：用 west debug/debugserver/attach 启动 GDB 或调试服务器，配置 debug
  Kconfig，使用 SEGGER RTT 日志通道，定位 sysbuild/单镜像 ELF，并用 addr2line 分析 fault、HardFault、
  crash dump 和调用栈。当需要附加调试器、抓 RTT、分析崩溃或用户提到 J-Link、GDB、Ozone、RTT、
  west debug、west attach、addr2line、fault 时使用；串口日志见 zephyr-serial-log。
---

# 调试与诊断（NCS / Zephyr）

目标：连接正确设备和正确 ELF，获取可复现的调试证据，再定位到源码或配置问题。

## 调试前 Gate

1. **确认 build 目录和 ELF**：先读取 [zephyr-build](../zephyr-build/SKILL.md)，读取 selected build dir 和实际 ELF 路径。
2. **确认设备**：运行 `nrfutil device list`；多设备时用 `--dev-id <segger_id>` 或停止询问用户。
3. **确认调试目标**：单核、app core、network core、FLPR、non-secure/TF-M 目标必须明确。多核或 TF-M 不明确时先查 Nordic MCP。
4. **确认构建配置**：需要断点和变量检查时启用 debug 配置后重新构建。

## west 调试命令

所有命令都加 NCS 工具链 wrapper：

```bash
nrfutil sdk-manager toolchain launch --ncs-version=<version> -- \
  west debug -d <selected-build-dir>
```

| 目的 | 命令 |
|------|------|
| 启动 GDB 会话 | `west debug -d <selected-build-dir>` |
| 启动 GDB server | `west debugserver -d <selected-build-dir>` |
| 附加运行中目标 | `west attach -d <selected-build-dir> --skip-rebuild` |
| 查看 runner 上下文 | `west debug -H -d <selected-build-dir>` |
| 指定 J-Link runner | `west debug -d <selected-build-dir> --runner jlink` |

多个调试器连接时加 runner 参数中的 `--dev-id <segger_id>`；具体位置以 `west debug -H` 输出为准。

## Debug Kconfig

用于可读调试：

```conf
CONFIG_DEBUG_OPTIMIZATIONS=y
CONFIG_DEBUG_THREAD_INFO=y
CONFIG_THREAD_NAME=y
```

需要线程分析时再加：

```conf
CONFIG_THREAD_ANALYZER=y
```

改配置后读取 [zephyr-build](../zephyr-build/SKILL.md) 重新构建。

## ELF 路径

- 非 sysbuild：`<build>/zephyr/zephyr.elf`。
- sysbuild：应用 ELF 通常为 `<build>/<app-dir-name>/zephyr/zephyr.elf`；MCUboot、net core、FLPR 等在各自镜像目录。
- Ozone、GDB、`addr2line` 必须使用与当前烧录固件同一次构建生成的 ELF。

## RTT 日志

UART 被占用、VCOM 不通或需要低侵入日志时使用 RTT。

常用配置：

```conf
CONFIG_USE_SEGGER_RTT=y
CONFIG_LOG_BACKEND_RTT=y
```

RTT shell 还需要：

```conf
CONFIG_SHELL_BACKEND_RTT=y
CONFIG_SHELL_BACKEND_SERIAL=n
```

构建时可使用 RTT snippet：

```bash
west build -d <selected-build-dir> --snippet rtt-console
```

读取方式按环境选择：`west rtt`、JLinkRTTViewer、JLinkRTTLogger、nRF Connect Serial Terminal 的 RTT 模式。无 RTT 输出时检查是否启用了 RTT backend、是否被 UART console 冲突、是否连接了正确设备。

## Fault / Crash 分析

固定流程：

1. 保存完整 fault log，包含 `pc`、`lr`、`r0-r3`、xPSR、线程名、栈回溯地址。
2. 确认 ELF 对应当前固件。
3. 对 `pc`、`lr` 和回溯地址逐个解析：

```bash
addr2line -e <path-to-zephyr.elf> -f -C <addr>
```

4. 地址落在不同镜像时，切换对应镜像 ELF 解析。
5. 地址解析、源码位置、Kconfig/Devicetree 条件必须交叉验证，不只凭一个栈帧下结论。

## 闭环验证

改调试配置、RTT、日志 backend、fault handler 后：[zephyr-build](../zephyr-build/SKILL.md) → [zephyr-flash](../zephyr-flash/SKILL.md) → [zephyr-serial-log](../zephyr-serial-log/SKILL.md) 或 RTT 重新采集。调试命令能连接不代表问题修复，最终仍以日志、断点证据或复现结果判定。

## 防幻觉

- fault 地址、寄存器、dump 字节按原始值核对；不补不存在的栈帧、函数名或线程名。
- 优化构建下变量值和行号可能不可靠；需要时启用 debug 优化后重现。
- 日志截断、乱码、替换符 `�` 或二进制片段不作为最终结论；换 UART/RTT/GDB 方式重取。
