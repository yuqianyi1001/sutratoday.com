# AGENTS

## 语言
- 始终使用简体中文回答我
- 除非我单独指定用其他语言回答，否则，始终用中文回答我

## 佛典工作流

- 状态流转
  - 开始 -> 找到佛经原文 -> 把佛经原文整理成md file -> 校验分组、分段的合理性  -> 分段已校验(segments_reviewed) -> (接下面)
  - 翻译成 `现代语译` -> translated -> 翻译校验 -> ai_reviewed -> 人工校验 -> human_reviewed

- 添加和处理一个佛经时，先找到佛经原本，并保存一份在本地。如果有多个版本，找到最通用的版本：
  - 优先查找本地：~/Downloads/bookcase_v098_20251216
  - 优先在线版本：https://github.com/cbeta-org/xml-p5
  - 如果上述方法都找不到，请在 Cbeta 查找： https://cbetaonline.dila.edu.tw/
  - 把佛经底本，保存到 `sources/cbeta/`

- 整理成 佛经 md 文件
  - 把 `sources/cbeta/` 的佛经原文，提取成 md 文件，并存放在 `content/sutras/` ，md要求见下方“佛经 md 文稿规范”
  - 用 opencc 工具，把繁体中文转成简体中文
  - 把 异体字、用字、句式以 CBETA 为先；若极少数字形不适合直接放进 markdown，则改用最常见、最通行的简体写法。
  - 分组和分段：
    - 分组标题必须有实际意义。若某层分组标题没有意义，就删除，不要保留空架子。
    - 主要分节标题若保留序号，统一使用 `一、二、三、...` 这种标点格式。
    - 分段时，不要过长。不要过于稀碎。一次对话，可以作为一个段落。
    - 原文每段不要超过 250 字。
  - 偈语的分段，以 4 句为一段
  - 章节内部优先采用这种结构：`原文` 第 1 段，`现代语译` 第 1 段，`原文` 第 2 段，`现代语译` 第 2 段，依次类推。
  - 标点符号一律使用中文符号。
  - 校验一次 分段 结果是否合适，不合适就要调整。
  - 如果一部经有超过一卷，文件名，统一用数字为后缀，例如01，02...，如果总卷数有100卷，就用001，002…

- 翻译成 `现代语译` ：
  - 一般说的 翻译 ，都是指 翻译成 `现代语译`
  - 必须逐句、逐段翻译。
  - 不得省略重复句、名单、套语、流通分、结尾等内容。
  - 处理佛典时，必须以该经所属的思想体系作为校验框架。若某部经典属于般若系、净土系、法华系、戒律警策类等特定系统，不可用泛泛的佛学常识混答。
  - 若原文段落过大，应拆成更小的原文 / 译文对应段落。
  - `现代语译` 应写成正常段落，不使用 `1. 2. 3.` 这种编号式列表。
  - 咒文 的地方，用这个格式补全下意译：“（意译：）“
  - “如是我闻“ 统一翻译为 “我是这样听佛说的“
  

- 校验评论
  - 分段逻辑，翻译，这些部分会有校验 
  - 校验评论，会以 md 里面的注释格式
  - 但 md 注释不一定全部都是校验评论，检查一下这些注释是否是 校验评论，如果是，则根据 评论 修改，如果不是校验评论，则忽略它
  - 根据校验评论的内容，确定评论的对象是 当前行，还是上一段，还是下一段

- 阅读器与文稿分离原则：
  - markdown 负责语义结构，不负责展示花样。
  - 不要为了显示效果，手工给佛经原文加粗。
  - `原文` 与 `现代语译` 的视觉强调，优先放在 reader 侧自动解析和渲染。

## 佛经 md 文稿规范

- 文稿统一存放在 `content/sutras/` 下，使用 Markdown + front matter。
- 当前正式参考稿：`content/sutras/heart-sutra.md`

### front matter 字段

