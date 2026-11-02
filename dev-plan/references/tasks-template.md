# tasks.md 模板

```markdown
# 任务：<需求名>

依据：spec.md、design.md　共 N 个任务　更新：YYYY-MM-DD

## 技术方案（只有规模“小”才写）

改哪里、怎么改、为什么，5–10 行。

## 测试计划

| 场景 | 层级 | 测试名 | 要点 | 谁写 |
|------|------|--------|------|------|
| R1.1 | 单元 | comments_create_valid_text | 返回 201，内容原样保存 | T1 |
| R1.3 | 浏览器 | R1.3 访问码过期后打开评论页 | 显示“访问码已过期” | dev-test |

### 容易出问题的情况

| 情况 | 合理的预期 | 测试 | 谁写 |
|------|------------|------|------|
| 连点两次“发表” | 只保存一条 | comments_double_submit_once | T3 |

## 任务

### T1 <标题>
- 状态：待办
- 文件：新建 `src/comments/store.js`；修改 `src/db.js:40-60`；测试 `test/comments-store.test.js`
- 接口：
  - 使用：`db.prepare(sql)`（现有）
  - 提供：`createComment({ itemId, version, author, text }) → { id, createdAt }`
- 场景：R1.1、R1.2
- 测试：
  - `comments_create_valid_text`：text="你好" → 返回 id，读回内容为 "你好"
  - `comments_reject_empty`：text="" → 抛出 `ValidationError`，消息包含 "内容不能为空"
- 完成定义：`node --test test/comments-store.test.js` 全部通过
- 依赖：无

### T2 <标题>
…

## 进度

（dev-implement 每完成一个任务追加一行）

| 任务 | 完成时间 | 提交 | 测试 |
|------|----------|------|------|
| T1 | 2026-11-03 10:20 | a1b2c3d | 4/4 通过 |

## 后续

（实现中发现、但不在本次范围的改进）

- …
```

任务状态只用四个值：

| 状态 | 含义 |
|------|------|
| 待办 | 还没开始 |
| 进行中 | 正在做 |
| 完成 | 测试通过、已提交 |
| 阻塞 | 试了 3 次做不下去；在任务下写一行“阻塞原因：…”，到关口 C 列进“紧急” |

关口 C 打回需要改代码时，在末尾追加“返工”任务（编号接着往下排，写明来源，比如“来源：关口 C，d2 改为 B”），状态“待办”。
