---
name: nrf54l-sqspi
description: >-
  nRF54L sQSPI soft peripheral 使用指南：配置 nordic,nrf-sqspi、FLPR/VPR、reserved-memory、
  SDP_MSPI pinctrl、Zephyr MSPI 子设备、runtime PM，并排查 sQSPI 外设不通或传输卡死。
  当用户在 nRF54L15/nRF54LM20 上接外部 QSPI flash、display，或提到 sQSPI、MSPI、
  nordic,nrf-sqspi、SDP_MSPI、cpuflpr_vpr 时使用。
---

# nRF54L sQSPI 使用方法

目标：把 nRF54L 的 sQSPI soft peripheral 作为 Zephyr MSPI bus 使用，再把 flash、display 等 MSPI 设备挂到 `&sqspi` 下。

## 使用前 Gate

1. 确认 NCS 版本、SoC、board target、硬件连线和目标外设协议。sQSPI 细节以 Nordic MCP 当前文档和本地 SDK 为准。
2. 读取 [nrf54l-pinctrl](../nrf54l-pinctrl/SKILL.md)，确认 `SDP_MSPI_*` 引脚属于允许的 P2 fixed-function 引脚。
3. 修改 sQSPI、reserved-memory、pinctrl、sysbuild 或 board target 后，读取 [zephyr-build](../zephyr-build/SKILL.md) 做 pristine 构建。

## Devicetree Overlay 模板

核心结构：定义 sQSPI pinctrl，把 pinctrl 和中断挂到 `&cpuflpr_vpr`，在 reserved RAM 中创建 `nordic,nrf-sqspi` 节点。

```dts
&pinctrl {
	sqspi_default: sqspi_default {
		group1 {
			psels = <NRF_PSEL(SDP_MSPI_SCK, 2, 1)>,
				<NRF_PSEL(SDP_MSPI_CS0, 2, 5)>,
				<NRF_PSEL(SDP_MSPI_DQ0, 2, 2)>;
			nordic,drive-mode = <NRF_DRIVE_E0E1>;
		};
		group2 {
			psels = <NRF_PSEL(SDP_MSPI_DQ1, 2, 4)>,
				<NRF_PSEL(SDP_MSPI_DQ2, 2, 3)>,
				<NRF_PSEL(SDP_MSPI_DQ3, 2, 0)>;
			nordic,drive-mode = <NRF_DRIVE_E0E1>;
			bias-pull-up;
		};
	};

	sqspi_sleep: sqspi_sleep {
		group1 {
			low-power-enable;
			psels = <NRF_PSEL(SDP_MSPI_SCK, 2, 1)>,
				<NRF_PSEL(SDP_MSPI_CS0, 2, 5)>,
				<NRF_PSEL(SDP_MSPI_DQ0, 2, 2)>,
				<NRF_PSEL(SDP_MSPI_DQ1, 2, 4)>,
				<NRF_PSEL(SDP_MSPI_DQ2, 2, 3)>,
				<NRF_PSEL(SDP_MSPI_DQ3, 2, 0)>;
		};
	};
};

&cpuflpr_vpr {
	pinctrl-0 = <&sqspi_default>;
	pinctrl-1 = <&sqspi_sleep>;
	pinctrl-names = "default", "sleep";
	interrupts = <76 NRF_DEFAULT_IRQ_PRIORITY>;
	status = "okay";
};
```

reserved-memory 不能盲抄。以下只是已验证过的样例值：

```dts
/* nRF54L15 DK sample */
softperipheral_ram: memory@2003c000 {
	reg = <0x2003c000 0x4000>;
	ranges = <0 0x2003c000 0x4000>;
	#address-cells = <1>;
	#size-cells = <1>;

	sqspi: sqspi@3b40 {
		compatible = "nordic,nrf-sqspi";
		#address-cells = <1>;
		#size-cells = <0>;
		reg = <0x3b40 0x200>;
		status = "okay";
		zephyr,pm-device-runtime-auto;
	};
};

/* nRF54LM20 DK sample: memory@20078000, size 0x8000 */
```

如果 `cpuflpr_vpr` 节点已有 `execution-memory`，按当前 Nordic MCP 文档确认是否需要 `/delete-property/ execution-memory;`。不要把某个 SoC 的 RAM 地址、大小或删除节点列表照搬到另一个 SoC。

## 挂载 MSPI 子设备

把设备节点放在 `&sqspi` 下。`ce-gpios` 是 software CE GPIO，子节点里的 `mspi-hardware-ce-num` 对应 pinctrl 中的硬件 CE 编号。

```dts
/delete-node/ &mx25r64;

&spi00 {
	status = "disabled";
};

&sqspi {
	status = "okay";
	ce-gpios = <&gpio2 5 GPIO_ACTIVE_LOW>;

	display: display@0 {
		compatible = "hongshi,a6ng";
		reg = <0>;
		status = "okay";
		mspi-hardware-ce-num = <0>;
		mspi-max-frequency = <DT_FREQ_M(1)>;
	};
};
```

只有在替换板载 QSPI flash 或复用默认 QSPI 引脚时才删除 `&mx25r64`、禁用 `&spi00`。如果设备是 flash，优先使用现有 `jedec,mspi-nor` binding；如果是自定义 display/sensor，读取 [zephyr-custom-driver](../zephyr-custom-driver/SKILL.md) 创建 binding 和驱动。

## 驱动侧用法

1. 驱动 include `zephyr/drivers/mspi.h`，从 Devicetree 取 bus 和设备 ID：
   - `DEVICE_DT_GET(DT_BUS(DT_DRV_INST(n)))`
   - `MSPI_DEVICE_ID_DT_INST(n)`
2. 初始化时填 `struct mspi_dev_cfg`，调用 `mspi_dev_config(..., MSPI_DEVICE_CONFIG_ALL, ...)`。
3. 每次传输前按命令需要切换 `io_mode`：寄存器读写常用 `MSPI_IO_MODE_SINGLE`，数据面可用 `MSPI_IO_MODE_QUAD_1_1_4` 等。
4. 用 `struct mspi_xfer_packet` + `struct mspi_xfer` 描述 cmd/address/data/dummy/timeout，再调用 `mspi_transceive()`。
5. 如果启用 runtime PM，外设工作期间保持 bus 唤醒：上电/显示开启时 `pm_device_runtime_get(config->bus)`，关断后 `pm_device_runtime_put(config->bus)`。

经验规则：display 等长时间工作的外设打开期间必须唤醒 MSPI bus，否则会明显变慢或表现不稳定。

## 验证与排错

1. pristine 构建后检查 `<build>/zephyr/zephyr.dts`：`&cpuflpr_vpr`、`sqspi_default`、`nordic,nrf-sqspi`、子设备节点都必须存在且 `status = "okay"`。
2. 检查 `devicetree_generated.h` 中子设备 compatible 生成了 `DT_HAS_<VENDOR>_<DEVICE>_ENABLED`。
3. 外设无响应时按顺序查：RAM base/size、`sqspi@... reg`、`cpuflpr_vpr` interrupt、P2 pinctrl、CE GPIO/CE 编号、默认 `mx25r64/spi00` 是否占用、runtime PM、MSPI io mode 和 timeout。
4. 如果卡在 sQSPI/FLPR 相关等待或 `__CSB()` 附近，优先怀疑 FLPR/sQSPI RAM、VPR 配置、中断或 pinctrl 没真正生效。
5. 烧录和日志闭环按 [zephyr-flash](../zephyr-flash/SKILL.md) 与 [zephyr-serial-log](../zephyr-serial-log/SKILL.md) 执行。
