// ── 原文 / 現代語譯 对照高亮 ────────────────────────────────
// 依据渲染时写入的 data-sid 将「原文」与「現代語譯」区块配对。
// 当两侧句读（。！？）数量一致时，按句拆分并逐句配对；
// 数量不一致时退回整段配对。
// 交互：鼠标悬停时高亮对应句（仅限支持 hover 的设备）；
// 点击 / 轻触可固定高亮，再次点击同一句或点击空白处取消。

const TERMINATOR_SETS = ["。！？", "。"];
const SENTENCE_CLOSERS = "」』”’\"）)〕】》〉";

let hoverKey = "";
let pinnedKey = "";
let highlightedElements = [];

export function setupSentenceSync(container) {
  hoverKey = "";
  pinnedKey = "";
  highlightedElements = [];

  const groups = new Map();
  container.querySelectorAll("[data-sid]").forEach((element) => {
    const sid = element.dataset.sid;
    let group = groups.get(sid);
    if (!group) {
      group = { original: [], translation: [] };
      groups.set(sid, group);
    }
    if (element.classList.contains("sutra-original")) group.original.push(element);
    else if (element.classList.contains("sutra-translation")) group.translation.push(element);
  });

  groups.forEach((group, sid) => {
    if (!group.original.length || !group.translation.length) return;
    const terminators = pickTerminators(group);
    if (terminators) {
      wrapSentences(group.original, sid, terminators);
      wrapSentences(group.translation, sid, terminators);
    } else {
      [...group.original, ...group.translation].forEach((element) => {
        element.dataset.syncKey = sid;
      });
    }
  });
}

export function bindSentenceSync(container, isEnabled) {
  container.addEventListener("pointerover", (event) => {
    if (!isEnabled()) return;
    if (event.pointerType && event.pointerType !== "mouse") return;
    const key = findSyncKey(event.target);
    if (key === hoverKey) return;
    hoverKey = key;
    applyHighlight(container);
  });
  container.addEventListener("pointerleave", () => {
    if (!hoverKey) return;
    hoverKey = "";
    applyHighlight(container);
  });
  // 绑定在 document 上，点击正文之外的区域也能取消固定的高亮
  document.addEventListener("click", (event) => {
    if (!isEnabled()) return;
    const selection = window.getSelection();
    if (selection && !selection.isCollapsed) return;
    const target = event.target instanceof Element && container.contains(event.target) ? event.target : null;
    const nextKey = target ? findSyncKey(target) : "";
    const nextPinned = nextKey && nextKey !== pinnedKey ? nextKey : "";
    if (nextPinned === pinnedKey) return;
    pinnedKey = nextPinned;
    applyHighlight(container);
  });
}

export function clearSentenceSync(container) {
  hoverKey = "";
  pinnedKey = "";
  applyHighlight(container);
}

function findSyncKey(target) {
  if (!(target instanceof Element)) return "";
  const element = target.closest("[data-sync-key]");
  return element ? element.dataset.syncKey : "";
}

function applyHighlight(container) {
  highlightedElements.forEach((element) => {
    element.classList.remove("is-sync-active", "is-sync-pinned");
  });
  highlightedElements = [];
  if (pinnedKey) highlightKey(container, pinnedKey, true);
  if (hoverKey && hoverKey !== pinnedKey) highlightKey(container, hoverKey, false);
}

function highlightKey(container, key, pinned) {
  container.querySelectorAll(`[data-sync-key="${key}"]`).forEach((element) => {
    element.classList.add("is-sync-active");
    if (pinned) element.classList.add("is-sync-pinned");
    highlightedElements.push(element);
  });
}

// ── 分句 ───────────────────────────────────────────────────

function pickTerminators(group) {
  return TERMINATOR_SETS.find((terminators) => {
    const originalCount = countSentences(group.original, terminators);
    return originalCount > 1 && originalCount === countSentences(group.translation, terminators);
  });
}

function countSentences(elements, terminators) {
  let count = 0;
  let hasTail = false;
  elements.forEach((element) => {
    collectTextNodes(element).forEach((node) => {
      splitByTerminators(node.nodeValue, terminators).forEach((piece) => {
        if (piece.terminated) {
          count += 1;
          hasTail = false;
        } else if (piece.text.trim()) {
          hasTail = true;
        }
      });
    });
  });
  return count + (hasTail ? 1 : 0);
}

function wrapSentences(elements, sid, terminators) {
  let sentenceIndex = 0;
  elements.forEach((element) => {
    collectTextNodes(element).forEach((node) => {
      const pieces = splitByTerminators(node.nodeValue, terminators);
      const fragment = document.createDocumentFragment();
      pieces.forEach((piece) => {
        const span = document.createElement("span");
        span.className = "sutra-sentence";
        span.dataset.syncKey = `${sid}-${sentenceIndex}`;
        span.textContent = piece.text;
        fragment.appendChild(span);
        if (piece.terminated) sentenceIndex += 1;
      });
      node.parentNode.replaceChild(fragment, node);
    });
  });
}

function splitByTerminators(text, terminators) {
  const pieces = [];
  let start = 0;
  let i = 0;
  while (i < text.length) {
    if (!terminators.includes(text[i])) {
      i += 1;
      continue;
    }
    let end = i + 1;
    while (end < text.length && SENTENCE_CLOSERS.includes(text[end])) end += 1;
    pieces.push({ text: text.slice(start, end), terminated: true });
    start = end;
    i = end;
  }
  if (start < text.length) pieces.push({ text: text.slice(start), terminated: false });
  return pieces;
}

function collectTextNodes(root) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  return nodes;
}
