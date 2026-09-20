import {
  escapeHtml,
  formatUpdatedAtBadgeLabel,
  getCatalogVolumeBadgeLabel,
  getReaderUrl,
  getReviewState,
  getTranslationState,
  loadWorksIndex,
} from "./site-data.js";
import { mountResumeBanner } from "./reading-progress.js?v=4";

mountResumeBanner();

const PAGE_SIZE = 50;

const dom = {
  catalogGrid: document.getElementById("catalog-grid"),
  lead: document.getElementById("catalog-page-lead"),
  searchInput: document.getElementById("catalog-search-input"),
  loadMoreWrap: document.getElementById("catalog-load-more-wrap"),
  loadMoreBtn: document.getElementById("catalog-load-more"),
  originFilters: document.getElementById("filter-origin"),
  genreFilters: document.getElementById("filter-genre"),
  doctrineFilters: document.getElementById("filter-doctrine"),
  breadcrumb: document.getElementById("catalog-breadcrumb"),
  clearFilters: document.getElementById("catalog-clear-filters"),
};

let allWorks = [];
let filteredWorks = [];
let displayedCount = 0;
let s2tConverter = null;
let taxonomy = { origins: [], genres: [], doctrines: [] };

const filters = {
  origin: "",
  genre: "",
  doctrine: "",
  query: "",
};

const labelMaps = {
  origin: new Map(),
  genre: new Map(),
  doctrine: new Map(),
};

init().catch((error) => {
  dom.catalogGrid.innerHTML = `<p class="loading-text">读取失败：${escapeHtml(error.message)}</p>`;
});

async function init() {
  try {
    const openCC = window.OpenCC || null;
    if (openCC && openCC.Converter) {
      s2tConverter = openCC.Converter({ from: "cn", to: "tw" });
    }
  } catch (_) {
    // OpenCC not available
  }

  const index = await loadWorksIndex();
  taxonomy = index.taxonomy || taxonomy;
  buildLabelMaps();
  allWorks = sortWorks(index.works);
  readFiltersFromUrl();

  dom.searchInput.value = filters.query;
  dom.searchInput.addEventListener("input", onSearchInput);
  dom.loadMoreBtn.addEventListener("click", showMore);
  dom.clearFilters.addEventListener("click", clearAllFilters);
  dom.originFilters.addEventListener("click", onFilterClick("origin"));
  dom.genreFilters.addEventListener("click", onFilterClick("genre"));
  dom.doctrineFilters.addEventListener("click", onFilterClick("doctrine"));

  applyFilters({ updateUrl: false });
}

function buildLabelMaps() {
  for (const item of taxonomy.origins || []) labelMaps.origin.set(item.id, item.short || item.label);
  for (const item of taxonomy.genres || []) labelMaps.genre.set(item.id, item.label);
  for (const item of taxonomy.doctrines || []) labelMaps.doctrine.set(item.id, item.label);
}

function readFiltersFromUrl() {
  const params = new URLSearchParams(window.location.search);
  filters.origin = params.get("origin") || "";
  filters.genre = params.get("genre") || "";
  filters.doctrine = params.get("doctrine") || "";
  filters.query = params.get("q") || "";
}

function writeFiltersToUrl() {
  const params = new URLSearchParams();
  if (filters.origin) params.set("origin", filters.origin);
  if (filters.genre) params.set("genre", filters.genre);
  if (filters.doctrine) params.set("doctrine", filters.doctrine);
  if (filters.query) params.set("q", filters.query);
  const qs = params.toString();
  const next = qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
  window.history.replaceState({}, "", next);
}

function onFilterClick(dimension) {
  return (event) => {
    const button = event.target.closest("[data-filter-id]");
    if (!button) return;
    const id = button.getAttribute("data-filter-id") || "";
    filters[dimension] = filters[dimension] === id ? "" : id;

    // Cascade: changing origin may invalidate genre
    if (dimension === "origin") {
      if (filters.genre && !genreAllowedForOrigin(filters.genre, filters.origin)) {
        filters.genre = "";
      }
    }
    applyFilters();
  };
}

function genreAllowedForOrigin(genreId, originId) {
  if (!originId) return true;
  const genre = (taxonomy.genres || []).find((g) => g.id === genreId);
  if (!genre || !genre.origins) return true;
  return genre.origins.includes(originId);
}

function onSearchInput() {
  filters.query = dom.searchInput.value.trim();
  applyFilters();
}

function clearAllFilters() {
  filters.origin = "";
  filters.genre = "";
  filters.doctrine = "";
  filters.query = "";
  dom.searchInput.value = "";
  applyFilters();
}

function applyFilters({ updateUrl = true } = {}) {
  filteredWorks = allWorks.filter(matchesFilters);
  const totalVolumes = filteredWorks.reduce((sum, w) => sum + (w.juan_total || 1), 0);
  updateLead(filteredWorks.length, totalVolumes);
  renderFilterBars();
  renderBreadcrumb();
  displayedCount = 0;
  dom.catalogGrid.innerHTML = "";
  showMore();
  if (updateUrl) writeFiltersToUrl();
}

function matchesFilters(work) {
  if (filters.origin && work.origin !== filters.origin) return false;
  if (filters.genre && work.genre !== filters.genre) return false;
  if (filters.doctrine) {
    const list = work.doctrine || [];
    if (!list.includes(filters.doctrine)) return false;
  }
  if (!filters.query) return true;

  const queries = [filters.query.toLowerCase()];
  if (s2tConverter) {
    const traditional = s2tConverter(filters.query);
    if (traditional !== filters.query) queries.push(traditional.toLowerCase());
  }
  const title = (work.title || "").toLowerCase();
  const shortTitle = (work.short_title || "").toLowerCase();
  const cbetaId = (work.cbeta_id || "").toLowerCase();
  return queries.some((q) => title.includes(q) || shortTitle.includes(q) || cbetaId.includes(q));
}

