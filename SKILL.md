---
name: zephyr-expert
description: >-
  Expert guidance for Zephyr RTOS and Nordic nRF Connect SDK (NCS): answers and implementation help
  grounded in workspace source, the Nordic docs MCP, official NCS docs, and the NCS Add-ons index.
  Covers build, flash, debug, and logging workflows (west build/flash/debug, sysbuild, menuconfig,
  west update/blobs, twister), configuration (Kconfig, prj.conf, Devicetree, .overlay, snippets),
  the nrfutil toolchain (including fast flashing with nrfutil device program and direct
  RRAM/flash/external-QSPI read/write/erase/dump via nrfutil device),
  MCUboot/DFU, SEGGER RTT/J-Link, and nRF54L cross-domain GPIO / pinctrl pin mapping.
  Use when the workspace contains Zephyr or NCS code (west.yml, zephyr/, prj.conf, *.overlay, boards/),
  or when the user asks about Zephyr, NCS, Kconfig, Devicetree, west, sysbuild, nrfutil, nrfjprog,
  MCUboot, NCS Add-ons, nRF54L pin mapping / cross-domain GPIO, reading or writing device flash/RRAM/external memory,
  or building/flashing/debugging Nordic/Zephyr firmware.
---

# Zephyr 专家（nRF Connect SDK / NCS）

## 角色与原则

1. 作为 Zephyr RTOS 与 Nordic nRF Connect SDK 的可靠参考：结论必须基于工作区源码或官方渠道可查证的信息，不做无依据的推断。
2. 引用事实时，标明来源：工作区文件路径，或文档/网页 URL。
3. 明确区分**上游 Zephyr 通用行为**与 **NCS / Nordic 特有**的扩展、补丁或限制。
4. 基础 build/flash/debug 流程按本 Skill 的固定步骤执行；只有版本差异、芯片/协议细节、疑难报错或不确定结论才查询 Nordic MCP。

## 知识来源（按此优先级使用）

1. **工程源码 + 对应版本 NCS 源码（最优先，同级）** — 两者都是最高优先、最可信的参考源：
   - **工程目录**：目录含 `prj.conf`、`*.overlay`、`CMakeLists.txt`（以及 `west.yml`、`sysbuild.conf`、`boards/` 等）即为 NCS/Zephyr 应用工程。优先检索并引用本地源码：Kconfig、Devicetree 绑定（`dts/bindings/`）与 overlay、驱动、子系统、samples。
   - **对应版本 NCS 安装树**：参考与工程匹配版本的 NCS 源码 `zephyr/`、`nrf/`、`modules/`、`nrfxlib/`、`bootloader/`。版本判断见「环境准备 · 确认 NCS 版本」；安装路径未知且必须依赖时，先询问用户版本与路径。

2. **Nordic MCP** — 涉及 Nordic 专有行为、NCS 版本差异、官方工具说明、UART 监控脚本、代码审查规范时使用。
   - 先列 MCP 资源，优先读取：
     - `resource://nordicsemi/embedded-code-guidance-ncs-zephyr`
     - `resource://nordicsemi/nrfutil-manual`
     - `resource://nordicsemi/nordicsemi_uart_monitor.py`
   - 需要查 Nordic 官方知识库时，用 `nordicsemi_search_sources`。query 使用一句完整自然语言问题，英文通常更准。

3. **网络搜索** — 前两者无法解决时（疑难报错、新版本行为、社区经验）使用；结论须与本地源码/MCP 交叉验证，并标明来源 URL。
   - **首选 https://devzone.nordicsemi.com/**（Nordic 官方开发者社区 DevZone）；其次官方文档 `docs.nordicsemi.com`、Zephyr 官方文档、相关 GitHub 仓库。
   - 用 WebSearch/WebFetch 检索；query 用完整自然语言问题，英文通常更准。

## 环境准备（编译 / 烧录 / 执行 west 前必须）

目标：让 Agent 执行的每条 `west build/flash/debug` 都运行在 NCS 工具链环境中，避免裸 PowerShell/CMD 里找不到 `west`、CMake、Python 包或交叉编译器。

1. **确认 NCS 版本**：
   - 优先从工程 `west.yml`、`VERSION`、已有 build log、用户上下文判断。
   - 若无法可靠判断，执行 `nrfutil sdk-manager list` 查看本机已安装版本，必要时询问用户。
   - `--ncs-version` 通常写完整版本，例如 `v3.3.0`、`v3.2.4`。

