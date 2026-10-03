import { escapeHtml, getReaderUrl } from "./site-data.js";
import {
  comparePosition,
  getLibrary,
  getRemoteProgress,
  isLoggedIn,
  onAccountChange,
  queueProgressSync,
  workIdFromSlug,
} from "./account-api.js?v=10";

export const READING_PROGRESS_KEY = "sutra_last_reading_position";
// 本机在每部经上读到的位置（按 workId），用来判断新位置是否比已保存的进度靠前
const WORK_POSITIONS_KEY = "sutra_work_reading_positions";
const WORK_POSITIONS_LIMIT = 200;
const BANNER_DISMISS_KEY = "sutra_resume_banner_dismissed";
const READING_BLOCK_SELECTOR = "h1, h2, h3, h4, p, blockquote, pre";
const SKIP_HEADING_CLASS = new Set(["sutra-original-heading", "sutra-translation-heading"]);
const SKIP_HEADING_TEXT = new Set(["原文", "现代语译", "現代語譯"]);
const SCROLL_ARM_DELTA = 24;
const RESTORE_RETRY_MS = [0, 50, 200, 500, 1000];
// 比已保存的进度靠前这么多段（或在更前面的卷）才提示"进度未更新"；退回几段属于正常回看
const BEHIND_PROMPT_BLOCKS = 5;

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
      textPreview: String(parsed.textPreview || "").trim(),
      savedAt: Number(parsed.savedAt) || 0,
    };
  } catch {
    return null;
  }
}

// confirmed：读者已确认用较前的位置覆盖较后的进度
export function saveReadingProgress(progress, { confirmed = false } = {}) {
  if (!progress?.slug) return;
  const blockIndex = Number(progress.blockIndex);
  if (!Number.isInteger(blockIndex) || blockIndex < 0) return;
  const payload = {
    version: 1,
    slug: progress.slug,
    title: String(progress.title || "").trim(),
    volumeLabel: String(progress.volumeLabel || "").trim(),
    blockIndex,
    textPreview: String(progress.textPreview || "").trim(),
    savedAt: Number(progress.savedAt) || Date.now(),
  };
  storageSet(localStorage, READING_PROGRESS_KEY, JSON.stringify(payload));
  saveWorkPosition(payload);
  queueProgressSync(payload, { confirmed });
}

// 本机在这部经上读到的位置
export function readWorkPosition(workId) {
  const map = readWorkPositions();
  const saved = map[workId];
  if (saved?.slug && Number.isInteger(saved.blockIndex)) return saved;
  // 兼容旧数据：只存过"最后一次阅读位置"
  const last = readReadingProgress();
  return last && workIdFromSlug(last.slug) === workId ? last : null;
}

// 这部经已保存的进度：已收藏经文以云端为准（含本机尚未发出的进度），否则用本机位置
export function savedProgressForWork(workId) {
  return getRemoteProgress(workId) || readWorkPosition(workId);
}

// 打开某一卷时的恢复计划：
// - restore：本卷要恢复到的位置，优先用本机自己的位置，其次用云端进度
// - incoming：其他设备上的进度与本机不同，需要提示读者是否跳过去
export function planRestore(slug) {
  const workId = workIdFromSlug(slug);
  const own = readWorkPosition(workId);
  const remote = getRemoteProgress(workId);
  const restore = [own, remote].find((p) => p?.slug === slug) || null;
  const incoming = remote?.slug && !samePosition(remote, own) ? remote : null;
  return { restore, incoming };
}

function samePosition(a, b) {
  return Boolean(a?.slug && b?.slug) && a.slug === b.slug && Number(a.blockIndex) === Number(b.blockIndex);
}

