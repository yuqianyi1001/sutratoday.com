import {
  escapeHtml,
  getReaderUrl,
  getReviewState,
  getTranslationState,
  getVolumeNavigation,
  getVolumeSlugPath,
  getWorkBySlug,
  loadDocument,
  loadWorksIndex,
  renderMarkdown,
  SITE_BASE_URL,
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
let worksIndex = null;
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

  // Load works index for volume navigation
  worksIndex = await loadWorksIndex();

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
  const slug = requestedSlug || "T0251-001"; // Default to Heart Sutra
  const loadId = ++currentLoadId;
  const selected = await getDocumentBySlug(slug);

  syncReaderUrl(selected.slug);
  if (loadId !== currentLoadId) return;

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
    <span class="reader-fact">译者：${escapeHtml(selected.ai_translator || selected.translated_by || "未标注")}</span>
    <span class="reader-fact">卷别：${escapeHtml(selected.volume_label || "单篇")}</span>
    <span class="reader-fact">更新：${escapeHtml(selected.updated_at || "未标注")}</span>
  `;
  resetSelectionFeedback();
  applyReadingMode(readingMode);
  applyFontSize(fontSize);
  initComments(selected.slug);
}

async function getDocumentBySlug(slug) {
  if (documentCache.has(slug)) return documentCache.get(slug);

  const path = getVolumeSlugPath(slug);
  const loaded = await loadDocument(path);
  const merged = { ...loaded, slug, path };
  documentCache.set(slug, merged);
  return merged;
}

function renderVolumeNavigation(doc) {
  if (!worksIndex) return;
  const work = getWorkBySlug(worksIndex, doc.slug);
  const items = work ? getVolumeNavigation(work, doc.slug) : [];
  const markup = items.length ? buildVolumeNavigationMarkup(items) : "";

  [dom.volumeNavTop, dom.volumeNavBottom].forEach((container) => {
    if (!container) return;
    if (!markup) {
      container.hidden = true;
      container.innerHTML = "";
      return;
    }
    container.hidden = false;
    container.innerHTML = markup;
    const select = container.querySelector(".reader-volume-select");
    if (select) {
      select.addEventListener("change", (event) => {
        const nextSlug = event.target.value;
        if (nextSlug) window.location.href = getReaderUrl(nextSlug);
      });
    }
  });
}

function buildVolumeNavigationMarkup(items) {
  const currentIndex = items.findIndex((item) => item.isCurrent);
  const previousItem = currentIndex > 0 ? items[currentIndex - 1] : null;
  const nextItem = currentIndex >= 0 && currentIndex < items.length - 1 ? items[currentIndex + 1] : null;
  const currentItem = currentIndex >= 0 ? items[currentIndex] : null;
  const options = items
    .map((item) => {
      const selected = item.isCurrent ? " selected" : "";
      return `<option value="${escapeHtml(item.slug)}"${selected}>${escapeHtml(item.label)}</option>`;
    })
    .join("");

  return `
    <div class="reader-volume-nav-inner">
      <div class="reader-volume-nav-row">
        ${
          previousItem
            ? `<a class="reader-volume-step" href="${getReaderUrl(previousItem.slug)}" title="${escapeHtml(previousItem.title)}">上一卷</a>`
            : `<span class="reader-volume-step is-disabled" aria-disabled="true">上一卷</span>`
        }
        <span class="reader-volume-current" aria-live="polite">
          ${escapeHtml(currentItem ? currentItem.label : "卷数导航")}
        </span>
        ${
          nextItem
            ? `<a class="reader-volume-step" href="${getReaderUrl(nextItem.slug)}" title="${escapeHtml(nextItem.title)}">下一卷</a>`
            : `<span class="reader-volume-step is-disabled" aria-disabled="true">下一卷</span>`
        }
      </div>
      <label class="reader-volume-select-wrap">
        <span class="reader-volume-select-label">跳转到</span>
        <select class="reader-volume-select" aria-label="选择卷数">
          ${options}
        </select>
      </label>
    </div>
  `;
}

// ── Reading Mode / Font Size ───────────────────────────────

function bindReadingModePicker() {
  if (!dom.modePicker) return;
  dom.modePicker.addEventListener("click", (event) => {
    const button = event.target.closest("[data-reading-mode-value]");
    if (!button) return;
    const nextMode = button.dataset.readingModeValue;
    if (!VALID_READING_MODES.has(nextMode)) return;
    applyReadingMode(nextMode, { persist: true });
  });
}

function bindFontPicker() {
  if (!dom.fontPicker) return;
  dom.fontPicker.addEventListener("click", (event) => {
    const button = event.target.closest("[data-font-size-value]");
    if (!button) return;
    const nextSize = button.dataset.fontSizeValue;
    if (!VALID_FONT_SIZES.has(nextSize)) return;
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
  if (persist) saveCookie(READING_MODE_COOKIE, nextMode);
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
  if (persist) saveCookie(FONT_SIZE_COOKIE, nextSize);
}

function getSavedReadingMode() {
  const cookieValue = readCookie(READING_MODE_COOKIE);
  return VALID_READING_MODES.has(cookieValue) ? cookieValue : READING_MODE_DEFAULT;
}

function getSavedFontSize() {
  const cookieValue = readCookie(FONT_SIZE_COOKIE);
  return VALID_FONT_SIZES.has(cookieValue) ? cookieValue : FONT_SIZE_DEFAULT;
}

// ── URL / Navigation ───────────────────────────────────────

function getCurrentSlug() {
  const slugFromSearch = new URLSearchParams(location.search).get("doc");
  if (slugFromSearch) return slugFromSearch;
  return new URLSearchParams(location.hash.replace(/^#/, "")).get("doc");
}

function syncReaderUrl(slug) {
  const nextRelativeUrl = getReaderUrl(slug);
  const nextSearch = `?doc=${encodeURIComponent(slug)}`;
  if (location.search !== nextSearch || location.hash) {
    history.replaceState(null, "", nextRelativeUrl);
  }
}

function handleReaderLoadError() {
  dom.rendered.innerHTML = `<p class="loading-text">当前经文加载失败，请稍后重试。</p>`;
  renderVolumeNavigation({ slug: "" });
}

// ── SEO ────────────────────────────────────────────────────

function updateSeo(doc) {
  const fullTitle = doc.title || "佛经";
  const pageTitle = `${fullTitle}白话文与现代语译 | 今文佛典`;
  const pageDescription = `阅读《${fullTitle}》的导读、原文、现代语译与白话文对照。帮助读者更快理解这部佛经的深刻义理。`;
  const canonicalUrl = getReaderUrl(doc.slug, SITE_BASE_URL);

  document.title = pageTitle;
  setMeta('meta[name="description"]', "content", pageDescription);
  setMeta('meta[property="og:title"]', "content", pageTitle);
  setMeta('meta[property="og:description"]', "content", pageDescription);
  setMeta('meta[property="og:url"]', "content", canonicalUrl);
  setMeta('meta[name="twitter:title"]', "content", pageTitle);
  setMeta('meta[name="twitter:description"]', "content", pageDescription);

  const canonicalLink = document.querySelector('link[rel="canonical"]');
  if (canonicalLink) canonicalLink.href = canonicalUrl;

  const structuredData = document.getElementById("seo-structured-data");
  if (structuredData) {
    structuredData.textContent = JSON.stringify({
      "@context": "https://schema.org",
      "@type": "Article",
      headline: fullTitle,
      url: canonicalUrl,
      description: pageDescription,
      author: { "@type": "Organization", name: "今文佛典" },
      inLanguage: "zh-CN",
      isPartOf: { "@type": "WebSite", name: "今文佛典", url: SITE_BASE_URL },
    }, null, 2);
  }
}

function setMeta(selector, attribute, value) {
  const element = document.querySelector(selector);
  if (element) element.setAttribute(attribute, value);
}

// ── Cookie Helpers ─────────────────────────────────────────

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
  if (!matched) return "";
  return decodeURIComponent(matched.slice(cookiePrefix.length));
}

// ── Selection Feedback ─────────────────────────────────────

function bindSelectionFeedback() {
  document.addEventListener("selectionchange", scheduleSyncSelectionFeedback);
  dom.rendered.addEventListener("mouseup", scheduleSyncSelectionFeedback);
  dom.rendered.addEventListener("touchend", scheduleSyncSelectionFeedback);
  dom.rendered.addEventListener("keyup", scheduleSyncSelectionFeedback);
  window.addEventListener("resize", syncSelectionAnchors);
  window.addEventListener("scroll", syncSelectionAnchors, { passive: true });
  dom.selectionCommentTrigger.addEventListener("mousedown", (event) => event.preventDefault());
  dom.selectionCommentTrigger.addEventListener("click", (event) => {
    event.preventDefault();
    if (!selectedQuote) return;
    feedbackPanelOpen = true;
    dom.selectionFeedback.hidden = false;
    dom.selectionFeedback.dataset.pendingQuote = selectedQuote;
    syncSelectionFeedbackPosition();
  });
  dom.selectionFeedbackLink.addEventListener("mousedown", (event) => event.preventDefault());
  dom.selectionFeedbackClose.addEventListener("click", () => hideSelectionFeedbackPanel());
  dom.selectionFeedbackDismiss.addEventListener("click", () => {
    clearSelection();
    resetSelectionFeedback();
  });
  dom.selectionFeedbackLink.addEventListener("click", (event) => {
    event.preventDefault();
    const quote = selectedQuote || dom.selectionFeedback.dataset.pendingQuote;
    if (!quote) return;
    sendQuoteToComment(quote);
  });
}

function scheduleSyncSelectionFeedback() {
  if (selectionSyncFrame) cancelAnimationFrame(selectionSyncFrame);
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
  if (!nextQuote) { resetSelectionFeedback(); return; }

  const quoteChanged = nextQuote !== selectedQuote;
  selectedQuote = nextQuote;
  lastSelectionRect = getSelectionRect(selection);
  dom.selectionCommentTrigger.hidden = false;
  dom.selectionFeedbackQuote.textContent = `"${selectedQuote}"`;
  syncSelectionTriggerPosition();
  if (quoteChanged) hideSelectionFeedbackPanel();
  if (feedbackPanelOpen) {
    dom.selectionFeedback.hidden = false;
    syncSelectionFeedbackPosition();
  }
}

function normalizeSelection(text) {
  return text.replace(/\s+\n/g, "\n").replace(/\n\s+/g, "\n").replace(/[ \t]+/g, " ").trim().slice(0, 1200);
}

function containsNode(container, node) {
  if (!container || !node) return false;
  return container.contains(node.nodeType === Node.ELEMENT_NODE ? node : node.parentNode);
}

function selectionInsideRendered(selection) {
  return containsNode(dom.rendered, selection.anchorNode) || containsNode(dom.rendered, selection.focusNode);
}

function syncSelectionAnchors() {
  if (!selectedQuote) return;
  const selection = window.getSelection();
  if (selection && selection.rangeCount > 0 && !selection.isCollapsed && selectionInsideRendered(selection)) {
    lastSelectionRect = getSelectionRect(selection);
  }
  syncSelectionTriggerPosition();
  if (feedbackPanelOpen) syncSelectionFeedbackPosition();
}

function syncSelectionTriggerPosition() {
  if (dom.selectionCommentTrigger.hidden || !selectedQuote) return;
  const rect = lastSelectionRect;
  if (!rect) { applyFallbackPosition(dom.selectionCommentTrigger); return; }

  const triggerRect = dom.selectionCommentTrigger.getBoundingClientRect();
  const proseRect = dom.rendered.getBoundingClientRect();
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  let left = proseRect.right + 12;
  let top = rect.top + rect.height / 2 - triggerRect.height / 2;

  if (left + triggerRect.width > viewportWidth - 12) left = viewportWidth - triggerRect.width - 12;
  if (left < 12) left = 12;
  top = clamp(top, 12, Math.max(12, viewportHeight - triggerRect.height - 12));

  dom.selectionCommentTrigger.style.left = `${left}px`;
  dom.selectionCommentTrigger.style.top = `${top}px`;
  dom.selectionCommentTrigger.dataset.position = "anchored";
}

function syncSelectionFeedbackPosition() {
  if (dom.selectionFeedback.hidden || !selectedQuote || !feedbackPanelOpen) return;
  const anchorRect = dom.selectionCommentTrigger.hidden
    ? lastSelectionRect
    : dom.selectionCommentTrigger.getBoundingClientRect();
  if (!anchorRect) { applyFallbackPosition(dom.selectionFeedback); return; }

  const bubbleRect = dom.selectionFeedback.getBoundingClientRect();
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  let left = anchorRect.right + 12;
  let top = anchorRect.top - 6;

  if (left + bubbleRect.width > viewportWidth - 16) left = anchorRect.left - bubbleRect.width - 12;
  if (left < 16) left = viewportWidth - bubbleRect.width - 16;
  top = clamp(top, 16, Math.max(16, viewportHeight - bubbleRect.height - 16));

  dom.selectionFeedback.style.left = `${left}px`;
  dom.selectionFeedback.style.top = `${top}px`;
  dom.selectionFeedback.dataset.position = "anchored";
}

function getSelectionRect(selection) {
  const range = selection.getRangeAt(0);
  const rects = Array.from(range.getClientRects()).filter((r) => r.width > 0 || r.height > 0);
  if (rects.length > 0) return rects[rects.length - 1];
  const rect = range.getBoundingClientRect();
  if (rect.width > 0 || rect.height > 0) return rect;
  return null;
}

function applyFallbackPosition(el) {
  el.style.left = "";
  el.style.top = "";
  el.dataset.position = "fallback";
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function sendQuoteToComment(quote) {
  const commentSection =
    document.getElementById("tk-comments") ||
    document.querySelector(".tk-comments") ||
    document.getElementById("tcomment");
  if (!commentSection) return;
  const textarea = commentSection.querySelector("textarea");
  if (textarea) {
    const prefix = `> ${quote.replace(/\n/g, "\n> ")}\n\n`;
    textarea.value = prefix + textarea.value;
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  }
  const scrollTarget = document.getElementById("tcomment") || commentSection;
  scrollTarget.scrollIntoView({ behavior: "smooth", block: "start" });
  if (textarea) setTimeout(() => textarea.focus(), 400);
  clearSelection();
  resetSelectionFeedback();
}

function resetSelectionFeedback() {
  if (selectionSyncFrame) { cancelAnimationFrame(selectionSyncFrame); selectionSyncFrame = 0; }
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
  if (selection) selection.removeAllRanges();
}

function hideSelectionFeedbackPanel() {
  feedbackPanelOpen = false;
  dom.selectionFeedback.hidden = true;
  dom.selectionFeedback.style.left = "";
  dom.selectionFeedback.style.top = "";
  delete dom.selectionFeedback.dataset.position;
}

function initComments(slug) {
  if (typeof twikoo === "undefined") return;
  twikoo.init({
    envId: "https://twikoo-cloudflare.jeffwoo2019.workers.dev",
    el: "#tcomment",
    path: slug,
    lang: "zh-CN",
  });
}