2. **首选：每条 west 命令通过 `nrfutil sdk-manager toolchain launch` 包起来**。这是 Agent 最稳的用法，不依赖持久 shell 环境，Windows/Linux/macOS 写法一致：
   ```bash
   nrfutil sdk-manager toolchain launch --ncs-version <version> -- west build -b <board> -p always
   ```
   传递带 `--flag` 的命令时，保留 `--` 分隔符：
   ```bash
   nrfutil sdk-manager toolchain launch --ncs-version <version> -- west build -b <board> --sysbuild -p always
   ```

3. **Freestanding 项目需要 `--chdir`**：
   对于非 west workspace 的 freestanding 项目（没有 `.west/` 目录），Zephyr extension 命令是 workspace-bound 的，必须加 `--chdir <ncs-install-dir>`（这是 `nrfutil` 的 flag，在 `--` 之前），且 app/build 目录用绝对路径：
   ```bash
   nrfutil sdk-manager toolchain launch --ncs-version <version> \
     --chdir <ncs-install-dir> -- \
     west build -p -b <board> -d <abs-build-dir> <abs-app-dir>
   ```
   West workspace 项目（有 `.west/` 目录）无需 `--chdir`，直接在 workspace 根目录执行即可。

4. **需要持久环境时才使用 env 脚本**：
   - Windows PowerShell：
     ```powershell
     nrfutil sdk-manager toolchain env --ncs-version <version> --as-script powershell | Invoke-Expression
     ```
   - Linux/macOS：
     ```bash
     source <(nrfutil sdk-manager toolchain env --ncs-version <version> --as-script)
     ```

5. **工程根目录** — 在应用工程根（含该应用 `CMakeLists.txt` 与 `prj.conf` 的目录）执行编译，**不要在 NCS 根目录直接编译**。

6. **不要写死 NCS 根路径或盘符**。需要 NCS 源码路径时，从 west manifest、build log、`nrfutil sdk-manager list --all-fields`、环境变量或用户输入推断。

## 构建日志重定向

编译输出可能非常冗长（200+ 行），直接输出到对话会污染上下文。推荐模式：

```bash
mkdir -p <build-dir>
nrfutil sdk-manager toolchain launch --ncs-version <version> -- \
  west build -p -b <board> -d <build-dir> <app-dir> \
  > <build-dir>/build.log 2>&1 && echo "BUILD_SUCCESS" || echo "BUILD_FAILED"
```

然后用 `tail -n 30 <build-dir>/build.log` 查看摘要，用 `grep "error:\|FAILED" <build-dir>/build.log` 排查问题。

## 常用命令速查

> 下表 `west` / `twister` 命令默认省略前缀 `nrfutil sdk-manager toolchain launch --ncs-version <version> --`（见「环境准备」）；仅当当前 shell 已处于 NCS 工具链环境时才可直接裸跑。`nrfutil device` / `nrfjprog` 无需此前缀。

| 目的 | 命令（已省略工具链前缀） |
|------|------|
| 编译（指定开发板） | `west build -b <board> -p always` |
| 指定构建目录 | `west build -b <board> -d build/<name> -p always` |
| 多镜像构建（含 MCUboot 等） | `west build -b <board> --sysbuild -p always` |
| 烧录（首选，免工具链启动） | `nrfutil device program --firmware build/merged.hex --serial-number <SN>` 然后 `nrfutil device reset --serial-number <SN>`（均无需前缀） |
| 烧录（需 west runner 特殊逻辑时） | `west flash --dev-id <serial>` |
| 调试 / 附加 | `west debug` / `west attach` |
| 交互式 Kconfig | `west build -t menuconfig`（或 `guiconfig`） |
| 内存占用报告 | `west build -t ram_report` / `rom_report` |
| 拉取/更新模块（按 manifest） | `west update` |
| 拉取二进制 blob | `west blobs fetch <module>` |
| 列出开发板 | `west boards` |
| 运行测试 | `twister -T <path> -p <board>` |
| 设备列表 / 擦除 | `nrfutil device list` / `nrfjprog --recover`（无需前缀） |
| 复位设备 | `nrfutil device reset --serial-number <serial>`（无需前缀） |

