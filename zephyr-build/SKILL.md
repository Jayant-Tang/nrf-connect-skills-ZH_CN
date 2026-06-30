---
name: zephyr-build
description: >-
  构建与配置 NCS / Zephyr 应用：选择应用目录和 build 目录、读取 build provenance、用 nrfutil sdk-manager
  toolchain launch 运行 west build/menuconfig/twister，处理 qualified board target、sysbuild、Kconfig、
  Devicetree overlay、snippet、MCUboot 与构建日志闭环。当需要编译、改配置、排查构建报错，或用户提到
  west build、Kconfig、Devicetree、overlay、prj.conf、sysbuild、menuconfig、ram_report/rom_report 时使用。
---

# 构建与配置（NCS / Zephyr）

目标：选对 NCS 版本、board target、应用目录和 build 目录，在匹配的 NCS 工具链环境中构建，并用日志证据判断成功或失败。

## 构建前 Gate

1. **确认 NCS 版本**：优先读 build provenance、`west.yml`、工程文档、现有 build log；仍无法确定时查 `nrfutil sdk-manager list --all-fields`。版本不唯一时停止询问用户。
2. **确认 board target**：使用 qualified board target，例如 `nrf54l15dk/nrf54l15/cpuapp`。用户只给 SoC 或板卡简称时，用 Nordic MCP 查候选；候选不唯一时停止询问用户。
3. **确认应用目录**：应用目录必须包含应用级 `CMakeLists.txt`。不要把 NCS 根目录当应用目录。
4. **选择 build 目录**：列出应用下的 `build`、`build_*`，以及含 `.vscode-nrf-connect.json`、`build_info.yml`、`CMakeCache.txt`、`build.ninja`、`zephyr/` 的目录。多个候选且用户未指定时停止询问。
5. **读取 provenance**：若 build 目录含 `.vscode-nrf-connect.json` 或 `build_info.yml`，先读取并复用其 NCS 版本、board target、source dir、build dir、sysbuild、CMake 参数。要改变这些参数时先问用户。
6. **确认工作区类型**：
   - NCS workspace：`west topdir` 成功且存在 `.west/`。
   - freestanding application：应用在 NCS workspace 外，但使用已安装 NCS 构建。
   - 非 Zephyr/NCS 工程：停止并让用户提供 SDK 路径、工程路径、NCS 版本和 board target。

## 命令包装

所有 `west`、CMake、Ninja、Twister 命令都在 NCS 工具链环境内执行：

```bash
nrfutil sdk-manager toolchain launch --ncs-version=<version> -- <command>
```

freestanding 应用必须通过 NCS workspace 暴露 west extension 命令，`--chdir` 是 `nrfutil sdk-manager toolchain launch` 的参数，放在 `--` 之前：

```bash
nrfutil sdk-manager toolchain launch --ncs-version=<version> \
  --chdir <ncs-install-dir> -- \
  west build -b <board_target> -d <abs-build-dir> <abs-app-dir>
```

环境只提供旧接口时才用：

```bash
nrfutil toolchain-manager launch --ncs-version=<version> -- <command>
```

## 构建命令

| 目的 | 命令（需加上工具链 wrapper） |
|------|------|
| 新建或重配构建 | `west build -b <board_target> -d <selected-build-dir> <app-dir>` |
| 复用已选 build 目录 | `west build -d <selected-build-dir>` |
| pristine 构建 | `west build -p always -b <board_target> -d <selected-build-dir> <app-dir>` |
| 显式启用 sysbuild | `west build -b <board_target> -d <selected-build-dir> <app-dir> --sysbuild` |
| 显式禁用 sysbuild | `west build -b <board_target> -d <selected-build-dir> <app-dir> --no-sysbuild` |
| 交互式 Kconfig | `west build -t menuconfig -d <selected-build-dir>` |
| 内存占用报告 | `west build -t ram_report -d <selected-build-dir>` / `rom_report` |
| 拉取/更新模块（按 manifest） | `west update` |
| 拉取二进制 blob | `west blobs fetch <module>` |
| 列出开发板 | `west boards` |
| 运行测试 | `twister -T <path> -p <board>` |

