# 单部佛经翻译工作流

输入一部经的名称或 CBETA 编号，最终得到一份完整、可发布的 `content/sutras-raw/<slug>.md`。
本文档覆盖端到端 4 步流程，给出每一步的命令、产物、常见排查。

> 默认翻译 backend：**百炼 DashScope `qwen3.5-plus`**。其余 backend（azure, lmstudio, gemini 等）在末尾对比。

---

## 0. 前置准备（仅首次配置）

| 检查项 | 路径 | 说明 |
| --- | --- | --- |
| 翻译密钥 | `.env` | 至少需要 `DASHSCOPE_API_KEY`；切换 backend 时再加对应 key。 |
| 经目清单 | `target_sutra_list.tsv` | 决定能拉取哪些经、优先级、卷数、译者。新经如果不在里面，先补一行。 |
| 任务队列 DB | `translation_jobs.db` | 已在 `.gitignore`。首次运行 `init_jobs.py` 自动建表。 |

```bash
# 验证环境
grep -E "^(DASHSCOPE_API_KEY|AZURE_API_KEY)=" .env
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"
```

---

## 1. 拉取 CBETA 原文 — `fetch_cbeta.py`

```bash
# 按 CBETA 编号
python3 scripts/fetch_cbeta.py T0002

# 按经名（简繁皆可，TSV 里有的都能查）
python3 scripts/fetch_cbeta.py 七佛經
python3 scripts/fetch_cbeta.py 七佛经

# 强制重下覆盖
python3 scripts/fetch_cbeta.py T0002 --force

# 只下 XML 不切卷
python3 scripts/fetch_cbeta.py T0002 --xml-only
```

**数据源**：`https://raw.githubusercontent.com/cbeta-org/xml-p5/master/<coll>/<coll><vol>/<coll><vol>n<no>.xml`

**产物**：

- `sources/cbeta/<coll><vol>n<no>.xml` — 完整 TEI XML 底本（一部经一个文件）
- `content/cbeta-raw/<coll>/<sutra_id>/<sutra_id>_NNN.txt` — 按卷拆分的 bookcase 风格 TXT，含 `No.X` 头、序文（仅卷一）、卷标题、译者、正文段落、偈颂（全角空格对齐）

**自检**：

```bash
ls content/cbeta-raw/T/T0002/        # 卷数对得上 TSV 的 juan_count
sed -n '1,15p' content/cbeta-raw/T/T0002/T0002_001.txt   # 头部结构正确
```

**常见报错**：

- `下载失败 HTTP 404`：TSV 里的 `volume` 字段不对（例如写成 `01` 实际归在 `02`），核对 CBETA 网站；
- `XML 中找不到 <body>`：XML 文件残缺，加 `--force` 重下；
- `XML 切出 N 卷，TSV 记 M 卷`：以 XML 实际为准，回去更正 TSV。

---

## 2. TXT 转 Markdown — `cbeta_txt_to_md.py`

```bash
# 增量生成（已有的 md 一律跳过）
python3 scripts/cbeta_txt_to_md.py T0002

# 重做未翻译的卷（已翻译的会被保护）
python3 scripts/cbeta_txt_to_md.py T0002 --force

# 危险：连已翻译的 md 也覆盖，会清空译文
python3 scripts/cbeta_txt_to_md.py T0002 --force-overwrite-translated
```

**做了什么**：

- 读 `content/cbeta-raw/T/<sutra_id>/<sutra_id>_NNN.txt`
- 自动拆分：散文按句末标点切成 ≤150 字段落；偈颂每 4 句一段；连续短段会被合并到 ~150 字上限
- 章节标题（`（一）...`、`...品第一`）单独成 `## ` 级标题
- 给每对 `### 原文 / ### 现代语译` 注入 `<!-- sid:NNN -->` 序号，每卷从 001 开始
- 写入 frontmatter：`title / slug / cbeta_id / category / translator / juan_index / translation_status: untranslated / review_status: unreviewed`

**产物**：`content/sutras-raw/<sutra_id>-NNN.md`，结构：

