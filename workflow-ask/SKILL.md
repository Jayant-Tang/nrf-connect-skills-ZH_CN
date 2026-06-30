---
name: workflow-ask
description: >-
  zephyr-expert 编排层的「询问 / 解释」只读工作流：界定问题边界、按总纲知识源顺序查证、用 Nordic MCP
  确认 NCS/Zephyr/nRF 事实、给出带来源的结论，并对高风险结论做独立复核。当任务是答疑、解释代码或原理、
  查文档、定位原因且不改文件、不动硬件时使用；需要改代码或实测时改用 workflow-modify 或 workflow-develop。
---

# 工作流 A：询问（只读）

适用：答疑、读代码、查文档、定位原理。全程只读，不改文件、不动硬件。

## 执行步骤

1. **分诊**：确认问题只需要只读回答。出现“修改、修复、烧录、串口验证、跑测试、新建工程”等动作时，停止本工作流并切到 [workflow-modify](../workflow-modify/SKILL.md) 或 [workflow-develop](../workflow-develop/SKILL.md)；现象异常但**根因未知**（崩溃 / 卡死 / 外设无反应等）需复现定位时，切到 [workflow-debug](../workflow-debug/SKILL.md)。
2. **锁定上下文**：明确芯片、开发板、board target、NCS 版本、工程路径、目标现象。缺少影响结论的关键信息时，先按知识源查证；仍无法确定时向用户提一个明确问题。
3. **查证顺序**：先用当前 skill 和相关工具 skill；命令语义用 `--help`；Nordic、Zephyr、NCS、nRF、`west`、board、`nrfutil` 相关事实必须先查 Nordic MCP；再查当前工程源码、NCS 源码或本地文档。Nordic MCP 不通时停止并要求用户恢复认证。
4. **控制上下文**：大范围源码检索交给 `generalPurpose` sub-agent（`readonly: true`），要求只返回结论、文件路径和关键证据；主线只保留最终证据。
5. **形成答案**：区分“上游 Zephyr 行为”和“NCS/Nordic 特有行为”；结论后标明来源类型（MCP URL、MCP resource、工程文件、NCS 源码路径）。
6. **交叉验证**：会影响后续实现、烧录、硬件连接、OTP/UICR、recover/erase 的结论，必须用第二个来源复核；必要时派全新 readonly sub-agent 按结论和来源独立检查。
7. **输出**：先给结论，再给依据和操作建议。不能确认的内容直接说明缺少哪项信息，不补全、不猜测。

## 防幻觉要求

- 串口乱码、内存 dump、半截日志、替换符 `�` 都不能当作可解释文本；必须说明该片段不可靠，并换方式重取或只按原始 hex 判断。
- board target、PCA、SN、VCOM、NCS 版本、外设引脚固定功能都不能凭记忆确定；使用 Nordic MCP 或本地 build provenance 确认。
- 只读问答无需 plan 文档；问题升级为实现任务时再进入对应工作流。
