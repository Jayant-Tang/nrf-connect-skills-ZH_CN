---
name: zephyr-expert
description: >-
  Zephyr 与 nRF Connect SDK (NCS) 开发的统一入口与总纲，含三种工作流：用户询问、功能修改、新项目开发。用户提到 Nordic, Zephyr, NCS, nRF 等关键词时使用。基于本地 SDK 源码或 Nordic MCP 给出可靠结果。不编造，也不在缺少信息时强行推进工作。
---

# Zephyr 专家总纲

## 1. 背景

通过预设的**工作流**和**工具指南**，充分调用 AI Agent 能力，在连续长任务时能够稳定可靠地完成用户要求的询问或代码编写任务。

## 2. 核心原则与策略

### 绝对铁律（MUST，不可绕过；与下方任何"建议性"原则冲突时以此为准）

动手前逐条过，任一不满足就**停**，不要用"我能搞定"的理由跳过：

1. **先懂意图再动手**：改既有项目前，先读 README / 设计文档 / 注释 / 既有 plan / Handover / git log，能说清"它为什么这么设计"。说不清就继续读或问用户，**不准先改代码**。
2. **MCP 不通就停**：必须先完成 **Nordic MCP 预检查**。只要出现“当前会话看不到 Nordic MCP 的 server / tools、最小只读探针失败、认证失效、或无法完成探针确认服务可用”任一情况，统一视为 **MCP 不通**。此时停下来让用户恢复并说明影响；**不得用 workaround（自写脚本、纯靠源码推断等）静默绕过**。用户明确同意放弃 MCP 后，才可改用源码独立推进。
3. **复杂任务先签字**：命中"版本迁移、 移植、修改SDK内部文件（驱动 / 协议栈 / 启动链 / 分区）、硬件风险"任一，**必须先用plan mode出文档并取得用户确认**再动手。用 `AskQuestion` 问澄清问题 **≠** plan 确认。
4. **自己改的自己不验**：自测通过后，必须用 clean-agent（全新只读上下文）按验收标准独立判定 PASS/FAIL，不能"自己测通过就收工"。
5. **方向错就接力**：一旦发现理解错需求 / 方向错误 / 需返工，或上下文将满，先停下与用户确认，再 `.agent/Handover.md` + clear，**不在原会话里硬扛打补丁**。

### 工作区识别

按照以下方式识别当前是什么工作区。

| 工作区                  | 目录结构                                                     | 说明                                                         |
| ----------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| 独立 Zephyr Project     | 含`prj.conf` 、`*.overlay`、  `CMakeLists.txt`等             | 需要指定 `ZEPHYR_BASE` 环境变量到对应版本 NCS 的`zephyr/`目录（如`D:\ncs\v3.3.0\zephyr`），那之后`west`工具才能支持`west build`等扩展命令。 |
| nRF Connect SDK （NCS） | 含`zephyr/`、`nrf/`、`modules/`、`nrfxlib/`、`bootloader/`等目录. | 工作区内可直接执行`west build`等扩展命令。因为`west`会自动向上层目录寻找`.west/`配置/。工作区内可参考的例程在`nrf/samples`,`zephyr/samples`下 |
| 非 Zephyr 工作区        | 不符合以上规律                                               | 大概率是处理“用户询问”工作流。如果不是，则停下来要求用户提供SDK路径和工程路径。 |

如果用户未指定 NCS 版本，要停下来询问用户。

### 上下文管理（连续长任务中上下文是珍贵资源）

- 渐进式披露：只在需要时才加载对应的工作流和工具指南。
- 避免无用信息污染上下文：编译、烧录等长日志工作放在后台运行并存入 `.agent/logs/` 下的 log 文件，使用`tail`等方法，只读取结果。
- 充分利用 Sub-Agent 节约主 Agent 上下文：
  - 大范围 / 探索式检索（会拉入大量无关文件）→ `generalPurpose` + `readonly: true`，只回摘要与来源。
  - 独立、可并行的子任务（同时调研多个模块 / 方案）→ 多个 Task 并行。
  - 一次性"用完即弃"的实验 / best-of-N 尝试、或独立验证产出 → sub-agent 或 `best-of-n-runner`，结果合入主线、丢弃中间上下文。

### 确保知识源完整

开始工作前确保已有所需知识，**不做无依据推断**。若认为当前任务缺失必要信息，可以要求用户补充。（按如下顺序查找）

