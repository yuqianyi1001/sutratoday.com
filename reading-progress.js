import { escapeHtml, getReaderUrl } from "./site-data.js";

export const READING_PROGRESS_KEY = "sutra_last_reading_position";
const BANNER_DISMISS_KEY = "sutra_resume_banner_dismissed";
const READING_BLOCK_SELECTOR = "h1, h2, h3, h4, p, blockquote, pre";
const SKIP_HEADING_CLASS = new Set(["sutra-original-heading", "sutra-translation-heading"]);
const SKIP_HEADING_TEXT = new Set(["原文", "现代语译", "現代語譯"]);
const SCROLL_ARM_DELTA = 48;
const HEADER_MARKER_OFFSET = 120;

export function readReadingProgress() {
  const raw = storageGet(localStorage, READING_PROGRESS_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed.slug !== "string" || !parsed.slug) return null;
    const blockIndex = Number(parsed.blockIndex);
    if (!Number.isInteger(blockIndex) || blockIndex < 0) return null;
    return {
      slug: parsed.slug,
      title: String(parsed.title || "").trim(),
      volumeLabel: String(parsed.volumeLabel || "").trim(),
      blockIndex,
      savedAt: Number(parsed.savedAt) || 0,
    };
  } catch {
    return null;
  }
}

export function saveReadingProgress(progress) {
  if (!progress?.slug) return;
  const blockIndex = Number(progress.blockIndex);
  if (!Number.isInteger(blockIndex) || blockIndex < 0) return;
  const payload = {
    version: 1,
    slug: progress.slug,
    title: String(progress.title || "").trim(),
    volumeLabel: String(progress.volumeLabel || "").trim(),
    blockIndex,
    savedAt: Number(progress.savedAt) || Date.now(),
  };
  storageSet(localStorage, READING_PROGRESS_KEY, JSON.stringify(payload));
}

export function formatResumeLabel(progress) {
  const title = String(progress?.title || "").trim() || progress?.slug || "上次阅读的经文";
  const volume = String(progress?.volumeLabel || "").trim();
  if (!volume || volume === "全一卷" || volume === "单篇" || volume === "單篇") {
    return `上次读到《${title}》`;
  }
  if (title.includes(volume)) return `上次读到《${title}》`;
  return `上次读到《${title}》${volume}`;
}

export function workTitleForProgress(doc, work) {
  if (work?.short_title) return work.short_title;
  const raw = String(doc?.short_title || doc?.title || doc?.slug || "").trim();
  return raw.replace(/卷[一二三四五六七八九十百千零〇两兩0-9]+$/, "") || raw;
}

export function getResumeUrl(slug, blockIndex) {
  const base = getReaderUrl(slug);
  if (!Number.isInteger(blockIndex) || blockIndex < 0) return base;
  return `${base}#p-${blockIndex}`;
}

export function readHashBlockIndex() {
  const match = location.hash.match(/^#p-(\d+)$/);
  if (!match) return null;
  return Number(match[1]);
}

export function assignReadingAnchors(container) {
  if (!container) return 0;
  const candidates = container.querySelectorAll(READING_BLOCK_SELECTOR);
  let index = 0;
  candidates.forEach((el) => {
    if (el.classList.contains("loading-text")) return;
    if ([...el.classList].some((name) => SKIP_HEADING_CLASS.has(name))) return;
    const text = (el.textContent || "").trim();
    if (!text) return;
    if (SKIP_HEADING_TEXT.has(text)) return;
    el.id = `p-${index}`;
    el.dataset.readingBlock = String(index);
    index += 1;
  });
  return index;
}

export function restoreReadingPosition(container, blockIndex) {
  const target = findVisibleRestoreTarget(container, blockIndex);
  if (!target) return false;
  const root = document.documentElement;
  const previousBehavior = root.style.scrollBehavior;
  root.style.scrollBehavior = "auto";
  target.scrollIntoView({ behavior: "auto", block: "start" });
  root.style.scrollBehavior = previousBehavior;
  return true;
}

export function startReadingProgressTracker(container, getMeta) {
  if (!container) return () => {};

  assignReadingAnchors(container);

  const abort = new AbortController();
  const { signal } = abort;
  let armed = false;
  let ticking = false;
  let baselineY = window.scrollY;
  let stopped = false;

  const persist = () => {
    if (stopped || !armed) return;
    const block = getActiveReadingBlock(container);
    if (!block) return;
    const meta = getMeta?.() || {};
    saveReadingProgress({
      slug: meta.slug,
      title: meta.title,
      volumeLabel: meta.volumeLabel,
      blockIndex: Number(block.dataset.readingBlock),
    });
  };

  const onScroll = () => {
    if (stopped) return;
    if (!armed) {
      if (Math.abs(window.scrollY - baselineY) < SCROLL_ARM_DELTA) return;
      armed = true;
    }
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      ticking = false;
      persist();
    });
  };

  const onKey = (event) => {
    if (["ArrowDown", "ArrowUp", "PageDown", "PageUp", "Home", "End", " "].includes(event.key)) {
      armed = true;
    }
  };

  const onHide = () => persist();

  window.addEventListener("scroll", onScroll, { passive: true, signal });
  window.addEventListener("wheel", onScroll, { passive: true, signal });
  window.addEventListener("touchmove", onScroll, { passive: true, signal });
  window.addEventListener("keydown", onKey, { signal });
  window.addEventListener("pagehide", onHide, { signal });
  document.addEventListener(
    "visibilitychange",
    () => {
      if (document.visibilityState === "hidden") onHide();
    },
    { signal },
  );

  requestAnimationFrame(() => {
    baselineY = window.scrollY;
  });

  return () => {
    persist();
    stopped = true;
    abort.abort();
  };
}

