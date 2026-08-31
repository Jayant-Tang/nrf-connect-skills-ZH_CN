---
name: zephyr-flash
description: >-
  烧录 NCS / Zephyr 固件并管理 nRF 设备：先用 nrfutil device list 确认目标设备，标准构建产物优先
  west flash -d <build-dir>，明确 HEX/ZIP 或需要 device 选项时用 nrfutil device program，含 reset、erase、
  recover、fw-verify 与破坏性操作确认。当需要烧录、复位、擦除、恢复设备，或用户提到 flash、west flash、
  nrfutil device program、merged.hex、recover 时使用；启动日志验证见 zephyr-serial-log。
---

# 烧录与设备操作（NCS / Zephyr）

目标：把已构建产物烧入明确的 Nordic 设备，复位运行，并交给日志工具确认固件真的启动。

## 烧录前 Gate

1. **确认 build 目录**：先读取 [zephyr-build](../zephyr-build/SKILL.md)，使用已选 build 目录和实际存在的产物；不要凭记忆拼产物路径。
2. **确认设备**：执行 `nrfutil device list`。无设备时停止；多个设备且 SN/board 不唯一时停止询问用户。
3. **确认 board 一致**：build 的 board target 必须与连接设备一致。无法确认时停止。
4. **确认风险**：`erase`、`recover`、保护位、外部 flash 擦除、OTP/UICR 写入属于红线，执行前必须取得用户明确确认。

## 标准烧录：west flash

标准 NCS/Zephyr 构建产物优先使用 west runner：

```bash
west flash -d <selected-build-dir>
```

多个调试器连接时指定 SEGGER/J-Link 序列号：

```bash
west flash -d <selected-build-dir> --dev-id <segger_id>
```

工具链模式继承 [zephyr-build](../zephyr-build/SKILL.md)；launch 模式按其规则添加 wrapper。

## 直接烧录：nrfutil device program

仅在以下场景使用：

- 用户给出明确 HEX/ZIP 文件并要求直接烧录。
- 需要 `nrfutil device` 特定选项或 traits。
- 不依赖当前 build 目录的产线/脚本式烧录。

```bash
nrfutil device program --firmware <abs-firmware.hex-or-zip> --serial-number <SN>
nrfutil device reset --serial-number <SN>
```

程序烧录后可用 `fw-verify` 比对固件：

```bash
nrfutil device fw-verify --firmware <abs-firmware.hex> --serial-number <SN>
```

## 产物路径

- 非 sysbuild：`<build>/zephyr/zephyr.hex`。
- sysbuild 单应用：应用镜像通常在 `<build>/<app-dir-name>/zephyr/zephyr.hex`。
- sysbuild 多镜像：合并镜像为 `<build>/merged.hex`。
- 路径必须从实际 build 目录确认。

## 设备操作

| 目的 | 命令（无需工具链前缀） |
|------|------|
| 设备列表 | `nrfutil device list` |
| 设备信息 | `nrfutil device device-info --serial-number <SN>` |
| 固件信息 | `nrfutil device fw-info --serial-number <SN>` |
| 保护状态 | `nrfutil device protection-get --serial-number <SN>` |
| 复位设备 | `nrfutil device reset --serial-number <SN>` |
| 擦全部用户可编程内部存储和 UICR | `nrfutil device erase --all --serial-number <SN>` |
| 擦页或地址范围 | `nrfutil device erase --pages <start>` / `--pages <start>-<end>` |
| 擦外部 flash | `nrfutil device erase --all-external --serial-number <SN>` |
| 恢复受保护或异常设备 | `nrfutil device recover --serial-number <SN>` |

## 人类在环

下列操作不可逆或破坏性，**先讲清后果并征得用户确认**，不要擅自执行：

- `nrfutil device recover`、`nrfjprog --recover`、chip erase：会清除固件和用户数据，并影响 UICR/OTP 的当前内容。
- `nrfutil device erase` 或 `erase --all`：默认擦除用户可用内部可编程存储和 UICR。
- `nrfutil device erase --pages ...`：擦指定页或范围，地址必须来自芯片内存布局。
- `nrfutil device erase --all-external` —— 擦除整片外部 flash。

## 闭环验证

1. 烧录成功后复位设备。
2. 读取 [zephyr-serial-log](../zephyr-serial-log/SKILL.md)：确认 VCOM，打开日志读取，再复位捕获 boot log。
3. 输出不符时，按顺序检查 build 目录、board target、SN、VCOM、DTR、供电、线缆、保护状态，再决定是否重编或重烧。
4. flash 命令成功不等于应用行为正确；最终通过标准来自日志、RTT、测试输出或用户可复现行为。
