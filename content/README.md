# 今文佛典内容目录说明

所有文稿原始稿都放在 `content/sutras/` 下，并使用 Markdown + front matter。

## front matter 字段

- `title`: 完整标题
- `short_title`: 页面短标题
- `slug`: 文稿唯一标识
- `volume_label`: 卷别或篇别说明
- `translation_status`: 翻译状态
- `review_status`: 校验状态
- `progress_percent`: 当前进度，0-100
- `updated_at`: 最后更新时间
- `summary`: 一句话摘要
- `tags`: 标签，逗号分隔

## 当前文稿体例

以 [`/Users/j.wu/ws/codex_anything/content/sutras/heart-sutra.md`]( /Users/j.wu/ws/codex_anything/content/sutras/heart-sutra.md ) 为当前正式参考稿。

- front matter 之后，先写一级标题 `# 经名`
- 标题下可接一段导语，使用 Markdown 引用块 `>`
- 正文主体使用 `## 一、... / 二、... / 三、...` 这种分节标题
- 每一节内部使用成对的：
  - `### 原文`
  - `### 现代语译`
- 末尾可加 `## 全篇总意`，用于对整篇义旨做简洁收束

## 原文与译文规范

- `原文` 以 CBETA 等底本校对，但在 md 中保持简体中文
- `现代语译` 必须逐句、逐段对应原文，不可省略名单、套语、重复句和结尾
- 若某段原文过长，应拆成更小的原文 / 译文对应段落
- `现代语译` 一律写成正常段落，不使用 `1. 2. 3.` 编号列表
- 语义结构放在 markdown 中，展示效果交给 reader；不要为了显示效果手工给原文整段加粗

## 内容取舍规范

- 默认不再使用 `关键词`、`简注`、`文稿说明` 这类区块
- 分组标题必须有实际意义；没有意义的分组应删除
- 标题命名要直接反映该段经文的义理重点，不要保留项目式、草稿式标题

## translation_status 约定

- `untranslated`: 未翻译
- `translating`: 翻译中
- `translated`: 已翻译

## review_status 约定

- `unreviewed`: 未校验
- `reviewing`: 校验中
- `ai_reviewed`: AI已校验
- `human_reviewed`: 人工已校验

## 建议流程

1. 新建文稿时，先写 front matter 与提纲。
2. 逐段补原文、现代语译。
3. 每次提交时更新 `progress_percent` 与 `updated_at`。
4. 开始核对时，把 `review_status` 改成 `reviewing`。
5. 完成一轮 AI 辅助检查后，可标记为 `ai_reviewed`。
6. 完成人工复核后，标记为 `human_reviewed`。

## 建议流程补充

1. 若已有 CBETA 底本，先校 `原文`，后校 `现代语译`。
2. 如果原文校到另一条版本线，必须继续重写章节标题与译文，使之重新对应。
3. 每次内容完成后，同步检查 `summary` 是否仍符合当前正式稿内容，而不是项目说明。

## 建议模板

```md
---
title: 示例经名
short_title: 示例
slug: sample
volume_label: 全一卷
translation_status: translating
review_status: unreviewed
progress_percent: 20
updated_at: 2026-03-21
summary: 这里写一行摘要
tags: 入门,示例
---

# 示例经名

> 这里写一段简短导语。

## 一、示例分节

### 原文

### 现代语译

## 全篇总意

```
