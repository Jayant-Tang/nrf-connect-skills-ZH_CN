---
name: workflow-modify
description: >-
  zephyr-expert 编排层的「修改 / 修复」工作流：在既有工程做有限范围改动，先确认目标、NCS 版本、board target、
  设备与风险；复杂改动先 plan 文档；改完执行 build→flash→serial/RTT 验证，再用 clean-agent 独立验收。
  当任务是改配置、改小段代码、修 bug 或实测既有工程时使用；纯问答用 workflow-ask，从零开发用 workflow-develop。
---

# 工作流 B：修改

适用：既有工程上的有限范围改动，并通过构建、烧录、日志或调试完成闭环验证。

根因未知的故障排查先走 [workflow-debug](../workflow-debug/SKILL.md)，定位到根因后再回到本工作流修复。

## 开工前 GATE（全部通过前，禁止执行后续步骤）

逐项确认，任一不满足就停下处理，不要因为"自己能搞定"而跳过：

1. **读懂项目意图**：先读 README / 设计文档 / 注释 / 既有 plan / Handover / git log，能说清这个项目"为什么这么做"。改既有项目时这是第一步，**优先于读源码**——否则可能把原始设计目标当成 bug 改掉。但**注意风险**：用户在sample基础上修改，但忘记了更新README，导致 README 和实际项目不一致。
2. **知识源可用**：先完成 Nordic MCP 预检查。必须确认当前会话能看到 Nordic MCP 的 server / tools，并完成一次最小只读探针；只要出现 tools 不可见、探针失败、认证失效、或因权限/网络/工具异常而无法证明服务可用，统一视为 **MCP 不通**。MCP 不通就停下让用户恢复，不要用 workaround 绕过（见总纲铁律 2）。
3. **目标齐全**：NCS 版本、board target、工程路径、Jlink Serial Number (SN) / 串口端口都明确，缺则先确认。
4. **复杂度判定**：命中下列任一 → **必须进 plan mode 文档并取得用户逐条签字**，再动手：
   - 版本迁移 / 移植
   - 跨多文件、多子系统
   - 修改SDK内部文件 （驱动 / 协议栈 / 启动链 / 分区 ）
   - 任何硬件风险

   ⚠ 用 `AskQuestion` 问澄清问题（板子型号、是否保留某平台等）**不等于** plan 确认。plan 确认 = 写出方案文档 + 用户明确同意。

## 执行步骤

1. **确认范围**：列出要改的功能、文件类型（C/Kconfig/Devicetree/overlay/sysbuild）、目标板、NCS 版本、验证方式。缺 NCS 版本、board target、工程路径、SN 或串口端口时先确认。
2. **判定复杂度**（见上方 GATE 第 4 条）：单文件或局部配置改动可直接执行；**版本迁移 / 移植**、跨多文件、多子系统、驱动、协议栈、启动链、分区、pinctrl 或硬件风险的改动，先进入 plan mode，写 plan 文档并取得用户**逐条确认**后再动手。拿不准复杂度时按"复杂"处理。
3. **查证事实**：Nordic/NCS/Zephyr 命令、board target、overlay 文件名、VCOM、pinctrl、`nrfutil` 行为必须先查 Nordic MCP；再结合当前工程与 NCS 源码核对。
4. **记录基线**：动手前读取 git 状态与目标文件当前内容，保留本次改动边界。工作区已有用户改动时只叠加必要修改，不还原用户改动。
5. **编辑前说明**：用一句话说明将修改哪些文件、为什么改、影响面是什么。涉及破坏性硬件动作时必须先取得用户明确授权。
6. **执行修改**：按现有工程风格改最小范围；配置改动优先放在应用层 `prj.conf`、`sysbuild.conf`、`boards/<normalized-board-target>.overlay` 或明确的 overlay/conf fragment，不改 SDK 上游文件。改自定义驱动、binding、`module.yml` 或 `DEVICE_DT_INST_DEFINE` 时读取 [zephyr-custom-driver](../zephyr-custom-driver/SKILL.md)；改 nRF54L sQSPI、`nordic,nrf-sqspi`、`cpuflpr_vpr` 或 MSPI 子设备时读取 [nrf54l-sqspi](../nrf54l-sqspi/SKILL.md)。
7. **自测闭环**：读取 [zephyr-build](../zephyr-build/SKILL.md)，选定工具链模式并全程沿用；然后 build → [flash](../zephyr-flash/SKILL.md) → [serial](../zephyr-serial-log/SKILL.md) / [debug](../zephyr-debug/SKILL.md)。改 Kconfig、Devicetree、board target、sysbuild、pinctrl 后使用 pristine 构建。
8. **独立验收（必须，不可自验）**：自测通过后读取 [clean-agent](../clean-agent/SKILL.md)，只给需求、验收标准和复现步骤，让全新只读 agent 判定 PASS/FAIL。**自己改的代码不能只靠自己测通过就收工**（见总纲铁律 4）。FAIL 时回到第 6 步。
9. **收尾**：总结改动、验证命令和结果；未能执行的硬件验证要说明缺少的设备、SN、端口或用户操作。

## 硬件与存储红线

- `recover`、`erase --all`、`erase --all-external`、OTP/UICR 写入、保护位修改、跨 power-domain pinctrl 方案，执行前必须说明后果并等待用户确认。
- 对 RRAM、UICR/OTP、外部 flash 做写/擦前，先用 [nrfutil-memory](../nrfutil-memory/SKILL.md) 读取或 dump 备份可备份区域；写后必须回读核对。
- 多设备连接时不能自动选择目标设备，除非 SN、board name 或用户选择唯一明确。

## 接力规则

上下文不足、任务被中断、**或发现返工级偏差（理解错需求 / 方向错误 / 需推翻重来）时**，先停下与用户确认，再写 `.agent/Handover.md`，记录需求、NCS 版本、board target、SN/COM、已改文件、验证结果、未完成事项和风险点，然后 clear。不要修改原始 plan 文档，除非用户同意。跨 Agent 临时文件（plan / Handover / 日志）统一放工程根的 `.agent/`，见总纲「跨 Agent 状态管理」。
