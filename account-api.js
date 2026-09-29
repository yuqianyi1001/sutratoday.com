// 账号、收藏与阅读进度云同步。
// 未登录时什么都不做；登录后，已收藏经文的阅读进度会同步到后端。
// 注意：所有文件都必须用同一个 URL（含 ?v=）导入本模块，才能共享同一份状态。

// 本地开发时可在控制台执行 localStorage.setItem("sutra_api_base", "http://localhost:8787") 连接本地后端
export const API_BASE = readApiOverride() || "https://sutratoday-api.jeffwoo2019.workers.dev";

const SESSION_KEY = "sutra_account_session";
const LIBRARY_KEY = "sutra_account_library";
// 进度最多每 30 秒同步一次；离开页面、切走标签或窗口时立即同步
const SYNC_INTERVAL_MS = 30_000;
const REFRESH_TIMEOUT_MS = 2000;
const REFOCUS_REFRESH_MS = 10_000;

let session = readJson(SESSION_KEY);
let library = readJson(LIBRARY_KEY) || [];
let pendingProgress = new Map();
let syncTimer = 0;
let refreshPromise = null;
let lastRefreshAt = 0;
let emitTimer = 0;

if (typeof window !== "undefined") {
  window.addEventListener("pagehide", () => flushProgress(true));
  // 切到别的窗口（浏览器仍可见时不会触发 visibilitychange）
  // 页面仍在，不需要 keepalive；这样可以先拉取云端进度再发送
  window.addEventListener("blur", () => flushProgress());
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") flushProgress(true);
    // 回到页面时拉取其他设备的最新进度
    else if (Date.now() - lastRefreshAt > REFOCUS_REFRESH_MS) refreshLibrary();
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
    lastRefreshAt = Date.now();
    refreshPromise = request("GET", "/library")
      .then((data) => {
        setLibrary(mergeLibrary(data.favorites || []));
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

// 服务器数据可能落后于本机（进度尚未发出，或正在发送），同一部经保留较新的进度。
// 例外：本机待发送的进度比云端位置靠前、且未经读者确认时，丢弃本机进度，以云端为准，
// 避免进度慢的设备覆盖其他设备读到的更后面的位置。
function mergeLibrary(remote) {
  return remote.map((item) => {
    const pending = pendingProgress.get(item.workId);
    if (pending && !pending.confirmed && item.progress?.slug && comparePosition(pending.progress, item.progress) < 0) {
      pendingProgress.delete(item.workId);
      return item;
    }
    const local = getFavorite(item.workId)?.progress;
    return isNewer(local, item.progress) ? { ...item, progress: local } : item;
  });
}

function isNewer(a, b) {
  if (!a?.slug) return false;
  if (!b?.slug) return true;
  return (Number(a.savedAt) || 0) > (Number(b.savedAt) || 0);
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

// 比较同一部经内两个阅读位置的先后：先比卷号（slug 末尾的数字），再比段落序号。
// 返回负数表示 a 在 b 之前。
export function comparePosition(a, b) {
  const volume = (p) => Number(String(p?.slug || "").match(/-(\d+)$/)?.[1] || 0);
  const diff = volume(a) - volume(b);
  if (diff) return diff;
  return (Number(a?.blockIndex) || 0) - (Number(b?.blockIndex) || 0);
}

// 由 reading-progress.js 在每次本地保存后调用；只同步已收藏的经文。
// confirmed：读者已确认用较前的位置覆盖较后的进度；未确认时，较前的位置不会覆盖云端进度。
export function queueProgressSync(progress, { confirmed = false } = {}) {
  if (!isLoggedIn() || !progress?.slug) return;
  const workId = workIdFromSlug(progress.slug);
  const fav = getFavorite(workId);
  if (!fav) return;
  if (!confirmed && fav.progress?.slug && comparePosition(progress, fav.progress) < 0) return;

  const next = toApiProgress(progress);
  fav.progress = { workId, ...next };
  writeJson(LIBRARY_KEY, library);
  pendingProgress.set(workId, { progress: next, confirmed });
  // 较长时间没拉取云端时，先拉一次，以便发现其他设备读到的更后面的位置
  if (Date.now() - lastRefreshAt > SYNC_INTERVAL_MS) refreshLibrary();
  // 节流而不是防抖：一直在读也会按时同步，期间的多次更新合并成一次请求
  if (!syncTimer) syncTimer = setTimeout(() => flushProgress(), SYNC_INTERVAL_MS);
  emitSoon();
}

// 取本经文在云端（缓存）中的进度
export function getRemoteProgress(workId) {
  return getFavorite(workId)?.progress || null;
}

export async function flushProgress(keepalive = false) {
  clearTimeout(syncTimer);
  syncTimer = 0;
  if (!isLoggedIn() || !pendingProgress.size) return;
  // 页面还在时，发送前确认云端没有更后面的位置（mergeLibrary 会丢弃未确认的较前进度）
  if (!keepalive && Date.now() - lastRefreshAt > SYNC_INTERVAL_MS) {
    await refreshLibrary();
    if (!isLoggedIn() || !pendingProgress.size) return;
  }
  const entries = [...pendingProgress.entries()];
  pendingProgress = new Map();
  await Promise.all(
    entries.map(([workId, entry]) =>
      request("PUT", `/progress/${encodeURIComponent(workId)}`, entry.progress, true, keepalive)
        .then((data) => {
          // 服务器返回最终保存的进度；若其他设备有更新的进度，以服务器为准
          const fav = getFavorite(workId);
          if (fav && data.progress && isNewer(data.progress, fav.progress)) {
            fav.progress = data.progress;
            writeJson(LIBRARY_KEY, library);
            emitSoon();
          }
        })
        .catch((error) => {
          // 网络失败时放回队列，下次再试；未收藏（409）等错误直接丢弃
          if (error.status === 0 && !pendingProgress.has(workId)) {
            pendingProgress.set(workId, entry);
            if (!syncTimer) syncTimer = setTimeout(() => flushProgress(), SYNC_INTERVAL_MS);
          }
        }),
    ),
  );
}

// 登录后，把本机最后一次阅读位置合并到云端（若该经已收藏，服务器保留较新的一条）
async function pushLocalProgress() {
  const { readReadingProgress } = await import("./reading-progress.js?v=11");
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

// ── 建议重翻 / 打卡 ─────────────────────────────────────────

// 登录可选；登录时会记下是谁提的建议
export function suggestRetranslate({ slug, sid, title, volumeLabel, original, translation }) {
  return request("POST", "/retranslate", { slug, sid, title, volumeLabel, original, translation }, isLoggedIn());
}

// slug 为空表示整部经
export function getCheckins(workId, slug = "") {
  const query = new URLSearchParams({ workId });
  if (slug) query.set("slug", slug);
  return request("GET", `/checkins?${query}`, undefined, isLoggedIn());
}

export function checkin({ workId, slug = "", title = "", volumeLabel = "" }) {
  return request("POST", "/checkins", { workId, slug, title, volumeLabel });
}

// ── 评论 ────────────────────────────────────────────────────

export function getComments(slug) {
  return request("GET", `/comments?${new URLSearchParams({ slug })}`, undefined, isLoggedIn());
}

// kind: "comment" | "translation_issue"
export function postComment({ slug, body = "", kind = "comment", quote = "", sid = "", target = "" }) {
  return request("POST", "/comments", { slug, body, kind, quote, sid: sid || undefined, target });
}

export function deleteComment(id) {
  return request("DELETE", `/comments/${encodeURIComponent(id)}`);
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
  clearTimeout(emitTimer);
  emitTimer = 0;
  window.dispatchEvent(new CustomEvent("sutra:account"));
}

// 滚动时进度更新很频繁，界面最多每秒刷新一次
function emitSoon() {
  if (!emitTimer) emitTimer = setTimeout(emit, 1000);
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