要点：
- **改了开发板、`prj.conf`、Kconfig 或 manifest 后，务必加 `-p always` 干净编译**，否则可能用到旧缓存。
- **烧录首选 `nrfutil device program` 直烧合并镜像**：它是 `nrfutil device` 原生命令，无需 `nrfutil sdk-manager toolchain launch` 前缀，省去 `west flash` 每次启动工具链的开销，最快。烧 sysbuild 的 `build/merged.hex`（单镜像工程烧 `build/zephyr/zephyr.hex`），烧完用 `nrfutil device reset --serial-number <SN>` 触发运行；需控制擦除/复位策略时加 `--options`（取值见 nrfutil-manual）。仅当需要 west runner 的特殊逻辑时才用 `west flash`。
- **产物路径**：
  - 单镜像工程：`build/zephyr/`，含 `zephyr.hex`、`zephyr.elf`。
  - 多镜像（sysbuild）工程：各镜像分目录，如 `build/<image>/zephyr/`（`build/mcuboot/zephyr/`、`build/hello_world/zephyr/` 等）。
  - sysbuild/MCUboot 烧录用合并镜像 `build/merged.hex`。

## 配置与文件结构要点

- **`prj.conf`** — 应用默认 Kconfig 配置；按开发板可加 `boards/<board>.conf`，额外片段用 `-DEXTRA_CONF_FILE=...` 或 `-DCONF_FILE=...`。
- **Kconfig** — 控制功能开关与子系统；与 Devicetree 配合（DT 描述硬件，Kconfig 决定软件特性）。
- **Devicetree** — 板级 `.dts`/SoC `.dtsi` 描述硬件；应用用 `<board>.overlay` 或 `boards/<board>.overlay` 覆盖；绑定在 `dts/bindings/`。生成结果见 `build/zephyr/zephyr.dts` 与 `devicetree_generated.h`。
- **snippets** — 复用型配置组合，`west build --snippet <name>`（如 `--snippet rtt-console`）。
- **sysbuild** — NCS 当前的多镜像构建系统（替代旧 child/parent image 及已弃用的 Partition Manager），用于应用 + MCUboot + 网络核心等组合；配置见 `sysbuild.conf` 与 `sysbuild/`。
  - 注意：`CONFIG_PARTITION_MANAGER` 在 NCS v2.6+ 已标记弃用（deprecated），sysbuild + `SB_CONFIG_PARTITION_MANAGER` 是替代方案。
- **MCUboot / DFU** — 启用后镜像需签名；签名用 west sign / `imgtool`，密钥与 slot 配置经 sysbuild/Kconfig 设定。

## 开发板 VCOM / 串口端口映射

不同 Nordic DK 系列的虚拟串口映射有本质差异，错误选择端口将导致完全收不到数据。开发板输出前必须先确定正确的 COM 口。

> **通用提示（任何 DK 都可能遇到）**：带可配置 interface MCU 的 DK（nRF52840 DK、nRF5340 DK、nRF54L/54LM 系列等）的 VCOM 可在 nRF Connect for Desktop - Board Configurator 上位机中被禁用。若端口和 DTR 都正确却收不到数据，先让用户在 Board Configurator 确认对应 VCOM 已启用（出厂默认启用）。

### 端口映射表

| DK 系列 | App 核 Console | App 核 UART 实例 | VCOM 端口 | 备注 |
|---------|---------------|-----------------|-----------|------|
| nRF52 DK (nrf52840dk, nrf52833dk, nrf52dk) | VCOM0 | uart0 | vcom:0 (首个 COM) | 单核，VCOM0 即 app 口 |
| nRF53 DK (nrf5340dk) | VCOM0 | uart0 | vcom:0 (首个 COM) | App + Network 双核，app 用 VCOM0 |
| **nRF54L15 DK** (无 shield) | **VCOM1** | **uart20** | **vcom:1 (第二个 COM)** | App 核用 VCOM1；VCOM0 是 FLPR/TF-M（uart30） |
| nRF54L15 DK (挂 nRF7002 EB II shield) | **VCOM0** | uart30 | vcom:0 (首个 COM) | Shield 会交换端口！VCOM1 被禁 |
| nRF54LM20 DK (无 shield) | VCOM1 | uart20 | vcom:1 (第二个 COM) | 同 nRF54L15 |
| nRF91 DK (nrf9151dk, nrf9160dk) | VCOM0 | uart0 | vcom:0 (首个 COM) | |

### nRF54L 系列 UART 架构

nRF54L15 / nRF54LM20 DK 板载一颗接口 MCU（Interface MCU）负责 VCOM 路由。UART 信号经模拟开关连接到 J-Link 调试器：

