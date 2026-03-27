import {
  documentIndex,
  escapeHtml,
  getVolumeNavigation,
  getReaderUrl,
  getReviewState,
  loadDocument,
  SITE_BASE_URL,
  getTranslationState,
  renderMarkdown,
} from "./site-data.js";

const dom = {
  statusbar: document.getElementById("reader-statusbar"),
  title: document.getElementById("reader-title"),
  rendered: document.getElementById("reader-rendered"),
  modePicker: document.getElementById("reader-mode-picker"),
  modeButtons: Array.from(document.querySelectorAll("[data-reading-mode-value]")),
  fontPicker: document.getElementById("reader-font-picker"),
  fontButtons: Array.from(document.querySelectorAll("[data-font-size-value]")),
  volumeNavTop: document.getElementById("reader-volume-nav-top"),
  volumeNavBottom: document.getElementById("reader-volume-nav-bottom"),
  selectionCommentTrigger: document.getElementById("selection-comment-trigger"),
  selectionFeedbackClose: document.getElementById("selection-feedback-close"),
  selectionFeedback: document.getElementById("selection-feedback"),
  selectionFeedbackDismiss: document.getElementById("selection-feedback-dismiss"),
  selectionFeedbackLink: document.getElementById("selection-feedback-link"),
  selectionFeedbackQuote: document.getElementById("selection-feedback-quote"),
  summary: document.getElementById("reader-summary"),
};

let currentDocument = null;
let selectedQuote = "";
let selectionSyncFrame = 0;
let lastSelectionRect = null;
let feedbackPanelOpen = false;
let currentLoadId = 0;
const documentCache = new Map();
const SELECTION_FEEDBACK_OFFSET = 14;
const READING_MODE_COOKIE = "sutra_reader_mode";
const READING_MODE_DEFAULT = "parallel";
const VALID_READING_MODES = new Set([READING_MODE_DEFAULT, "original", "translation"]);
const FONT_SIZE_COOKIE = "sutra_reader_font_size";
const FONT_SIZE_DEFAULT = "default";
const VALID_FONT_SIZES = new Set([FONT_SIZE_DEFAULT, "large", "xlarge"]);
const READING_MODE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;
let readingMode = getSavedReadingMode();
let fontSize = getSavedFontSize();

init().catch((error) => {
  dom.rendered.innerHTML = `<p class="loading-text">请通过站点地址访问本页，避免直接打开本地文件。</p>`;
});

async function init() {
  bindReadingModePicker();
  bindFontPicker();
  applyReadingMode(readingMode);
  applyFontSize(fontSize);
  bindSelectionFeedback();
  await selectCurrent();
  window.addEventListener("hashchange", () => {
    selectCurrent().catch(handleReaderLoadError);
  });
  window.addEventListener("popstate", () => {
    selectCurrent().catch(handleReaderLoadError);
  });
}

async function selectCurrent() {
  const requestedSlug = getCurrentSlug();
  const selectedMeta = getSafeDocumentMeta(requestedSlug);
  const loadId = ++currentLoadId;
  const selected = await getDocumentBySlug(selectedMeta.slug);

  syncReaderUrl(selected.slug);
  if (loadId !== currentLoadId) {
    return;
  }

  currentDocument = selected;

  const translationBadge = getTranslationState(selected.translation_status);
  const reviewBadge = getReviewState(selected.review_status);

  dom.title.textContent = selected.title;
  dom.summary.textContent = selected.summary || "";
  dom.rendered.innerHTML = renderMarkdown(selected.body);
  renderVolumeNavigation(selected);
  updateSeo(selected);
  dom.statusbar.innerHTML = `
    <span class="badge ${translationBadge.className}">${translationBadge.label}</span>
    <span class="badge ${reviewBadge.className}">${reviewBadge.label}</span>
    <span class="reader-fact">译者：${escapeHtml(selected.translated_by || "未标注")}</span>
    <span class="reader-fact">卷别：${escapeHtml(selected.volume_label || "单篇")}</span>
    <span class="reader-fact">进度：${escapeHtml(String(selected.progress_percent || 0))}%</span>
    <span class="reader-fact">更新：${escapeHtml(selected.updated_at || "未标注")}</span>
  `;
  resetSelectionFeedback();
  applyReadingMode(readingMode);
  applyFontSize(fontSize);
  initComments(selected.slug);
}

