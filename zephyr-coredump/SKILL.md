---
name: zephyr-coredump
description: >-
  Zephyr coredump 崩溃转储的启用、提取与离线分析：配置 flash 分区后端、取出 dump、
  用 GDB 离线回溯崩溃寄存器和完整调用栈。排查崩溃 / HardFault 或提到 coredump、崩溃转储时使用。
---

# Zephyr Coredump：启用、提取与离线分析

Zephyr coredump 子系统在 fatal error 时把异常线程的寄存器 + 栈写入后端存储（本指南用 flash 分区），
设备复位后 dump 仍在，可随时取出用 GDB 离线回溯——适合现场 / 偶发崩溃、无法挂调试器的场景。

## 1. 启用配置（prj.conf）

| 配置 | 作用 |
|------|------|
| `CONFIG_FLASH=y` | flash 驱动（flash 分区后端的前置依赖，默认关） |
| `CONFIG_DEBUG_COREDUMP=y` | 启用 coredump 子系统 |
| `CONFIG_DEBUG_COREDUMP_BACKEND_FLASH_PARTITION=y` | dump 写入 flash 分区 |
| `CONFIG_DEBUG_COREDUMP_MEMORY_DUMP_MIN=y` | 最小 dump（异常线程栈 + 寄存器），省空间 |
| `CONFIG_RESET_ON_FATAL_ERROR=y` | NCS fatal_error 库，崩溃后自动复位 |
| `CONFIG_LOG_PRINTK=n` | **必须关**：否则 printk 走 LOG deferred 缓冲，大量 dump 打印会被丢弃 |

## 2. 预留分区（`coredump_partition`）

flash 分区后端通过 fixed partition **`coredump_partition`** 定位存储（见 Zephyr 源码
`subsys/debug/coredump/coredump_backend_flash_partition.c`），分区定义方式随 NCS 版本不同：

### NCS ≤ v3.3.x：Partition Manager

在工程根 `pm_static.yml` 的静态分区表尾部加（nRF54L15 示例：RRAM 尾部 `0x161000`，16KB）：

```yaml
coredump_partition:
  address: 0x161000
  region: flash_primary
  size: 0x4000
```

- PM 要求静态配置中恰好只有一个空隙（留给动态大小的 app），其余区域必须填满，不能留空洞。
- sysbuild.conf 需启用 `SB_CONFIG_PARTITION_MANAGER=y`。

### NCS ≥ v3.4.0：Devicetree 分区（PM 已移除）

在应用 overlay 的 `partitions` 节点里加。nRF54L15 示例——默认布局尾部无空闲空间，
从 `storage_partition` 切 16KB 出来：

```dts
&storage_partition {
	reg = <0x174000 DT_SIZE_K(20)>;	/* 36K 缩到 20K */
};

&cpuapp_rram {
	partitions {
		coredump_partition: partition@179000 {
			label = "coredump_partition";
			reg = <0x179000 DT_SIZE_K(16)>;
		};
	};
};
```

- 各板型默认分区布局见 `zephyr/dts/vendor/nordic/<soc>_cpuapp_partition.dtsi`，地址 / 大小按实际板子调整，别和相邻分区重叠。
- 其他 SoC 把 `&cpuapp_rram` 换成对应的 flash 节点（如 `&flash0`）。

### 通用注意

- 改完分区定义必须 pristine 构建：`west build -p always`。
- 分区大小：`MEMORY_DUMP_MIN` 约 1KB 足够，16KB 是留余量；开全量 dump 需相应加大。
- 分区实际地址以构建产物为准（`build/<app>/zephyr/zephyr.dts` 或 PM 的 `partitions.yml`），取 dump 时要用这个地址。

## 3. 取出 dump

**红线：重新烧录固件会擦除该分区——先读 dump，再烧录。**

方式一：nrfutil 直接读分区（推荐，不依赖应用代码）：

```powershell
# 地址 / 长度填 coredump_partition 的实际值（从 build 产物的 zephyr.dts 或 partitions.yml 查）
nrfutil device read --address <分区地址> --bytes <分区大小> --to-file coredump.hex --serial-number <SN>
```

方式二：应用重启后通过串口把 dump 以 hex 打印出来（需应用自己实现读取 + 打印，且按第 1 节关 `LOG_PRINTK`）。

分区前 16 字节是 header，之后才是 dump 数据：

| 偏移 | 字段 | 说明 |
|------|------|------|
| 0 | `id[2]` | 魔数 `'C' 'D'`（0x43 0x44），不是则分区无有效 dump |
| 2 | `hdr_version` | 头部版本，当前为 1 |
| 4 | `size` | dump 数据长度（不含 header），小端 |
| 8 | `flags` | 保留 |
| 10 | `checksum` | 数据累加和校验 |
| 12 | `error` | 非 0 表示上次写入失败（如写中途断电），dump 无效 |
| 16 | dump 数据 | Zephyr coredump 二进制格式 |

分区内永远只保存一份 dump：每次崩溃后端先整区擦除再写入。应用侧可用
`COREDUMP_CMD_ERASE_STORED_DUMP`（整区擦除）或 `COREDUMP_CMD_INVALIDATE_STORED_DUMP`（仅作废 header）主动清理。

## 4. 离线分析（一条命令出调用栈）

用本 skill 自带脚本 [scripts/analyze_dump.py](scripts/analyze_dump.py)，**在 NCS 工具链环境中、工程根目录**执行：

```powershell
python <skill目录>\scripts\analyze_dump.py coredump.hex build\<app>\zephyr\zephyr.elf
```

流程：ihex → bin → 剥掉 16 字节 flash header → 启动 Zephyr 自带 `coredump_gdbserver.py` →
GDB batch 打印 `pc/lr/sp` 寄存器和完整 `bt` 回溯（每帧带源文件 + 行号，`#0` 帧即崩溃点）。

前提与坑：

1. **ELF 必须与崩溃时运行的固件是同一次构建的产物**，否则地址对不上、回溯全是垃圾。
2. 需要 `ZEPHYR_BASE` 已设置（脚本靠它定位 `scripts/coredump/coredump_gdbserver.py`），即必须在 NCS toolchain env 里跑。
3. 依赖 `arm-zephyr-eabi-gdb` / `arm-zephyr-eabi-objcopy`（工具链自带）。
4. gdbserver 把第一个 TCP 连接当作 GDB 会话——**不要用 socket 探测端口**，否则 GDB 连上后看到 "No stack"（脚本内已规避）。
5. 串口 hex 打印方式拿到的 dump 没有 flash header，需自行转成二进制后直接喂 `coredump_gdbserver.py`，不要走 analyze_dump.py 的 header 校验。

## 5. 结果解读与防幻觉

- `#0` 帧是崩溃点，结合 `pc` / `lr` 与 fault 寄存器（CFSR/BFAR，见 [zephyr-debug](../zephyr-debug/SKILL.md)）交叉确认。
- dump 是二进制数据，**不要肉眼读 hex 脑补内容**（呼应总纲防幻觉原则）；一切结论以 GDB 回溯为准。
- header `error` 字段非 0 或魔数不对 → dump 无效，直接说明"无有效 dump"，不要硬解。
