# 当前任务看板

只记三类内容：进行中的任务、下一批待分配的任务、需要 Jeff 决定的事。完成后删除对应行，历史看 git。
各经的数字进度见 `docs/STATUS.md`（脚本生成，尚未建立）。协作规则见 `AGENTS.md` 的「多 AI 协作」一节。

## 进行中

| 任务 | 负责 | 分支 / PR |
| --- | --- | --- |
| 规范与文件整理（第一个 PR） | Claude（总管） | `claude/multi-ai-docs-workflow-lp0zko` |

## 下一批待分配

1. 加脚本：`scripts/status_report.py`（生成 `docs/STATUS.md`）、front matter 检查脚本。
2. 统一 front matter：`translated_by` 改 `ai_translator`，非规范的 `review_status` 值并入 `ai_reviewed`；只改 front matter。
3. 补译空的 `### 現代語譯` 块：2057 个文稿里共 5382 个（2026-10-04 统计）。先出清单，按经号分给各 AI，一个 AI 一批；补不完的文稿把 `translation_status` 降回 `translating`。
4. 处理 `docs/review-notes/` 里的待复核项。

## 需要 Jeff 决定

- 暂无。
