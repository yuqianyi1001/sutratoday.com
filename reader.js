import {
  documentIndex,
  escapeHtml,
  GITHUB_REPO_BASE,
  getMarkdownSourceUrl,
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
  raw: document.getElementById("reader-raw"),
  selectionCommentTrigger: document.getElementById("selection-comment-trigger"),
  selectionFeedbackClose: document.getElementById("selection-feedback-close"),
  selectionFeedback: document.getElementById("selection-feedback"),
  selectionFeedbackDismiss: document.getElementById("selection-feedback-dismiss"),
  selectionFeedbackLink: document.getElementById("selection-feedback-link"),
  selectionFeedbackQuote: document.getElementById("selection-feedback-quote"),
  sourceLink: document.getElementById("source-link"),
  summary: document.getElementById("reader-summary"),
};

let currentDocument = null;
let selectedQuote = "";
let selectionSyncFrame = 0;
let lastSelectionRect = null;
let feedbackPanelOpen = false;
let currentLoadId = 0;
const documentCache = new Map();
const GITHUB_ISSUES_NEW_BASE = GITHUB_REPO_BASE.replace("/blob/main/", "/issues/new");
const SELECTION_FEEDBACK_OFFSET = 14;

init().catch((error) => {
  dom.rendered.innerHTML = `<p class="loading-text">请通过站点地址访问本页，避免直接打开本地文件。</p>`;
});

async function init() {
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
  dom.sourceLink.href = getMarkdownSourceUrl(selected.path);
  dom.rendered.innerHTML = renderMarkdown(selected.body);
  dom.raw.textContent = selected.raw;
  updateSeo(selected);
  resetSelectionFeedback();
  dom.statusbar.innerHTML = `
    <span class="badge ${translationBadge.className}">${translationBadge.label}</span>
    <span class="badge ${reviewBadge.className}">${reviewBadge.label}</span>
    <span class="reader-fact">卷别：${escapeHtml(selected.volume_label || "单篇")}</span>
    <span class="reader-fact">进度：${escapeHtml(String(selected.progress_percent || 0))}%</span>
    <span class="reader-fact">更新：${escapeHtml(selected.updated_at || "未标注")}</span>
  `;
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
}

function syncReaderUrl(slug) {
  const nextRelativeUrl = getReaderUrl(slug);
  const nextSearch = `?doc=${encodeURIComponent(slug)}`;
  if (location.search !== nextSearch || location.hash) {
    history.replaceState(null, "", nextRelativeUrl);
  }
}

function updateSeo(doc) {
  const names = [doc.short_title, doc.title].filter(Boolean);
  const pageTitle = `${names[0] || doc.title}白话文与现代语译 | 今文佛典`;
  const pageDescription = `阅读《${doc.title}》的导读、原文、现代语译与白话文对照，帮助读者更快理解这部佛经在说什么、目的是什么。`;
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
        headline: doc.title,
        url: canonicalUrl,
        description: pageDescription,
        keywords,
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
    if (!selectedQuote) {
      event.preventDefault();
      return;
    }
    event.preventDefault();
    window.open(buildIssueUrl(selectedQuote), "_blank", "noopener,noreferrer");
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
  dom.selectionFeedbackLink.href = buildIssueUrl(selectedQuote);
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

function buildIssueUrl(quote) {
  const pageUrl = window.location.href;
  const sourceUrl = currentDocument ? getMarkdownSourceUrl(currentDocument.path) : "";
  const titleSeed = quote.length > 24 ? `${quote.slice(0, 24)}...` : quote;
  const title = `阅读页反馈：${currentDocument?.title || "文稿"} - ${titleSeed}`;
  const body = [
    "## 反馈位置",
    `- 文稿：${currentDocument?.title || "未识别"}`,
    `- 阅读页：${pageUrl}`,
    sourceUrl ? `- Markdown 原稿：${sourceUrl}` : "",
    "",
    "## 选中文字",
    `> ${quote.replace(/\n/g, "\n> ")}`,
    "",
    "## 问题或建议",
    "- 请在这里补充你的评论、疑问或修订建议。",
  ]
    .filter(Boolean)
    .join("\n");

  return `${GITHUB_ISSUES_NEW_BASE}?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
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
  dom.selectionFeedbackLink.href = "#";
  dom.selectionCommentTrigger.style.left = "";
  dom.selectionCommentTrigger.style.top = "";
  dom.selectionFeedback.style.left = "";
  dom.selectionFeedback.style.top = "";
  delete dom.selectionCommentTrigger.dataset.position;
  delete dom.selectionFeedback.dataset.position;
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
