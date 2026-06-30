---
name: nrf54l-pinctrl
description: >-
  nRF54L GPIO / pinctrl 引脚规划：按 power domain 映射 P0/P1/P2、校验 NRF_PSEL 端口号、同一外设不混端口、
  P2 无 GPIOTE/SENSE/DETECT/唤醒、专用 clock pin 与 fixed-function pin、跨 power-domain 指定 P2 引脚和
  Constant Latency 要求。当为 nRF54L15/nRF54L10/nRF54L05/nRF54LM20 分配引脚、写 overlay/pinctrl、
  排查外设不工作、GPIO 中断不触发或跨域 GPIO 时使用。
---

# nRF54L 跨域 GPIO / pinctrl

nRF54L 按 power domain 划分 GPIO。外设默认使用本 domain 对应端口的引脚；同一外设的所有信号必须在同一端口。跨 power-domain 只适用于 datasheet 标明的特定 P2 引脚和特定串行接口，并且需要 Constant Latency。

## 修改前 Gate

1. 用 Nordic MCP 或芯片 datasheet 确认具体 SoC、package、board target、外设实例和目标引脚。
2. 读应用 overlay 和生成后的 `zephyr.dts`，确认 `zephyr,console`、外设 `status`、pinctrl 节点和 `NRF_PSEL()`。
3. 需要 GPIO 中断、按键唤醒、FEM 控制、传感器 interrupt 时，禁止选择 P2。
4. 需要跨域时，先说明功耗和延迟代价，并取得用户确认。

## domain ↔ 端口 ↔ GPIOTE 映射（nRF54L15）

| Power domain | GPIO 端口 | 最高速 | GPIOTE / 中断·唤醒 | 代表外设 |
|---|---|---|---|---|
| MCU | **P2** | 64 MHz | **无 GPIOTE、无 SENSE/DETECT、不能唤醒** | UARTE00、SPIM00/SPIS00、FLPR、TRACE |
| PERI | **P1** | 8 MHz | GPIOTE20（8 通道） | UARTE20/21/22、SPIM/SPIS/TWIM/TWIS2x、PWM2x、PDM20、I2S20、SAADC(AIN) |
| LP | **P0** | 8 MHz | GPIOTE30（4 通道） | UARTE30、SPIM30/SPIS30/TWIM30、GRTC |
| RADIO | 无 GPIO 端口 | — | — | —（仅测向/多天线时借用 P1） |

速记：外设实例 ID 的首位数字通常对应 domain 和 GPIO 端口：`uart20` → PERI → P1，`uart30` → LP → P0，`uart00`/`spim00` → MCU → P2。具体器件和 package 仍以 Nordic MCP/datasheet 为准。

## 三条硬规则

1. **同域**：pinctrl `NRF_PSEL(FUN, port, pin)` 的 `port` 必须匹配外设所在域——`uart20` 用 port=1（P1）、`uart30` 用 port=0（P0）、`uart00`/`spim00` 用 port=2（P2）。
2. **不混端口**：同一外设的所有信号必须落在同一端口，不能一脚 P1、一脚 P0。
3. **P2 无中断/唤醒**：P2 做通用 GPIO 没有 GPIOTE、SENSE/DETECT，也不能唤醒系统。按键、传感器中断、需唤醒的引脚必须放 **P1 或 P0**。

## 专用引脚规则

- SPIM、SPIS、TWI 等带 clock 信号的外设存在 dedicated clock pin 限制；使用前查 datasheet pin assignment 表。
- `SPIM00`、`UARTE00`、TRACE、FLPR 等 MCU domain 外设使用 P2 专用引脚；高速 SPIM00/TRACE 还涉及 extra high drive。
- `SDP_MSPI_*` / sQSPI 需要同时配置 P2 pinctrl、`cpuflpr_vpr`、reserved-memory 和 MSPI 子设备；完整流程见 [nrf54l-sqspi](../nrf54l-sqspi/SKILL.md)。
- NFC、TAMPC、RADIO DFEGPIO、GRTC 等有固定或推荐引脚；不能只按 GPIO 号自由分配。
- 所有 fixed-function pins（电源、晶振、ANT、reset、SWD 等）不能当普通 GPIO 使用。

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

## 真要跨域（cross power-domain）时

- 只有 **PERI 域的指定串行接口（UARTE20/21、SPIM20/21、SPIS20/21 等）能借用 datasheet 标明的 P2 引脚**；PSEL 必须连接到 pin assignment 表中对应功能的 P2 引脚，例如 SCK 只能接表中标出的 SCK。
- 不能把 P0 当作跨域目标端口给其他 domain 外设随意使用。
- 跨域必须开 Constant Latency 子模式：置 `CONFIG_NRF_SYS_EVENT=y`，并在使用前后调用 `nrf_sys_event_request_global_constlat()` / `nrf_sys_event_release_global_constlat()`。
- 跨域会增加功耗和延迟；优先改用同域引脚。

```c
#include <nrf_sys_event.h>

nrf_sys_event_request_global_constlat();
/* 使用跨 power-domain pin mapping 的外设 */
nrf_sys_event_release_global_constlat();
```

## 闭环验证

1. overlay 文件使用 normalized board target 命名，例如 `boards/nrf54l15dk_nrf54l15_cpuapp.overlay`。
2. 读取 [zephyr-build](../zephyr-build/SKILL.md) 做 pristine 构建。
3. 检查生成的 `zephyr.dts` 和 `devicetree_generated.h`，确认 `NRF_PSEL()` 端口和 pinctrl 已生效。
4. 读取 [zephyr-flash](../zephyr-flash/SKILL.md) 烧录，再用 [zephyr-serial-log](../zephyr-serial-log/SKILL.md)、RTT 或外设实测验证。
5. 外设无输出时按顺序查：`status = "okay"`、clock pin、port/domain、是否混端口、P2 中断限制、cross-domain constlat、shield 占用。
