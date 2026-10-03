// 页头的"登录 / 我的收藏"入口，以及登录注册弹窗。
import { escapeHtml } from "./site-data.js";
import { getResumeUrl, readReadingProgress } from "./reading-progress.js?v=16";
import { getLibrary, getUser, isLoggedIn, login, logout, onAccountChange, refreshLibrary, register } from "./account-api.js?v=12";

const USERNAME_RE = /^[A-Za-z0-9_]{5,20}$/;
const PANEL_REFRESH_MS = 15_000;

let entryButton = null;
let panel = null;
let panelTimer = 0;
let lastSyncedAt = 0;
let dialog = null;
let dialogMode = "login";
let dialogOptions = {};

if (typeof document !== "undefined") {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
}

function init() {
  if (entryButton) return;
  const header = document.querySelector(".site-header");
  if (!header) return;
  const host = header.querySelector(".site-header-tools") || header.querySelector(".site-header-actions") || header;

  const wrap = document.createElement("div");
  wrap.className = "site-account";
  wrap.innerHTML = `
    <button class="site-account-button" type="button" aria-haspopup="true" aria-expanded="false"></button>
    <div class="site-account-panel" hidden></div>
  `;
  host.appendChild(wrap);
  entryButton = wrap.querySelector(".site-account-button");
  panel = wrap.querySelector(".site-account-panel");

  entryButton.addEventListener("click", () => {
    if (!isLoggedIn()) openAccountDialog();
    else togglePanel();
  });
  document.addEventListener("click", (event) => {
    if (!panel.hidden && !wrap.contains(event.target)) togglePanel(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) togglePanel(false);
  });
  panel.addEventListener("click", async (event) => {
    if (event.target.closest("[data-account-logout]")) {
      togglePanel(false);
      await logout();
    } else if (event.target.closest("[data-account-refresh]")) {
      syncPanel();
    } else if (event.target.closest("a")) {
      togglePanel(false);
    }
  });

  onAccountChange(render);
  render();
  refreshLibrary();
}

function render() {
  if (!entryButton) return;
  const user = getUser();
  entryButton.textContent = user ? `收藏和进度 · ${user.username}` : "登录";
  entryButton.setAttribute("aria-haspopup", user ? "true" : "dialog");
  if (!user) togglePanel(false);
  else if (!panel.hidden) renderPanel();
}

function togglePanel(open = panel.hidden) {
  panel.hidden = !open;
  entryButton.setAttribute("aria-expanded", String(open));
  clearInterval(panelTimer);
  panelTimer = 0;
  if (open) {
    renderPanel();
    syncPanel();
    // 打开期间定期拉取最新进度（包括其他设备上的）
    panelTimer = setInterval(syncPanel, PANEL_REFRESH_MS);
  }
}

async function syncPanel() {
  if (!isLoggedIn()) return;
  panel.classList.add("is-syncing");
  await refreshLibrary();
  lastSyncedAt = Date.now();
  panel.classList.remove("is-syncing");
  if (!panel.hidden) renderPanel();
}

function renderPanel() {
  const user = getUser();
  const items = [...getLibrary()].sort((a, b) => sortTime(b) - sortTime(a));
  const favoriteIds = new Set(items.map((item) => item.workId));
  // 本机最后读的经若未收藏，也列出来（只存在本机，不同步）
  const local = readReadingProgress();
  const localWorkId = local?.slug?.replace(/-\d+$/, "");
  const localItem =
    local && !favoriteIds.has(localWorkId)
      ? `<p class="site-account-subheading">最近阅读（未收藏，仅本机）</p>
         <ul class="site-account-list">${renderItem({ workId: localWorkId, title: local.title, progress: local })}</ul>`
      : "";
  const list = items.length
    ? `<ul class="site-account-list">${items.map(renderItem).join("")}</ul>`
    : `<p class="site-account-empty">还没有收藏的经文。在阅读页点击"收藏本经"，阅读进度就会在多台设备间同步。</p>`;
  panel.innerHTML = `
    <div class="site-account-top">
      <p class="site-account-heading">收藏和进度</p>
      <button class="site-account-refresh" type="button" data-account-refresh title="立即刷新">
        ${lastSyncedAt ? `${formatTime(lastSyncedAt)} 已同步` : "同步中…"} · 刷新
      </button>
    </div>
    ${list}
    ${localItem}
    <div class="site-account-footer">
      <span>${escapeHtml(user?.username || "")}</span>
      <button type="button" data-account-logout>退出登录</button>
    </div>
  `;
}

function sortTime(item) {
  return Number(item.progress?.savedAt) || Number(item.createdAt) || 0;
}