function bindReadingModePicker() {
  if (!dom.modePicker) {
    return;
  }

  dom.modePicker.addEventListener("click", (event) => {
    const button = event.target.closest("[data-reading-mode-value]");
    if (!button) {
      return;
    }

    const nextMode = button.dataset.readingModeValue;
    if (!VALID_READING_MODES.has(nextMode)) {
      return;
    }

    applyReadingMode(nextMode, { persist: true });
  });
}

function bindFontPicker() {
  if (!dom.fontPicker) {
    return;
  }

  dom.fontPicker.addEventListener("click", (event) => {
    const button = event.target.closest("[data-font-size-value]");
    if (!button) {
      return;
    }

    const nextSize = button.dataset.fontSizeValue;
    if (!VALID_FONT_SIZES.has(nextSize)) {
      return;
    }

    applyFontSize(nextSize, { persist: true });
  });
}

function applyReadingMode(mode, options = {}) {
  const { persist = false } = options;
  const nextMode = VALID_READING_MODES.has(mode) ? mode : READING_MODE_DEFAULT;

  readingMode = nextMode;
  dom.rendered.dataset.readingMode = nextMode;

  dom.modeButtons.forEach((button) => {
    const isActive = button.dataset.readingModeValue === nextMode;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-checked", isActive ? "true" : "false");
  });

  if (persist) {
    saveReadingMode(nextMode);
  }

  clearSelection();
  resetSelectionFeedback();
}

function applyFontSize(size, options = {}) {
  const { persist = false } = options;
  const nextSize = VALID_FONT_SIZES.has(size) ? size : FONT_SIZE_DEFAULT;

  fontSize = nextSize;
  dom.rendered.dataset.fontSize = nextSize;

  dom.fontButtons.forEach((button) => {
    const isActive = button.dataset.fontSizeValue === nextSize;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-checked", isActive ? "true" : "false");
  });

  if (persist) {
    saveCookie(FONT_SIZE_COOKIE, nextSize);
  }
}

function getSavedReadingMode() {
  const cookieValue = readCookie(READING_MODE_COOKIE);
  return VALID_READING_MODES.has(cookieValue) ? cookieValue : READING_MODE_DEFAULT;
}

function getSavedFontSize() {
  const cookieValue = readCookie(FONT_SIZE_COOKIE);
  return VALID_FONT_SIZES.has(cookieValue) ? cookieValue : FONT_SIZE_DEFAULT;
}

function saveReadingMode(mode) {
  saveCookie(READING_MODE_COOKIE, mode);
}

function saveCookie(name, value) {
  document.cookie = [
    `${name}=${encodeURIComponent(value)}`,
    `Max-Age=${READING_MODE_COOKIE_MAX_AGE}`,
    "Path=/",
    "SameSite=Lax",
  ].join("; ");
}

function readCookie(name) {
  const cookiePrefix = `${name}=`;
  const matched = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(cookiePrefix));

  if (!matched) {
    return "";
  }

  return decodeURIComponent(matched.slice(cookiePrefix.length));
}