```markdown
---
title: 七佛經卷第一
slug: T0002-001
cbeta_id: T0002
translation_status: untranslated
...
---

# 七佛經

### 原文
<!-- sid:001 -->

如是我聞：

### 现代语译
<!-- sid:001 -->


### 原文
<!-- sid:002 -->

一時，佛在舍衛國...
...
```

**自检**：

```bash
grep -c "sid:" content/sutras-raw/T0002-001.md     # 段数 × 2
grep "translation_status" content/sutras-raw/T0002-001.md   # untranslated
```

**保护机制**：

- `--force` 只覆盖 `translation_status: untranslated` 的文件。已翻译的会跳过并提示。
- 真要重做已翻译文件（例如分段策略改了，需要重切），必须显式 `--force-overwrite-translated`。
- 如果误覆盖：`git checkout HEAD -- content/sutras-raw/<slug>.md` 立即恢复（前提是已提交到 git）。

---

## 3. 入翻译队列 — `init_jobs.py`

```bash
# 全量扫描（每轮翻译开始前都跑一次）
python3 scripts/init_jobs.py

# 只扫某部经
python3 scripts/init_jobs.py T0002
```

**做了什么**：

- 遍历 `content/sutras-raw/*.md`，给每卷在 `translation_jobs.db` 建/更新一条任务
- 按 frontmatter 的 `category` 设优先级（阿含部類 10、本緣部類 9、般若部類 8 …）
- 已翻译完的卷自动标为 `done`，不会被重新分配
- 输出整体队列状态

**自检**：

```bash
python3 scripts/job_queue.py status        # 看 pending/running/done 计数
python3 scripts/job_queue.py locks         # 看各部经被哪个 backend+model 锁着
```

---

## 4. 翻译 — `agent_worker.py`（默认 dashscope qwen3.5-plus）

```bash
# 翻译某一部经的全部卷（推荐：单卷模式更可控）
python3 scripts/agent_worker.py --backend dashscope --slug T0002-001

# 持续抢任务，直到没有为止（适合一次翻很多部）
python3 scripts/agent_worker.py --backend dashscope

# 限定卷数（最多翻 5 卷后退出，便于试运行）
python3 scripts/agent_worker.py --backend dashscope --limit 5

# 换模型
python3 scripts/agent_worker.py --backend dashscope --model qwen3-max
python3 scripts/agent_worker.py --backend dashscope --model qwen3.5-flash

# 调批量大小（默认每请求 5 段；设 1 退化为逐段）
python3 scripts/agent_worker.py --backend dashscope --batch-size 10
```

**做了什么（每卷循环）**：

1. 从 `translation_jobs.db` 原子抢占一个 `pending` 任务（同一部经在一次会话内只锁给一个 backend+model，保证风格一致）
2. 用正则按 `<!-- sid:NNN -->` 定位每段空白的 `### 现代语译`
3. 批量发送给 backend（5 段一批 JSON 包），失败的项目自动逐段回退
4. 用 sid 精确替换写回 md，每批结束 heartbeat 更新进度
5. 全卷完成后：
   - frontmatter `translation_status` → `translated`
   - 写入/更新 `ai_translator: <model>`
   - 检查整部经是否全卷完成，若是发 Telegram 通知（需 `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`）

**自检**：

```bash
grep -c "sid:" content/sutras-raw/T0002-001.md      # 段数 × 2，不应变
grep "translation_status" content/sutras-raw/T0002-001.md     # translated
grep "ai_translator" content/sutras-raw/T0002-001.md          # qwen3.5-plus 或所用模型
# 抽几段看译文质量
sed -n '20,40p' content/sutras-raw/T0002-001.md
```

**翻译质量复检**：见 `claude.md` 中"校验评论"小节。基本要求：

- 必须逐句、逐段翻译，不省略名单、套语、流通分；
- "如是我闻" → "我是这样听佛说的"；
- 偈颂必须翻成白话，不能只抄原文改标点；
- 咒文用 `（意译：）` 格式补意译。

**常见情况**：

