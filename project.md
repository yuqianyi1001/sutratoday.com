# 今文佛典 (SutraToday) 项目架构设计书

## 1. 项目愿景
构建一个高性能、易维护、零成本且支持大规模（万卷级）佛典阅读与搜索的现代化平台。通过 AI 辅助翻译与人工校验，让深奥的经典以清晰、准确的现代语体呈现。

---

## 2. 核心挑战与技术选型
| 维度 | 挑战 | 解决方案 |
| :--- | :--- | :--- |
| **规模化** | 数千部经、数万卷 MD 文件导致浏览器无法全量扫描 | **SSG (静态站点生成) + 预索引**。将文件扫描移至构建期。 |
| **全文搜索** | 纯前端搜索无法承载上亿字，后端服务器成本高 | **Pagefind (静态索引分片)**。构建时生成索引，搜索时按需加载碎片。 |
| **部署成本** | 几万个文件的高频访问与存储费用 | **Cloudflare Pages (免费版)**。利用其无限带宽与边缘节点分发。 |
| **可维护性** | 经文 Markdown 与展示数据的一致性 | **Git-to-Build 自动化流**。脚本自动提取 MD 元数据生成索引，替代手工维护。 |

---

## 3. 系统架构图 (万卷级演进方案)

### 3.1 生产流水线 (GitHub Actions)
```
content/sutras/*.md  (Source of Truth)
        │
        ▼
  [Build: Python 扫描脚本]
  解析所有 MD Front Matter
        │
        ├──▶ catalog.json        # 目录元数据 (标题/标签/状态/路径)
        │      带 Hash 文件名 → Cloudflare 长效缓存
        │
        └──▶ [Pagefind Indexer]
               生成静态搜索索引 (分片存储，每片几 KB)
               存放于 _pagefind/ 目录
```

> **不再手工维护** `site-data.js` 中的 `documentIndex` 与 `documentMetadata`，
> 里程碑 1 完成后由构建脚本完全接管，彻底切换，不允许新旧两套并存。

### 3.2 运行环境 (Cloudflare Pages)
- **Static Assets**: HTML, CSS, JS 部署在边缘节点。
- **Sutra Files**: 各 `.md` 文件按需 Fetch，只有进入阅读页才请求对应正文。
- **Search**: 无后端。Pagefind 在客户端执行，从 CDN 按需拉取对应索引分片。

---

## 4. 数据库与 Markdown 的维护关系

### 4.1 Markdown 是唯一真理来源 (Source of Truth)
- 所有编辑、校对、版本追踪、AI 处理，均在 Markdown 文件上进行。
- 保证数据透明、可迁移，任何工具链更替不会造成数据丢失。

### 4.2 构建产物是派生视图，不可反向编辑
| 产物 | 用途 | 生成时机 |
| :--- | :--- | :--- |
| `catalog.json` | 目录页列表渲染、过滤、排序 | 每次 Git Push 触发构建 |
| `_pagefind/` 索引分片 | 全文检索 | 每次 Git Push 触发构建 |

**原则：永远不要手动修改构建产物。** 若数据有误，改 Markdown，重新构建即可。

---

## 5. 性能优化策略 (针对万卷规模)

### 5.1 三层加载策略
| 页面 | 加载内容 | 请求数 |
| :--- | :--- | :--- |
| **首页** | 12 部精选经目（`site-data.js` 硬编码） | 固定，极快 |
| **目录页** | `catalog.json` + **分页渲染**（每页 50 条） | 1 次 JSON + 按需渲染 |
| **阅读页** | 对应单个 `.md` 正文 | 1 次 Fetch |

> **分页优先于虚拟列表**：虚拟列表实现复杂（需动态行高测量），分页实现简单且 SEO 友好。
> 等规模超过 5000+ 卷、分页体验明显变差时，再评估虚拟列表。

### 5.2 缓存策略
- `catalog.json` 使用构建时生成的 **Hash 文件名**（如 `catalog.a3f2c1.json`），实现即时更新 + 永久缓存。
- Hash 文件名需引入轻量构建工具（Vite 或自定义 Node 脚本）生成并注入 HTML 引用，需在里程碑中明确实现。
- Cloudflare Pages 对静态资源自动设置 `Cache-Control: max-age=31536000`，无需额外配置。
- MD 正文文件名本身含 slug，内容变更时 slug 不变，依赖 CDN 短 TTL（1 小时）缓存即可。

### 5.3 Pagefind 中文搜索注意事项
- Pagefind 1.x 版本已改善中文分词支持，当前规模（百卷级）无问题。
- 预计 5000+ 卷、上亿字时，索引分片数量增多，首次搜索需下载的 fragment 会上升，届时需实测并考虑：
  - 限制搜索结果数量（`pageSize`）
  - 为高频词预热索引分片（Service Worker 预取）

---

## 6. 成本核算 (Cloudflare Free Tier)

| 项目 | 费用 |
| :--- | :--- |
| 存储 | $0 (Cloudflare Pages 无存储限制) |
| 流量 | $0 (Cloudflare Pages 不计流量) |
| 计算 (Worker) | $0 (Pagefind 静态搜索，无需 Workers) |
| 构建时间 | GitHub Actions 每月 2000 分钟免费，支持每天多次构建万卷索引 |

---

## 7. 后续里程碑

### 阶段一：自动化基础（解除手工维护依赖）
- [ ] **构建脚本**：编写 Python 脚本扫描 `content/sutras/`，自动提取 Front Matter，生成 `catalog.json`。
- [ ] **切换目录页**：`catalog.html` 改为从 `catalog.json` 加载，**同步删除** `site-data.js` 中手工维护的 `documentIndex` / `documentMetadata` 区块，不允许两套并存。
- [ ] **GitHub Actions 集成**：Push 时自动运行构建脚本，产物提交或直接部署。

### 阶段二：全文搜索
- [ ] **集成 Pagefind**：在 GitHub Actions 构建步骤中加入 `pagefind --site .` 生成索引。
- [ ] **搜索界面**：全站顶部增加搜索框，接入 Pagefind JS API，支持简繁字转换后搜索。

### 阶段三：目录页规模化
- [ ] **分页加载**：`catalog.html` 支持上千条目的分页（每页 50 条）或无限滚动。
- [ ] **过滤与排序**：按翻译状态、审校状态、部类（阿含/大乘/律）过滤。

### 阶段四：缓存与构建工具
- [ ] **Hash 文件名**：引入 Vite 或自定义脚本，为 `catalog.json` 生成带 Hash 的文件名并注入 HTML。
- [ ] **Service Worker**（可选）：预取高频经目 MD 文件，支持离线阅读。
