---
name: workflow-develop
description: >-
  zephyr-expert 编排层的「开发 / 新建」工作流：新功能、新模块或从零搭建工程时，先 plan mode 写需求、
  架构、board target、NCS 版本、验收标准和阶段计划；实施时按阶段构建、烧录、日志验证，并用 clean-agent
  独立验收。当任务是多步开发或新建项目时使用；既有工程小范围修复用 workflow-modify。
---

# 工作流 C：开发

适用：新功能、新模块、新应用、驱动接入、协议栈集成、从零搭建或多阶段开发。此类任务默认先规划。

## 开工前 GATE（全部通过前，禁止执行后续步骤）

不要因为"自己能搞定"而跳过：

1. **读懂上下文意图**：在既有 workspace 上加功能 → 先读现有 README / 架构 / 设计意图 / 注释 / git log，理解"为什么这么搭"，确保新增量不破坏原始设计目标；从零新建 → 先与用户对齐需求、约束、目标场景，不臆测。
2. **知识源可用**：先完成 Nordic MCP 预检查。必须确认当前会话能看到 Nordic MCP 的 server / tools，并完成一次最小只读探针；只要出现 tools 不可见、探针失败、认证失效、或因权限/网络/工具异常而无法证明服务可用，统一视为 **MCP 不通**。MCP 不通就停下让用户恢复，不要用 workaround 绕过（见总纲铁律 2）。
3. **目标齐全**：NCS 版本、qualified board target、工程路径、SN / 串口端口都明确，缺则先确认。
4. **plan 必须签字**：开发 / 新建默认是复杂任务，**必须先出 plan 文档并取得用户逐条确认**再实施（展开见下方步骤 1、3）。用 `AskQuestion` 问澄清问题 **≠** plan 确认。

## 执行步骤

1. **进入 plan mode**：写 plan 文档（存 `.agent/plan.md`），包含目标、非目标、目标板、qualified board target、NCS 版本、外设/协议栈、硬件连接、验收标准、阶段任务、风险和回退点。
2. **先做 Nordic MCP 预检查**：凡是涉及 Nordic、Zephyr、NCS、nRF、`west`、board、`nrfutil` 的事实判断，先确认当前会话能看到 Nordic MCP 的 server / tools，再执行一次最小只读探针，确认 server 可访问且已认证。
3. **预检查失败就停**：如果看不到 Nordic MCP 的 server / tools，或探针失败、认证失效、权限/网络/工具异常导致无法完成探针，统一视为 **MCP 不通**。此时停止后续规划与实施准备，不得继续基于猜测或源码片面结论推进方案。
4. **查证前置事实**：用 Nordic MCP 确认 board target、overlay 命名、示例路径、Kconfig/Devicetree/sysbuild 用法、外设限制和 `nrfutil` 命令；再结合当前工程和 NCS 源码核对。
5. **确认方案**：向用户说明架构、文件布局、验证方式和需要用户配合的硬件动作；用户确认后实施。
6. **拆分阶段**：每阶段只交付一个可构建、可运行、可观察的增量。独立可并行任务使用 readonly sub-agent 或隔离 worktree；主线只保留架构、接口和验收状态。
7. **实施阶段**：遵循工程已有风格。新建 NCS/Zephyr 应用时保留标准结构：`CMakeLists.txt`、`prj.conf`、`boards/<normalized-board-target>.overlay`、必要的 `sysbuild.conf`、源文件和 README。需要新增/接入自定义驱动时读取 [zephyr-custom-driver](../zephyr-custom-driver/SKILL.md)；需要 nRF54L sQSPI/MSPI bus 时读取 [nrf54l-sqspi](../nrf54l-sqspi/SKILL.md)。
8. **阶段验证**：每阶段读取 [zephyr-build](../zephyr-build/SKILL.md) 构建；需要硬件行为时读取 [zephyr-flash](../zephyr-flash/SKILL.md) 和 [zephyr-serial-log](../zephyr-serial-log/SKILL.md)；需要断点、RTT 或 fault 分析时读取 [zephyr-debug](../zephyr-debug/SKILL.md)。验证结果写回 plan 文档。
9. **里程碑验收（必须，不可自验）**：每个里程碑和最终交付都读取 [clean-agent](../clean-agent/SKILL.md)，只传 plan 的验收标准与复现步骤，要求全新只读 agent 输出 PASS/FAIL。**自己开发的功能不能只靠自己测通过就交付**（见总纲铁律 4）。
10. **失败处理**：失败只回退本阶段改动或回到最近通过的 checkpoint；不推翻已验证阶段。修复后重新执行本阶段验证。

## 计划文档要求

计划文档（`.agent/plan.md`）是跨 agent 的唯一持久状态，至少包含：

```markdown
# Plan

## 需求
## 硬件与环境
- NCS version:
- Board target:
- Device SN:
- UART/RTT:

## 验收标准
## 阶段任务
## 当前进度
## 风险与回退
```

上下文不足、**或发现返工级偏差（需求理解错 / 架构方向错 / 需推翻重来）时**，先停下与用户确认，再写 `.agent/Handover.md`，记录 plan 路径、当前阶段、已完成验证、未解决问题和下一步命令，然后 clear。原始 plan 文档只更新状态，不重写历史决策，除非用户同意。

## 质量门槛

- board target、NCS 版本、VCOM、SN、硬件连接不明确时停止询问。
- 破坏性硬件动作、跨 power-domain pinctrl、OTP/UICR 写入必须先取得用户确认。
- 最终交付不能只以“能编译”为通过标准；必须有日志、RTT、测试或用户可复现的硬件行为作为验收依据。
