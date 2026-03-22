import {
  escapeHtml,
  getFeaturedDocuments,
  getDocumentBySlug,
  getPrimarySample,
  getReviewState,
  getTranslationState,
  HOME_FEATURED_LIMIT,
  loadDocuments,
  renderMarkdown,
} from "./site-data.js";

const dom = {
  catalogGrid: document.getElementById("catalog-grid"),
  statUntranslated: document.getElementById("stat-untranslated"),
  statTranslating: document.getElementById("stat-translating"),
  statTranslated: document.getElementById("stat-translated"),
  statUnreviewed: document.getElementById("stat-unreviewed"),
  statReviewing: document.getElementById("stat-reviewing"),
  statAiReviewed: document.getElementById("stat-ai-reviewed"),
  statHumanReviewed: document.getElementById("stat-human-reviewed"),
  catalogLead: document.getElementById("catalog-lead"),
  sampleTitle: document.getElementById("sample-title"),
  sampleMeta: document.getElementById("sample-meta"),
  sampleRendered: document.getElementById("sample-rendered"),
  sampleLink: document.getElementById("sample-link"),
};

init().catch((error) => {
  dom.catalogGrid.innerHTML = `<p class="loading-text">读取失败：${escapeHtml(error.message)}</p>`;
  dom.sampleRendered.innerHTML = `<p class="loading-text">请通过站点地址访问本页，避免直接打开本地文件。</p>`;
});

async function init() {
  const documents = await loadDocuments();
  renderStats(documents);
  renderCatalog(getFeaturedDocuments(documents));
  renderSample(getPrimarySample(documents));
  dom.catalogLead.textContent = `首页仅展示精选的 ${HOME_FEATURED_LIMIT} 部经目。完整目录请进入单独的经文目录页查看。`;
}

function renderStats(docs) {
  dom.statUntranslated.textContent = String(docs.filter((doc) => doc.translation_status === "untranslated").length);
  dom.statTranslating.textContent = String(docs.filter((doc) => doc.translation_status === "translating").length);
  dom.statTranslated.textContent = String(docs.filter((doc) => doc.translation_status === "translated").length);
  dom.statUnreviewed.textContent = String(docs.filter((doc) => doc.review_status === "unreviewed").length);
  dom.statReviewing.textContent = String(docs.filter((doc) => doc.review_status === "reviewing").length);
  dom.statAiReviewed.textContent = String(docs.filter((doc) => doc.review_status === "ai_reviewed").length);
  dom.statHumanReviewed.textContent = String(docs.filter((doc) => doc.review_status === "human_reviewed").length);
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
          <a class="catalog-open" href="./reader.html#doc=${encodeURIComponent(doc.slug)}">进入阅读页</a>
        </article>
      `;
    })
    .join("");
}

function renderSample(sample) {
  const selected = getDocumentBySlug(sample.slug);
  const translationBadge = getTranslationState(selected.translation_status);
  const reviewBadge = getReviewState(selected.review_status);

  dom.sampleTitle.textContent = selected.title;
  dom.sampleMeta.innerHTML = `
    <span class="badge ${translationBadge.className}">${translationBadge.label}</span>
    <span class="badge ${reviewBadge.className}">${reviewBadge.label}</span>
  `;
  dom.sampleRendered.innerHTML = renderMarkdown(extractSampleExcerpt(selected.body));
  dom.sampleLink.href = `./reader.html#doc=${encodeURIComponent(selected.slug)}`;
}

function extractSampleExcerpt(body) {
  const sections = body.split("\n## ");
  return sections.slice(0, 3).join(sections.length > 1 ? "\n## " : "");
}
