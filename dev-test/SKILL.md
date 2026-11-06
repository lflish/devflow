---
name: dev-test
description: 测试和验收（devflow 第 4 阶段）。在使用 devflow 的项目里（有 .devflow.yml 或 docs/changes/），开发阶段“可提测”后，或用户对某个需求说“测试”“验收”“e2e”时使用。按项目环境配置连接测试浏览器（CDP），补齐测试、编写浏览器端到端测试、做探索式检查和修复；项目还没有验证 skill 时先生成 verify-<项目名>；最后由没写过代码的验证者（优先同级别的其他模型）独立验证，机器关口 C 放行。产出 test-report.md、verdict.md 和截图。
---

# dev-test：测试和验收

目标：**每个验收场景都在真实环境里被证明过；放行凭的是独立验证的结论。**

## 开始

1. 先读 `../dev-workflow/SKILL.md` 的“每次开始时”，照做其中第 1–3 步（包括读 `../dev-workflow/references/decisions.md`、`verification.md`、`config.md`）。本阶段还要读同目录下的 `gates.md`、`preview.md`。
2. 状态行“阶段”改为 `dev-test`；状态应为“测试中”。
3. **独立模式**：找不到需求文件夹时（用户只是说“跑一下测试”），只运行或补写用户指的测试，结果直接告诉用户；不写报告、不做机器关口、不交接。

**接着做**：看 test-report.md 和 verdict.md 到了哪一步，从没完成的步骤继续。**返工回来时**（tasks.md 里有刚完成的“返工”任务）：第 1、2 步已经做过，从第 3 步补齐返工相关的测试开始，然后第 5–8 步；第 8 步按 verification.md 规则 4 决定派一个验证者还是全套。

## 1. 准备环境

1. 按 config.md 的读取规则取 `test.e2e_env` 和 `test.verify_env` 的地址（测试浏览器用的地址按规则 4 换主机）。缺地址的：一次性问用户，写进本机配置（config.md“缺地址时”）。
2. 读这两个环境的 `data` 规则，整个阶段都按它来（共享环境只动测试数据，production 只读）。
3. 按 [references/browser.md](references/browser.md) 选这次用哪种测试浏览器（本机无头 / 固定 CDP / 云浏览器；云浏览器只能测公网地址），把 `devflow-browser.js` 复制到项目的 `tests/e2e/`（已有就跳过），检查能连上、能打开被测地址；local 环境需要时先用 `environments.local.start` 启动服务。

## 2. 项目验证 skill

看项目里有没有 `verify-<项目名>` skill（`.claude/skills/` 或 `.agents/skills/` 下）。没有就按 [references/verify-skill.md](references/verify-skill.md) 生成，并实际跑通一次；有就读它，检查本需求涉及的功能在它的功能清单里，没有就补上。

后面的探索式检查和独立验证都按它操作项目。

## 3. 补齐测试

读 spec 的全部场景和 tasks.md 的“测试计划”“容易出问题的情况”，列对照表（场景 → 层级 → 测试 → 状态），每个场景至少一个测试。确实没法测的写明原因。

- **单元、集成**：补齐缺的。具体值、精确断言；覆盖空、零、超长、非法、重复、无权限；互相独立。
- **浏览器**：每个“浏览器”场景写一个 Playwright 测试，提交进仓库，写法见 [references/e2e-example.md](references/e2e-example.md)：有 CDP 地址时连远程浏览器，没有时用本机无头浏览器；关键场景最后调用 `evidence('<场景编号>')` 截图。按 browser.md 的“运行脚本化测试”在 `e2e_env` 上运行。

## 4. 探索式检查

按 verify skill 和 [references/explore-checklist.md](references/explore-checklist.md)，把本需求涉及的页面像用户一样实际用一遍，问题编号 `X1`、`X2`…，记录严重程度、复现步骤、截图。只用测试浏览器（browser.md 的“只用测试浏览器”）。

## 5. 修复

按严重程度从高到低处理测试失败和探索发现的问题：
1. **复现**，找到原因：先查测试是否写错，再查实现，最后查设计。
2. **先写回归测试**，确认它失败。
3. **最小修复**（可以按决策原则 4 补全同一文件里直接相关的缺口）。
4. **复测**：回归测试、原来失败的测试、相关的正常流程都要通过。
5. **提交**：每个修复和它的回归测试一起提交，`fix:` 开头。

约束：撤回 2 次、或修复开始波及无关文件时，停手，剩下的问题写进报告；一轮最多修 30 个。不改测试迁就错误的实现。修复累计超过 5 个文件或改了接口的，读 `../dev-review/SKILL.md`，对这些修复再评审一次。

## 6. 全量运行和测试报告

运行全部测试（`commands.test`，以及在 `e2e_env` 上运行 `commands.e2e`），附实际输出。按 [references/report-template.md](references/report-template.md) 写 `test-report.md`（每轮覆盖）。浏览器测试没做或只做了一部分，在报告开头醒目写明原因。

## 7. 验收核对

自己先核对一遍，有问题先修好再进入独立验证：

| 方面 | 检查 |
|------|------|
| 完整 | 任务都是“完成”（“阻塞”的单独列出）；每条需求有对应代码；每个场景有测试和结果 |
| 正确 | 测试全过；spec 里的具体数值、文案、权限在代码里一致；完成条件成立 |
| 一致 | 设计里的决定在代码里都能看到；偏差都记在 design.md 的“变更”和 decisions.md 里 |
| 干净 | 没有未提交的改动；没有调试代码、注释掉的大段代码；`.devflow-tmp/` 不在仓库里 |

## 8. 机器关口 C：独立验证

1. **让验证环境跑的是这个提交**：`verify_env` 是 local 时，在验证用的 worktree 里启动；是共享环境（如 staging）时，用 `.devflow.yml` 里它的 `deploy` 命令部署这个提交，然后读回版本或健康检查，确认部署的就是这个 sha。没配 `deploy`、或部署失败的，改用 `e2e_env` 验证，在汇总里说明。
2. 按 verification.md：选验证者（优先同级别的其他模型），在验证环境上验证当前提交，用其中的提示词，结论写到 `verdict.md`（派之前先把旧结论追加到 `verdict-history.md`）。

- **通过 / 通过，有备注**：按 gates.md 更新汇总（等你的事在最前，然后是场景、截图、验证者和提交），汇总页源文件在 `pages/summary/`。
  - **L1**：状态和阶段先不改；汇总末尾请用户回复，状态行写 `待关口：C`，提交，这一轮结束。回复后按 gates.md 的表处理（状态“已验证”、阶段 `dev-release`）。
  - **L2 / L3**：状态改为“已验证”，阶段改为 `dev-release`，提交，然后读 `../dev-release/SKILL.md` 并执行。
- **不通过**：每个拦下的问题在 tasks.md 加一个“返工”任务（来源写 `X<n>`），状态改回“开发中”，阶段改为 `dev-build`，读 `../dev-build/SKILL.md` 并执行；修完会依次回到这里，按 verification.md 规则 4 重新验证。同一个问题 3 轮不过，记 `c<n>` 交给用户。

## 不要做的事

- 不改测试迁就错误的实现。
- 不用操作用户个人浏览器的工具（Claude in Chrome、桌面内置浏览器、computer use）。
- 浏览器测试没做不能算通过；独立验证没做不能放行。
- 不违反环境的数据规则：共享环境只动测试数据，production 只读。
