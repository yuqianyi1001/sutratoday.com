import {
  escapeHtml,
  formatUpdatedAtBadgeLabel,
  getCatalogVolumeBadgeLabel,
  getEstimatedWorkCount,
  getManifestVolumeCount,
  getReaderUrl,
  getReviewState,
  getTranslationState,
  HOME_FEATURED_WORK_IDS,
  loadDocument,
  loadFeaturedDocuments,
  renderMarkdown,
} from "./site-data.js";

const dom = {
  catalogGrid: document.getElementById("catalog-grid"),
  statWorks: document.getElementById("stat-works"),
  statVolumes: document.getElementById("stat-volumes"),
  catalogLead: document.getElementById("catalog-lead"),
  sampleTitle: document.getElementById("sample-title"),
  sampleMeta: document.getElementById("sample-meta"),
  sampleRendered: document.getElementById("sample-rendered"),
  sampleLink: document.getElementById("sample-link"),
};

init().catch((error) => {
  dom.catalogGrid.innerHTML = `<p class="loading-text">读取失败：${escapeHtml(error.message)}</p>`;
  dom.sampleRendered.innerHTML = `<p class="loading-text">加载示例佛经失败：${escapeHtml(error.message)}</p>`;
});

async function init() {
  // 1. 立即渲染统计数据，无需加载文件
  renderStats(getEstimatedWorkCount(), getManifestVolumeCount());

  // 2. 仅加载首页展示所需的 11 部经目
  const featuredDocuments = await loadFeaturedDocuments();
  renderCatalog(featuredDocuments);

  dom.catalogLead.textContent = `首页固定展示 ${HOME_FEATURED_WORK_IDS.length} 部精选经目。完整目录请进入单独的经文目录页查看。`;

  // 3. 单独加载示例经文（心经）
  renderSampleBySlug("heart-sutra").catch((error) => {
    dom.sampleRendered.innerHTML = `<p class="loading-text">加载示例佛经失败：${escapeHtml(error.message)}</p>`;
  });
}

function renderStats(workCount, volumeCount) {
  dom.statWorks.textContent = String(workCount);
  dom.statVolumes.textContent = String(volumeCount);
}

function renderCatalog(docs) {
  dom.catalogGrid.innerHTML = docs
    .map((doc) => {
      const volumeLabel = getCatalogVolumeBadgeLabel(doc);
      const translationBadge = getTranslationState(doc.translation_status);
      const reviewBadge = getReviewState(doc.review_status);

      return `
        <article class="catalog-card">
          <div class="catalog-top">
            <div class="catalog-title-wrap">
              <h3>${escapeHtml(doc.short_title || doc.title)}</h3>
            </div>
            <div class="badge-row catalog-badge-row">
              <span class="badge badge-muted">${escapeHtml(volumeLabel)}</span>
              <span class="badge ${translationBadge.className}">${translationBadge.label}</span>
              <span class="badge ${reviewBadge.className}">${reviewBadge.label}</span>
              <span class="badge badge-muted">${escapeHtml(formatUpdatedAtBadgeLabel(doc.updated_at))}</span>
            </div>
          </div>
          <p class="catalog-summary">${escapeHtml(doc.summary || "暂无摘要。")}</p>
          <a class="catalog-open" href="${getReaderUrl(doc.slug)}">进入阅读页</a>
        </article>
      `;
    })
    .join("");
}

async function renderSampleBySlug(slug) {
  // 查找对应的路径并加载
  const path = "content/sutras/heart-sutra.md";
  const selected = await loadDocument(path);
  
  const translationBadge = getTranslationState(selected.translation_status || "translated");
  const reviewBadge = getReviewState(selected.review_status || "ai_reviewed");

  dom.sampleTitle.textContent = selected.title || "般若波罗蜜多心经";
  dom.sampleMeta.innerHTML = `
    <span class="badge ${translationBadge.className}">${translationBadge.label}</span>
    <span class="badge ${reviewBadge.className}">${reviewBadge.label}</span>
  `;
  dom.sampleRendered.innerHTML = renderMarkdown(selected.body);
  dom.sampleLink.href = getReaderUrl(slug);
}