改 board target、sysbuild、Kconfig、Devicetree overlay、snippet、manifest、pinctrl 或工具链输入后，使用 pristine 构建。普通源文件改动可先增量构建。

## 配置与文件结构

- **`prj.conf`**：应用默认 Kconfig；额外片段用 `-DEXTRA_CONF_FILE="a.conf;b.conf"`；单个临时符号可用 `-- -DCONFIG_FOO=y`。
- **board conf**：按板配置放 `boards/<normalized-board-target>.conf`。
- **Devicetree overlay**：board target 里的 `/` 规范化为 `_`，如 `nrf54l15dk/nrf54l15/cpuapp` 对应 `boards/nrf54l15dk_nrf54l15_cpuapp.overlay`。多核板不能只写 `nrf54l15dk.overlay`。
- **额外 overlay**：用 `-- -DEXTRA_DTC_OVERLAY_FILE="my.overlay"`；多文件用空格或分号。
- **生成结果**：检查 `<build>/zephyr/zephyr.dts`、`devicetree_generated.h`、`.config`、`build_info.yml`。
- **snippets**：用 `west build --snippet <name>` 或 `-S <name>`，例如 RTT console。
- **sysbuild**：用于应用、MCUboot、网络核等多镜像。NCS SDK 仓库应用默认启用 sysbuild；freestanding 应用按项目需要显式 `--sysbuild` 或配置 west。配置文件为 `sysbuild.conf` 和 `sysbuild/`，sysbuild Kconfig 使用 `SB_CONFIG_*`。
- **MCUboot/DFU**：用 sysbuild 配置，例如 `-DSB_CONFIG_BOOTLOADER_MCUBOOT=y`；镜像签名由构建系统和 imgtool 处理。
- **自定义驱动 module**：改 `ZEPHYR_EXTRA_MODULES`、`zephyr/module.yml`、driver `CMakeLists.txt`/`Kconfig`、Devicetree binding 或 `DT_DRV_COMPAT` 时读取 [zephyr-custom-driver](../zephyr-custom-driver/SKILL.md)，并用 pristine 构建确认 Kconfig 与 Devicetree 重新生成。
- **nRF54L sQSPI**：改 `nordic,nrf-sqspi`、reserved-memory、`cpuflpr_vpr`、`SDP_MSPI_*` pinctrl 或 MSPI 子设备时读取 [nrf54l-sqspi](../nrf54l-sqspi/SKILL.md)，构建后检查 `zephyr.dts` 和 `devicetree_generated.h`。

## 日志闭环

构建日志重定向到 `.agent/logs/`（或 build 目录），只读取末尾和错误摘要，不把完整日志贴进上下文。跨 Agent 临时文件统一放工程根 `.agent/`，见总纲「跨 Agent 状态管理」。

```bash
nrfutil sdk-manager toolchain launch --ncs-version=<version> -- \
  west build -p always -b <board_target> -d <selected-build-dir> <app-dir> \
  > <selected-build-dir>/build.log 2>&1
```

判定规则：

1. 命令退出码为 0，且日志显示生成目标产物，才进入烧录或运行验证。
2. 失败时只读取末尾、`error:`、`FAILED`、`undefined reference`、Kconfig warning、Devicetree error 相关行。
3. 修复后回到 build directory gate，确认是否需要 pristine 构建。

## 产物路径

- 非 sysbuild 或单镜像：`<build>/zephyr/zephyr.hex`、`<build>/zephyr/zephyr.elf`。
- sysbuild：应用产物通常在 `<build>/<app-dir-name>/zephyr/`；MCUboot 等镜像在 `<build>/<image>/zephyr/`；多镜像合并产物为 `<build>/merged.hex`。
- 产物路径必须从 build tree 实际存在的文件确认，不根据 `project()` 名称或记忆推断。

构建成功后烧录见 [zephyr-flash](../zephyr-flash/SKILL.md)，跑起来验证日志见 [zephyr-serial-log](../zephyr-serial-log/SKILL.md)。
