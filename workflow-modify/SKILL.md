---
name: workflow-modify
description: >-
  zephyr-expert 编排层的「修改 / 修复」工作流：在既有工程做有限范围改动，先确认目标、NCS 版本、board target、
  设备与风险；复杂改动先 plan 文档；改完执行 build→flash→serial/RTT 验证，再用 clean-agent 独立验收。
  当任务是改配置、改小段代码、修 bug 或实测既有工程时使用；纯问答用 workflow-ask，从零开发用 workflow-develop。
---

# 工作流 B：修改

适用：既有工程上的有限范围改动，并通过构建、烧录、日志或调试完成闭环验证。

## 执行步骤

1. **确认范围**：列出要改的功能、文件类型（C/Kconfig/Devicetree/overlay/sysbuild）、目标板、NCS 版本、验证方式。缺 NCS 版本、board target、工程路径、SN 或串口端口时先确认。
2. **判定复杂度**：单文件或局部配置改动可直接执行；跨多文件、多子系统、驱动、协议栈、启动链、分区、pinctrl 或硬件风险的改动，先进入 plan mode，写 plan 文档并取得用户确认。
3. **查证事实**：Nordic/NCS/Zephyr 命令、board target、overlay 文件名、VCOM、pinctrl、`nrfutil` 行为必须先查 Nordic MCP。MCP 不通时停止。
4. **记录基线**：动手前读取 git 状态与目标文件当前内容，保留本次改动边界。工作区已有用户改动时只叠加必要修改，不还原用户改动。
5. **编辑前说明**：用一句话说明将修改哪些文件、为什么改、影响面是什么。涉及破坏性硬件动作时必须先取得用户明确授权。
6. **执行修改**：按现有工程风格改最小范围；配置改动优先放在应用层 `prj.conf`、`sysbuild.conf`、`boards/<normalized-board-target>.overlay` 或明确的 overlay/conf fragment，不改 SDK 上游文件。改自定义驱动、binding、`module.yml` 或 `DEVICE_DT_INST_DEFINE` 时读取 [zephyr-custom-driver](../zephyr-custom-driver/SKILL.md)；改 nRF54L sQSPI、`nordic,nrf-sqspi`、`cpuflpr_vpr` 或 MSPI 子设备时读取 [nrf54l-sqspi](../nrf54l-sqspi/SKILL.md)。
7. **自测闭环**：读取 [zephyr-build](../zephyr-build/SKILL.md) 选择构建目录并构建；成功后读取 [zephyr-flash](../zephyr-flash/SKILL.md) 烧录或复位；读取 [zephyr-serial-log](../zephyr-serial-log/SKILL.md) 或 [zephyr-debug](../zephyr-debug/SKILL.md) 验证输出。改 Kconfig、Devicetree、board target、sysbuild、pinctrl 后使用 pristine 构建。
8. **独立验收**：自测通过后读取 [clean-agent](../clean-agent/SKILL.md)，只给需求、验收标准和复现步骤，让全新只读 agent 判定 PASS/FAIL。FAIL 时回到第 6 步。
9. **收尾**：总结改动、验证命令和结果；未能执行的硬件验证要说明缺少的设备、SN、端口或用户操作。

## 硬件与存储红线

- `recover`、`erase --all`、`erase --all-external`、OTP/UICR 写入、保护位修改、跨 power-domain pinctrl 方案，执行前必须说明后果并等待用户确认。
- 对 RRAM、UICR/OTP、外部 flash 做写/擦前，先用 [nrfutil-memory](../nrfutil-memory/SKILL.md) 读取或 dump 备份可备份区域；写后必须回读核对。
- 多设备连接时不能自动选择目标设备，除非 SN、board name 或用户选择唯一明确。

## 接力规则

上下文不足或任务被中断时，写 `Handover.md`，记录需求、NCS 版本、board target、SN/COM、已改文件、验证结果、未完成事项和风险点。不要修改原始 plan 文档，除非用户同意。
