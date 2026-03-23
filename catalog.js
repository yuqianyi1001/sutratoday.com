import { escapeHtml, getCatalogDocuments, getReaderUrl, getReviewState, getTranslationState, loadDocuments } from "./site-data.js";

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
  dom.lead.textContent = `当前共整理共 ${catalogDocuments.length} 部佛典，共 ${documents.length} 卷。点击任一条目即可进入阅读页。`;
  renderCatalog(sortCatalogDocuments(catalogDocuments));
}

function renderCatalog(docs) {
  dom.catalogGrid.innerHTML = docs
    .map((doc) => {
      const translationBadge = getTranslationState(doc.translation_status);
      const reviewBadge = getReviewState(doc.review_status);
      const isMultiVolumeWork = Boolean(doc.work_id && /^共\d+卷$/.test(doc.volume_label || ""));
      const displayVolumeLabel = isMultiVolumeWork ? doc.volume_label.replace(/^共/, "全") : doc.volume_label || "单篇";
      const titleMarkup = isMultiVolumeWork
        ? `<h3>${escapeHtml(doc.short_title || doc.title)} <span class="catalog-title-suffix">${escapeHtml(displayVolumeLabel)}</span></h3>`
        : `<p>${escapeHtml(displayVolumeLabel)}</p><h3>${escapeHtml(doc.short_title || doc.title)}</h3>`;

      return `
        <article class="catalog-card">
          <div class="catalog-top">
            <div class="catalog-title-wrap">
              ${titleMarkup}
            </div>
            <span class="badge ${translationBadge.className}">${translationBadge.label}</span>
          </div>
          <p>${escapeHtml(doc.summary || "暂无摘要。")}</p>
          <div class="badge-row">
            <span class="badge ${reviewBadge.className}">${reviewBadge.label}</span>
          </div>
          <div class="progress-track" aria-label="进度">
            <span class="progress-bar" style="width: ${Math.max(0, Math.min(100, Number(doc.progress_percent) || 0))}%"></span>
          </div>
          <div class="catalog-meta">
            <span>进度 ${escapeHtml(String(doc.progress_percent || 0))}%</span>
            <span>${escapeHtml(doc.updated_at || "未标注日期")}</span>
          </div>
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
