---
name: zephyr-custom-driver
description: >-
  在 Zephyr/NCS 应用中开发并接入自定义驱动：创建 out-of-tree Zephyr module、
  zephyr/module.yml、CMake/Kconfig、Devicetree binding、DEVICE_DT_INST_DEFINE、
  subsystem API，并通过 prj.conf 和 overlay 加载到工程。当用户要写自己的 sensor/display/
  mspi/spi/i2c/gpio 驱动，或提到 ZEPHYR_EXTRA_MODULES、module.yml、DT_DRV_COMPAT、
  DT_HAS_*_ENABLED、自定义 binding 时使用。
---

# Zephyr 自定义驱动接入

目标：把应用内或独立目录中的自定义驱动做成 Zephyr module，让应用通过 Kconfig、Devicetree 和标准 subsystem API 使用它。

## 推荐目录

应用内驱动可使用这种结构：

```text
app/
|-- CMakeLists.txt
|-- Kconfig
|-- prj.conf
|-- boards/<board-target>.overlay
|-- dts/bindings/<subsystem>/<vendor,device>.yaml
|-- drivers/
|   |-- zephyr/module.yml
|   |-- CMakeLists.txt
|   |-- Kconfig
|   `-- <subsystem>/<driver>/
|       |-- CMakeLists.txt
|       |-- Kconfig.<driver>
|       `-- <driver>.c
`-- src/main.c
```

如果驱动要跨工程复用，把 `dts/` 也放进 module 根目录，并在 `module.yml` 加 `settings: dts_root: .`。

## 让应用加载 module

应用顶层 `CMakeLists.txt` 必须在 `find_package(Zephyr ...)` 之前追加 module：

```cmake
list(APPEND ZEPHYR_EXTRA_MODULES
    ${CMAKE_CURRENT_SOURCE_DIR}/drivers/
)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(app)
```

`drivers/zephyr/module.yml` 指向 module 根目录的 CMake/Kconfig。应用内 `drivers/` 作为 module 时可这样写：

```yaml
name: custom-drivers

build:
  cmake: zephyr/../
  kconfig: zephyr/../Kconfig
```

更常见的独立 module 写法：

```yaml
name: custom-drivers

build:
  cmake: .
  kconfig: Kconfig
  settings:
    dts_root: .
```

## CMake 与 Kconfig 链路

每一层只负责把下一层接进来。不要在应用 `CMakeLists.txt` 里直接枚举驱动 `.c` 文件。

```cmake
# drivers/CMakeLists.txt
add_subdirectory(display)

# drivers/display/CMakeLists.txt
add_subdirectory(a6ng)

# drivers/display/a6ng/CMakeLists.txt
zephyr_library()
zephyr_library_sources_ifdef(CONFIG_A6NG_DISPLAY display_a6ng.c)
```

module Kconfig 从 module 根目录逐层 `rsource`：

```kconfig
# drivers/Kconfig
rsource "display/Kconfig"

# drivers/display/Kconfig
rsource "a6ng/Kconfig.a6ng"
```

应用根 `Kconfig` 仍然要 `source "Kconfig.zephyr"`。如果驱动已经通过 `zephyr/module.yml` 的 `build.kconfig` 加载，不要再从应用根重复 source 同一个 driver Kconfig；只有非 module 的 app-local 驱动才需要在应用根手动 `rsource`。

驱动符号要依赖 subsystem 和 Devicetree compatible：

```kconfig
if DISPLAY

menuconfig A6NG_DISPLAY
	bool "Hongshi A6NG display driver"
	default y
	depends on DISPLAY
	depends on DT_HAS_HONGSHI_A6NG_ENABLED
	select MSPI
	select GPIO

endif # DISPLAY
```

## Devicetree Binding 与 Overlay

binding 文件名通常和 compatible 对应：`dts/bindings/display/hongshi,a6ng.yaml`。

```yaml
description: Hongshi A6NG display on QSPI bus

compatible: "hongshi,a6ng"

include: [display-controller.yaml, mspi-device.yaml]

properties:
  reg:
    required: true

  reset-gpios:
    type: phandle-array
    required: true
