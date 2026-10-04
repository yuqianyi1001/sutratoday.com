# 当前任务看板

只记三类内容：进行中的任务、下一批待分配的任务、需要 Jeff 决定的事。完成后删除对应行，历史看 git。
各经的数字进度见 `docs/STATUS.md`（`python3 scripts/status_report.py` 生成）。规范检查：`python3 scripts/check_frontmatter.py`。协作规则见 `AGENTS.md` 的「多 AI 协作」一节。

## 进行中

暂无。

## 下一批待分配

1. 处理 `docs/review-notes/` 里的待复核项。`2026-10-04-fill-empty-blocks.md` 开头那几类已处理（T1646-016、X0595-002、X0608-006 三处底本断句待对照 CBETA 网页，T0152 的套语写法待校验时统一）；该文件第 1 批以后约 440 条是各批译者标出的字句疑点，要等校验时逐条看。
2. AI 校验：10241 卷 `unreviewed`（含 2056 卷刚补完空块的文稿），按经分批，翻译者和校验者用不同的模型。

## 已决定（备忘）

- 14 个没有 `ai_translator` 的文稿（T0221 六卷、T0223 六卷、T1925-001、X0454-001）：继续留空，不填；`check_frontmatter.py` 会把它们列出来，属已知情况。
- T0007-002、T0007-003、T0020-001 原来 `ai_translator` 是 deepseek-v3.2、`translated_by` 是 gemini3，合并写成 `deepseek-v3.2+gemini-3`；T0007-001 两个值本来相同，保持 `gemini-3`。
- X0227-001、X0587-001 的 `ai_translator` 保留 `opencode`。
- 引号：文稿统一用 CBETA 的「」『』，网页简体显示换成“”‘’（`scripts/normalize_quotes.py`）。

## 需要 Jeff 决定

暂无。