- **关键机制**：调试器 UART 引脚默认为高阻态（tri-stated），**必须由终端软件发送 DTR 信号才能激活**。
- **DTR 触发时序**：打开串口 → `DTR=False` → 等待 200ms → `DTR=True` → 等待 200ms → 此时 UART 路由被激活 → 复位开发板 → 开始接收数据。
- **时序至关重要**：boot log 在启动瞬间打印，必须**先打开串口并激活 DTR，再复位/烧录开发板**，否则错过开机 log。

### 查端口方法

```bash
nrfutil device list
# 输出中关注 "Ports" 行：COMx, vcom: 0 / COMy, vcom: 1
```

PowerShell 备选：`[System.IO.Ports.SerialPort]::GetPortNames()`

## 串口 / 日志验证（agent 自动读取设备输出）

**关键约束**：串口是无限数据流，命令不会自动退出。验证时务必为读取设定结束边界，否则命令会一直阻塞。

### 流程

1. 用 `nrfutil device list` 确定 COM 口 → 按上方端口映射表选目标端口（nRF54L15 DK 无 shield 时为 VCOM1 = 第二个 COM）。
2. **先读后复位**：boot log 在启动瞬间打印，必须先打开串口读取、再复位/烧录。
3. **读取阻塞 → 用后台命令复位**：限时读取（`--duration N`）是前台阻塞、不自动退出的命令，而复位要在读取进行中触发。务必让二者**并发**：把读取放后台（如另起一个 shell 或后台进程），再用另一条命令跑 `nrfutil device reset`，最后回收读取输出。**切勿“先等读取结束再复位”**——那样必然错过 boot log。

> **DTR（nRF54L 系列）**：nRF54L15 / 54LM20 的 UART 经板载 interface MCU 路由，需 DTR 激活。先读后复位时，pyserial 打开端口默认拉高的 DTR 即可激活 UART，无需手动 toggle；若仍收不到数据，在打开端口后手动 toggle（`dtr=False` → 200ms → `dtr=True` → 200ms）。

### Nordic UART Monitor 脚本

读取 MCP 资源 `resource://nordicsemi/nordicsemi_uart_monitor.py` 获取脚本（依赖 `pip install pyserial`）。脚本有 `read` / `write` / `monitor` 三个子命令；`read --duration N` 读 N 秒后自动退出，最适合 agent 自动验证。

```bash
# 读 COM8（nRF54L15 DK 的 VCOM1）15 秒后自动退出
python nordicsemi_uart_monitor.py read --port COM8 --baud 115200 --duration 15
```

单脚本实现“后台读取 + 复位”（Windows PowerShell）：读取进程后台启动（`Start-Process ... -PassThru`），`Start-Sleep` 让其先就绪，再复位触发 boot log，最后 `WaitForExit` 回收输出。

```powershell
$rd = 'nordicsemi_uart_monitor.py','read','--port','COM8','--baud','115200','--duration','15'
$p = Start-Process python -ArgumentList $rd -RedirectStandardOutput out.txt -PassThru -NoNewWindow
Start-Sleep -Seconds 2
nrfutil device reset --serial-number <SN>   # 复位触发 boot log
$p.WaitForExit()
Get-Content out.txt
```

nRF54L15 DK + hello_world（UART console）预期输出：

```text
*** Booting nRF Connect SDK v3.3.0 ***
Hello World! nrf54l15dk/nrf54l15/cpuapp
```

## 乱码与防幻觉（串口日志 / 内存 dump）

读到乱码、不可见字符或半截字节时，**先排查物理/编码原因，绝不“脑补”出有意义的字符串或结论**。

- **串口乱码**：几乎都是波特率不符（默认 115200）、选错 VCOM 口、或 DTR 未激活时的线路噪声。先核对这三项；必要时按原始 hex 字节查看，而非猜测文字。
- **内存 dump 乱码**：擦除态为全 `0xFF`（RRAM / 外部 flash），未初始化或非文本区出现非 ASCII 字节属正常。以 word / hex 形式核对原始字节，**不要把随机字节臆测成固件版本、序列号、字符串等内容**。
- **只对完整、可解释的输出下结论**：output 被截断或含替换符（如 `�`）时，明确说明该处不可靠，换方式重取（提高 `--duration`、改走 RTT、或按 hex 重读）后再判断，不要基于残缺数据推断。

## 调试与日志