```

overlay 中的节点必须设置 `compatible`、`status = "okay"`，并补齐 binding 要求的属性：

```dts
&sqspi {
	status = "okay";
	ce-gpios = <&gpio2 5 GPIO_ACTIVE_LOW>;

	display: display@0 {
		compatible = "hongshi,a6ng";
		reg = <0>;
		status = "okay";
		reset-gpios = <&gpio0 0 GPIO_ACTIVE_LOW>;
		mspi-hardware-ce-num = <0>;
		mspi-max-frequency = <DT_FREQ_M(1)>;
	};
};
```

binding 或 overlay 改动后必须 pristine 构建，并检查生成的 `zephyr.dts` 和 `devicetree_generated.h`。

## 驱动源码模板

1. 文件顶部设置 `DT_DRV_COMPAT`，把 compatible 的逗号和连字符改成下划线：`hongshi,a6ng` → `hongshi_a6ng`。
2. 分离 `config` 和 `data`：Devicetree、GPIO spec、bus device、尺寸等放 `config`；mutex、transfer buffer、状态位放 `data`。
3. 初始化函数里先检查 bus/GPIO `device_is_ready()` 或 `gpio_is_ready_dt()`，再配置 GPIO、mutex、外设默认状态。
4. 尽量挂到 Zephyr 标准 subsystem API，例如 `display_driver_api`、`sensor_driver_api`、`gpio_driver_api`。
5. 用 `DEVICE_DT_INST_DEFINE()` 定义设备，用 `DT_INST_FOREACH_STATUS_OKAY()` 为每个 enabled 节点展开实例。

```c
#define DT_DRV_COMPAT hongshi_a6ng

static DEVICE_API(display, a6ng_driver_api) = {
	.blanking_on = a6ng_suspend,
	.blanking_off = a6ng_resume,
	.write = a6ng_write,
	.get_capabilities = a6ng_get_capabilities,
};

#define A6NG_DEFINE(n) \
	static struct a6ng_data data##n; \
	static const struct a6ng_config config##n = { \
		.bus = DEVICE_DT_GET(DT_BUS(DT_DRV_INST(n))), \
		.mspi_id = MSPI_DEVICE_ID_DT_INST(n), \
		.reset_gpio = GPIO_DT_SPEC_INST_GET(n, reset_gpios), \
	}; \
	DEVICE_DT_INST_DEFINE(n, a6ng_init, NULL, &data##n, &config##n, \
			      POST_KERNEL, CONFIG_DISPLAY_INIT_PRIORITY, \
			      &a6ng_driver_api);

DT_INST_FOREACH_STATUS_OKAY(A6NG_DEFINE)
```

## 应用侧启用与调用

`prj.conf` 启用 subsystem、驱动依赖和必要日志：

```conf
CONFIG_LOG=y
CONFIG_DISPLAY=y
CONFIG_DISPLAY_LOG_LEVEL_DBG=y
CONFIG_PM_DEVICE=y
CONFIG_PM_DEVICE_RUNTIME=y
```

应用代码通过 Devicetree label 获取设备，先检查 ready，再调用 subsystem API：

```c
const struct device *display_dev = DEVICE_DT_GET(DT_NODELABEL(display));

if (!device_is_ready(display_dev)) {
	LOG_ERR("Display device %s is not ready", display_dev->name);
}
```

## 验证与常见坑

1. `CONFIG_<DRIVER>` 没出现：检查 `module.yml`、`ZEPHYR_EXTRA_MODULES`、Kconfig `rsource` 链路。
2. `DT_HAS_*_ENABLED` 为 false：检查 binding 路径、compatible 拼写、overlay 是否按 normalized board target 命名。
3. 链接不到驱动符号：检查 `zephyr_library_sources_ifdef(CONFIG_<DRIVER> ...)` 和 Kconfig 是否真的启用。
4. 设备 not ready：检查 bus 节点、GPIO controller、依赖 subsystem、init priority、runtime PM。
5. 接在 sQSPI/MSPI 上的设备，先读取 [nrf54l-sqspi](../nrf54l-sqspi/SKILL.md) 确认 bus overlay 和 runtime PM。
