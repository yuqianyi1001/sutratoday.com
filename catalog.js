import {
  escapeHtml,
  formatUpdatedAtBadgeLabel,
  getCatalogVolumeBadgeLabel,
  getReaderUrl,
  getReviewState,
  getTranslationState,
  loadWorksIndex,
} from "./site-data.js";

const PAGE_SIZE = 50;

const dom = {
  catalogGrid: document.getElementById("catalog-grid"),
  lead: document.getElementById("catalog-page-lead"),
  searchInput: document.getElementById("catalog-search-input"),
  loadMoreWrap: document.getElementById("catalog-load-more-wrap"),
  loadMoreBtn: document.getElementById("catalog-load-more"),
};

let allWorks = [];
let filteredWorks = [];
let displayedCount = 0;
let s2tConverter = null;

init().catch((error) => {
  dom.catalogGrid.innerHTML = `<p class="loading-text">读取失败：${escapeHtml(error.message)}</p>`;
});

async function init() {
  // Initialize OpenCC simplified→traditional converter for search
  try {
    const openCC = window.OpenCC || null;
    if (openCC && openCC.Converter) {
      s2tConverter = openCC.Converter({ from: "cn", to: "tw" });
    }
  } catch (_) {
    // OpenCC not available, search will use original input only
  }

  const index = await loadWorksIndex();
  allWorks = sortWorks(index.works);
  filteredWorks = allWorks;

  updateLead(index.stats.workCount, index.stats.volumeCount);
  dom.catalogGrid.innerHTML = "";
  displayedCount = 0;
  showMore();

  dom.searchInput.addEventListener("input", onSearchInput);
  dom.loadMoreBtn.addEventListener("click", showMore);
}

function onSearchInput() {
  const raw = dom.searchInput.value.trim();
  if (!raw) {
    filteredWorks = allWorks;
  } else {
    const queries = [raw.toLowerCase()];
    // Convert simplified to traditional for matching
    if (s2tConverter) {
      const traditional = s2tConverter(raw);
      if (traditional !== raw) {
        queries.push(traditional.toLowerCase());
      }
    }
    filteredWorks = allWorks.filter((work) => {
      const title = (work.title || "").toLowerCase();
      const shortTitle = (work.short_title || "").toLowerCase();
      const cbetaId = (work.cbeta_id || "").toLowerCase();
      return queries.some((q) => title.includes(q) || shortTitle.includes(q) || cbetaId.includes(q));
    });
  }

  const totalVolumes = filteredWorks.reduce((sum, w) => sum + (w.juan_total || 1), 0);
  updateLead(filteredWorks.length, totalVolumes, !!raw);
  displayedCount = 0;
  dom.catalogGrid.innerHTML = "";
  showMore();
}

function showMore() {
  const nextBatch = filteredWorks.slice(displayedCount, displayedCount + PAGE_SIZE);
  if (nextBatch.length === 0 && displayedCount === 0) {
    dom.catalogGrid.innerHTML = `<p class="loading-text">未找到匹配的经文。</p>`;
    dom.loadMoreWrap.hidden = true;
    return;
  }

  dom.catalogGrid.insertAdjacentHTML("beforeend", renderCards(nextBatch));
  displayedCount += nextBatch.length;

  const hasMore = displayedCount < filteredWorks.length;
  dom.loadMoreWrap.hidden = !hasMore;
  if (hasMore) {
    dom.loadMoreBtn.textContent = `加载更多（已显示 ${displayedCount} / ${filteredWorks.length}）`;
  }
}

function updateLead(workCount, volumeCount, isSearching = false) {
  if (isSearching) {
    dom.lead.textContent = `搜索结果：共 ${workCount} 部佛典，共 ${volumeCount} 卷。`;
  } else {
    dom.lead.textContent = `当前共整理 ${workCount} 部佛典，共 ${volumeCount} 卷。点击任一条目即可进入阅读页。`;
  }
}

function renderCards(works) {
  return works
    .map((work) => {
      const volumeLabel = getCatalogVolumeBadgeLabel(work);
      const translationBadge = getTranslationState(work.translation_status);
      const reviewBadge = getReviewState(work.review_status);
      const displayTitle = work.short_title || work.title;
      const readerSlug = work.first_slug || work.cbeta_id;

      return `
        <article class="catalog-card">
          <div class="catalog-top">
            <div class="catalog-title-wrap">
              <h3>${escapeHtml(displayTitle)}</h3>
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

function sortWorks(works) {
  return [...works].sort((a, b) => {
    const rankDiff = getCatalogRank(a) - getCatalogRank(b);
    if (rankDiff !== 0) return rankDiff;
    return a.cbeta_id.localeCompare(b.cbeta_id);
  });
}

function getCatalogRank(work) {
  if (work.review_status === "human_reviewed") return 0;
  if (work.review_status === "ai_reviewed") return 1;
  if (work.translation_status === "translated") return 2;
  return 3;
}