- `title`: 完整标题
- `short_title`: 页面短标题
- `slug`: 文稿唯一标识
- `volume_label`: 卷别或篇别说明
- `cbeta_source`: 对应的 CBETA 底本文件路径
- `translation_status`: 翻译状态
- `review_status`: 校验状态
- `updated_at`: 最后更新时间
- `summary`: 一句话摘要
- `tags`: 标签，逗号分隔
- `translated_by`: 翻译所使用的 AI 模型名称（如 gpt5, gemini3）

### 正文体例

- front matter 之后，先写一级标题 `# 经名`
- 正文主体使用 `## 一、... / 二、... / 三、...` 这种分节标题
- 每一节内部使用成对的：
  - `### 原文`
  - `### 现代语译`

### 内容取舍补充

- 默认不再使用 `关键词`、`简注`、`文稿说明` 这类区块
- 标题命名要直接反映该段经文的义理重点，不要保留项目式、草稿式标题

### 状态字段约定

- `translation_status`
  - `untranslated`: 未翻译
  - `translating`: 翻译中
  - `translated`: 已翻译
- `review_status`
  - `unreviewed`: 未校验
  - `reviewing`: 校验中
  - `ai_reviewed`: AI已校验
  - `human_reviewed`: 人工已校验

### 文稿处理补充流程

1. 新建文稿时，先写 front matter 与提纲。
2. 逐段补原文、现代语译。
3. 每次提交时更新 `updated_at`。
4. 开始核对时，把 `review_status` 改成 `reviewing`。
5. 完成一轮 AI 辅助检查后，可标记为 `ai_reviewed`。
6. 完成人工复核后，标记为 `human_reviewed`。
7. 若已有 CBETA 底本，先校 `原文`，后校 `现代语译`。
8. 如果原文校到另一条版本线，必须继续重写章节标题与译文，使之重新对应。
9. 每次内容完成后，同步检查 `summary` 是否仍符合当前正式稿内容，而不是项目说明。

### 文稿模板

```md
---
title: 示例经名
short_title: 示例
slug: sample
volume_label: 全一卷
cbeta_source: file://${workspaceFolder}/sources/cbeta/T00n0000_001.xml
translation_status: translating
review_status: unreviewed
updated_at: 2026-03-21
summary: 这里写一行摘要
tags: 入门,示例
translated_by: gpt5
---

# 示例经名

## 导读

导读文本

## 译者(卷二以及以后的卷数，跳过这个部分)

### 原文
作者原文

### 现代语译
白话翻译

## 一、示例分节

### 原文

原文文本

### 现代语译

白话翻译

```

## 禁止黑话式表达

- 回答、翻译、总结、说明时，禁止使用空泛的“黑话”来代替具体内容。
- 少用或禁用这类词：`很直白`、`收得很深`、`说得极稳`、`很干脆`、`很重要`、`很关键`、`很有力量`、`很完整`、`很清楚`、`非常鲜明`、`很像`、`其实是在说`、`归根到底`、`最终指向`、`收束为`、`闭环`、`痛点`、`一句话总结`、`不踩坑`、`稳稳接住`、`砍一刀`、`补一刀` 等。
- 不要写“这一段的意思是……”“这一经很重要”“这其实都在说同一件事”这种评论腔。
- 不要用评价词、方法论词、销售话术、产品黑话，去掩盖没有逐句说明、没有逐段翻译、没有贴着原文处理的问题。
- 如果能直接写事实，就不要写判断。
  - 不写：`这里说得很清楚`
  - 改写为：`这里直接说……`
- 如果能直接写原文含义，就不要写抽象总结。
  - 不写：`这一段其实是在强调无常`
  - 改写为：`这一段逐句说色无常、受无常、想无常、行无常、识无常`
- 如果不能从原文逐句对应推出，就不要自行拔高、升华、概括。
- 结论必须从原文或代码直接落出，不能靠语气词硬撑。
- 发现自己在写“很、非常、其实、核心、本质、收束、闭环、痛点、稳住、说人话就是”这类词时，先删掉，再改成具体事实。


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
