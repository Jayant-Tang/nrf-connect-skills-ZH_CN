# nrf-connect-skills-ZH_CN

为 **Cursor** 和 **Claude Code** AI Agent 设计的 **Zephyr / nRF Connect SDK (NCS) 中文技能包**，通过预设工作流和工具指南，让 AI Agent 在嵌入式开发长任务中稳定可靠地完成询问、代码修改和项目开发。

---

## 技能树结构

```
zephyr-expert/
├── SKILL.md                  # 总纲入口：工作区识别、任务分诊、核心原则
│
├── workflow-ask/             # 工作流 A：询问 / 解释（只读）
├── workflow-modify/          # 工作流 B：修改 / 修复（有限范围改动 + 实测）
├── workflow-develop/         # 工作流 C：开发 / 新建（多步、从零搭建）
│
├── zephyr-build/             # 工具指南：west build、Kconfig、Devicetree、overlay
├── zephyr-flash/             # 工具指南：烧录、复位、擦除、设备管理
├── zephyr-serial-log/        # 工具指南：串口日志、UART monitor、COM 口选择
├── zephyr-debug/             # 工具指南：GDB、J-Link、RTT、fault / crash 分析
│
├── nrf54l-pinctrl/           # 专项：nRF54L GPIO / pinctrl 引脚规划与校验
├── nrf54l-sqspi/             # 专项：nRF54L sQSPI soft peripheral / Zephyr MSPI
├── zephyr-custom-driver/     # 专项：out-of-tree 自定义驱动接入
├── nrfutil-memory/           # 专项：nrfutil device 读写 RRAM / UICR / OTP / 外部 flash
│
└── clean-agent/              # 辅助：零上下文只读子 Agent 独立验收
```

---

## 快速上手

### Cursor

将本仓库克隆到 `~/.claude/skills/` 目录下（保持目录名 `zephyr-expert`）：

```powershell
cd $HOME\.claude\skills
git clone https://github.com/Jayant-Tang/nrf-connect-skills-ZH_CN.git zephyr-expert
```

Cursor Agent 会自动发现 `~/.claude/skills/` 下的 `SKILL.md` 文件并在对话中按需加载。

### Claude Code

将本仓库克隆到 `~/.claude/skills/` 目录下（保持目录名 `zephyr-expert`）：

```bash
cd ~/.claude/skills
git clone https://github.com/Jayant-Tang/nrf-connect-skills-ZH_CN.git zephyr-expert
```

Claude Code 会自动扫描 `~/.claude/skills/` 下的 `SKILL.md`，并在 `available_skills` 中列出供 Agent 按需读取。

### 触发条件

对话中提到以下关键词时，技能包会被自动激活：

> `Nordic` / `nRF` / `NCS` / `Zephyr` / `west build` / `nrfutil` / `DK` / `overlay` / `Kconfig`

---

## 三种工作流

| 场景 | 工作流 | 适用描述 |
|------|--------|---------|
| 答疑 / 查文档 / 读代码 | `workflow-ask` | 只读，不改文件、不动硬件 |
| 改配置 / 修 bug / 改小段代码 | `workflow-modify` | 有限范围改动 + build → flash → 串口验证闭环 |
| 新功能 / 新模块 / 从零建工程 | `workflow-develop` | 先 plan 文档，按阶段开发，里程碑验收 |

---

## 核心设计原则

- **渐进式加载**：总纲只加载分诊逻辑，具体工具指南按需读取，避免无用信息污染上下文。
- **知识源优先级**：Skill 内置指南 → Nordic MCP → 本地 NCS 源码 → 官方文档，不在缺信息时强行推进。
- **防幻觉**：串口乱码、内存 dump、截断日志不做脑补；Nordic MCP 不通时停止而非猜测。
- **独立验收**：所有修改/开发产出在自测通过后，派零上下文只读子 Agent 独立判定 PASS/FAIL。
- **跨 Agent 状态**：plan、Handover、日志等过程产物统一放工程根 `.agent/`（有 git 则记得把`.agent/`加入 `.gitignore`）；复杂任务的 plan mode 写 `.agent/plan.md`，上下文将满时写 `.agent/Handover.md` 接力，不丢进度。

---

## 工具指南速查

| 需要做什么 | 读取哪个 Skill |
|-----------|--------------|
| `west build`、Kconfig、Devicetree overlay | `zephyr-build/SKILL.md` |
| 烧录 hex、复位、擦除、恢复设备 | `zephyr-flash/SKILL.md` |
| 读串口 / boot log / 选 COM 口 | `zephyr-serial-log/SKILL.md` |
| GDB、J-Link、RTT、crash 分析 | `zephyr-debug/SKILL.md` |
| nRF54L 引脚分配 / pinctrl / GPIO 跨域 | `nrf54l-pinctrl/SKILL.md` |
| nRF54L sQSPI / MSPI bus | `nrf54l-sqspi/SKILL.md` |
| out-of-tree 自定义驱动 | `zephyr-custom-driver/SKILL.md` |
| nrfutil 读写 RRAM / UICR / OTP / 外部 flash | `nrfutil-memory/SKILL.md` |

---

## 依赖

- [Cursor](https://cursor.com) 或 [Claude Code](https://claude.ai/code) IDE（Agent 模式）
- [Nordic MCP](https://github.com/NordicSemiconductor/mcp-server-nordic) — NCS / Zephyr 文档实时查询
- [nRF Connect SDK](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/installation.html) 本地安装（构建、烧录需要）

---

## License

Copyright 2026 Jayant Tang

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