0. **项目自身意图（改 / 移植既有项目时，优先于一切外部知识）**：README、设计文档、代码注释、既有 plan / Handover、git log。先搞清"原作者要解决什么、为什么这么做"，再谈怎么改——否则容易把原始设计目标（如低功耗、特定时序）当成 bug 改掉。
1. 工作流 / Skill 提供的指南。CLI 工具的`--help` 输出。
2. Nordic MCP（**先做预检查；MCP不通时停下来要求用户恢复 / 重新认证，并说明影响；不要用 workaround 静默绕过**）。
3. 当前工作区源码，NCS 源码。如有 CodeGraph MCP，可优先使用。
4. 来自`https://docs.nordicsemi.com/`的文档。它是 NCS 仓库中的源码经过 Sphinx 构建后发布的 HTML 版本。网络不好时也可以在`nrf/doc/`中找到未构建的`*.rst`文档。同理`zephyr/doc`也有

### Nordic MCP 预检查（MUST）

进入任何 Nordic / Zephyr / NCS / nRF / `west` / `nrfutil` 相关任务前，必须先做下面两步：

1. **检查可见性**：确认当前会话已经暴露 Nordic MCP 的 server / tools；看不到就不要假设“也许能用”。
2. **执行最小探针**：做一次最小只读查询，确认 server 可访问且已认证。

若出现以下任一情况，统一视为 **MCP 不通**：

- Nordic MCP 的 server / tools 不可见。
- 最小只读探针失败。
- 认证失效。
- 因权限、网络、工具异常等原因无法完成探针，因而**不能证明**服务可用。

`MCP 不通` 时立即停止，不得继续输出 Nordic / Zephyr / NCS / nRF 相关事实性结论；只能向用户说明当前阻塞和恢复建议。只有用户**明确同意放弃 MCP**，才可改用源码、本地文档或其它次级来源独立推进。

### 跨 Agent 状态管理

**统一存放位置（MUST）**：所有跨 Agent / 跨会话的临时产物——plan 文档、`Handover.md`、clean-agent 的复现步骤、构建 / 烧录 / 串口等长日志——统一放在**目标工程根目录的 `.agent/` 下**，不要散落在工程根目录或随手命名。约定结构：

```
<工程根>/.agent/
├── plan.md       # 复杂任务的计划文档（跨会话持久状态）
├── Handover.md   # 接力文档
├── repro.md      # clean-agent 验收用的复现步骤
└── logs/         # 构建 / 烧录 / 串口等长日志
```

- **工程有 git 时**：把 `.agent/` 写入工程根的 `.gitignore`（这些是过程产物，不进版本库）；没有 git 则跳过。
- 路径一律以工程根为基准；非 Zephyr 工作区（纯询问）通常不产生这些文件。

1. **复杂任务先计划并存档**：进 plan mode，出方案并存 `.agent/plan.md`。
2. **接力时机（满足任一即接力）**：上下文将满，**或发现返工级偏差（理解错需求 / 方向错误 / 需推翻重来）**。先停下与用户确认，再把进度 / 已完成 / 待办 / 坑写入 `.agent/Handover.md`，然后 clear；禁止修改原始 plan 文档（除非用户同意）。不要在原会话里靠不断打补丁掩盖方向错误。
3. **验证用全新 agent**：产出自测通过后，派一个**干净上下文的 Agent**（参考 [clean-agent](clean-agent/SKILL.md)），只给它验收标准 + 如何复现，独立判定通过与否，避免"自己改自己验"的确认偏差。

### 全局防止乱码幻觉

读到乱码、不可见字符、半截字节或内存 dump 时，**先排查物理/编码原因，绝不脑补出有意义的字符串或结论**。擦除态全 `0xFF`、非文本区出现非 ASCII 属正常；按原始 hex 核对，不把随机字节臆测成版本号 / 序列号 / 字符串。output 截断或含替换符（`�`）时明确说明该处不可靠，换方式重取后再判断。细则见 [zephyr-serial-log](zephyr-serial-log/SKILL.md) 与 [nrfutil-memory](nrfutil-memory/SKILL.md)。

### 验收方式（按以下优先级顺序）

根据不同的工作流，有不同的验收方式。但都需要派一个**干净上下文的 Agent**（参考 [clean-agent](clean-agent/SKILL.md)）来执行。

| 工作流            | 产物                                                         | 验收方式                                                     | 验收通过标准         |
| ----------------- | ------------------------------------------------------------ | ------------------------------------------------------------ | -------------------- |
| 询问              | 用户询问的答案（文本），原理解释文档（`*.md`, `*.html`）等等 | 知识源交叉验证。如果是来源MCP/网络的答案，就用源码验证；如果是来自源码探索的答案，就用MCP/网络搜索结果验证。 | 不同知识源的说法一致 |
| 修改， 新项目开发 | `build*/`下的固件。对于 sysbuild 多镜像可能是`merged.hex`，`build*/`下每个子镜像中`mcuboot/`,`<app_name>/`也会有`zephyr.hex`,`zephyr.elf`等产物。 | 先确认工程编译的板子型号与电脑连接的板子型号一致。烧录到**对应的板子**中，通过串口日志或RTT进行验证。如果需要用户操作按钮等物理硬件，可以代码里先模拟。如果无法模拟，再去要求用户操作后，再验证。 | 输出符合期望的log。  |