function getCurrentSlug() {
  const slugFromSearch = new URLSearchParams(location.search).get("doc");
  if (slugFromSearch) {
    return slugFromSearch;
  }
  return new URLSearchParams(location.hash.replace(/^#/, "")).get("doc");
}

function getSafeDocumentMeta(slug) {
  const fallback = documentIndex.find((doc) => doc.slug === "heart-sutra") || documentIndex[0];
  if (!slug) {
    return fallback;
  }
  return documentIndex.find((doc) => doc.slug === slug) || fallback;
}

async function getDocumentBySlug(slug) {
  if (documentCache.has(slug)) {
    return documentCache.get(slug);
  }

  const meta = getSafeDocumentMeta(slug);
  const loaded = await loadDocument(meta.path);
  const merged = {
    ...meta,
    ...loaded,
    slug: meta.slug,
    path: meta.path,
  };
  documentCache.set(meta.slug, merged);
  return merged;
}

function handleReaderLoadError() {
  dom.rendered.innerHTML = `<p class="loading-text">当前经文加载失败，请稍后重试。</p>`;
  renderVolumeNavigation(null);
}

function syncReaderUrl(slug) {
  const nextRelativeUrl = getReaderUrl(slug);
  const nextSearch = `?doc=${encodeURIComponent(slug)}`;
  if (location.search !== nextSearch || location.hash) {
    history.replaceState(null, "", nextRelativeUrl);
  }
}

function updateSeo(doc) {
  const isMultiVolume = !!doc.volume_index;
  const fullTitle = isMultiVolume ? `${doc.work_short_title || doc.title} · ${doc.volume_label}` : doc.title;
  const pageTitle = `${fullTitle}白话文与现代语译 | 今文佛典`;
  const pageDescription = `阅读《${fullTitle}》的导读、原文、现代语译与白话文对照。${doc.summary || ""} 帮助读者更快理解这部佛经的深刻义理。`;
  const canonicalUrl = getReaderUrl(doc.slug, SITE_BASE_URL);
  const keywords = buildSeoKeywords(doc);

  document.title = pageTitle;
  setMeta('meta[name="description"]', "content", pageDescription);
  setMeta('meta[name="keywords"]', "content", keywords);
  setMeta('meta[property="og:title"]', "content", pageTitle);
  setMeta('meta[property="og:description"]', "content", pageDescription);
  setMeta('meta[property="og:url"]', "content", canonicalUrl);
  setMeta('meta[name="twitter:title"]', "content", pageTitle);
  setMeta('meta[name="twitter:description"]', "content", pageDescription);

  const canonicalLink = document.querySelector('link[rel="canonical"]');
  if (canonicalLink) {
    canonicalLink.href = canonicalUrl;
  }

  const structuredData = document.getElementById("seo-structured-data");
  if (structuredData) {
    structuredData.textContent = JSON.stringify(
      {
        "@context": "https://schema.org",
        "@type": "Article",
        headline: fullTitle,
        url: canonicalUrl,
        description: pageDescription,
        keywords,
        author: {
          "@type": "Organization",
          name: "今文佛典",
        },
        inLanguage: "zh-CN",
        isPartOf: {
          "@type": "WebSite",
          name: "今文佛典",
          url: SITE_BASE_URL,
        },
      },
      null,
      2,
    );
  }
}

function renderVolumeNavigation(doc) {
  const items = doc ? getVolumeNavigation(doc) : [];
  const markup = items.length ? buildVolumeNavigationMarkup(items) : "";

  [dom.volumeNavTop, dom.volumeNavBottom].forEach((container) => {
    if (!container) {
      return;
    }

    if (!markup) {
      container.hidden = true;
      container.innerHTML = "";
      return;
    }

    container.hidden = false;
    container.innerHTML = markup;
  });
}

function buildVolumeNavigationMarkup(items) {
  const links = items
    .map((item) => {
      if (item.isCurrent) {
        return `<span class="reader-volume-link is-current" aria-current="page">${escapeHtml(item.label)}</span>`;
      }
      return `<a class="reader-volume-link" href="${getReaderUrl(item.slug)}" title="${escapeHtml(item.title)}">${escapeHtml(item.label)}</a>`;
    })
    .join("");

  return `
    <div class="reader-volume-nav-inner">
      <div class="reader-volume-link-list">
        ${links}
      </div>
    </div>
  `;
}

function buildSeoKeywords(doc) {
  const seeds = [doc.short_title, doc.title].filter(Boolean);
  const keywords = [];

  seeds.forEach((name) => {
    keywords.push(name);
    keywords.push(`${name}白话`);
    keywords.push(`${name}白话文`);
    keywords.push(`${name}现代语译`);
  });

  keywords.push("白话佛经", "佛经白话文", "佛经现代语译");

  return [...new Set(keywords)].join(",");
}

function setMeta(selector, attribute, value) {
  const element = document.querySelector(selector);
  if (element) {
    element.setAttribute(attribute, value);
  }
}

function bindSelectionFeedback() {
  document.addEventListener("selectionchange", scheduleSyncSelectionFeedback);
  dom.rendered.addEventListener("mouseup", scheduleSyncSelectionFeedback);
  dom.rendered.addEventListener("touchend", scheduleSyncSelectionFeedback);
  dom.rendered.addEventListener("keyup", scheduleSyncSelectionFeedback);
  window.addEventListener("resize", syncSelectionAnchors);
  window.addEventListener("scroll", syncSelectionAnchors, { passive: true });
  dom.selectionCommentTrigger.addEventListener("mousedown", (event) => {
    event.preventDefault();
  });
  dom.selectionCommentTrigger.addEventListener("click", (event) => {
    event.preventDefault();
    if (!selectedQuote) {
      return;
    }
    feedbackPanelOpen = true;
    dom.selectionFeedback.hidden = false;
    dom.selectionFeedback.dataset.pendingQuote = selectedQuote;
    syncSelectionFeedbackPosition();
  });
  dom.selectionFeedbackLink.addEventListener("mousedown", (event) => {
    event.preventDefault();
  });
  dom.selectionFeedbackClose.addEventListener("click", () => {
    hideSelectionFeedbackPanel();
  });
  dom.selectionFeedbackDismiss.addEventListener("click", () => {
    clearSelection();
    resetSelectionFeedback();
  });
  dom.selectionFeedbackLink.addEventListener("click", (event) => {
    event.preventDefault();
    const quote = selectedQuote || dom.selectionFeedback.dataset.pendingQuote;
    if (!quote) {
      return;
    }
    sendQuoteToComment(quote);
  });
}

function scheduleSyncSelectionFeedback() {
  if (selectionSyncFrame) {
    cancelAnimationFrame(selectionSyncFrame);
  }
  selectionSyncFrame = requestAnimationFrame(() => {
    selectionSyncFrame = 0;
    syncSelectionFeedback();
  });
}

function syncSelectionFeedback() {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0 || selection.isCollapsed || !selectionInsideRendered(selection)) {
    resetSelectionFeedback();
    return;
  }

  const nextQuote = normalizeSelection(selection.toString());
  if (!nextQuote) {
    resetSelectionFeedback();
    return;
  }

  const quoteChanged = nextQuote !== selectedQuote;
  selectedQuote = nextQuote;
  lastSelectionRect = getSelectionRect(selection);
  dom.selectionCommentTrigger.hidden = false;
  dom.selectionFeedbackQuote.textContent = `“${selectedQuote}”`;
  syncSelectionTriggerPosition();
  if (quoteChanged) {
    hideSelectionFeedbackPanel();
  }
  if (feedbackPanelOpen) {
    dom.selectionFeedback.hidden = false;
    syncSelectionFeedbackPosition();
  }
}

function getSelectedQuote() {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
    return "";
  }

  if (!selectionInsideRendered(selection)) {
    return "";
  }

  return normalizeSelection(selection.toString());
}

