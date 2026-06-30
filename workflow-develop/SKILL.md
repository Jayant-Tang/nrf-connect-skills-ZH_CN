---
name: workflow-develop
description: >-
  zephyr-expert 编排层的「开发 / 新建」工作流：新功能、新模块或从零搭建工程时，先 plan mode 写需求、
  架构、board target、NCS 版本、验收标准和阶段计划；实施时按阶段构建、烧录、日志验证，并用 clean-agent
  独立验收。当任务是多步开发或新建项目时使用；既有工程小范围修复用 workflow-modify。
---

# 工作流 C：开发

适用：新功能、新模块、新应用、驱动接入、协议栈集成、从零搭建或多阶段开发。此类任务默认先规划。

## 执行步骤

1. **进入 plan mode**：写 plan 文档，包含目标、非目标、目标板、qualified board target、NCS 版本、外设/协议栈、硬件连接、验收标准、阶段任务、风险和回退点。
2. **查证前置事实**：用 Nordic MCP 确认 board target、overlay 命名、示例路径、Kconfig/Devicetree/sysbuild 用法、外设限制和 `nrfutil` 命令。MCP 不通时停止。
3. **确认方案**：向用户说明架构、文件布局、验证方式和需要用户配合的硬件动作；用户确认后实施。
4. **拆分阶段**：每阶段只交付一个可构建、可运行、可观察的增量。独立可并行任务使用 readonly sub-agent 或隔离 worktree；主线只保留架构、接口和验收状态。
5. **实施阶段**：遵循工程已有风格。新建 NCS/Zephyr 应用时保留标准结构：`CMakeLists.txt`、`prj.conf`、`boards/<normalized-board-target>.overlay`、必要的 `sysbuild.conf`、源文件和 README。需要新增/接入自定义驱动时读取 [zephyr-custom-driver](../zephyr-custom-driver/SKILL.md)；需要 nRF54L sQSPI/MSPI bus 时读取 [nrf54l-sqspi](../nrf54l-sqspi/SKILL.md)。
6. **阶段验证**：每阶段读取 [zephyr-build](../zephyr-build/SKILL.md) 构建；需要硬件行为时读取 [zephyr-flash](../zephyr-flash/SKILL.md) 和 [zephyr-serial-log](../zephyr-serial-log/SKILL.md)；需要断点、RTT 或 fault 分析时读取 [zephyr-debug](../zephyr-debug/SKILL.md)。验证结果写回 plan 文档。
7. **里程碑验收**：每个里程碑和最终交付都读取 [clean-agent](../clean-agent/SKILL.md)，只传 plan 的验收标准与复现步骤，要求全新只读 agent 输出 PASS/FAIL。
8. **失败处理**：失败只回退本阶段改动或回到最近通过的 checkpoint；不推翻已验证阶段。修复后重新执行本阶段验证。

## 计划文档要求

计划文档是跨 agent 的唯一持久状态，至少包含：

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

上下文不足时写 `Handover.md`，记录 plan 路径、当前阶段、已完成验证、未解决问题和下一步命令。原始 plan 文档只更新状态，不重写历史决策，除非用户同意。

## 质量门槛

- board target、NCS 版本、VCOM、SN、硬件连接不明确时停止询问。
- 破坏性硬件动作、跨 power-domain pinctrl、OTP/UICR 写入必须先取得用户确认。
- 最终交付不能只以“能编译”为通过标准；必须有日志、RTT、测试或用户可复现的硬件行为作为验收依据。
