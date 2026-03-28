import {
  documentIndex,
  escapeHtml,
  formatUpdatedAtBadgeLabel,
  getCatalogDocuments,
  getCatalogVolumeBadgeLabel,
  getFeaturedDocuments,
  getDocumentIndexBySlug,
  getPrimarySample,
  getReaderUrl,
  getReviewState,
  getTranslationState,
  HOME_FEATURED_LIMIT,
  loadDocument,
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
  renderStats(getCatalogDocuments(documentIndex), documentIndex.length);
  renderCatalog(getFeaturedDocuments(documentIndex));
  dom.catalogLead.textContent = `首页仅展示精选的 ${HOME_FEATURED_LIMIT} 部经目。完整目录请进入单独的经文目录页查看。`;
  renderSample(getPrimarySample(documentIndex)).catch((error) => {
    dom.sampleRendered.innerHTML = `<p class="loading-text">加载示例佛经失败：${escapeHtml(error.message)}</p>`;
  });
}

function renderStats(catalogDocs, volumeCount) {
  dom.statWorks.textContent = String(catalogDocs.length);
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

async function renderSample(sample) {
  const selectedMeta = getDocumentIndexBySlug(sample.slug);
  const selected = await loadDocument(selectedMeta.path);
  const translationBadge = getTranslationState(selected.translation_status);
  const reviewBadge = getReviewState(selected.review_status);

  dom.sampleTitle.textContent = selected.title;
  dom.sampleMeta.innerHTML = `
    <span class="badge ${translationBadge.className}">${translationBadge.label}</span>
    <span class="badge ${reviewBadge.className}">${reviewBadge.label}</span>
  `;
  dom.sampleRendered.innerHTML = renderMarkdown(selected.body);
  dom.sampleLink.href = getReaderUrl(selected.slug);
}