export function mountResumeBanner(options = {}) {
  const { currentSlug = "" } = options;
  const existing = document.querySelector(".reading-resume-banner");
  if (existing) existing.remove();

  const progress = readReadingProgress();
  if (!progress) return null;
  if (isBannerDismissed()) return null;
  if (currentSlug && currentSlug === progress.slug) return null;

  const shell = document.querySelector(".page-shell");
  if (!shell) return null;

  const banner = document.createElement("div");
  banner.className = "reading-resume-banner";
  banner.setAttribute("role", "region");
  banner.setAttribute("aria-label", "继续阅读");
  banner.innerHTML = `
    <p class="reading-resume-copy">${escapeHtml(formatResumeLabel(progress))}</p>
    <div class="reading-resume-actions">
      <a class="primary-link reading-resume-continue" href="${escapeHtml(getResumeUrl(progress.slug, progress.blockIndex))}">继续阅读</a>
      <button class="reading-resume-dismiss" type="button" aria-label="关闭继续阅读提示">关闭</button>
    </div>
  `;

  const header = shell.querySelector(".site-header");
  if (header) shell.insertBefore(banner, header);
  else shell.prepend(banner);

  banner.querySelector(".reading-resume-dismiss")?.addEventListener("click", () => {
    dismissBanner();
    banner.remove();
  });

  return banner;
}

function findVisibleRestoreTarget(container, blockIndex) {
  if (!container || !Number.isInteger(blockIndex) || blockIndex < 0) return null;
  const blocks = getReadingBlocks(container);
  if (!blocks.length) return null;

  const exact = blocks.find((el) => Number(el.dataset.readingBlock) === blockIndex);
  if (exact && isBlockVisible(exact)) return exact;

  const start = blocks.findIndex((el) => Number(el.dataset.readingBlock) >= blockIndex);
  const from = start === -1 ? blocks.length - 1 : start;
  for (let i = from; i < blocks.length; i += 1) {
    if (isBlockVisible(blocks[i])) return blocks[i];
  }
  for (let i = from; i >= 0; i -= 1) {
    if (isBlockVisible(blocks[i])) return blocks[i];
  }
  return null;
}

function getActiveReadingBlock(container) {
  const blocks = getReadingBlocks(container).filter(isBlockVisible);
  if (!blocks.length) return null;
  const marker = HEADER_MARKER_OFFSET;
  let current = blocks[0];
  for (const el of blocks) {
    if (el.getBoundingClientRect().top <= marker) current = el;
    else break;
  }
  return current;
}

function getReadingBlocks(container) {
  return Array.from(container.querySelectorAll("[data-reading-block]"));
}

function isBlockVisible(el) {
  if (!el || el.hidden) return false;
  const style = window.getComputedStyle(el);
  if (style.display === "none" || style.visibility === "hidden") return false;
  return el.getClientRects().length > 0;
}

function isBannerDismissed() {
  return storageGet(sessionStorage, BANNER_DISMISS_KEY) === "1";
}

function dismissBanner() {
  storageSet(sessionStorage, BANNER_DISMISS_KEY, "1");
}

function storageGet(storage, key) {
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}

function storageSet(storage, key, value) {
  try {
    storage.setItem(key, value);
  } catch {
    // 无痕模式或禁用存储时忽略
  }
}
