# AGENTS

## 佛典工作流

- 状态流转
  - 开始 -> 找到佛经原文 -> 把佛经原文整理成md file -> 校验分组、分段的合理性  -> 分段已校验(segments_reviewed) -> (接下面)
  - 翻译成 `现代语译` -> translated -> 翻译校验 -> ai_reviewed -> 人工校验 -> human_reviewed

- 添加和处理一个佛经时，先找到佛经原本，并保存一份在本地。如果有多个版本，找到最通用的版本：
  - 优先查找本地：~/Downloads/bookcase_v090_20231219
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
  - 校验一次 分段 结果是否合适，不合适就要调整。

- 翻译成 `现代语译` ：
  - 一般说的 翻译 ，都是指 翻译成 `现代语译`
  - 必须逐句、逐段翻译。
  - 不得省略重复句、名单、套语、流通分、结尾等内容。
  - 处理佛典时，必须以该经所属的思想体系作为校验框架。若某部经典属于般若系、净土系、法华系、戒律警策类等特定系统，不可用泛泛的佛学常识混答。
  - 若原文段落过大，应拆成更小的原文 / 译文对应段落。
  - 章节内部优先采用这种结构：`原文` 第 1 段，`现代语译` 第 1 段，`原文` 第 2 段，`现代语译` 第 2 段，依次类推。
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
- `progress_percent`: 当前进度，0-100
- `updated_at`: 最后更新时间
- `summary`: 一句话摘要
- `tags`: 标签，逗号分隔

### 正文体例

- front matter 之后，先写一级标题 `# 经名`
- 正文主体使用 `## 一、... / 二、... / 三、...` 这种分节标题
- 每一节内部使用成对的：
  - `### 原文`
  - `### 现代语译`
- 末尾可加 `## 全篇总意`，用于对整篇义旨做简洁收束

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
3. 每次提交时更新 `progress_percent` 与 `updated_at`。
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
cbeta_source: sources/cbeta/T00n0000_001.xml
translation_status: translating
review_status: unreviewed
progress_percent: 20
updated_at: 2026-03-21
summary: 这里写一行摘要
tags: 入门,示例
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

## Git

- 推送远端时，使用 `--no-verify` 跳过 push hooks。例如：`git push --no-verify parent main`
- 当用户要求提交并推送时，除非另有说明，否则默认按以下顺序执行：
  - `git add ...`
  - 如果需要提交，执行 `git commit --no-verify -m "..."`
  - 然后执行 `git push --no-verify parent main`
