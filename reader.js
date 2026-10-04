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
import {
  assignReadingAnchors,
  mountResumeBanner,
  readHashBlockIndex,
  planRestore,
  readReadingProgress,
  startReadingProgressTracker,
  workTitleForProgress,
} from "./reading-progress.js?v=16";
import {
  addFavorite,
  checkin,
  getCheckins,
  getUser,
  isFavorite,
  isLoggedIn,
  onAccountChange,
  refreshLibraryWithTimeout,
  removeFavorite,
  suggestRetranslate,
  workIdFromSlug,
} from "./account-api.js?v=12";
import { openAccountDialog } from "./account.js?v=12";
import { bindSentenceSync, clearSentenceSync, setupSentenceSync } from "./sentence-sync.js?v=1";
import { flagTranslationIssue, initComments, loadComments } from "./comments.js?v=9";
import { openCheckinShare } from "./checkin-share.js?v=1";

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
  checkin: document.getElementById("reader-checkin"),
  comments: document.getElementById("reader-comments"),
};

let currentDocument = null;
let selectedQuote = "";
let selectedContext = { sid: "", target: "" };
let selectionSyncFrame = 0;
let lastSelectionRect = null;
let feedbackPanelOpen = false;
let currentLoadId = 0;
let worksIndex = null;
let stopReadingProgress = null;
const documentCache = new Map();
let bootHashIndex = readHashBlockIndex();
let libraryReady = null;
let favoriteButton = null;
let favoriteBusy = false;
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
  const slug = getCurrentSlug() || "";
  mountResumeBanner();
  dom.title.textContent = "经文未找到";
  dom.rendered.innerHTML = `
    <div class="reader-error">
      <p>抱歉，未能找到经文「<strong>${escapeHtml(slug)}</strong>」。</p>
      <p>可能的原因：</p>
      <ul>
        <li>该经文编号不存在或链接已过期</li>
        <li>本站近期更新了经文编号格式（如 T0251-001）</li>
      </ul>
      <p>您可以：</p>
      <ul>
        <li><a href="./catalog.html">前往经文目录</a>搜索您要阅读的经典</li>
        <li><a href="./index.html">返回首页</a>浏览精选经目</li>
      </ul>
    </div>
  `;
});

async function init() {
  bindReadingModePicker();
  bindFontPicker();
  applyReadingMode(readingMode);
  applyFontSize(fontSize);
  bindSelectionFeedback();
  bindSentenceSync(dom.rendered, () => readingMode === READING_MODE_DEFAULT);
  bindFavoriteButton();
  bindRetranslateButtons();
  if (dom.comments) initComments({ container: dom.comments, showToast, onJumpToParagraph: jumpToParagraph });
  // 只在登录 / 退出时刷新打卡区（进度更新也会触发账号事件）
  let checkinUserId = getUser()?.id ?? null;
  onAccountChange(() => {
    const userId = getUser()?.id ?? null;
    if (userId === checkinUserId) return;
    checkinUserId = userId;
    if (currentDocument) renderCheckins(currentDocument);
  });
  // 登录用户先拉取云端进度（最多等 2 秒），与经文加载并行
  libraryReady = refreshLibraryWithTimeout();

  // Load works index for volume navigation
  worksIndex = await loadWorksIndex();

  await selectCurrent();
  window.addEventListener("hashchange", () => {
    if (isParagraphHashChange()) return;
    selectCurrent().catch(handleReaderLoadError);
  });
  window.addEventListener("popstate", () => {
    selectCurrent().catch(handleReaderLoadError);
  });
}

