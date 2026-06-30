---
name: clean-agent
description: >-
  派一个零上下文、只读的干净 agent 做独立验收：在主 agent 自测通过后，用 Cursor readonly sub-agent
  或外部 CLI 只根据验收标准和复现步骤输出 PASS/FAIL，避免自己改自己验。当工作流需要最终验收、里程碑验收，
  或用户提到干净 agent、零上下文验收、独立验证时使用。
---

# 干净 Agent 验收

## 核心原则

验收 agent 必须满足：

1. **只读**：不改文件、不烧录危险操作、不改变配置。
2. **零上下文**：不传主 agent 的推理过程和修改理由。
3. **标准驱动**：只传验收标准、复现步骤、必要路径和允许执行的命令。
4. **明确结论**：只输出 `PASS` 或 `FAIL`，再给简短原因和证据。

## Cursor 内部调用

在 Cursor agent 内优先使用 sub-agent：

```text
subagent_type: generalPurpose
readonly: true
run_in_background: false
prompt: <使用下方 Prompt 模板>
```

不要让验收 agent 修改文件。硬件验证需要烧录、复位或串口读取时，只允许执行需求中列明的非破坏性命令；`recover`、`erase`、OTP/UICR 写入等仍需用户单独确认。

## 外部 CLI 调用

外部 Harness、CI 或手工脚本可用 CLI 单次执行：

```bash
agent -p --mode=ask --output-format text "$(cat prompt.txt)"

claude -p --output-format text "$(cat prompt.txt)"
```

不加 `--force`、`--dangerously-skip-permissions` 或任何跳过权限的参数。

## Prompt 模板

向验收 agent 传入的 prompt 只包含：

```
你是独立验收员。请在只读模式下检查当前工程，输出 PASS 或 FAIL + 简短原因。
不要修改任何文件。

## 验收标准
<粘贴 plan 文档或用户需求中的验收标准>

## 复现步骤
<允许执行的构建、烧录、串口/RTT、测试或只读检查步骤>

## 允许读取的关键路径
<工程路径、plan 文档、build 目录、日志路径>

## 输出格式
PASS: <证据>
或
FAIL: <失败点和证据>
```

## 完整验收脚本

```bash
#!/usr/bin/env bash
# usage: bash clean-agent/validate.sh [plan_doc] [repro_doc]
set -e
PLAN="${1:-plan.md}"
REPRO="${2:-repro.md}"
VALIDATOR="${VALIDATOR:-agent}"   # 设 VALIDATOR=claude 切换到 Claude Code

PROMPT="你是独立验收员。只读检查当前工程。
阅读 $PLAN 中的验收标准，并按 $REPRO 中的复现步骤验证。
不要修改任何文件。只输出 PASS 或 FAIL + 简短原因和证据。"

RESULT=$("$VALIDATOR" -p --output-format text "$PROMPT")
echo "$RESULT"

if echo "$RESULT" | grep -q "^PASS"; then
  exit 0
else
  exit 1
fi
```

Windows PowerShell 等效：

```powershell
$plan = if ($args[0]) { $args[0] } else { "plan.md" }
$repro = if ($args[1]) { $args[1] } else { "repro.md" }
$tool = if ($env:VALIDATOR) { $env:VALIDATOR } else { "agent" }
$prompt = "你是独立验收员。只读检查当前工程。阅读 $plan 中的验收标准，并按 $repro 中的复现步骤验证。不要修改文件。只输出 PASS 或 FAIL + 简短原因和证据。"
$result = & $tool -p --output-format text $prompt
Write-Host $result
if ($result -match "^PASS") { exit 0 } else { exit 1 }
```

## 场景选择

| 场景 | 推荐方式 |
|------|----------|
| 主 agent 在 Cursor IDE/CLI 内运行 | Cursor sub-agent，`readonly: true` |
| 外部 Harness 脚本 / CI | 本 skill 的脚本 |
| 需要跨工具通用 | 本 skill 的脚本 |

## 结果处理

- `PASS`：保留验收证据，主 agent 可以收尾。
- `FAIL`：主 agent 回到对应工作流修复；修复后重新自测，再重新派干净 agent。
- 验收 agent 输出不符合格式时，视为 FAIL，重新给出更明确的验收标准和复现步骤。

## 注意事项

- **plan 文档是跨 agent 的唯一信息载体**：验收标准写入 plan 文档，不要口头传递。
- **硬件命令白名单**：复位、串口读取、RTT、测试可在复现步骤中列明；破坏性命令不能由验收 agent 自行决定。
- **退出码**：脚本返回 `0` 表示通过，`1` 表示失败。
