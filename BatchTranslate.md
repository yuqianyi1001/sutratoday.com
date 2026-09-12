
## 翻译任务队列（多 Agent 并发翻译规范）

**所有翻译工作必须通过任务队列协调。严禁直接翻译文件而不经过队列抢占。**

队列数据库：`translation_jobs.db`（已在 `.gitignore`，不提交）

### 任务状态流转

```
pending → running → done
                 ↘ failed → pending（自动重置）
running → pending（超时 10 分钟无心跳，自动释放）
```

### 同一部经风格一致性保证

一部经（同一 cbeta_id）的所有卷，必须由同一个 backend/model 翻译。
系统在第一卷被抢占时自动锁定该经剩余卷，其他 backend 不会分配到同一部经。

---

## 方式一：AI Agent 自己翻译（Claude Code / Codex / Gemini CLI / OpenCode）

适用于：agent 自身就是翻译者，直接读写 md 文件。

### 开始翻译前（必须）

```bash
# 抢占一个任务，获取待翻文件
python3 scripts/job_queue.py claim --backend <你的名字> --model <模型名>
```

输出 JSON：
```json
{"ok": true, "agent_id": "a1b2c3d4", "slug": "T0005-001",
 "file_path": "content/sutras-raw/T0005-001.md",
 "seg_total": 86, "seg_done": 0}
```

- `ok: false` 表示没有待翻任务，停止。
- 记住 `agent_id` 和 `slug`，后续命令需要用到。
- `--backend` 填写你的工具名，如 `claude-code`、`gemini-cli`、`codex`。

### 翻译过程中（每翻完若干段调用一次，防止超时被回收）

```bash
python3 scripts/job_queue.py heartbeat T0005-001 --agent-id a1b2c3d4 --seg-done 12
```

### 翻译完成后（必须）

```bash
python3 scripts/job_queue.py done T0005-001 --agent-id a1b2c3d4
```

此命令会自动将 md 文件的 `translation_status` 更新为 `translated`。

### 翻译失败时（必须）

```bash
python3 scripts/job_queue.py fail T0005-001 --agent-id a1b2c3d4 --error "原因说明"
```

### 完整工作流示例

```bash
# 1. 抢任务
RESULT=$(python3 scripts/job_queue.py claim --backend claude-code --model claude-opus-4)
SLUG=$(echo $RESULT | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['slug'] if d['ok'] else '')")
FILE=$(echo $RESULT | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('file_path',''))")
AGENT=$(echo $RESULT | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('agent_id',''))")

# 2. 检查是否有任务
[ -z "$SLUG" ] && echo "无待翻任务" && exit 0

# 3. 翻译文件（由 agent 自行完成）
#    读取 $FILE，逐段翻译，每段翻完立即写回文件
#    每翻 5 段调用一次 heartbeat：
#    python3 scripts/job_queue.py heartbeat $SLUG --agent-id $AGENT --seg-done N

# 4. 标记完成
python3 scripts/job_queue.py done $SLUG --agent-id $AGENT
```

---

## 方式二：Python 脚本 Worker（调用外部 LLM API）

适用于：通过 API 调用 Azure/LMStudio/AnyRouter 翻译。

```bash
# 自动循环翻译，支持 azure/lmstudio/anyrouter
python3 scripts/agent_worker.py --backend azure
python3 scripts/agent_worker.py --backend azure --model Kimi-K2.5
python3 scripts/agent_worker.py --backend lmstudio
python3 scripts/agent_worker.py --backend anyrouter
python3 scripts/agent_worker.py --backend azure --slug T0003-001  # 单卷
python3 scripts/agent_worker.py --backend azure --limit 10        # 最多翻 10 卷
```

---

## 运维命令

```bash
python3 scripts/init_jobs.py                    # 同步 md 状态到队列（每次开始前运行）
python3 scripts/job_queue.py status             # 查看整体进度
python3 scripts/job_queue.py locks              # 查看各部经锁定情况
python3 scripts/job_queue.py reset <slug>       # 重置某卷（保留锁）
python3 scripts/job_queue.py reset <slug> --clear-lock  # 重置并解锁（允许换模型）
python3 scripts/job_queue.py release-stale      # 释放超时卡死任务
```

### 优先级规则

队列按 `priority DESC, cbeta_id ASC, juan_index ASC` 排序：

| 类别 | priority |
|------|---------|
| 阿含部類 | 10 |
| 本緣部類 | 9 |
| 般若部類 | 8 |
| 法華/華嚴部類 | 7 |
| 其他 | 0~6 |

## 安全与密钥管理

- **禁止在代码中硬编码任何密钥、token、API key、密码**，这是一个 public repo。
- 所有密钥统一存放在 repo 根目录的 `.env` 文件中，该文件已加入 `.gitignore`，永远不提交。
- Python 脚本通过读取 `.env` 文件加载环境变量（见 `scripts/` 下各翻译脚本的加载示例），不依赖 `python-dotenv`，直接解析。
- 如需新增密钥，只写入 `.env`，在代码中用 `os.environ["KEY_NAME"]` 读取。
- 提交前检查：确认没有密钥明文出现在 staged 文件中。

## Git

- 推送远端时，使用 `--no-verify` 跳过 push hooks。例如：`git push --no-verify parent main`
- 当用户要求提交并推送时，除非另有说明，否则默认按以下顺序执行：
  - `git add ...`
  - 如果 git diff 中有 api key，llm key，就立即停止！！！
  - 如果需要提交，执行 `git commit --no-verify -m "..."`，提交的message用中文写。
  - 然后执行 `git push --no-verify parent main`
