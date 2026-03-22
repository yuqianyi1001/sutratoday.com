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

### 原文

### 现代语译

```
