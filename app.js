import {
  documentIndex,
  escapeHtml,
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
  statTranslated: document.getElementById("stat-translated"),
  statAiReviewed: document.getElementById("stat-ai-reviewed"),
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
  renderStats(documentIndex);
  renderCatalog(getFeaturedDocuments(documentIndex));
  dom.catalogLead.textContent = `首页仅展示精选的 ${HOME_FEATURED_LIMIT} 部经目。完整目录请进入单独的经文目录页查看。`;
  renderSample(getPrimarySample(documentIndex)).catch((error) => {
    dom.sampleRendered.innerHTML = `<p class="loading-text">加载示例佛经失败：${escapeHtml(error.message)}</p>`;
  });
}

function renderStats(docs) {
  dom.statTranslated.textContent = String(docs.filter((doc) => doc.translation_status === "translated").length);
  dom.statAiReviewed.textContent = String(docs.filter((doc) => doc.review_status === "ai_reviewed").length);
}

function renderCatalog(docs) {
  dom.catalogGrid.innerHTML = docs
    .map((doc) => {
      const translationBadge = getTranslationState(doc.translation_status);
      const reviewBadge = getReviewState(doc.review_status);

      return `
        <article class="catalog-card">
          <div class="catalog-top">
            <div class="catalog-title-wrap">
              <p>${escapeHtml(doc.volume_label || "单篇")}</p>
              <h3>${escapeHtml(doc.short_title || doc.title)}</h3>
            </div>
            <span class="badge ${translationBadge.className}">${translationBadge.label}</span>
          </div>
          <p class="catalog-summary">${escapeHtml(doc.summary || "暂无摘要。")}</p>
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
