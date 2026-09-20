---
name: zephyr-readme
description: >-
  为 Zephyr / NCS 工程编写双语 README（英文 README.md + 中文版），覆盖功能、设计意图、
  构建烧录、操作步骤与预期行为。当用户要求写工程 README 或项目文档时使用。
---

# Zephyr / NCS 工程双语 README 编写

目标：产出 `README.md`（英文主文档）+ 中文版，说清**功能、设计原理与意图、操作步骤、预期行为**，让读者能照着复现。

## 铁律

1. **不编造内容**：功能、配置项、日志、功耗数据必须来自工程实际（源码、`prj.conf`、overlay、Kconfig、git log、实测日志）。预期日志用真实抓取的 boot log（见 [zephyr-serial-log](../zephyr-serial-log/SKILL.md)），禁止脑补。没实测的数据留 TODO，不写估计值冒充实测。
2. **命令环境假设**：读者已打开 nRF 工具链环境（`toolchain env` / `toolchain launch` 已完成），**不写**工具链安装、环境初始化步骤。直接给 `west build` / `west flash`。
3. **路径假设**：当前目录 = 工程根目录。命令一律用相对路径（`-d build`、`.`），**禁止绝对路径**。
4. **双语同步**：中英文两版结构、章节、数据一致，只改语言。改一版必须同步另一版。

## 文件约定

- 英文：`README.md`（主文档，GitHub 默认展示）。
- 中文：跟随工程已有约定（`README_zh.md` 或 `README-CN.md`）；新工程默认 `README_zh.md`。
- 两版开头互相放链接，英文版如 `[中文说明](README_zh.md)`，中文版如 `[English](README.md)`。

## 章节结构

按工程实际裁剪，空章节不留。完整骨架见 [template.md](template.md)。典型顺序：

1. **标题 + 一句话定位**：工程名、是什么 demo、跑在什么 SoC / 板上。紧接一行 `Environment: nRF Connect SDK vX.Y.Z`（版本从 `west.yml` / build provenance / 实测 boot log 取）。
2. **Features / 功能**：分点列功能与基本操作，一句话一条。
3. **Architecture / 架构**：数据流或状态机，用 mermaid 或 ASCII 字符画（见下节）。
4. **Hardware / 硬件**：board target（qualified，如 `nrf54l15dk/nrf54l15/cpuapp`）、外接器件、接线表（Markdown 表格）、供电 / 测量注意点。
5. **Getting the project / 获取项目**（可选）：submodule、patch 等获取后必做的步骤。
6. **Build and flash / 构建烧录**：每种构建变体（debug / release / 特殊模式）各给一组命令：

   ```bash
   west build -p always -b <board_target> -d build .
   west flash -d build
   ```

   多 board 支持时给一组命令 + 一句"换 board target 即可"，不重复罗列。
7. **Configuration / 配置**：关键 Kconfig 选项，每条注明默认值、取值范围、影响。非 Kconfig 的配置（如 devicetree `queue-size`）说明在哪改、应用侧如何跟随。
8. **Running / 运行（操作步骤）**：编号步骤写清用户操作（按键、串口、手机 App）和每步预期现象（LED、日志、文件）。
9. **Expected output / 预期行为**：贴真实抓取的日志片段（```text 代码块），长日志中间用 `...` 截断。
10. **Power measurement / 功耗测量**（可选）：测量方法步骤 + 实测数据（状态、平均值、底电流），截图留 TODO 占位。
11. **Notes / 注意事项（设计原理与意图）**：每个主题一小节，讲清"为什么这么做"——约束来源（硬件 / 驱动 / 协议）、踩过的坑、关键代码片段及逐条解释。这是 README 最有价值的部分，写设计意图而非复述代码。
12. **Related links / 参考链接**（可选）：博客、官方文档。

## 图示约定

- **结构图 / 数据流 / 状态机**：优先 mermaid（GitHub 原生渲染），其次 ASCII 字符画。不为了画图引入二进制图片。
- **实测功耗截图、实物照片、接线照片**：留 TODO 占位符，让用户自行替换：

  ```markdown
  <!-- TODO: 补充 PPK2 实测功耗截图：release 固件 IDLE 状态，存为 docs/imgs/release_idle.png -->
  ![TODO: release 固件 IDLE 功耗](docs/imgs/release_idle.png)
  ```

  占位符必须写清要拍/截什么内容和建议路径，图片统一放 `docs/imgs/`。

## 写作流程

1. **读工程**：`prj.conf*`、`*.overlay`、`CMakeLists.txt`、`Kconfig*`、`src/` 关键文件、git log、既有文档。说清设计意图后再动笔（与总纲"先懂意图再动手"一致）。
2. **确认事实**：NCS 版本、board target、配置项默认值与范围，以工程文件为准；SDK 行为不确定时查 Nordic MCP / NCS 源码。
3. **取真实素材**：预期日志从实测串口输出截取；功耗数据从实测记录取。拿不到的留 TODO，不编造。
4. **先写英文版**，再同步出中文版。技术术语（Kconfig、Devicetree、overlay、board target 等）两版都保持英文原词。
5. **自查清单**：
   - [ ] 无绝对路径、无工具链环境搭建步骤
   - [ ] 所有命令可在工程根目录直接执行
   - [ ] 日志 / 数据为真实实测或明确 TODO
   - [ ] 中英文版章节与数据一致
   - [ ] mermaid / 代码块语法正确，图片占位符写清内容
