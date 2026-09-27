// 账号、收藏与阅读进度云同步。
// 未登录时什么都不做；登录后，已收藏经文的阅读进度会同步到后端。
// 注意：所有文件都必须用同一个 URL（含 ?v=）导入本模块，才能共享同一份状态。

// 本地开发时可在控制台执行 localStorage.setItem("sutra_api_base", "http://localhost:8787") 连接本地后端
export const API_BASE = readApiOverride() || "https://sutratoday-api.jeffwoo2019.workers.dev";

const SESSION_KEY = "sutra_account_session";
const LIBRARY_KEY = "sutra_account_library";
const SYNC_DELAY_MS = 3000;
const REFRESH_TIMEOUT_MS = 2000;

let session = readJson(SESSION_KEY);
let library = readJson(LIBRARY_KEY) || [];
let pendingProgress = new Map();
let syncTimer = 0;
let refreshPromise = null;

if (typeof window !== "undefined") {
  window.addEventListener("pagehide", () => flushProgress(true));
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") flushProgress(true);
  });
  // 其他标签页登录/退出时同步状态
  window.addEventListener("storage", (event) => {
    if (event.key === SESSION_KEY) {
      session = readJson(SESSION_KEY);
      if (!session) setLibrary([]);
      emit();
    } else if (event.key === LIBRARY_KEY) {
      library = readJson(LIBRARY_KEY) || [];
      emit();
    }
  });
}

// ── 状态 ────────────────────────────────────────────────────

export function getUser() {
  return session?.user || null;
}

export function isLoggedIn() {
  return Boolean(session?.token);
}

export function onAccountChange(handler) {
  window.addEventListener("sutra:account", handler);
  return () => window.removeEventListener("sutra:account", handler);
}

export function workIdFromSlug(slug) {
  return String(slug || "").replace(/-\d+$/, "");
}

export function getLibrary() {
  return library;
}

export function getFavorite(workId) {
  return library.find((item) => item.workId === workId) || null;
}

export function isFavorite(workId) {
  return Boolean(getFavorite(workId));
}

// ── 登录 / 注册 ─────────────────────────────────────────────

export async function register({ username, password, email }) {
  const data = await request("POST", "/auth/register", { username, password, email: email || undefined }, false);
  await startSession(data);
  return data.user;
}

export async function login({ username, password }) {
  const data = await request("POST", "/auth/login", { username, password }, false);
  await startSession(data);
  return data.user;
}

export async function logout() {
  await flushProgress();
  try {
    await request("POST", "/auth/logout");
  } catch {
    // 即使网络失败也清掉本地登录态
  }
  clearSession();
}

async function startSession(data) {
  session = { token: data.token, user: data.user };
  writeJson(SESSION_KEY, session);
  emit();
  await refreshLibrary();
  await pushLocalProgress();
}

function clearSession() {
  session = null;
  pendingProgress.clear();
  removeKey(SESSION_KEY);
  setLibrary([]);
}

// ── 收藏 ────────────────────────────────────────────────────

