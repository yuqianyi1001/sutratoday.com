import {
  escapeHtml,
  formatUpdatedAtBadgeLabel,
  getCatalogVolumeBadgeLabel,
  getReaderUrl,
  getReviewState,
  getTranslationState,
  getVolumeSlugPath,
  HOME_FEATURED_WORK_IDS,
  loadDocument,
  loadFeaturedWorks,
  loadWorksIndex,
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
  // 1. Load index for stats
  const indexPromise = loadWorksIndex();

  // 2. Load featured works and render catalog
  const featuredPromise = loadFeaturedWorks();

  // 3. Load sample sutra (Heart Sutra = T0251-001)
  const samplePromise = loadDocument(getVolumeSlugPath("T0251-001")).catch((error) => {
    dom.sampleRendered.innerHTML = `<p class="loading-text">加载示例佛经失败：${escapeHtml(error.message)}</p>`;
    return null;
  });

  const [index, featuredWorks, sampleDoc] = await Promise.all([indexPromise, featuredPromise, samplePromise]);

  // Render stats
  dom.statWorks.textContent = String(index.stats.workCount);
  dom.statVolumes.textContent = String(index.stats.volumeCount);

  // Render featured catalog
  renderCatalog(featuredWorks);
  dom.catalogLead.textContent = `首页固定展示 ${HOME_FEATURED_WORK_IDS.length} 部精选经目。完整目录请进入单独的经文目录页查看。`;

  // Render sample
  if (sampleDoc) {
    renderSample(sampleDoc);
  }
}

function renderCatalog(works) {
  dom.catalogGrid.innerHTML = works
    .map((work) => {
      const volumeLabel = getCatalogVolumeBadgeLabel(work);
      const translationBadge = getTranslationState(work.translation_status);
      const reviewBadge = getReviewState(work.review_status);
      const readerSlug = work.first_slug || work.cbeta_id;

      return `
        <article class="catalog-card">
          <div class="catalog-top">
            <div class="catalog-title-wrap">
              <h3>${escapeHtml(work.short_title || work.title)}</h3>
            </div>
            <div class="badge-row catalog-badge-row">
              <span class="badge badge-muted">${escapeHtml(volumeLabel)}</span>
              <span class="badge ${translationBadge.className}">${translationBadge.label}</span>
              <span class="badge ${reviewBadge.className}">${reviewBadge.label}</span>
              <span class="badge badge-muted">${escapeHtml(formatUpdatedAtBadgeLabel(work.updated_at))}</span>
            </div>
          </div>
          <p class="catalog-summary">${escapeHtml(work.category || "")}${work.translator ? " · " + escapeHtml(work.translator) : ""}</p>
          <a class="catalog-open" href="${getReaderUrl(readerSlug)}">进入阅读页</a>
        </article>
      `;
    })
    .join("");
}

function renderSample(doc) {
  const translationBadge = getTranslationState(doc.translation_status || "translated");
  const reviewBadge = getReviewState(doc.review_status || "unreviewed");

  dom.sampleTitle.textContent = doc.title || "般若波罗蜜多心经";
  dom.sampleMeta.innerHTML = `
    <span class="badge ${translationBadge.className}">${translationBadge.label}</span>
    <span class="badge ${reviewBadge.className}">${reviewBadge.label}</span>
  `;
  dom.sampleRendered.innerHTML = renderMarkdown(doc.body);
  dom.sampleLink.href = getReaderUrl("T0251-001");
}