- **SEGGER RTT** — 无串口时的备用日志通道（`CONFIG_USE_SEGGER_RTT=y` + `--snippet rtt-console`，经 `JLinkRTTLogger` 读取）；本 skill 的自动日志验证统一走上文串口方式，RTT 抓取流程不在此展开。
- **串口日志** — UART console backend（`CONFIG_UART_CONSOLE=y`），用串口终端查看。nRF54L 系列务必按上方端口映射表和 DTR 流程操作。
- **J-Link / nRF** — 烧录调试经 J-Link；`west debug` 启动 GDB，`nrfjprog`/`nrfutil device` 用于擦除、恢复、读取复位原因。
- **Fault 分析** — 崩溃日志含寄存器与调用栈；用 `addr2line -e build/zephyr/zephyr.elf <addr>` 定位代码行；必要时开 `CONFIG_DEBUG`、`CONFIG_THREAD_NAME` 等。

## nRF54L 系列注意事项：GPIO 跨域分配（pinctrl 最常见坑）

nRF54L 按 power domain 把 GPIO 拆成多个端口，**外设默认只能用本 domain 对应端口的引脚，且一个外设的所有引脚必须在同一端口**。在 `.overlay` / pinctrl 里把外设分到别的端口，是最高频的坑——外设直接不工作，或必须额外开跨域配置才跑得起来。

### domain ↔ 端口 ↔ GPIOTE 映射（nRF54L15）

| Power domain | GPIO 端口 | 最高速 | GPIOTE / 中断·唤醒 | 代表外设 |
|---|---|---|---|---|
| MCU | **P2** | 64 MHz | **无 GPIOTE、无 SENSE/DETECT、不能唤醒** | UARTE00、SPIM00/SPIS00、FLPR、TRACE |
| PERI | **P1** | 8 MHz | GPIOTE20（8 通道） | UARTE20/21/22、SPIM/SPIS/TWIM/TWIS2x、PWM2x、PDM20、I2S20、SAADC(AIN) |
| LP | **P0** | 8 MHz | GPIOTE30（4 通道） | UARTE30、SPIM30/SPIS30/TWIM30、GRTC |
| RADIO | 无 GPIO 端口 | — | — | —（仅测向/多天线时借用 P1） |

> 速记：**外设实例 ID 的首位数字 = 域 = 端口号**。`uart20`→PERI→P1，`uart30`→LP→P0，`uart00`/`spim00`→MCU→P2。（nRF54LM20A 另有 P3，归 PERI、由 GPIOTE20 兼管。）

### 三条硬规则

1. **同域**：pinctrl `NRF_PSEL(FUN, port, pin)` 的 `port` 必须匹配外设所在域——`uart20` 用 port=1（P1）、`uart30` 用 port=0（P0）、`uart00`/`spim00` 用 port=2（P2）。
2. **不混端口**：同一外设的所有信号必须落在同一端口，不能一脚 P1、一脚 P0。
3. **P2 无中断/唤醒**：P2 做通用 GPIO 没有 GPIOTE、SENSE/DETECT，也不能唤醒系统。按键、传感器中断、需唤醒的引脚必须放 **P1 或 P0**。

pinctrl 正确示例（`uart20` 属 PERI 域 → 端口号必须是 1）：

```dts
&pinctrl {
    uart20_default: uart20_default {
        group1 {
            psels = <NRF_PSEL(UART_TX, 1, 4)>,   /* P1.04 */
                    <NRF_PSEL(UART_RX, 1, 5)>;   /* P1.05 */
        };
    };
};
```

### 真要跨域（cross power-domain）时

- 只有 **PERI 域的串口类外设（UARTE/SPIM/SPIS 的 2x 实例）能借用指定的 P2 引脚**，且必须用 datasheet pin assignment 表里该功能的固定引脚（如某 P2 脚只能作 SCK）；**P0（LP 域）不接受任何外设跨入**。
- 跨域必须开 Constant Latency 子模式：置 `CONFIG_NRF_SYS_EVENT=y`，并在使用前后调用 `nrf_sys_event_request_global_constlat()` / `nrf_sys_event_release_global_constlat()`；代价是更费电、延迟增大。
- 依据：NCS《nRF54L pin mapping》、器件 datasheet 的 *Pin assignments / Cross power-domain use*。

## nrfutil 直接读写存储（RRAM / flash / 外部 QSPI）

经 J-Link 用 `nrfutil device` 直接操作内部 RRAM、RAM、外部 QSPI flash，无需烧整份固件——适合读标定/寄存器、备份、改少量配置。下列 read/write/erase 已在 **nRF54L15 DK（PCA10156）** 上验证（含外部 flash 写入→读回→擦除还原全流程）；nRF52/53/91 通用，仅地址不同。`<SN>` 为 `nrfutil device list` 里的序列号。

