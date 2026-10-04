# 当前任务看板

只记三类内容：进行中的任务、下一批待分配的任务、需要 Jeff 决定的事。完成后删除对应行，历史看 git。
各经的数字进度见 `docs/STATUS.md`（`python3 scripts/status_report.py` 生成）。规范检查：`python3 scripts/check_frontmatter.py`。协作规则见 `AGENTS.md` 的「多 AI 协作」一节。

## 进行中

| 任务 | 负责 | 分支 / PR |
| --- | --- | --- |
| 规范与文件整理，状态汇总与检查脚本（PR #57） | Claude（总管） | `claude/multi-ai-docs-workflow-lp0zko` |

## 下一批待分配

1. 补译空的 `### 現代語譯` 块：2057 个文稿里共 5382 个（2026-10-04 统计）。先出清单，按经号分给各 AI，一个 AI 一批；补不完的文稿把 `translation_status` 降回 `translating`。
2. 处理 `docs/review-notes/` 里的待复核项。

## 需要 Jeff 决定

- 14 个文稿（T0221 六卷、T0223 六卷、T1925-001、X0454-001）没有 `ai_translator`，不知道是哪个模型翻的，没有擅自填写。
- 4 个文稿同时有 `translated_by` 和 `ai_translator` 且值不同：T0007-001、T0007-002、T0007-003、T0020-001（`translated_by` 都是 gemini3，`ai_translator` 是 gemini-3 或 deepseek-v3.2），已保留 `ai_translator`，删掉 `translated_by`。
- X0227-001、X0587-001 的 `ai_translator` 是工具名 `opencode`，不是模型名。