function normalizeSelection(text) {
  return text.replace(/\s+\n/g, "\n").replace(/\n\s+/g, "\n").replace(/[ \t]+/g, " ").trim().slice(0, 1200);
}

function containsNode(container, node) {
  if (!container || !node) {
    return false;
  }
  return container.contains(node.nodeType === Node.ELEMENT_NODE ? node : node.parentNode);
}

function selectionInsideRendered(selection) {
  return containsNode(dom.rendered, selection.anchorNode) || containsNode(dom.rendered, selection.focusNode);
}

function syncSelectionAnchors() {
  if (!selectedQuote) {
    return;
  }
  const selection = window.getSelection();
  if (selection && selection.rangeCount > 0 && !selection.isCollapsed && selectionInsideRendered(selection)) {
    lastSelectionRect = getSelectionRect(selection);
  }
  syncSelectionTriggerPosition();
  if (feedbackPanelOpen) {
    syncSelectionFeedbackPosition();
  }
}

function syncSelectionTriggerPosition() {
  if (dom.selectionCommentTrigger.hidden || !selectedQuote) {
    return;
  }

  const rect = lastSelectionRect;
  if (!rect) {
    applySelectionTriggerFallbackPosition();
    return;
  }

  const triggerRect = dom.selectionCommentTrigger.getBoundingClientRect();
  const proseRect = dom.rendered.getBoundingClientRect();
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  let left = proseRect.right + 12;
  let top = rect.top + rect.height / 2 - triggerRect.height / 2;

  if (left + triggerRect.width > viewportWidth - 12) {
    left = viewportWidth - triggerRect.width - 12;
  }

  if (left < 12) {
    left = 12;
  }

  top = clamp(top, 12, Math.max(12, viewportHeight - triggerRect.height - 12));
  dom.selectionCommentTrigger.style.left = `${left}px`;
  dom.selectionCommentTrigger.style.top = `${top}px`;
  dom.selectionCommentTrigger.dataset.position = "anchored";
}