async function selectCurrent() {
  const requestedSlug = getCurrentSlug();
  const hashIndex = readHashBlockIndex() ?? bootHashIndex;
  bootHashIndex = null;
  const slug = requestedSlug || "T0251-001"; // Default to Heart Sutra
  const loadId = ++currentLoadId;
  const selected = await getDocumentBySlug(slug);

  if (loadId !== currentLoadId) return;
  stopReadingProgressTracker();
  syncReaderUrl(selected.slug, hashIndex);
  if (loadId !== currentLoadId) return;

  currentDocument = selected;

  const translationBadge = getTranslationState(selected.translation_status);
  const reviewBadge = getReviewState(selected.review_status);

  dom.title.textContent = selected.title;
  dom.summary.textContent = selected.summary || "";
  dom.rendered.innerHTML = renderMarkdown(selected.body);
  setupSentenceSync(dom.rendered);
  mountRetranslateButtons(selected);
  renderVolumeNavigation(selected);
  renderCheckins(selected);
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
  loadComments(selected.slug);
  renderFavoriteButton();
  await libraryReady;
  if (loadId !== currentLoadId) return;
  restoreAndTrackReadingProgress(selected, hashIndex);
  mountResumeBanner({ currentSlug: selected.slug });
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
  clearSentenceSync(dom.rendered);
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

function restoreAndTrackReadingProgress(doc, hashIndex) {
  assignReadingAnchors(dom.rendered);
  // 优先恢复到本机自己读到的位置；其他设备上的进度不同时，由阅读器提示是否跳过去
  const { restore: saved, incoming } = planRestore(doc.slug);
  let restoreIndex = null;
  let restorePreview = "";
  if (hashIndex != null) restoreIndex = hashIndex;
  else if (saved) {
    restoreIndex = saved.blockIndex;
    restorePreview = saved.textPreview || "";
  }

  const work = worksIndex ? getWorkBySlug(worksIndex, doc.slug) : null;
  const title = workTitleForProgress(doc, work);
  stopReadingProgress = startReadingProgressTracker(
    dom.rendered,
    () => ({
      slug: currentDocument?.slug || doc.slug,
      title,
      volumeLabel: (currentDocument || doc).volume_label || "",
    }),
    { restoreIndex, restorePreview, incoming },
  );
}

// ── 收藏 ───────────────────────────────────────────────────

function bindFavoriteButton() {
  const actions = document.querySelector(".reader-actions");
  if (!actions) return;
  favoriteButton = document.createElement("button");
  favoriteButton.type = "button";
  favoriteButton.className = "reader-favorite-button";
  favoriteButton.hidden = true;
  actions.prepend(favoriteButton);
  favoriteButton.addEventListener("click", () => toggleFavorite());
  onAccountChange(renderFavoriteButton);
}

function currentWork() {
  if (!currentDocument) return null;
  const workId = workIdFromSlug(currentDocument.slug);
  const work = worksIndex ? getWorkBySlug(worksIndex, currentDocument.slug) : null;
  return { workId, title: workTitleForProgress(currentDocument, work) };
}

function renderFavoriteButton() {
  if (!favoriteButton) return;
  const work = currentWork();
  favoriteButton.hidden = !work;
  if (!work) return;
  const active = isLoggedIn() && isFavorite(work.workId);
  favoriteButton.classList.toggle("is-active", active);
  favoriteButton.setAttribute("aria-pressed", String(active));
  favoriteButton.disabled = favoriteBusy;
  favoriteButton.textContent = active ? "★ 已收藏" : "☆ 收藏本经";
  favoriteButton.title = active ? "取消收藏" : "收藏后，阅读进度会在多台设备间同步";
}

async function toggleFavorite() {
  const work = currentWork();
  if (!work || favoriteBusy) return;
  if (!isLoggedIn()) {
    openAccountDialog({
      reason: "登录后即可收藏经文，并在多台设备间同步阅读进度。",
      onSuccess: () => {
        if (!isFavorite(work.workId)) toggleFavorite();
      },
    });
    return;
  }
  favoriteBusy = true;
  renderFavoriteButton();
  try {
    if (isFavorite(work.workId)) {
      await removeFavorite(work.workId);
    } else {
      const local = readReadingProgress();
      await addFavorite(work.workId, work.title, local?.slug && workIdFromSlug(local.slug) === work.workId ? local : null);
    }
  } catch (error) {
    alert(error.message || "操作失败，请稍后再试");
  } finally {
    favoriteBusy = false;
    renderFavoriteButton();
  }
}

// ── 建议重翻 ───────────────────────────────────────────────

const RETRANSLATE_SENT_KEY = "sutra_retranslate_sent";
const RETRANSLATE_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false"><path d="M4.5 12a7.5 7.5 0 0 1 12.8-5.3M19.5 12a7.5 7.5 0 0 1-12.8 5.3" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M17.8 3.5v3.7h-3.7M6.2 20.5v-3.7h3.7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const RETRANSLATE_SENT_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false"><path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

// 从 markdown 源文按 sid 取出原文与译文，保证提交的是源文件里的文字（不受繁简切换影响）
function extractParagraphSources(body) {
  const sections = new Map();
  let tone = null;
  let sid = "";
  for (const line of String(body || "").replace(/\r\n/g, "\n").split("\n")) {
    const heading = line.match(/^(#{1,4})\s+(.*)$/);
    if (heading) {
      const text = heading[2].trim();
      tone =
        heading[1].length >= 3 && text === "原文"
          ? "original"
          : heading[1].length >= 3 && (text === "现代语译" || text === "現代語譯")
            ? "translation"
            : null;
      sid = "";
      continue;
    }
    const sidMatch = line.trim().match(/^<!--\s*sid:\s*([\w.-]+)\s*-->$/);
    if (sidMatch) {
      sid = sidMatch[1];
      continue;
    }
    if (!tone || !sid) continue;
    if (!sections.has(sid)) sections.set(sid, { original: [], translation: [] });
    sections.get(sid)[tone].push(line);
  }
  const result = new Map();
  sections.forEach((value, key) => {
    const original = value.original.join("\n").trim();
    const translation = value.translation.join("\n").trim();
    if (original && translation) result.set(key, { original, translation });
  });
  return result;
}

function readSentRetranslations() {
  try {
    return new Set(JSON.parse(localStorage.getItem(RETRANSLATE_SENT_KEY) || "[]"));
  } catch {
    return new Set();
  }
}

function rememberSentRetranslation(key) {
  const sent = readSentRetranslations();
  sent.add(key);
  try {
    localStorage.setItem(RETRANSLATE_SENT_KEY, JSON.stringify([...sent].slice(-500)));
  } catch {
    // ignore
  }
}

function mountRetranslateButtons(doc) {
  const sources = extractParagraphSources(doc.body);
  const sent = readSentRetranslations();
  const groups = new Map();
  dom.rendered.querySelectorAll(".sutra-translation[data-sid]").forEach((el) => {
    const group = groups.get(el.dataset.sid) || [];
    group.push(el);
    groups.set(el.dataset.sid, group);
  });

  groups.forEach((elements, sid) => {
    if (!sources.has(sid)) return;
    const state = sent.has(`${doc.slug}#${sid}`) ? "sent" : "idle";
    // 图标放在每段译文前的「现代语译」小标题后面
    const heading = elements[0].previousElementSibling;
    if (heading?.classList.contains("sutra-translation-heading")) {
      heading.append(createRetranslateButton(sid, state));
    }
    // 「只读现代语译」模式会隐藏小标题，此时改用段末的图标（其他模式下由 CSS 隐藏）
    const last = elements[elements.length - 1];
    const fallback = createRetranslateButton(sid, state);
    fallback.classList.add("retranslate-button-inline");
    if (last.tagName === "P" || last.tagName === "BLOCKQUOTE") last.append(fallback);
    else last.insertAdjacentElement("afterend", fallback);
  });
}

function createRetranslateButton(sid, state) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "retranslate-button";
  button.dataset.sid = sid;
  setRetranslateState(button, state);
  return button;
}

function setRetranslateState(button, state) {
  button.dataset.state = state;
  button.disabled = state !== "idle";
  const label = state === "sent" ? "已提交重翻建议" : state === "sending" ? "正在提交…" : "建议重翻这段译文";
  button.setAttribute("aria-label", label);
  button.title = label;
  button.innerHTML = state === "sent" ? RETRANSLATE_SENT_ICON : RETRANSLATE_ICON;
}

function bindRetranslateButtons() {
  dom.rendered.addEventListener("click", async (event) => {
    const button = event.target.closest(".retranslate-button");
    if (!button || !currentDocument) return;
    // 不触发原文/译文对照高亮
    event.stopPropagation();
    if (button.dataset.state !== "idle") return;

    const doc = currentDocument;
    const sid = button.dataset.sid;
    const source = extractParagraphSources(doc.body).get(sid);
    if (!source) return;
    const work = currentWork();
    const siblings = dom.rendered.querySelectorAll(`.retranslate-button[data-sid="${CSS.escape(sid)}"]`);
    siblings.forEach((el) => setRetranslateState(el, "sending"));
    try {
      await suggestRetranslate({
        slug: doc.slug,
        sid,
        title: work?.title || doc.title || "",
        volumeLabel: doc.volume_label || "",
        original: source.original,
        translation: source.translation,
      });
      rememberSentRetranslation(`${doc.slug}#${sid}`);
      dom.rendered.querySelectorAll(`.retranslate-button[data-sid="${CSS.escape(sid)}"]`).forEach((el) => setRetranslateState(el, "sent"));
      showToast("已提交重翻建议，谢谢！");
    } catch (error) {
      siblings.forEach((el) => setRetranslateState(el, "idle"));
      showToast(error.message || "提交失败，请稍后再试");
    }
  });
}

let toastTimer = 0;
function showToast(message) {
  let toast = document.querySelector(".reader-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.className = "reader-toast";
    toast.setAttribute("role", "status");
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add("is-visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("is-visible"), 2400);
}

// ── 打卡 ───────────────────────────────────────────────────

let checkinRenderId = 0;

// 多卷经：每卷卷末可打卡，最后一卷另有"全经"打卡；单卷经只有"全经"打卡
function getCheckinTargets(doc) {
  const work = worksIndex ? getWorkBySlug(worksIndex, doc.slug) : null;
  const workId = workIdFromSlug(doc.slug);
  const title = workTitleForProgress(doc, work);
  const volumes = Array.isArray(work?.volumes) ? work.volumes : [];
  const volumeLabel = doc.volume_label || "";
  if (volumes.length <= 1) {
    return [{ workId, slug: "", title, volumeLabel: "", heading: "读毕本经", action: "读毕打卡" }];
  }
  const targets = [
    {
      workId,
      slug: doc.slug,
      title,
      volumeLabel,
      heading: `读毕本卷${volumeLabel ? `（${volumeLabel}）` : ""}`,
      action: "本卷打卡",
    },
  ];
  const lastVolume = volumes[volumes.length - 1];
  if ((Array.isArray(lastVolume) ? lastVolume[0] : lastVolume) === doc.slug) {
    targets.push({ workId, slug: "", title, volumeLabel: "", heading: `读毕全经《${title}》`, action: "全经打卡" });
  }
  return targets;
}

async function renderCheckins(doc) {
  if (!dom.checkin) return;
  const renderId = ++checkinRenderId;
  const targets = getCheckinTargets(doc);
  dom.checkin.hidden = false;
  dom.checkin.innerHTML = targets.map((t, i) => checkinCardMarkup(t, i, null)).join("");

  const summaries = await Promise.all(targets.map((t) => getCheckins(t.workId, t.slug).catch(() => null)));
  if (renderId !== checkinRenderId) return;
  dom.checkin.innerHTML = targets.map((t, i) => checkinCardMarkup(t, i, summaries[i])).join("");
  dom.checkin.querySelectorAll("[data-checkin-index]").forEach((button) => {
    button.addEventListener("click", () => onCheckinClick(doc, targets[Number(button.dataset.checkinIndex)], button));
  });
  dom.checkin.querySelectorAll("[data-checkin-share]").forEach((button) => {
    button.addEventListener("click", () => shareCheckin(doc, targets[Number(button.dataset.checkinShare)]));
  });
}

// 分享图里的二维码：卷打卡指向本卷，全经打卡指向第一卷
function shareCheckin(doc, target) {
  const work = worksIndex ? getWorkBySlug(worksIndex, doc.slug) : null;
  const first = Array.isArray(work?.volumes) ? work.volumes[0] : null;
  const firstSlug = (Array.isArray(first) ? first[0] : first) || doc.slug;
  openCheckinShare({
    title: target.title,
    slug: target.slug,
    volumeLabel: target.volumeLabel,
    qrSlug: target.slug || firstSlug,
    username: getUser()?.username || "",
  });
}

function checkinCardMarkup(target, index, summary) {
  const done = Boolean(summary?.mine?.checkedInToday);
  const loggedIn = isLoggedIn();
  const buttonLabel = done ? "今日已打卡" : loggedIn ? target.action : "登录后打卡";
  const records = summary?.recent?.length
    ? `<ul class="reader-checkin-list">${summary.recent
        .map(
          (r) =>
            `<li><strong>${escapeHtml(r.username)}</strong> 于 ${escapeHtml(formatCheckinDate(r.createdAt))} 已阅读</li>`,
        )
        .join("")}</ul>`
    : summary
      ? `<p class="reader-checkin-empty">还没有人打卡，来做第一个吧。</p>`
      : `<p class="reader-checkin-empty">正在加载打卡记录…</p>`;
  const more =
    summary && summary.total > summary.recent.length
      ? `<p class="reader-checkin-more">共 ${summary.total} 次打卡，显示最近 ${summary.recent.length} 条</p>`
      : "";
  return `
    <div class="reader-checkin-card">
      <div class="reader-checkin-head">
        <div>
          <p class="reader-checkin-title">${escapeHtml(target.heading)}</p>
          ${summary ? `<p class="reader-checkin-count">已有 ${summary.total} 次打卡</p>` : ""}
        </div>
        <div class="reader-checkin-buttons">
          <button class="primary-link reader-checkin-button" type="button" data-checkin-index="${index}" ${done ? "disabled" : ""}>
            ${escapeHtml(buttonLabel)}
          </button>
          ${done ? `<button class="reader-checkin-share" type="button" data-checkin-share="${index}">分享打卡</button>` : ""}
        </div>
      </div>
      ${records}
      ${more}
    </div>
  `;
}

async function onCheckinClick(doc, target, button) {
  if (!isLoggedIn()) {
    openAccountDialog({
      reason: "登录后即可打卡，打卡记录会显示在经文末尾。",
      onSuccess: () => onCheckinClick(doc, target, button),
    });
    return;
  }
  button.disabled = true;
  try {
    await checkin(target);
    showToast(`${getUser()?.username || ""} 打卡成功，随喜功德！可以点"分享打卡"生成分享图`);
  } catch (error) {
    showToast(error.message || "打卡失败，请稍后再试");
  }
  if (currentDocument === doc) renderCheckins(doc);
}

function formatCheckinDate(ms) {
  const d = new Date(ms);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function stopReadingProgressTracker() {
  if (!stopReadingProgress) return;
  stopReadingProgress();
  stopReadingProgress = null;
}

function isParagraphHashChange() {
  const slug = getCurrentSlug();
  if (currentDocument && slug && slug === currentDocument.slug) return true;
  return false;
}

function syncReaderUrl(slug, blockIndex) {
  const paragraphHash =
    Number.isInteger(blockIndex) && blockIndex >= 0
      ? `#p-${blockIndex}`
      : /^#p-\d+$/.test(location.hash)
        ? location.hash
        : "";
  const nextRelativeUrl = `${getReaderUrl(slug)}${paragraphHash}`;
  const nextSearch = `?doc=${encodeURIComponent(slug)}`;
  if (location.search !== nextSearch || location.hash !== paragraphHash) {
    history.replaceState(null, "", nextRelativeUrl);
  }
}

function handleReaderLoadError() {
  stopReadingProgressTracker();
  mountResumeBanner();
  const slug = getCurrentSlug() || "";
  dom.title.textContent = "加载失败";
  dom.rendered.innerHTML = `
    <div class="reader-error">
      <p>经文「<strong>${escapeHtml(slug)}</strong>」加载失败。</p>
      <p>您可以<a href="./catalog.html">前往经文目录</a>搜索其他经典，或稍后重试。</p>
    </div>
  `;
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
  dom.selectionFeedbackLink.addEventListener("click", async (event) => {
    event.preventDefault();
    const quote = selectedQuote || dom.selectionFeedback.dataset.pendingQuote;
    if (!quote) return;
    const context = { ...selectedContext };
    // 登录框会清掉选区，先收起气泡；flagTranslationIssue 会在登录成功后继续提交
    clearSelection();
    resetSelectionFeedback();
    await flagTranslationIssue({ quote, sid: context.sid, target: context.target });
  });
}

// 选区所在段落的 sid，以及是在原文还是译文里
function getSelectionContext(selection) {
  const range = selection.getRangeAt(0);
  const node = range.startContainer.nodeType === Node.ELEMENT_NODE ? range.startContainer : range.startContainer.parentElement;
  const block = node?.closest?.("[data-sid]");
  if (!block || !dom.rendered.contains(block)) return { sid: "", target: "" };
  const target = block.classList.contains("sutra-original") ? "original" : block.classList.contains("sutra-translation") ? "translation" : "";
  return { sid: block.dataset.sid || "", target };
}

// 评论区"查看段落"：滚动到对应段落并短暂高亮
function jumpToParagraph(sid, target) {
  const escaped = CSS.escape(sid);
  const selector = target ? `.sutra-${target}[data-sid="${escaped}"]` : `[data-sid="${escaped}"]`;
  const el = dom.rendered.querySelector(selector) || dom.rendered.querySelector(`[data-sid="${escaped}"]`);
  if (!el) {
    showToast("找不到这一段，经文可能已更新");
    return;
  }
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.classList.add("is-flash");
  setTimeout(() => el.classList.remove("is-flash"), 1800);
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
  selectedContext = getSelectionContext(selection);
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

function resetSelectionFeedback() {
  if (selectionSyncFrame) { cancelAnimationFrame(selectionSyncFrame); selectionSyncFrame = 0; }
  selectedQuote = "";
  selectedContext = { sid: "", target: "" };
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