function renderItem(item) {
  const p = item.progress;
  const title = item.title || p?.title || item.workId;
  const url = p ? getResumeUrl(p.slug, p.blockIndex) : getResumeUrl(`${item.workId}-001`);
  const volume = p?.volumeLabel && !["全一卷", "单篇", "單篇"].includes(p.volumeLabel) ? p.volumeLabel : "";
  const where = p ? (volume ? `读到${volume}` : "读到") : "尚未开始阅读";
  const preview = p?.textPreview ? `<span class="site-account-preview">${escapeHtml(p.textPreview.slice(0, 24))}…</span>` : "";
  const when = p?.savedAt ? `<span class="site-account-when">${escapeHtml(formatAgo(p.savedAt))}</span>` : "";
  return `
    <li>
      <a href="${escapeHtml(url)}">
        <strong>《${escapeHtml(title)}》</strong>
        <span class="site-account-where">${escapeHtml(where)} ${when}</span>
        ${preview}
      </a>
    </li>
  `;
}

function formatAgo(ms) {
  const diff = Math.max(0, Date.now() - ms);
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} 天前`;
  const d = new Date(ms);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function formatTime(ms) {
  const d = new Date(ms);
  return [d.getHours(), d.getMinutes(), d.getSeconds()].map((n) => String(n).padStart(2, "0")).join(":");
}

// ── 登录 / 注册弹窗 ─────────────────────────────────────────

export function openAccountDialog(options = {}) {
  dialogOptions = options;
  ensureDialog();
  setMode("login");
  dialog.querySelector(".account-dialog-reason").textContent = options.reason || "";
  dialog.querySelector(".account-dialog-reason").hidden = !options.reason;
  dialog.querySelector("form").reset();
  setError("");
  dialog.showModal();
  dialog.querySelector("input[name=username]").focus();
}

function ensureDialog() {
  if (dialog) return;
  dialog = document.createElement("dialog");
  dialog.className = "account-dialog";
  dialog.innerHTML = `
    <form method="dialog" novalidate>
      <div class="account-dialog-top">
        <div class="account-dialog-tabs" role="tablist">
          <button type="button" role="tab" data-mode="login">登录</button>
          <button type="button" role="tab" data-mode="register">注册</button>
        </div>
        <button class="account-dialog-close" type="button" aria-label="关闭">×</button>
      </div>
      <p class="account-dialog-reason" hidden></p>
      <label>
        <span>用户名</span>
        <input name="username" autocomplete="username" autocapitalize="off" spellcheck="false" required />
        <small data-register-only>5–20 位，字母、数字或下划线</small>
      </label>
      <label>
        <span>密码</span>
        <input name="password" type="password" autocomplete="current-password" required />
        <small data-register-only>至少 5 位</small>
      </label>
      <label data-register-only>
        <span>邮箱（选填）</span>
        <input name="email" type="email" autocomplete="email" />
        <small>以后可用于找回密码</small>
      </label>
      <p class="account-dialog-error" role="alert" hidden></p>
      <button class="primary-link account-dialog-submit" type="submit"></button>
    </form>
  `;
  document.body.appendChild(dialog);

  dialog.querySelectorAll("[data-mode]").forEach((tab) => {
    tab.addEventListener("click", () => {
      setMode(tab.dataset.mode);
      setError("");
    });
  });
  dialog.querySelector(".account-dialog-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.querySelector("form").addEventListener("submit", onSubmit);
}

function setMode(mode) {
  dialogMode = mode;
  const isRegister = mode === "register";
  dialog.querySelectorAll("[data-mode]").forEach((tab) => {
    const active = tab.dataset.mode === mode;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  dialog.querySelectorAll("[data-register-only]").forEach((el) => {
    el.hidden = !isRegister;
  });
  dialog.querySelector("input[name=password]").autocomplete = isRegister ? "new-password" : "current-password";
  dialog.querySelector(".account-dialog-submit").textContent = isRegister ? "注册并登录" : "登录";
}

function setError(message) {
  const el = dialog.querySelector(".account-dialog-error");
  el.textContent = message;
  el.hidden = !message;
}

async function onSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const username = form.username.value.trim();
  const password = form.password.value;
  const email = form.email.value.trim();

  if (dialogMode === "register") {
    if (!USERNAME_RE.test(username)) return setError("用户名需 5–20 位，只能包含字母、数字、下划线");
    if (password.length < 5) return setError("密码至少 5 位");
  } else if (!username || !password) {
    return setError("请输入用户名和密码");
  }

  const submit = form.querySelector(".account-dialog-submit");
  submit.disabled = true;
  setError("");
  try {
    if (dialogMode === "register") await register({ username, password, email });
    else await login({ username, password });
    dialog.close();
    const { onSuccess } = dialogOptions;
    dialogOptions = {};
    onSuccess?.();
  } catch (error) {
    setError(error.message || "操作失败，请稍后再试");
  } finally {
    submit.disabled = false;
  }
}
