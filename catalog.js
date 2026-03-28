import {
  escapeHtml,
  formatUpdatedAtBadgeLabel,
  getCatalogDocuments,
  getCatalogVolumeBadgeLabel,
  getReaderUrl,
  getReviewState,
  getTranslationState,
  loadDocuments,
} from "./site-data.js";

const dom = {
  catalogGrid: document.getElementById("catalog-grid"),
  lead: document.getElementById("catalog-page-lead"),
};

init().catch((error) => {
  dom.catalogGrid.innerHTML = `<p class="loading-text">读取失败：${escapeHtml(error.message)}</p>`;
});

async function init() {
  const documents = await loadDocuments();
  const catalogDocuments = getCatalogDocuments(documents);
  dom.lead.textContent = `当前共整理 ${catalogDocuments.length} 部佛典，共 ${documents.length} 卷。点击任一条目即可进入阅读页。`;
  renderCatalog(sortCatalogDocuments(catalogDocuments));
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

function sortCatalogDocuments(docs) {
  return [...docs].sort((a, b) => {
    const rankDiff = getCatalogRank(a) - getCatalogRank(b);
    if (rankDiff !== 0) {
      return rankDiff;
    }
    return a.title.localeCompare(b.title, "zh-Hans-CN");
  });
}

function getCatalogRank(doc) {
  if (doc.review_status === "human_reviewed") {
    return 0;
  }
  if (doc.review_status === "ai_reviewed") {
    return 1;
  }
  if (doc.translation_status === "translated") {
    return 2;
  }
  return 3;
}
