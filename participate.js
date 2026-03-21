import { escapeHtml, renderMarkdown } from "./site-data.js";

const CONTENT_PATH = "content/pages/participate.md";
const rendered = document.getElementById("content-rendered");

init().catch((error) => {
  rendered.innerHTML = `<p class="loading-text">读取失败：${escapeHtml(error.message)}</p>`;
});

async function init() {
  const response = await fetch(CONTENT_PATH);
  if (!response.ok) {
    throw new Error(`无法读取 ${CONTENT_PATH}`);
  }

  const markdown = await response.text();
  rendered.innerHTML = renderMarkdown(markdown);
}
