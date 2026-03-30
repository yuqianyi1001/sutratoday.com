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
| **可维护性** | 经文 Markdown 与展示数据的一致性 | **Git-to-DB 自动化流**。脚本自动提取 MD 元数据同步到索引。 |

---

## 3. 系统架构图 (万卷级演进方案)

### 3.1 生产流水线 (GitHub Actions)
1. **Source (Git)**: 所有的 `.md` 存放在 `content/sutras/`。
2. **Build (Scanner)**: 运行 Python/Node 脚本，解析所有 MD 的 Front Matter。
3. **Indexer (Pagefind)**: 对所有正文生成静态搜索索引（分片存储，每片几 KB）。
4. **Metadata**: 生成 `catalog.json` (包含标题、作者、标签、路径等)，用于目录页渲染。

### 3.2 运行环境 (Cloudflare Pages)
- **Static Assets**: HTML, CSS, JS 部署在边缘节点。
- **Sutra Files**: 几万个 `.md` 文件作为静态资源，只有在阅读某卷时才 Fetch。
- **Search API**: 无。搜索由 Pagefind 库在客户端执行，直接从 CDN 抓取对应的索引分片。

---

## 4. 数据库与 Markdown 的维护关系

### 4.1 Markdown 的地位 (Source of Truth)
- 所有的编辑、校对、版本追踪、AI 处理都在 Markdown 文件上进行。
- 它是“真理的唯一来源”，保证数据的透明度与可迁移性。

### 4.2 数据库的作用 (Query Layer)
- **构建期数据库 (SQLite/JSON)**：仅用于加快列表渲染和复杂过滤。
- **全文搜索索引 (Pagefind Index)**：仅用于全文检索。
- **维护逻辑**：每次 Git Commit 触发重新索引，数据库是 Markdown 的“派生视图”，**永远不要手动修改数据库**。

---

## 5. 性能优化策略 (针对万卷规模)

### 5.1 加载策略
- **首页 (Fast Path)**: 仅加载 `site-data.js` 中定义的 12 部精选经目，请求数固定。
- **目录页 (Lazy Path)**: 引入 `catalog.json`，配合 **虚拟列表 (Virtual List)** 或分页加载，避免浏览器渲染成千上万个 DOM 节点。
- **阅读页 (On-Demand)**: 进入阅读页后才请求对应的 `.md` 正文，不预加载正文。

### 5.2 缓存与 CDN
- 利用 Cloudflare 的 `Cache-Control` 对静态索引和 MD 文件进行长效缓存。
- 通过构建时的 `Hash` 文件名（如 `catalog.abcdef123.json`）实现即时更新与完美缓存。

---

## 6. 成本核算 (Cloudflare Free Tier)

- **存储费**: $0 (Cloudflare Pages 无存储限制)。
- **流量费**: $0 (Cloudflare Pages 不计流量)。
- **计算费 (Worker)**: $0 (利用 Pagefind 静态搜索，无需 Workers 算力)。
- **构建时间**: GitHub Actions 每月 2000 分钟免费额度，支持每天多次构建万卷索引。

---

## 7. 后续里程碑
1. [ ] **自动化脚本**: 编写 Python 脚本扫描 `content/` 自动生成 `site-data.js` 的 `documentIndex` 部分。
2. [ ] **集成 Pagefind**: 在 GitHub Actions 中加入 Pagefind 构建步骤。
3. [ ] **UI 分页**: 改造 `catalog.html` 支持上千条目的分页/无限滚动。
4. [ ] **搜索界面**: 在全站顶部增加搜索框，接入 Pagefind 检索接口。