// 拉取最新书架。已在请求中时复用同一个请求。
export function refreshLibrary() {
  if (!isLoggedIn()) return Promise.resolve(library);
  if (!refreshPromise) {
    refreshPromise = request("GET", "/library")
      .then((data) => {
        setLibrary(data.favorites || []);
        return library;
      })
      .catch(() => library)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

// 等待书架刷新，但最多等 REFRESH_TIMEOUT_MS，避免网络慢时卡住阅读页
export function refreshLibraryWithTimeout(ms = REFRESH_TIMEOUT_MS) {
  if (!isLoggedIn()) return Promise.resolve(library);
  return Promise.race([refreshLibrary(), new Promise((resolve) => setTimeout(() => resolve(library), ms))]);
}

export async function addFavorite(workId, title, progress = null) {
  const body = { title: title || "" };
  if (progress && workIdFromSlug(progress.slug) === workId) body.progress = toApiProgress(progress);
  const saved = await request("PUT", `/favorites/${encodeURIComponent(workId)}`, body);
  setLibrary([saved, ...library.filter((item) => item.workId !== workId)]);
  return saved;
}

export async function removeFavorite(workId) {
  await request("DELETE", `/favorites/${encodeURIComponent(workId)}`);
  pendingProgress.delete(workId);
  setLibrary(library.filter((item) => item.workId !== workId));
}

// ── 阅读进度 ────────────────────────────────────────────────

// 由 reading-progress.js 在每次本地保存后调用；只同步已收藏的经文
export function queueProgressSync(progress) {
  if (!isLoggedIn() || !progress?.slug) return;
  const workId = workIdFromSlug(progress.slug);
  const fav = getFavorite(workId);
  if (!fav) return;

  const next = toApiProgress(progress);
  fav.progress = { workId, ...next };
  writeJson(LIBRARY_KEY, library);
  pendingProgress.set(workId, next);
  clearTimeout(syncTimer);
  syncTimer = setTimeout(() => flushProgress(), SYNC_DELAY_MS);
}

// 取本经文在云端（缓存）中的进度
export function getRemoteProgress(workId) {
  return getFavorite(workId)?.progress || null;
}

export async function flushProgress(keepalive = false) {
  clearTimeout(syncTimer);
  if (!isLoggedIn() || !pendingProgress.size) return;
  const entries = [...pendingProgress.entries()];
  pendingProgress = new Map();
  await Promise.all(
    entries.map(([workId, progress]) =>
      request("PUT", `/progress/${encodeURIComponent(workId)}`, progress, true, keepalive).catch((error) => {
        // 网络失败时放回队列，下次再试；未收藏（409）等错误直接丢弃
        if (error.status === 0 && !pendingProgress.has(workId)) pendingProgress.set(workId, progress);
      }),
    ),
  );
}

// 登录后，把本机最后一次阅读位置合并到云端（若该经已收藏，服务器保留较新的一条）
async function pushLocalProgress() {
  const { readReadingProgress } = await import("./reading-progress.js?v=5");
  const local = readReadingProgress();
  if (local) queueProgressSync(local);
  await flushProgress();
}

function toApiProgress(p) {
  return {
    slug: p.slug,
    blockIndex: p.blockIndex,
    textPreview: p.textPreview || "",
    title: p.title || "",
    volumeLabel: p.volumeLabel || "",
    savedAt: p.savedAt || Date.now(),
  };
}

// ── 工具 ────────────────────────────────────────────────────

async function request(method, path, body, auth = true, keepalive = false) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth && session?.token) headers.Authorization = `Bearer ${session.token}`;

  let res;
  try {
    res = await fetch(API_BASE + path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      keepalive,
    });
  } catch {
    throw makeError(0, "network_error", "网络连接失败，请稍后再试");
  }

  let data = {};
  try {
    data = await res.json();
  } catch {
    // 非 JSON 响应
  }
  if (!res.ok) {
    if (res.status === 401 && auth) clearSession();
    throw makeError(res.status, data.error || "error", data.message || "请求失败，请稍后再试");
  }
  return data;
}

function makeError(status, code, message) {
  const error = new Error(message);
  error.status = status;
  error.code = code;
  return error;
}

function setLibrary(next) {
  library = next;
  if (next.length) writeJson(LIBRARY_KEY, next);
  else removeKey(LIBRARY_KEY);
  emit();
}

function emit() {
  window.dispatchEvent(new CustomEvent("sutra:account"));
}

function readApiOverride() {
  try {
    const value = localStorage.getItem("sutra_api_base");
    return value && /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(value) ? value : "";
  } catch {
    return "";
  }
}

function readJson(key) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeJson(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // 无痕模式或禁用存储时忽略
  }
}

function removeKey(key) {
  try {
    localStorage.removeItem(key);
  } catch {
    // ignore
  }
}