- **卡死**：单卷 10 分钟无 heartbeat 自动释放回 `pending`，下次 worker 再抢就续；也可手动 `python3 scripts/job_queue.py reset T0002-001`。
- **想换模型重译某一卷**：`python3 scripts/job_queue.py reset T0002-001 --clear-lock` 解锁后用新 backend 跑。
- **批量失败大段返回"【翻译失败」**：通常是 backend 限速或模型抽风，等几分钟后 `--slug` 单独重跑该卷。

---

## 5. 重建前端索引 — `build-index.js`（必做）

```bash
node scripts/build-index.js
```

**为什么必须做**：网站搜索靠根目录的 `sutras-raw-index.json`。新经入站、卷的 `translation_status` / `review_status` 变化，都必须重跑这个脚本，否则前端搜不到。曾经因为漏跑导致 T2087 翻完了但网站搜不到《大唐西域記》。

**附带**：如果想让该经进 sitemap（影响 SEO 收录，不影响站内搜索），还要跑：

```bash
node scripts/build-sitemap.js
```

但 sitemap 只取索引中得分前 100 的经，权重 = `PRIORITY_WORKS` (1000) + `human_reviewed` (100) + `ai_reviewed` (50) + `translated` (30)。普通 `translated` 状态的小众经一般进不了 top 100，要进 sitemap 通常得人工 review 或加进 `scripts/build-sitemap.js` 的 `PRIORITY_WORKS` 列表。

---

## 6. 后续校验（独立流程，不在本工作流必走）

| 目的 | 命令 |
| --- | --- |
| 找原文=译文的段（模型偷懒抄回） | `python3 scripts/agent_worker.py retranslate --backend dashscope --slug T0002-001` |
| AI 查重，处理打了 `dup_suspect` 的段 | `python3 scripts/agent_worker.py dedup --backend dashscope --slug T0002-001` |
| 把 raw md 整理到正式发布目录 | 见 `content/sutras/heart-sutra.md` 为参考稿，目前手工搬运 |

校验状态字段约定（`review_status`）：`unreviewed → reviewing → ai_reviewed → human_reviewed`。

---

## Backend 选型速查

| backend | 默认模型 | 适用场景 | 备注 |
| --- | --- | --- | --- |
| **dashscope** | `qwen3.5-plus` | **工作流默认**，国内速度快，质量稳，免费额度可用 | `DASHSCOPE_API_KEY` |
| azure | `DeepSeek-V3.2` | 大体量、对译文质量要求最高时的备选 | `AZURE_API_KEY` `AZURE_ENDPOINT` |
| azure2 | `gpt-5.3-chat` | 想用 GPT-5 系列比较风格 | `AZURE2_API_KEY` `AZURE2_ENDPOINT` |
| lmstudio | `qwen3.5-9b` | 完全离线、零成本，机器够强可用 | 本地 LM Studio 跑 `:1234` |
| anyrouter | `claude-3-5-haiku-20241022` | Claude 风格译文 | `ANYROUTER_API_KEY` |
| gemini | `gemini-2.5-flash` | 子进程调用 Gemini CLI；强制逐段 | 安装 `gemini` CLI |
| openrouter / nvidia / groq / codex | 同名脚本 | 各家备份/比对实验 | 各自 key |

> 同一部经一次只允许一个 backend+model 锁定（见 `job_queue.py:claim_job`），保证全经风格一致。要换 backend，先 `reset <slug> --clear-lock`。

---

## 端到端示例：从零翻译 T0002《七佛經》

```bash
# 1. 拉原文（确保 TSV 里已有 T0002 行）
python3 scripts/fetch_cbeta.py T0002

# 2. 转 md 并注入 sid
python3 scripts/cbeta_txt_to_md.py T0002

# 3. 入队
python3 scripts/init_jobs.py T0002

# 4. 翻译
python3 scripts/agent_worker.py --backend dashscope --slug T0002-001

# 5. 重建索引（让网站搜得到，必做！）
node scripts/build-index.js

# 6. 验收
grep "translation_status\|ai_translator" content/sutras-raw/T0002-001.md
grep "T0002" sutras-raw-index.json   # 索引里应该有
```

每一步都是幂等的：重跑只会跳过已完成的部分，不会破坏现有翻译。
