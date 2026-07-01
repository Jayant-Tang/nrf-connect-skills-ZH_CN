---
name: workflow-debug
description: >-
  zephyr-expert 编排层的「调试 / 排障」工作流：现象异常但根因未知时，先稳定复现并取得 runtime 证据，
  再用假设驱动循环（一次只改一个变量）缩小范围、定位根因；诊断委托 zephyr-debug / zephyr-serial-log，
  根因明确后转 workflow-modify 修复并回归验收。当任务是查崩溃 / HardFault / fault、卡死、外设无反应、
  数值或时序不对、偶发异常等需要定位根因时使用；已知改什么用 workflow-modify，纯查原理不动硬件用 workflow-ask。
---

# 工作流 D：调试 / 排障

适用：固件行为异常但**根因未知**——崩溃 / HardFault / fault、卡死、外设无反应、数值 / 时序不对、偶发问题。
本工作流只管**定位根因的诊断纪律**；具体操作委托工具层，定位后修复转 [workflow-modify](../workflow-modify/SKILL.md)。

- 已知该改什么、只差动手 → 直接用 [workflow-modify](../workflow-modify/SKILL.md)。
- 纯查原理、不动硬件 / 不改文件 → 用 [workflow-ask](../workflow-ask/SKILL.md)。

## 开工前 GATE（全部通过前，禁止执行后续步骤）

逐项确认，任一不满足就停，不要凭"我大概知道是哪"的猜测直接改：

1. **读懂项目意图**：先读 README / 设计文档 / 注释 / 既有 plan / Handover / git log，能说清"它本来该怎么工作"。否则会把原始设计（如低功耗时序）当 bug 改掉。
2. **知识源可用**：先完成 Nordic MCP 预检查。必须确认当前会话能看到 Nordic MCP 的 server / tools，并完成一次最小只读探针；只要出现 tools 不可见、探针失败、认证失效、或因权限/网络/工具异常而无法证明服务可用，统一视为 **MCP 不通**。MCP 不通就停下让用户恢复，不要 workaround 绕过（见总纲铁律 2）。
3. **目标齐全**：NCS 版本、board target、工程路径、SN / 串口端口都明确，缺则先确认。
4. **能复现 + 有证据**：能**稳定复现**现象，且至少拿到一份 **runtime 证据**（串口日志 / RTT / fault 寄存器 / GDB 状态）。复现不了或没有证据，先去取证，**不准凭猜改代码**。

## 执行步骤（假设驱动循环）

1. **定义现象**：精确写出"期望 vs 实际"和复现步骤，存入 `.agent/repro.md`（后续 clean-agent 验收直接用）。
2. **稳定复现**：读取 [zephyr-flash](../zephyr-flash/SKILL.md) 烧录、[zephyr-serial-log](../zephyr-serial-log/SKILL.md) 或 [zephyr-debug](../zephyr-debug/SKILL.md) 采集，确认能稳定触发；偶发问题先想办法提高复现率。
3. **收集证据**（按现象选工具，只取不改）：
   - 崩溃 / HardFault / fault → [zephyr-debug](../zephyr-debug/SKILL.md)（halt 决策表、CFSR/HFSR/BFAR、addr2line）。
   - 启动 / 运行日志异常 → [zephyr-serial-log](../zephyr-serial-log/SKILL.md)；低侵入用 RTT（见 zephyr-debug）。
   - 外设无反应 / GPIO 中断不触发 → [zephyr-debug](../zephyr-debug/SKILL.md) 外设在线检查 + [nrf54l-pinctrl](../nrf54l-pinctrl/SKILL.md) / [nrf54l-sqspi](../nrf54l-sqspi/SKILL.md)。
   - 配置 / 存储可疑 → 检查 build 产物（`.config`、`zephyr.dts`）、[nrfutil-memory](../nrfutil-memory/SKILL.md) 读 RRAM/UICR。
4. **建假设 + 缩小范围**：列出可能原因，**一次只验一个假设**；用二分法缩小（回退 git 改动、临时 disable 模块、做最小复现工程）。
5. **验证假设**：用 runtime 证据**证实或证伪**，不靠"看代码觉得是它"。**一次只改一个变量**，便于归因。
6. **定位根因**：区分**症状与根因**（如"加了 delay 就好"往往只是掩盖时序竞争）；根因结论必须**多源交叉验证**（日志 + 寄存器 + 源码 + MCP / 文档一致），呼应总纲防幻觉。
7. **修复**：根因明确后转 [workflow-modify](../workflow-modify/SKILL.md)，按其步骤改最小范围 + 自测闭环。若还在定位阶段（加 log、临时桩、disable），留在本工作流。
8. **回归验收（必须，不可自验）**：修复后重跑 `.agent/repro.md` 的复现步骤确认现象消失、且无新回归；再读取 [clean-agent](../clean-agent/SKILL.md)，用 `.agent/repro.md` 让全新只读 agent 判定 PASS/FAIL（见总纲铁律 4）。

## 调试红线

- **没复现 / 没证据不改代码**；不靠猜测批量改、不一次改多处。
- **一次只改一个变量**：多处同时改会污染归因，定位失效。
- **破坏性操作先确认**：`recover`、`erase`、OTP/UICR 写入等先取得用户授权（见总纲红线与 [zephyr-debug](../zephyr-debug/SKILL.md) APPROTECT 一节）。
- **临时调试代码**（log、桩、disable）在修复后清理或显式标注，不残留进交付。

## 接力规则

上下文将满、**或发现方向错（假设全被证伪、根因判断需推翻）时**，先停下与用户确认，再把现象、`.agent/repro.md`、已验证 / 已排除的假设、当前最可疑点、已收集证据路径写入 `.agent/Handover.md`，然后 clear。证据日志统一放 `.agent/logs/`（见总纲「跨 Agent 状态管理」）。