### 先查内存布局

```bash
nrfutil device core-info --serial-number <SN>
```

nRF54L15 内存布局：内部 RRAM `0x0`–`0x17D000`（1524 KB）、RAM `0x20000000`（256 KB）、UICR `0xFFD000`、外部 QSPI flash 映射在 `0x10000000`（`qspiPresent: true`）。地址因芯片而异，操作前用 `core-info` 确认。

### 读 / 写 / 擦 / dump

```bash
# 读：默认按 32 位字打印；--bytes 指定长度，--to-file 存为 Intel HEX
nrfutil device read --address 0x0 --bytes 64 --serial-number <SN>
nrfutil device read --address 0x10000000 --bytes 64 --serial-number <SN>   # 外部 flash
nrfutil device read --address 0x0 --bytes 0x1000 --to-file dump.hex --serial-number <SN>

# 写：一次一个 32 位字
nrfutil device write --address 0x17C000 --value 0xDEADBEEF --serial-number <SN>     # 内部 RRAM
nrfutil device write --address 0x10000000 --value 0xCAFEBABE --serial-number <SN>   # 外部 flash

# 擦
nrfutil device erase --pages 0x17C000 --serial-number <SN>     # 内部某页
nrfutil device erase --pages 0x10000000 --serial-number <SN>   # 外部某 sector
nrfutil device erase --all-external --serial-number <SN>       # 整片外部 flash（数分钟）

# dump 整块到 HEX
nrfutil device dump-to-file --code --uicr --ficr dump.hex --serial-number <SN>
nrfutil device dump-to-file --external ext.hex --serial-number <SN>
```

要点：
- `read`/`write` 默认校验地址是否在可编程区并自动配置 RRAMC/NVMC；读任意地址（如外设寄存器）加 `--direct` 做纯 J-Link 访问。多核加 `--core application|flpr|network|secure`（默认 application）。
- `write` 只写单个 32 位字，**批量数据用 `nrfutil device program --firmware <hex/bin>`**。
- **RRAM** 可按 word 直接覆写；**外部 NOR flash** 只能把 bit 由 1→0，改写已有数据前须先擦对应 sector。
- 板载外部 flash 的 DK（PCA10056 / 10095 / 10143 / 10156 等）有内置默认配置可直接读写擦；接非默认外部 flash 时，需用 `nrfutil device --x-ext-mem-config-file <cfg.json>` 提供 QSPI/SPI 配置。
- **读 dump 防幻觉**：擦除态全 `0xFF`、非文本区的非 ASCII 字节均属正常，按 hex 核对、勿把随机字节臆测成版本号/序列号/字符串（见「乱码与防幻觉」节）。

### UICR / OTP（nRF54L 系列特殊）

nRF54L 的 UICR 内含一段 **emulated OTP**（仿真一次性存储，**非真实熔丝**）：

- **地址**（nRF54L15）：UICR base `0xFFD000`；OTP 区从 `0xFFD500` 起，共 320 个 4 字节 word（`UICR.OTP[]`）。`OTP[0..287]` 归 bootloader / 安全固件（`bl_storage`）；**`OTP[288..319]`（`0xFFD980`–`0xFFD9FC`）是用户自定义区**（存序列号、标定等），建议从末尾 `OTP[319]` 往前用，避开 NCS 占用。
- **"一次性"语义**：一次 chip erase 后每个 word 只能写一次、且只能写非 `0xFFFFFFFF` 值；已写的 word 再写会报错 `Address ... is in a protected RRAMC region`（写入 `0xFFD9FC` 后重写即被拒）。报错里的 "RRAMC" 也说明它**本质是 RRAM 而非真 OTP**——`nrfutil device recover`（chip erase / ERASEALL）整片擦除后即可重写。
- UICR/OTP 只能整片 chip erase，**没有单页擦除**（`erase --pages` 对 UICR 无效）。

```bash
nrfutil device read --address 0xFFD980 --bytes 128 --serial-number <SN>          # 读用户 OTP 区 288-319
nrfutil device write --address 0xFFD9FC --value 0xA5A5A5A5 --serial-number <SN>  # 写 OTP[319]（写后不可改）
nrfutil device program --firmware uicr.hex --serial-number <SN>                  # 用 hex 批量烧 UICR/OTP
nrfutil device recover --serial-number <SN>                                      # 整片 chip erase → OTP 可重写（会连固件一起擦！）
```