function syncSelectionFeedbackPosition() {
  if (dom.selectionFeedback.hidden || !selectedQuote || !feedbackPanelOpen) {
    return;
  }

  const anchorRect = dom.selectionCommentTrigger.hidden
    ? lastSelectionRect
    : dom.selectionCommentTrigger.getBoundingClientRect();
  if (!anchorRect) {
    applySelectionFeedbackFallbackPosition();
    return;
  }

  const bubbleRect = dom.selectionFeedback.getBoundingClientRect();
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  let left = anchorRect.right + 12;
  let top = anchorRect.top - 6;

  if (left + bubbleRect.width > viewportWidth - 16) {
    left = anchorRect.left - bubbleRect.width - 12;
  }

  if (left < 16) {
    left = viewportWidth - bubbleRect.width - 16;
  }

  top = clamp(top, 16, Math.max(16, viewportHeight - bubbleRect.height - 16));
  dom.selectionFeedback.style.left = `${left}px`;
  dom.selectionFeedback.style.top = `${top}px`;
  dom.selectionFeedback.dataset.position = "anchored";
}

function getSelectionRect(selection) {
  const range = selection.getRangeAt(0);
  const rects = Array.from(range.getClientRects()).filter((rect) => rect.width > 0 || rect.height > 0);
  if (rects.length > 0) {
    return rects[rects.length - 1];
  }
  const rect = range.getBoundingClientRect();
  if (rect.width > 0 || rect.height > 0) {
    return rect;
  }
  return null;
}

function applySelectionFeedbackFallbackPosition() {
  dom.selectionFeedback.style.left = "";
  dom.selectionFeedback.style.top = "";
  dom.selectionFeedback.dataset.position = "fallback";
}

function applySelectionTriggerFallbackPosition() {
  dom.selectionCommentTrigger.style.left = "";
  dom.selectionCommentTrigger.style.top = "";
  dom.selectionCommentTrigger.dataset.position = "fallback";
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function sendQuoteToComment(quote) {
  const commentSection =
    document.getElementById("tk-comments") ||
    document.querySelector(".tk-comments") ||
    document.getElementById("tcomment");
  if (!commentSection) {
    return;
  }

  const textarea = commentSection.querySelector("textarea");
  if (textarea) {
    const prefix = `> ${quote.replace(/\n/g, "\n> ")}\n\n`;
    textarea.value = prefix + textarea.value;
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  }

  const scrollTarget = document.getElementById("tcomment") || commentSection;
  scrollTarget.scrollIntoView({ behavior: "smooth", block: "start" });

  if (textarea) {
    setTimeout(() => textarea.focus(), 400);
  }

  clearSelection();
  resetSelectionFeedback();
}

function resetSelectionFeedback() {
  if (selectionSyncFrame) {
    cancelAnimationFrame(selectionSyncFrame);
    selectionSyncFrame = 0;
  }
  selectedQuote = "";
  lastSelectionRect = null;
  feedbackPanelOpen = false;
  dom.selectionCommentTrigger.hidden = true;
  dom.selectionFeedback.hidden = true;
  dom.selectionFeedbackQuote.textContent = "";
  dom.selectionCommentTrigger.style.left = "";
  dom.selectionCommentTrigger.style.top = "";
  dom.selectionFeedback.style.left = "";
  dom.selectionFeedback.style.top = "";
  delete dom.selectionCommentTrigger.dataset.position;
  delete dom.selectionFeedback.dataset.position;
  delete dom.selectionFeedback.dataset.pendingQuote;
}

function clearSelection() {
  const selection = window.getSelection();
  if (selection) {
    selection.removeAllRanges();
  }
}

function hideSelectionFeedbackPanel() {
  feedbackPanelOpen = false;
  dom.selectionFeedback.hidden = true;
  dom.selectionFeedback.style.left = "";
  dom.selectionFeedback.style.top = "";
  delete dom.selectionFeedback.dataset.position;
}

function initComments(slug) {
  if (typeof twikoo === "undefined") {
    return;
  }
  twikoo.init({
    envId: "https://twikoo-cloudflare.jeffwoo2019.workers.dev",
    el: "#tcomment",
    path: slug, // 使用 slug 区分不同经文的评论区
    lang: "zh-CN",
  });
}
