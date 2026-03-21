import {
  escapeHtml,
  getMarkdownSourceUrl,
  getReviewState,
  getTranslationState,
  loadDocuments,
  renderMarkdown,
} from "./site-data.js";

const dom = {
  statusbar: document.getElementById("reader-statusbar"),
  title: document.getElementById("reader-title"),
  rendered: document.getElementById("reader-rendered"),
  raw: document.getElementById("reader-raw"),
  sourceLink: document.getElementById("source-link"),
  summary: document.getElementById("reader-summary"),
};

let documents = [];

init().catch((error) => {
  dom.rendered.innerHTML = `<p class="loading-text">请通过站点地址访问本页，避免直接打开本地文件。</p>`;
});

async function init() {
  documents = await loadDocuments();
  selectCurrent();
  window.addEventListener("hashchange", selectCurrent);
}

function selectCurrent() {
  const slugFromHash = new URLSearchParams(location.hash.replace(/^#/, "")).get("doc");
  const selected = documents.find((doc) => doc.slug === slugFromHash) || documents.find((doc) => doc.slug === "heart-sutra") || documents[0];
  if (!selected) {
    return;
  }

  const translationBadge = getTranslationState(selected.translation_status);
  const reviewBadge = getReviewState(selected.review_status);

  dom.title.textContent = selected.title;
  dom.summary.textContent = selected.summary || "";
  dom.sourceLink.href = getMarkdownSourceUrl(selected.path);
  dom.rendered.innerHTML = renderMarkdown(selected.body);
  dom.raw.textContent = selected.raw;
  dom.statusbar.innerHTML = `
    <span class="badge ${translationBadge.className}">${translationBadge.label}</span>
    <span class="badge ${reviewBadge.className}">${reviewBadge.label}</span>
    <span class="reader-fact">卷别：${escapeHtml(selected.volume_label || "单篇")}</span>
    <span class="reader-fact">进度：${escapeHtml(String(selected.progress_percent || 0))}%</span>
    <span class="reader-fact">更新：${escapeHtml(selected.updated_at || "未标注")}</span>
  `;
}
