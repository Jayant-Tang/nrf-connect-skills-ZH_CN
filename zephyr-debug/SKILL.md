---
name: zephyr-debug
description: >-
  调试与诊断 NCS / Zephyr 固件：用 west debug/debugserver/attach 或直连 J-Link GDB Server 取证，配置 debug
  Kconfig，用 SEGGER RTT 日志通道，定位 sysbuild/单镜像 ELF；在线读 CFSR/HFSR/BFAR 等 fault 寄存器配合 halt
  决策表与 TrustZone Secure/Non-Secure 外设检查，再用 addr2line 离线解析 fault、HardFault、crash dump 和调用栈；
  APPROTECT 连不上时 recover。当需要附加调试器、抓 RTT、分析崩溃，或用户提到 J-Link、JLinkGDBServer、GDB、
  Ozone、RTT、west debug、west attach、addr2line、CFSR、fault、APPROTECT、device name 时使用；串口日志见 zephyr-serial-log。
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

## GDB 直连 J-Link GDB Server（脚本化 / 批量取证）

优先用上面的 `west debug` / `west attach`（已封装 server 启动与 gdb）。仅在需要脚本化批量取证、`west` runner 不可用、或要同时驱动多核时才手动直连。**用 NCS 工具链自带的 `arm-zephyr-eabi-gdb`，不要用系统 gdb。**

```bash
GDB="arm-zephyr-eabi-gdb"            # 经 nrfutil sdk-manager toolchain launch 运行时在 PATH 内
JLINK_SERVER="JLinkGDBServerCL.exe"  # SEGGER 安装目录；多版本取最新

# 1. 起 server（后台，日志写 .agent/logs/）
"$JLINK_SERVER" -device <jlink-device-name> -if SWD -speed 4000 -port 2331 \
  -nogui -silent -noir -timeout 0 > .agent/logs/jlink.log 2>&1 &

# 2. 等端口 LISTEN（最多 30s）
for i in $(seq 1 30); do netstat -an | grep -q ":2331.*LISTEN" && break; sleep 1; done

# 3. batch 取证（抓 PC/LR/SP + 反汇编 + 回溯）
nrfutil sdk-manager toolchain launch --ncs-version=<version> -- \
  "$GDB" -batch -ex "target remote localhost:2331" -ex "monitor halt" \
    -ex "print/x \$pc" -ex "print/x \$lr" -ex "print/x \$sp" \
    -ex "x/4i \$pc" -ex "backtrace 10" \
    -ex "detach" -ex "quit" <build>/zephyr/zephyr.elf

# 4. 用完必杀 server（务必执行）
taskkill //F //IM JLinkGDBServerCL.exe
```

- `<jlink-device-name>` 是 J-Link 设备名（如 `NRF54L15_M33`、`nRF52840_xxAA`），**与 qualified board target 不是一回事**，见下方设备速查。
- ELF 必须与已烧录固件同一次构建；多核 / sysbuild 各镜像用各自 ELF（见下方 ELF 路径）。
- SWD ≤ 4000 kHz。多核（nRF53/54）用不同端口（2331/2332），结束时分别 kill。
- 常用命令：`break main` / `break *0xADDR` / `watch *0xADDR`，`continue` / `stepi` / `next` / `finish`，`info registers` / `print $pc`，`x/32xw ADDR` / `x/i $pc`，`backtrace full` / `info threads` / `info locals`。

## Nordic 设备速查（GDB device name / J-Link 版本 / 基址）

GDB 直连填 `-device`、外设检查算地址时用：

| Board (PCA) | 设备 | J-Link device name | Core / Arch |
|---|---|---|---|
| PCA10156 | nRF54L15 DK | `NRF54L15_M33` | Cortex-M33 / armv8-m |
| PCA10095 | nRF5340 DK | `nRF5340_xxAA`（App）/ `nRF5340_xxAA_net`（Net） | Cortex-M33 / armv8-m |
| PCA10090 | nRF9160 DK | `nRF9160_xxAA` | Cortex-M33 / armv8-m |
| PCA10056 | nRF52840 DK | `nRF52840_xxAA` | Cortex-M4F / armv7e-m |
| PCA10040 | nRF52832 DK | `nRF52832_xxAA` | Cortex-M4F / armv7e-m |
| PCA10100 | nRF52833 DK | `nRF52833_xxAA` | Cortex-M4F / armv7e-m |

- J-Link 最低版本：nRF52 ≥ V7.80，nRF53 ≥ V7.94，nRF91 ≥ V8.10，**nRF54L ≥ V9.24a（很新，必须升级到最新）**。报 "bad device name" 多半是 J-Link 太旧。
- nRF54L15 关键地址：flash origin `0x00000000`(NS) / `0x10000000`(S)，RAM `0x20000000`，外设基址 `0x50000000`；FICR `0x00FF0000`、UICR `0x00FF8000`。
- **确切设备名与外设地址以 `nrfutil device list`、`build/zephyr/zephyr.dts` 和 SoC header（`modules/hal/nordic/nrfx/mdk/nrf*.h`）为准，不要凭记忆套表。**

## 连不上设备 / APPROTECT

GDB / J-Link 连不上时，先判断是不是被安全锁（APPROTECT）：