function countBy(dimension, pool) {
  const counts = new Map();
  for (const work of pool) {
    if (dimension === "doctrine") {
      for (const id of work.doctrine || []) {
        counts.set(id, (counts.get(id) || 0) + 1);
      }
    } else {
      const id = work[dimension];
      if (!id) continue;
      counts.set(id, (counts.get(id) || 0) + 1);
    }
  }
  return counts;
}

function poolWithout(dimension) {
  return allWorks.filter((work) => {
    if (dimension !== "origin" && filters.origin && work.origin !== filters.origin) return false;
    if (dimension !== "genre" && filters.genre && work.genre !== filters.genre) return false;
    if (dimension !== "doctrine" && filters.doctrine) {
      if (!(work.doctrine || []).includes(filters.doctrine)) return false;
    }
    return matchesQueryOnly(work, filters.query);
  });
}

function matchesQueryOnly(work, raw) {
  if (!raw) return true;
  const queries = [raw.toLowerCase()];
  if (s2tConverter) {
    const traditional = s2tConverter(raw);
    if (traditional !== raw) queries.push(traditional.toLowerCase());
  }
  const title = (work.title || "").toLowerCase();
  const shortTitle = (work.short_title || "").toLowerCase();
  const cbetaId = (work.cbeta_id || "").toLowerCase();
  return queries.some((q) => title.includes(q) || shortTitle.includes(q) || cbetaId.includes(q));
}

function renderFilterBars() {
  const originPool = poolWithout("origin");
  const genrePool = poolWithout("genre");
  const doctrinePool = poolWithout("doctrine");

  const originCounts = countBy("origin", originPool);
  const genreCounts = countBy("genre", genrePool);
  const doctrineCounts = countBy("doctrine", doctrinePool);

  dom.originFilters.innerHTML = renderChips(
    taxonomy.origins || [],
    filters.origin,
    originCounts,
    "全部产地",
    originPool.length,
  );

  const genreDefs = (taxonomy.genres || []).filter((g) => genreAllowedForOrigin(g.id, filters.origin));
  dom.genreFilters.innerHTML = renderChips(genreDefs, filters.genre, genreCounts, "全部文体", genrePool.length);

  const doctrineDefs = (taxonomy.doctrines || []).filter(
    (d) => (doctrineCounts.get(d.id) || 0) > 0 || filters.doctrine === d.id,
  );
  dom.doctrineFilters.innerHTML = renderChips(
    doctrineDefs,
    filters.doctrine,
    doctrineCounts,
    "全部思想系",
    doctrinePool.length,
  );

  const hasActive = !!(filters.origin || filters.genre || filters.doctrine || filters.query);
  dom.clearFilters.hidden = !hasActive;
}

function renderChips(items, activeId, counts, allLabel, allCount) {
  const chips = [
    `<button type="button" class="tax-chip${!activeId ? " is-active" : ""}" data-filter-id="">${escapeHtml(allLabel)}<span>${allCount}</span></button>`,
  ];

  for (const item of items) {
    const count = counts.get(item.id) || 0;
    if (count === 0 && activeId !== item.id) continue;
    const label = item.short || item.label;
    chips.push(
      `<button type="button" class="tax-chip${activeId === item.id ? " is-active" : ""}" data-filter-id="${escapeHtml(item.id)}">${escapeHtml(label)}<span>${count}</span></button>`,
    );
  }
  return chips.join("");
}

function renderBreadcrumb() {
  const parts = ["全部经目"];
  if (filters.origin) parts.push(labelMaps.origin.get(filters.origin) || filters.origin);
  if (filters.genre) parts.push(labelMaps.genre.get(filters.genre) || filters.genre);
  if (filters.doctrine) parts.push(labelMaps.doctrine.get(filters.doctrine) || filters.doctrine);
  if (filters.query) parts.push(`搜索「${filters.query}」`);
  dom.breadcrumb.textContent = parts.join(" › ");
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

function updateLead(workCount, volumeCount) {
  const hasFilter = !!(filters.origin || filters.genre || filters.doctrine || filters.query);
  if (hasFilter) {
    dom.lead.textContent = `当前筛选：${workCount} 部佛典，共 ${volumeCount} 卷。`;
  } else {
    dom.lead.textContent = `当前共整理 ${workCount} 部佛典，共 ${volumeCount} 卷。可按产地、文体、思想系浏览，或搜索经名。`;
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
      const taxLine = formatTaxonomyLine(work);

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
          <p class="catalog-summary">${escapeHtml(taxLine)}${work.translator ? " · " + escapeHtml(work.translator) : ""}</p>
          <a class="catalog-open" href="${getReaderUrl(readerSlug)}">进入阅读页</a>
        </article>
      `;
    })
    .join("");
}

function formatTaxonomyLine(work) {
  const parts = [];
  if (work.origin) parts.push(labelMaps.origin.get(work.origin) || work.origin);
  if (work.genre) parts.push(labelMaps.genre.get(work.genre) || work.genre);
  const doctrines = (work.doctrine || [])
    .map((id) => labelMaps.doctrine.get(id) || id)
    .filter(Boolean);
  if (doctrines.length) parts.push(doctrines.join("、"));
  else if (work.category) parts.push(work.category);
  return parts.join(" · ");
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
