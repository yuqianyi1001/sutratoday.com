# 当前任务看板

只记三类内容：进行中的任务、下一批待分配的任务、需要 Jeff 决定的事。完成后删除对应行，历史看 git。
各经的数字进度见 `docs/STATUS.md`（`python3 scripts/status_report.py` 生成）。规范检查：`python3 scripts/check_frontmatter.py`。协作规则见 `AGENTS.md` 的「多 AI 协作」一节。

## 进行中

暂无。

## 下一批待分配

1. 处理 `docs/review-notes/` 里的待复核项，其中 `2026-10-04-fill-empty-blocks.md` 是 2026-10-04 补译 5381 个空译文块时各批译者标出的疑点（共约 440 条），开头列了需要先看的几类。
2. AI 校验：10241 卷 `unreviewed`（含 2056 卷刚补完空块的文稿），按经分批，翻译者和校验者用不同的模型。

## 已决定（备忘）

- 14 个没有 `ai_translator` 的文稿（T0221 六卷、T0223 六卷、T1925-001、X0454-001）：继续留空，不填；`check_frontmatter.py` 会把它们列出来，属已知情况。
- T0007-002、T0007-003、T0020-001 原来 `ai_translator` 是 deepseek-v3.2、`translated_by` 是 gemini3，合并写成 `deepseek-v3.2+gemini-3`；T0007-001 两个值本来相同，保持 `gemini-3`。
- X0227-001、X0587-001 的 `ai_translator` 保留 `opencode`。

## 需要 Jeff 决定

- 译文里引号写法是否统一（见对话里的统计）。