```bash
printf "device <name>\nconnect\nexit\n" > .agent/logs/jlink-probe.txt
JLink.exe -autoconnect 1 -CommanderScript .agent/logs/jlink-probe.txt 2>&1
```

提示 secured / 无法连接时：**`recover` 会擦除 flash / UICR / 密钥 / bonding，属破坏性操作，必须先告知用户并取得确认**（见总纲红线），再执行：

```bash
nrfutil device recover --serial-number <SN>
```

recover 后需重新烧录全部镜像（见 [zephyr-flash](../zephyr-flash/SKILL.md)）。nRF52/53 另有 `nrfjprog --recover` / CTRL-AP ERASEALL，nRF54L 走 `nrfutil device recover`。

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

### Windows CLI 重定向

较旧 Zephyr/NCS 的 J-Link runner 在 Windows PowerShell 中执行 `west rtt`，可能因 Python `select()` 监听非 socket 的 `stdin` 而报 `WinError 10038`。该问题由 Zephyr PR #100473 修复；当前 SDK 未包含修复时，使用 SEGGER `JLinkRTTLogger`，不要反复调整 RTT Kconfig。

先用 `nrfutil device list` 确认只有一个目标设备。PowerShell 示例：

```powershell
$log = ".\.agent\logs\rtt_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

JLinkRTTLogger.exe `
  -Device <jlink-device-name> `
  -If SWD `
  -Speed 4000 `
  -RTTChannel 0 `
  $log
```

- 最后一个位置参数 `$log` 才是 target RTT 数据文件；`>`、`2>&1` 或 `Tee-Object` 只能重定向 Logger 自身的连接状态和传输速率。
- 需要同时保存 Logger 诊断信息时，在命令末尾追加 `2>&1 | Tee-Object "$log.runner.log"`。
- 自动采集时后台启动 Logger，确认出现 `Searching for RTT Control Block...OK.` 后执行测试；到达采集时限后终止 Logger，再读取 `$log`。Logger 可能缓存文件写入，运行期间文件为空不代表没有收到 RTT 数据。
- 捕获 boot log 时先执行 `nrfutil device reset --serial-number <SN>`，随后立即启动 Logger；RTT ring buffer 可保留启动阶段尚未读取的数据。
- nRF54L15 DK 的 `<jlink-device-name>` 通常为 `NRF54L15_M33`，但仍以 build runner 配置和 J-Link 支持列表为准。

## 在线诊断（halt → 决策表 → 寄存器 / 外设）

固件跑飞或卡死时，先 halt 看 PC 定位状态，再决定下一步：

| PC 落点 | 状态 | 下一步 |
|---|---|---|
| `arch_system_halt+N` | 触发 fatal error | 读 fault 寄存器（下方） |
| `0xdeadbeef` / `0xffffffff` | Hard fault | recover 后重试，查栈 / 函数指针损坏 |
| `arch_cpu_idle+N` | 已启动进 idle | 主逻辑提前返回 / 线程没起来 |
| `z_cstart` / `z_sched_init` | 启动中卡住 | 初始化卡死 |
| 合法函数 / idle | 在运行 | 转查外设或业务逻辑 |

**读 fault 寄存器**（J-Link 可能不支持一行多寄存器，逐个读）：

```bash
nrfutil sdk-manager toolchain launch --ncs-version=<version> -- \
  arm-zephyr-eabi-gdb -batch -ex "target remote localhost:2331" -ex "monitor halt" \
    -ex "monitor reg CFSR" -ex "monitor reg HFSR" -ex "monitor reg BFAR" \
    -ex "info registers" -ex "backtrace 10" \
    -ex "detach" -ex "quit" <build>/zephyr/zephyr.elf
```

CFSR 位域：`[31:16]`=UFSR，`[15:8]`=BFSR，`[7:0]`=MMFSR（部分 J-Link 接受 `UFSR` / `BFSR` 别名）。

| 寄存器 | 看什么 |
|---|---|
| HFSR | FORCED=1 → 由低优先级异常升级；VECTTBL → 取向量表出错 |
| CFSR(UFSR) | UNDEFINSTR / INVSTATE / DIVBYZERO |
| CFSR(BFSR) | PRECISERR + BFARVALID → BFAR 即出错地址 |
| BFAR | BFARVALID 时为触发 bus fault 的地址 |

常见 fault → 根因：
- Usage Fault @ `PRE_KERNEL_1` → kernel API 调用过早（该阶段用 nrfx HAL，别用内核 API）。
- Undef instruction → 函数指针损坏 / 栈溢出。
- Bus Fault @ 外设地址 → 外设没上电 / 没开时钟。
- Bus Fault @ SRAM → 函数指针损坏 / 用了未初始化对象。
- MPU Fault @ SRAM → 在数据区执行代码，或越权访问。

**外设在线检查**：DT `reg` 是偏移，需加外设总线基址（见设备速查 / SoC header）。读出全 0 → 初始化被跳过 / 时钟未开；读到合法值 → 硬件 OK，查逻辑；返回 "Cannot access" → 域不对（nRF53/54/91 的 TrustZone Secure/Non-Secure 有 `_S` / `_NS` 地址别名，换域重试）、已崩溃或未上电。TrustZone 目标域看 `build/zephyr/.config` 的 `CONFIG_BOARD`（带 `/ns` 为 Non-Secure），nRF91 默认 `/ns`。

## Fault / Crash 离线解析（addr2line）

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
