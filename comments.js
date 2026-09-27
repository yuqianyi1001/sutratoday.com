// 阅读页评论区（取代 Twikoo）。浏览公开；发表、标记翻译问题需登录。
import { escapeHtml } from "./site-data.js";
import { deleteComment, getComments, getUser, isLoggedIn, onAccountChange, postComment } from "./account-api.js?v=4";
import { openAccountDialog } from "./account.js?v=4";

const STATUS_LABELS = { in_progress: "处理中", resolved: "已解决", closed: "已关闭" };

let root = null;
let currentSlug = "";
let comments = [];
let loadId = 0;
let toast = () => {};
let jumpToParagraph = () => {};

export function initComments({ container, showToast, onJumpToParagraph }) {
  root = container;
  toast = showToast || toast;
  jumpToParagraph = onJumpToParagraph || jumpToParagraph;
  root.addEventListener("submit", onSubmit);
  root.addEventListener("click", onClick);
  // 登录状态变化时刷新（显示/隐藏输入框、识别"我的"评论）；进度同步也会触发账号事件，所以只比较用户
  let userId = getUser()?.id ?? null;
  onAccountChange(() => {
    const next = getUser()?.id ?? null;
    if (next === userId) return;
    userId = next;
    if (currentSlug) loadComments(currentSlug);
  });
}

export async function loadComments(slug) {
  if (!root) return;
  currentSlug = slug;
  const id = ++loadId;
  comments = [];
  render("loading");
  try {
    const data = await getComments(slug);
    if (id !== loadId) return;
    comments = data.comments || [];
    render();
  } catch {
    if (id !== loadId) return;
    render("error");
  }
}

// 选中文字 →「标记翻译问题」：自动发一条评论
export async function flagTranslationIssue({ quote, sid, target }) {
  const slug = currentSlug;
  if (!slug || !quote) return false;
  if (!isLoggedIn()) {
    openAccountDialog({
      reason: "登录后即可标记翻译问题，标记会显示在评论区。",
      onSuccess: () => flagTranslationIssue({ quote, sid, target }),
    });
    return false;
  }
  try {
    const { comment } = await postComment({ slug, kind: "translation_issue", quote, sid, target });
    if (slug === currentSlug) {
      comments.push(comment);
      render();
    }
    toast("已标记翻译问题，已加到评论区");
    return true;
  } catch (error) {
    toast(error.message || "标记失败，请稍后再试");
    return false;
  }
}

function render(state = "") {
  const list =
    state === "loading"
      ? `<p class="comment-empty">正在加载评论…</p>`
      : state === "error"
        ? `<p class="comment-empty">评论加载失败，请稍后刷新重试。</p>`
        : comments.length
          ? `<ol class="comment-list">${comments.map(renderComment).join("")}</ol>`
          : `<p class="comment-empty">还没有评论。</p>`;
  const form = isLoggedIn()
    ? `
      <form class="comment-form">
        <textarea name="body" rows="3" maxlength="2000" placeholder="写下你的评论、疑问或建议…" required></textarea>
        <div class="comment-form-actions">
          <span class="comment-form-hint">以 ${escapeHtml(getUser()?.username || "")} 的身份发表</span>
          <button class="primary-link comment-submit" type="submit">发表评论</button>
        </div>
      </form>`
    : `
      <div class="comment-login">
        <p>登录后才能发表评论。</p>
        <button class="primary-link" type="button" data-comment-login>登录后评论</button>
      </div>`;
  root.innerHTML = `
    <h2 class="reader-comments-title">评论与反馈${comments.length ? `<span>（${comments.length}）</span>` : ""}</h2>
    <p class="comment-tip">选中经文中的文字，可以"标记翻译问题"。</p>
    ${list}
    ${form}
  `;
}

function renderComment(c) {
  const badges = [
    c.kind === "translation_issue" ? `<span class="comment-badge is-issue">翻译问题</span>` : "",
    STATUS_LABELS[c.status] ? `<span class="comment-badge is-${c.status}">${STATUS_LABELS[c.status]}</span>` : "",
  ].join("");
  const quote = c.quote
    ? `<blockquote class="comment-quote">${escapeHtml(c.quote)}${
        c.sid ? ` <button type="button" class="comment-jump" data-comment-jump="${escapeHtml(c.sid)}" data-target="${escapeHtml(c.target || "")}">查看段落</button>` : ""
      }</blockquote>`
    : "";
  const body = c.body
    ? `<p class="comment-body">${escapeHtml(c.body)}</p>`
    : c.kind === "translation_issue"
      ? `<p class="comment-body is-muted">标记了这段文字的翻译问题。</p>`
      : "";
  const note = c.resolutionNote ? `<p class="comment-resolution">处理说明：${escapeHtml(c.resolutionNote)}</p>` : "";
  return `
    <li class="comment" data-comment-id="${c.id}">
      <div class="comment-meta">
        <strong>${escapeHtml(c.author)}</strong>
        ${c.legacy ? `<span class="comment-legacy">旧评论</span>` : ""}
        <span class="comment-time">${escapeHtml(formatTime(c.createdAt))}</span>
        ${badges}
        ${c.mine ? `<button type="button" class="comment-delete" data-comment-delete="${c.id}">删除</button>` : ""}
      </div>
      ${quote}
      ${body}
      ${note}
    </li>
  `;
}

async function onSubmit(event) {
  const form = event.target.closest(".comment-form");
  if (!form) return;
  event.preventDefault();
  const textarea = form.elements.body;
  const body = textarea.value.trim();
  if (!body) return;
  const button = form.querySelector(".comment-submit");
  button.disabled = true;
  try {
    const { comment } = await postComment({ slug: currentSlug, body });
    comments.push(comment);
    render();
    toast("评论已发表");
  } catch (error) {
    toast(error.message || "发表失败，请稍后再试");
    button.disabled = false;
  }
}

async function onClick(event) {
  if (event.target.closest("[data-comment-login]")) {
    openAccountDialog({ reason: "登录后即可发表评论。" });
    return;
  }
  const jump = event.target.closest("[data-comment-jump]");
  if (jump) {
    jumpToParagraph(jump.dataset.commentJump, jump.dataset.target);
    return;
  }
  const del = event.target.closest("[data-comment-delete]");
  if (del) {
    if (!confirm("确定删除这条评论吗？")) return;
    const id = Number(del.dataset.commentDelete);
    try {
      await deleteComment(id);
      comments = comments.filter((c) => c.id !== id);
      render();
    } catch (error) {
      toast(error.message || "删除失败，请稍后再试");
    }
  }
}

function formatTime(ms) {
  const d = new Date(ms);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
