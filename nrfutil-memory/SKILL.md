---
name: nrfutil-memory
description: >-
  用 nrfutil device 直接读写 Nordic 设备存储：core-info 查内存布局，read/write/erase/dump-to-file 操作
  内部 flash/RRAM/RAM、UICR/OTP 和外部 flash，处理 --core、--width、--direct、--to-file、外部存储
  JSON 配置和写后回读。适合读寄存器、dump、备份、写少量 32-bit 配置值；当用户提到 nrfutil device
  read/write/erase/dump、core-info、RRAM、UICR、OTP、external flash、QSPI/SPIM、内存 dump 时使用。
---

# nrfutil 直接读写存储（flash/RRAM/RAM/外部 flash/UICR/OTP）

目标：在不重烧整份固件的情况下读取、备份或写入少量设备存储。写/擦类操作有硬件风险，必须先确认地址、长度、core 和设备 SN。

## 操作前 Gate

1. **确认设备**：运行 `nrfutil device list`。多个设备时必须使用用户确认的 `<SN>`。
2. **确认内存布局**：运行 `nrfutil device core-info --serial-number <SN>`。地址因 SoC、core、TrustZone、安全配置、外部 flash 连接方式而不同。
3. **确认 core**：多核设备读写前指定或确认 `--core application|network|secure|...`；默认 core 为 application。
4. **确认风险**：写、擦、recover、OTP/UICR 写入、外部 flash 擦除必须说明后果并等待用户确认。
5. **先备份**：写/擦前先读同地址或 dump 相关区域到文件。

## 设备与内存信息

```bash
nrfutil device device-info --serial-number <SN>
nrfutil device core-info --serial-number <SN>
nrfutil device protection-get --serial-number <SN>
```

nRF54L15 常见 application core 容量：RRAM 1524 KB，RAM 256 KB；具体地址范围以 `core-info` 和 datasheet/FICR 为准。nRF54L10/nRF54L05/nRF54LM20 等容量不同，不能复用 nRF54L15 地址。

## 读内存

```bash
nrfutil device read --address <addr> --serial-number <SN>
nrfutil device read --address <addr> --bytes <len> --width 8 --serial-number <SN>
nrfutil device read --address <addr> --bytes <len> --to-file dump.hex --serial-number <SN>
nrfutil device read --address <addr> --bytes <len> --core network --serial-number <SN>
```

规则：

- `--address` 必填。
- `--bytes` 缺省为一个 word。
- `--width` 可为 8、16、32；缺省按地址对齐自动选择，word-aligned 默认 32。
- `--to-file` 输出 Intel HEX，且一次只用于一个设备。
- `--direct` 跳过 memory controller setup 和地址范围检查，仅用于寄存器或非常明确的调试场景；使用前说明风险。

## 写内存

`write` 一次写一个 32-bit value：

```bash
nrfutil device write --address <addr> --value <u32-value> --serial-number <SN>
nrfutil device read --address <addr> --serial-number <SN>
```

规则：

- 写后必须立刻 read 回读核对。
- 批量写入用 `nrfutil device program --firmware <hex-or-bin>`，不要循环 `write` 大量数据。
- 外部 NOR flash 改写前先擦对应 sector/page，因为 NOR flash 不能把已经为 0 的 bit 写回 1。
- 写外设寄存器或受保护区域前必须确认安全状态、core 和地址含义。

## 擦除

```bash
nrfutil device erase --pages <start> --serial-number <SN>
nrfutil device erase --pages <start>-<end> --serial-number <SN>
nrfutil device erase --all --serial-number <SN>
nrfutil device erase --all-external --serial-number <SN>
```

规则：

- `--pages <start>-<end>` 的 end address 不包含在擦除范围内。
- 不带参数的 `erase` 等价于擦除全部用户可用内部可编程存储和 UICR；不要使用无参数 `erase`。
- 多核设备上 `--core` 会决定擦除哪个 core 的可编程存储和 UICR page。
- `--all-external` 擦除整片外部 flash，耗时长且不可恢复。

## dump / 备份

优先用 `read --to-file` 备份明确地址范围：

```bash
nrfutil device read --address <addr> --bytes <len> --to-file backup.hex --serial-number <SN>
```

需要整块 dump 时，先读 `resource://nordicsemi/nrfutil-manual` 或执行 `nrfutil device dump-to-file --help`，按当前安装版本选择 `--code`、`--ram`、`--uicr`、`--ficr`、`--external` 等区域参数。dump 后记录命令、SN、core、NCS/工具版本和文件路径。

## 外部 flash

- nRF52840/nRF5340 支持 QSPI 配置；nRF54L Series 使用 SPIM/SPI peripheral 配置；nRF54H20 使用 EXMIF 配置。
- 标准 DK 和标准构建通常可通过 `west flash` 使用默认 runner 配置。
- 非默认外部 flash 或非默认 SPI/QSPI 参数，使用命令级配置文件：

```bash
nrfutil device --x-ext-mem-config-file <cfg.json> program --firmware <firmware.hex> --serial-number <SN>
```

配置文件字段包含 `firmware_config.peripheral`、`pins.*`、`flash_size`、`page_size`、`sck_frequency`、`address_mode`、读写 opcode 等；pin number 计算公式为 `pin + 32 * port`。

## UICR / OTP（nRF54L 系列特殊）

nRF54L 的 UICR 内含一段 **emulated OTP**（仿真一次性存储，**非真实熔丝**）：

- UICR base：`0x00FFD000`。
- `UICR.OTP[n]` offset：`0x500 + n * 4`。
- OTP 共 320 个 4-byte word；NCS 保留 `OTP[0..287]` 给 `bl_storage`，用户自定义区为 `OTP[288..319]`。
- 用户区地址：`OTP[288] = 0xFFD980`，`OTP[319] = 0xFFD9FC`。
- 每次 Erase All 后，每个 word 只能从 `0xFFFFFFFF` 写成一次非 `0xFFFFFFFF` 值；已写 word 不能二次改写。
- UICR/OTP 是 emulated OTP，Erase All / recover 后会被擦除并可重新写；这不是不可熔断的物理 OTP。

```bash
nrfutil device read --address 0xFFD980 --bytes 128 --serial-number <SN>
nrfutil device write --address 0xFFD9FC --value 0xA5A5A5A5 --serial-number <SN>
nrfutil device read --address 0xFFD9FC --serial-number <SN>
```

## 人类在环（红线：执行前必须确认）

- OTP/UICR 写入：确认地址、值、endianness、word index、用途和备份。
- `erase --all`、无参数 `erase`、`recover`：擦除固件、用户数据和 UICR 当前内容。
- `erase --all-external`：擦除整片外部 flash。
- `--direct` 写读寄存器：可能改变外设状态或安全状态。

## 闭环验证

- 写后必须 read 同地址核对。
- 擦后必须 read 抽查目标范围是否为擦除态。
- dump 文件要记录命令和来源，不能把裸 bytes 当文本解释。
- 擦除态全 `0xFF`、未初始化或非文本区出现非 ASCII 字节是正常现象；只按 word/hex 下结论。
- 输出截断、乱码、替换符 `�` 或混入二进制时，换 `--to-file` 或更小范围重读。
