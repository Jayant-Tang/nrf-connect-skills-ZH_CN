---
name: zephyr-expert
description: >-
  Zephyr 与 nRF Connect SDK (NCS) 开发的统一入口与总纲，含三种工作流：用户询问、功能修改、新项目开发。用户提到 Nordic, Zephyr, NCS, nRF 等关键词时使用。基于本地 SDK 源码或 Nordic MCP 给出可靠结果。不编造，也不在缺少信息时强行推进工作。
---

# Zephyr 专家总纲

## 1. 背景

通过预设的**工作流**和**工具指南**，充分调用 AI Agent 能力，在连续长任务时能够稳定可靠地完成用户要求的询问或代码编写任务。

## 2. 核心原则与策略

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
- 避免无用信息污染上下文：编译、烧录等长日志工作放在后台运行并存入log文件，使用`tail`等方法，只读取结果。
- 充分利用 Sub-Agent 节约主 Agent 上下文：
  - 大范围 / 探索式检索（会拉入大量无关文件）→ `generalPurpose` + `readonly: true`，只回摘要与来源。
  - 独立、可并行的子任务（同时调研多个模块 / 方案）→ 多个 Task 并行。
  - 一次性"用完即弃"的实验 / best-of-N 尝试、或独立验证产出 → sub-agent 或 `best-of-n-runner`，结果合入主线、丢弃中间上下文。

### 确保知识源完整

开始工作前确保已有所需知识，**不做无依据推断**。若认为当前任务缺失必要信息，可以要求用户补充。（按如下顺序查找）

1. 工作流 / Skill 提供的指南。CLI 工具的`--help` 输出。
2. Nordic MCP（**MCP不通时，停下来要求用户重新认证**）。
3. 当前工作区源码，NCS 源码。如有 CodeGraph MCP，可优先使用。
4. 来自`https://docs.nordicsemi.com/`的文档。它是 NCS 仓库中的源码经过 Sphinx 构建后发布的 HTML 版本。网络不好时也可以在`nrf/doc/`中找到未构建的`*.rst`文档。同理`zephyr/doc`也有

### 跨 Agent 状态管理

1. **复杂任务先计划并存档**：进 plan mode，出方案并存 plan 文档。
2. **上下文不够就接力**：上下文将满时，先把进度 / 已完成 / 待办 / 坑 保存到当前工程 `Handover.md`，禁止修改原始 plan 文档（除非用户同意）。
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
- **修改 / 修复**（在既有工程改配置 / 小段代码 / 修 bug；有限范围写 + 实测）→ 读取 [workflow-modify](workflow-modify/SKILL.md)。
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