此外，工作流中可能在中间阶段内置一些检查点（Checkpoint），要根据检查点要求检查中间成果，防止走偏。

### 用户交互原则

- **决策收集铁律·禁止静默替用户选择**，在每个 Checkpoint，所有需要用户确认的 决策项**必须每项独立列出 + 等用户答复**。Agent **可以推荐**（"我推荐 X，因为 …"），但 **不能"已经替你定了 X，如果不对再说"** —— 这等于剥夺选择机会。
  - **优先**：如果环境有 `AskQuestion` 工具，每个决策项作为一个独立 question（一次调用可 传多个 question），用户能用选择卡逐项确认。
  - **否则**：停下来在消息里把所有问题**编号列出**（每个问题独占一段、写清推荐项 + 理由 + 备选项），明确说"我等你逐项答复后再继续"，**不要继续做任何后续工作**。
  - **绝不**：把多项决策打包成一个"全选我推荐的 / 全部 OK 吗？"yes/no 问题；也不要在 "推荐一句话"后默认直接进下一步。

- 已经遵循规则做的事，不需要说原因（用户本身就了解原因）。例如，不需要说 “任务已暂停，因为根据要求，mcp不通时要先询问用户”；而是应该直接跟客户说“当前MCP不通，请确认连接状态”。

## 3. 任务分诊

判定用户意图属于哪类，**读取对应工作流辅助文件**；拿不准就用一句话与用户确认：

- **询问 / 解释**（答疑、读代码、查文档、定位原理；只读，不改文件 / 不动硬件）→ 读取 [workflow-ask](workflow-ask/SKILL.md)。
- **修改 / 修复**（在既有工程改配置 / 小段代码、**已知要改什么**；有限范围写 + 实测）→ 读取 [workflow-modify](workflow-modify/SKILL.md)。
- **调试 / 排障**（现象异常但**根因未知**：崩溃 / HardFault、卡死、外设无反应、偶发；需复现 + runtime 证据定位根因）→ 读取 [workflow-debug](workflow-debug/SKILL.md)。
- **开发 / 新建**（新功能 / 新模块 / 从零搭；多步、跨多工具、需规划）→ 读取 [workflow-develop](workflow-develop/SKILL.md)。

## 【附】工具辅助文件索引（渐进式披露，按需读取）

工作流在需要执行具体操作时读取对应工具辅助文件；各工具辅助文件 **自包含、无隐式加载顺序**：

- **要编译 / 改配置**（`west build`、配置开发环境、处理环境变量）→ 读取 [zephyr-build](zephyr-build/SKILL.md)。
- **要烧录 / 操作设备**（烧 hex、复位、擦除、恢复、列设备）→ 读取 [zephyr-flash](zephyr-flash/SKILL.md)。
- **要读串口 / 验证启动日志 / 选 COM 口**（端口映射、DTR、UART monitor、boot log 比对）→ 读取 [zephyr-serial-log](zephyr-serial-log/SKILL.md)。
- **要调试 / 诊断**（SEGGER RTT、J-Link、`west debug` / `attach`、fault/crash 分析）→ 读取 [zephyr-debug](zephyr-debug/SKILL.md)。
- **nRF54L 引脚分配 / pinctrl / GPIO 跨域**（外设不工作、`NRF_PSEL`、domain↔端口）→ 读取 [nrf54l-pinctrl](nrf54l-pinctrl/SKILL.md)。
- **nRF54L sQSPI / Zephyr MSPI**（`nordic,nrf-sqspi`、`SDP_MSPI_*`、`cpuflpr_vpr`、sQSPI 外设不通）→ 读取 [nrf54l-sqspi](nrf54l-sqspi/SKILL.md)。
- **Zephyr 自定义驱动接入**（out-of-tree driver、`ZEPHYR_EXTRA_MODULES`、`module.yml`、binding、`DEVICE_DT_INST_DEFINE`）→ 读取 [zephyr-custom-driver](zephyr-custom-driver/SKILL.md)。
- **用 nrfutil 直接读写存储**（RRAM/RAM/外部 QSPI flash、UICR/OTP 的读写擦 dump）→ 读取 [nrfutil-memory](nrfutil-memory/SKILL.md)。
- **BLE 射频 / DTM 测试**（Direct Test Mode、2-wire UART 19200、TX/RX/PER、射频认证）→ 读取 [ble-dtm](ble-dtm/SKILL.md)。