function readWorkPositions() {
  try {
    const parsed = JSON.parse(storageGet(localStorage, WORK_POSITIONS_KEY) || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function saveWorkPosition(payload) {
  const map = readWorkPositions();
  map[workIdFromSlug(payload.slug)] = payload;
  const keys = Object.keys(map);
  if (keys.length > WORK_POSITIONS_LIMIT) {
    keys
      .sort((a, b) => (Number(map[a]?.savedAt) || 0) - (Number(map[b]?.savedAt) || 0))
      .slice(0, keys.length - WORK_POSITIONS_LIMIT)
      .forEach((key) => delete map[key]);
  }
  storageSet(localStorage, WORK_POSITIONS_KEY, JSON.stringify(map));
}

// "继续阅读"提示用：本机与所有收藏经文中最近读的一条
export function latestProgress() {
  const candidates = [readReadingProgress()];
  if (isLoggedIn()) getLibrary().forEach((item) => candidates.push(item.progress));
  return newestProgress(candidates);
}

function newestProgress(list) {
  let best = null;
  for (const p of list) {
    if (!p?.slug || !Number.isInteger(p.blockIndex)) continue;
    if (!best || (Number(p.savedAt) || 0) > (Number(best.savedAt) || 0)) best = p;
  }
  return best;
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
  const match = String(location.hash || "").match(/^#p-(\d+)$/);
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

export function restoreReadingPosition(container, blockIndex, textPreview = "") {
  const target = findRestoreTarget(container, blockIndex, textPreview);
  if (!target) return false;
  scrollToReadingBlock(target);
  return true;
}

export function startReadingProgressTracker(container, getMeta, options = {}) {
  if (!container) return () => {};

  assignReadingAnchors(container);
  if (typeof history !== "undefined" && history.scrollRestoration) {
    history.scrollRestoration = "manual";
  }

  const abort = new AbortController();
  const { signal } = abort;
  let armed = false;
  let ticking = false;
  let restoring = false;
  let stopped = false;
  let baselineY = getScrollY();
  let initialBlockIndex = null;
  let lastSavedKey = "";
  // 上次检查过的位置：位置没变时不重复检查
  let lastCheckedKey = "";
  // 本页保存过的位置，用来区分云端进度是本机发出的还是其他设备的
  const ownKeys = new Set();
  const restoreTimers = [];
  const restoreIndex = Number.isInteger(options.restoreIndex) ? options.restoreIndex : null;
  const restorePreview = String(options.restorePreview || "");
  const currentWorkId = () => workIdFromSlug(getMeta?.()?.slug);
  let seenRemoteKey = progressKey(getRemoteProgress(currentWorkId()));

  const blockProgress = (block) => {
    const meta = getMeta?.() || {};
    return {
      slug: meta.slug,
      title: meta.title,
      volumeLabel: meta.volumeLabel,
      blockIndex: Number(block.dataset.readingBlock),
      textPreview: normalizePreview(block.textContent),
    };
  };

  // 保存某一段为阅读进度。比已保存的进度靠前时不保存（除非读者已确认），改为提示读者
  const saveBlock = (block, { confirmed = false, promptIfBehind = true } = {}) => {
    const next = blockProgress(block);
    if (!next.slug) return;
    const key = progressKey(next);
    if (!confirmed) {
      const saved = savedProgressForWork(workIdFromSlug(next.slug));
      if (saved?.slug && comparePosition(next, saved) < 0) {
        const farBehind = next.slug !== saved.slug || saved.blockIndex - next.blockIndex >= BEHIND_PROMPT_BLOCKS;
        if (!farBehind) prompt.reached(next);
        else if (promptIfBehind) prompt.show("behind", saved);
        return;
      }
      prompt.reached(next);
      // 位置没变就不重新保存：否则闲置的标签页切到后台时，会用"现在"的时间覆盖别处更新的进度
      if (key === lastSavedKey) return;
    }
    if (confirmed) prompt.hide();
    lastSavedKey = key;
    ownKeys.add(key);
    saveReadingProgress(next, { confirmed });
  };

  const prompt = createSyncPrompt({
    onJump: (target) => {
      const meta = getMeta?.() || {};
      if (target.slug !== meta.slug) {
        location.href = getResumeUrl(target.slug, target.blockIndex);
        return;
      }
      cancelRestoreLock();
      restoreReadingPosition(container, target.blockIndex, target.textPreview);
      lastCheckedKey = "";
      baselineY = getScrollY();
    },
    onConfirm: () => {
      const block = getActiveReadingBlock(container);
      if (!block) return;
      armed = true;
      saveBlock(block, { confirmed: true });
      lastCheckedKey = progressKey(blockProgress(block));
    },
  });

  const persist = () => {
    if (stopped || restoring) return;
    const block = getActiveReadingBlock(container);
    if (!block) return;
    const blockIndex = Number(block.dataset.readingBlock);
    if (!armed) {
      const moved = Math.abs(getScrollY() - baselineY) >= SCROLL_ARM_DELTA;
      const blockChanged = initialBlockIndex != null && blockIndex !== initialBlockIndex;
      if (!moved && !blockChanged) return;
      armed = true;
    }
    const key = `${getMeta?.()?.slug}#${blockIndex}`;
    if (key === lastCheckedKey) return;
    lastCheckedKey = key;
    saveBlock(block);
  };

  const onScroll = () => {
    if (stopped) return;
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      ticking = false;
      persist();
    });
  };

  const cancelRestoreLock = () => {
    restoring = false;
    restoreTimers.splice(0).forEach((id) => clearTimeout(id));
    baselineY = getScrollY();
    initialBlockIndex = Number(getActiveReadingBlock(container)?.dataset.readingBlock);
    if (Number.isInteger(initialBlockIndex) && initialBlockIndex < 0) initialBlockIndex = null;
  };

  const applyRestore = () => {
    if (stopped || !restoring) return;
    const ok = restoreReadingPosition(container, restoreIndex, restorePreview);
    baselineY = getScrollY();
    const target = findRestoreTarget(container, restoreIndex, restorePreview);
    initialBlockIndex = Number(target?.dataset.readingBlock);
    // 恢复的位置若比已保存的进度靠前，不保存；由"其他设备上有新的阅读位置"提示读者
    if (ok && target) saveBlock(target, { promptIfBehind: false });
  };

  // 云端进度有变化（其他设备读到了新位置）时提示读者
  const onRemoteChange = () => {
    if (stopped) return;
    const remote = getRemoteProgress(currentWorkId());
    const key = progressKey(remote);
    if (key === seenRemoteKey) return;
    seenRemoteKey = key;
    lastCheckedKey = "";
    if (!key || ownKeys.has(key)) return;
    const block = getActiveReadingBlock(container);
    const current = block ? blockProgress(block) : null;
    if (current && progressKey(current) === key) return;
    prompt.show("incoming", remote, { ahead: !current || comparePosition(remote, current) > 0 });
  };

  const onKey = (event) => {
    if (["ArrowDown", "ArrowUp", "PageDown", "PageUp", "Home", "End", " "].includes(event.key)) {
      cancelRestoreLock();
      armed = true;
    }
  };

  const onHide = () => persist();

  addPassive(window, "scroll", onScroll, signal);
  addPassive(document, "scroll", onScroll, signal);
  addPassive(window, "wheel", onScroll, signal);
  addPassive(window, "touchmove", onScroll, signal);
  addPassive(window, "wheel", cancelRestoreLock, signal);
  addPassive(window, "touchmove", cancelRestoreLock, signal);
  window.addEventListener("keydown", onKey, { signal });
  window.addEventListener("pagehide", onHide, { signal });
  document.addEventListener(
    "visibilitychange",
    () => {
      if (document.visibilityState === "hidden") onHide();
    },
    { signal },
  );
  const stopAccountWatch = onAccountChange(onRemoteChange);

  let observer = null;
  if (typeof IntersectionObserver === "function") {
    observer = new IntersectionObserver(() => onScroll(), {
      root: null,
      rootMargin: "-20% 0px -65% 0px",
      threshold: [0, 0.25, 0.5, 1],
    });
    getReadingBlocks(container).forEach((el) => observer.observe(el));
  }

  if (restoreIndex != null || restorePreview) {
    restoring = true;
    applyRestore();
    requestAnimationFrame(applyRestore);
    RESTORE_RETRY_MS.forEach((ms) => {
      restoreTimers.push(setTimeout(applyRestore, ms));
    });
    restoreTimers.push(
      setTimeout(() => {
        restoring = false;
        baselineY = getScrollY();
        initialBlockIndex = Number(getActiveReadingBlock(container)?.dataset.readingBlock);
      }, 1100),
    );
    if (document.fonts?.ready) {
      document.fonts.ready.then(() => applyRestore()).catch(() => {});
    }
  } else {
    requestAnimationFrame(() => {
      baselineY = getScrollY();
      initialBlockIndex = Number(getActiveReadingBlock(container)?.dataset.readingBlock);
    });
  }

  // 本机恢复到的位置与其他设备的进度不同：提示是否跳到新位置
  const incoming = options.incoming;
  if (incoming?.slug) {
    const meta = getMeta?.() || {};
    const here = { slug: meta.slug, blockIndex: restoreIndex ?? 0 };
    const restoredHere = incoming.slug === meta.slug && incoming.blockIndex === restoreIndex;
    if (!restoredHere) prompt.show("incoming", incoming, { ahead: comparePosition(incoming, here) > 0 });
  }

  return () => {
    restoring = false;
    restoreTimers.splice(0).forEach((id) => clearTimeout(id));
    persist();
    stopped = true;
    stopAccountWatch();
    prompt.destroy();
    observer?.disconnect();
    abort.abort();
  };
}

function progressKey(p) {
  return p?.slug && Number.isInteger(Number(p.blockIndex)) ? `${p.slug}#${Number(p.blockIndex)}` : "";
}

function describePosition(p) {
  const volume = String(p?.volumeLabel || "").trim();
  const showVolume = volume && !["全一卷", "单篇", "單篇"].includes(volume);
  const preview = String(p?.textPreview || "").trim();
  const quote = preview ? `「${preview.length > 20 ? `${preview.slice(0, 20)}…` : preview}」` : `第 ${Number(p?.blockIndex) + 1} 段`;
  return `${showVolume ? `${volume} ` : ""}${quote}`;
}

// 阅读位置提示条：
// - incoming：其他设备上有新的阅读位置，是否跳过去
// - behind：当前位置在已保存的进度之前，进度未更新，需读者确认才覆盖
function createSyncPrompt({ onJump, onConfirm }) {
  let el = null;
  let target = null;
  let mode = "";
  let ahead = false;
  let dismissedKey = "";

  const hide = () => {
    if (!el) return;
    el.remove();
    el = null;
    target = null;
    mode = "";
  };

  // ahead：提示的位置在读者当前位置之后，读者自己读到那里时提示自动收起
  const show = (nextMode, progress, options = {}) => {
    const key = progressKey(progress);
    if (!key || key === dismissedKey) return;
    // 已在提示同一位置时，保留原来的说法（例如"其他设备上有新位置"不改成"进度未更新"）
    if (el && progressKey(target) === key && (mode === nextMode || mode === "incoming")) return;
    target = progress;
    mode = nextMode;
    ahead = Boolean(options.ahead);
    if (!el) {
      el = document.createElement("div");
      el.className = "reading-sync-prompt";
      el.setAttribute("role", "status");
      el.setAttribute("aria-live", "polite");
      el.addEventListener("click", (event) => {
        const action = event.target.closest("[data-sync-action]")?.dataset.syncAction;
        if (!action || !target) return;
        const current = target;
        if (action === "dismiss") dismissedKey = progressKey(current);
        hide();
        if (action === "jump") onJump(current);
        else if (action === "confirm") onConfirm(current);
      });
      document.body.appendChild(el);
    }
    const position = escapeHtml(describePosition(progress));
    const copy =
      mode === "incoming"
        ? `其他设备上有新的阅读位置：${position}，是否跳过去？`
        : `当前位置在已保存的进度之前，进度未更新。已读到：${position}`;
    el.innerHTML = `
      <p class="reading-sync-copy">${copy}</p>
      <div class="reading-sync-actions">
        <button class="primary-link" type="button" data-sync-action="jump">${mode === "incoming" ? "跳到新位置" : "回到已读位置"}</button>
        <button class="reading-sync-secondary" type="button" data-sync-action="confirm">以当前位置为进度</button>
        <button class="reading-sync-dismiss" type="button" data-sync-action="dismiss" aria-label="关闭阅读位置提示">关闭</button>
      </div>
    `;
  };

  return {
    show,
    hide,
    destroy: hide,
    // 读者的位置已不在已保存进度之前：收起"进度未更新"；读到了提示的新位置，也收起
    reached(position) {
      if (mode === "behind") hide();
      else if (mode === "incoming" && ahead && comparePosition(position, target) >= 0) hide();
    },
  };
}

export function mountResumeBanner(options = {}) {
  const { currentSlug = "" } = options;
  const existing = document.querySelector(".reading-resume-banner");
  if (existing) existing.remove();

  // 登录后进度在页头"收藏和进度"里，不再显示这个提示；只给未登录的读者用
  if (isLoggedIn()) return null;
  watchLoginForBanner();

  const progress = latestProgress();
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

let bannerWatcherBound = false;

// 在当前页登录后，立即收起提示
function watchLoginForBanner() {
  if (bannerWatcherBound) return;
  bannerWatcherBound = true;
  onAccountChange(() => {
    if (isLoggedIn()) document.querySelector(".reading-resume-banner")?.remove();
  });
}

function findRestoreTarget(container, blockIndex, textPreview) {
  const blocks = getReadingBlocks(container);
  if (!blocks.length) return null;
  const preview = normalizePreview(textPreview);

  if (preview) {
    const match = blocks.find((el) => {
      if (!isBlockVisible(el)) return false;
      const text = normalizePreview(el.textContent);
      return Boolean(text) && (text.startsWith(preview.slice(0, 16)) || preview.startsWith(text.slice(0, 16)));
    });
    if (match) return match;
  }

  return findVisibleRestoreTarget(blocks, blockIndex);
}

function findVisibleRestoreTarget(blocks, blockIndex) {
  if (!Number.isInteger(blockIndex) || blockIndex < 0) return null;
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
  const markerY = getReadMarkerY();
  const rect = container.getBoundingClientRect();
  const x = Math.min(Math.max(rect.left + 32, 24), window.innerWidth - 24);
  let node = document.elementFromPoint(x, markerY);
  while (node && node !== document.body) {
    if (node.dataset?.readingBlock && container.contains(node) && isBlockVisible(node)) {
      return node;
    }
    node = node.parentElement;
  }

  const blocks = getReadingBlocks(container).filter(isBlockVisible);
  if (!blocks.length) return null;
  let current = blocks[0];
  for (const el of blocks) {
    if (el.getBoundingClientRect().top <= markerY) current = el;
    else break;
  }
  return current;
}

function getReadMarkerY() {
  const header = document.querySelector(".site-header");
  if (header) {
    const style = window.getComputedStyle(header);
    const rect = header.getBoundingClientRect();
    if ((style.position === "sticky" || style.position === "fixed") && rect.bottom > 0) {
      return Math.min(rect.bottom + 18, window.innerHeight * 0.4);
    }
  }
  return Math.min(88, Math.max(48, window.innerHeight * 0.18));
}

function scrollToReadingBlock(target) {
  const markerY = getReadMarkerY();
  const y = Math.max(0, Math.round(target.getBoundingClientRect().top + getScrollY() - markerY));
  const root = document.documentElement;
  const previousBehavior = root.style.scrollBehavior;
  root.style.scrollBehavior = "auto";
  window.scrollTo(0, y);
  root.scrollTop = y;
  document.body.scrollTop = y;
  root.style.scrollBehavior = previousBehavior;
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

function getScrollY() {
  return window.scrollY || document.documentElement.scrollTop || document.body.scrollTop || 0;
}

function normalizePreview(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 48);
}

function addPassive(target, event, handler, signal) {
  target.addEventListener(event, handler, { passive: true, capture: true, signal });
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
