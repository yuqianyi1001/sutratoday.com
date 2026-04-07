// ── Constants ──────────────────────────────────────────────

export const SITE_BASE_URL = "https://sutratoday.com/";
export const GITHUB_REPO_BASE = "https://github.com/yuqianyi1001/sutratoday.com/blob/main/";
const INDEX_URL = "./sutras-raw-index.json";

export const HOME_FEATURED_WORK_IDS = [
  "T0251", // 心经
  "T0235", // 金刚经
  "T0262", // 法华经
  "T0360", // 无量寿经
  "T0366", // 阿弥陀经
  "T0450", // 药师经
  "T0412", // 地藏经
  "T0475", // 维摩诘经
  "T0784", // 四十二章经
  "T0842", // 圆觉经
  "T0001", // 长阿含经
  "T0099", // 杂阿含经
];

const translationStates = {
  untranslated: { label: "未翻译", className: "badge-muted" },
  translating: { label: "翻译中", className: "badge-amber" },
  translated: { label: "已翻译", className: "badge-green" },
};

const reviewStates = {
  unreviewed: { label: "未校验", className: "badge-muted" },
  reviewing: { label: "校验中", className: "badge-amber" },
  ai_reviewed: { label: "AI已校验", className: "badge-warm" },
  human_reviewed: { label: "人工已校验", className: "badge-green" },
};

// ── Index Loading ──────────────────────────────────────────

let indexCache = null;

export async function loadWorksIndex() {
  if (indexCache) return indexCache;
  const response = await fetch(INDEX_URL);
  if (!response.ok) throw new Error(`无法加载索引 (${response.status})`);
  indexCache = await response.json();
  return indexCache;
}

export function getWorkBySlug(index, slug) {
  // slug can be a volume slug like T0001-001 or a cbeta_id like T0001
  const cbetaId = slug.replace(/-\d+$/, "");
  return index.works.find((w) => w.cbeta_id === cbetaId) || null;
}

export function getWorkByCbetaId(index, cbetaId) {
  return index.works.find((w) => w.cbeta_id === cbetaId) || null;
}

export function getVolumeSlugPath(slug) {
  return `content/sutras-raw/${slug}.md`;
}

// ── Featured Documents (Homepage) ──────────────────────────

export async function loadFeaturedWorks() {
  const index = await loadWorksIndex();
  return HOME_FEATURED_WORK_IDS.map((cbetaId) =>
    index.works.find((w) => w.cbeta_id === cbetaId),
  ).filter(Boolean);
}

// ── Volume Navigation ──────────────────────────────────────

export function getVolumeNavigation(work, currentSlug) {
  if (!work || !work.volumes || work.volumes.length <= 1) return [];
  return work.volumes.map(([slug, title]) => ({
    slug,
    label: buildVolumeNavLabel(slug, work.volumes.length),
    title,
    isCurrent: slug === currentSlug,
  }));
}

function buildVolumeNavLabel(slug, totalVolumes) {
  const match = slug.match(/-(\d+)$/);
  if (!match) return slug;
  const index = parseInt(match[1], 10);
  return `卷${toChineseNumeral(index)}`;
}

// ── Document Loading ───────────────────────────────────────

export async function loadDocument(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`无法读取 ${path} (Status: ${response.status})`);
  const contentType = response.headers.get("content-type") || "";
  const raw = await response.text();
  // Guard against SPA fallback: if the server returned HTML instead of markdown, treat as not found
  if (contentType.includes("text/html") || (!raw.startsWith("---") && raw.trimStart().startsWith("<!DOCTYPE"))) {
    throw new Error(`经文文件不存在: ${path}`);
  }
  return parseDocument(raw, path);
}

function parseDocument(raw, path) {
  const { meta, body } = parseFrontMatter(raw);
  return {
    ...meta,
    body,
    raw,
    path,
    slug: meta.slug || path.split("/").pop().replace(/\.md$/, ""),
  };
}

function parseFrontMatter(raw) {
  const match = raw.match(/^---\n([\s\S]*?)\n---\n?/);
  let meta = {};
  let body = raw;

  if (match) {
    const lines = match[1].split("\n");
    meta = Object.fromEntries(
      lines
        .map((line) => {
          const divider = line.indexOf(":");
          if (divider === -1) return null;
          const key = line.slice(0, divider).trim();
          const value = line.slice(divider + 1).trim();
          return [key, coerceValue(value)];
        })
        .filter(Boolean),
    );
    body = raw.slice(match[0].length);
  }

  return { meta, body };
}

function coerceValue(value) {
  if (value === "true") return true;
  if (value === "false") return false;
  if (/^\d+$/.test(value)) return Number(value);
  if (value.includes(",")) {
    return value
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean);
  }
  return value;
}

// ── Badge / Status Helpers ─────────────────────────────────

export function getTranslationState(status) {
  return translationStates[status] || translationStates.untranslated;
}

export function getReviewState(status) {
  return reviewStates[status] || reviewStates.unreviewed;
}

export function getCatalogVolumeBadgeLabel(work) {
  if (!work) return "单篇";
  if (work.juan_total <= 1) return "全一卷";
  return `全${work.juan_total}卷`;
}

export function formatUpdatedAtBadgeLabel(value) {
  return value ? `更新 ${value}` : "未标注日期";
}

// ── URL Helpers ────────────────────────────────────────────

export function getReaderUrl(slug, base = "") {
  const encodedSlug = encodeURIComponent(slug);
  const queryOnly = `reader.html?doc=${encodedSlug}`;
  if (base) return new URL(queryOnly, base).toString();
  return `./${queryOnly}`;
}

export function getMarkdownSourceUrl(path) {
  return new URL(path, GITHUB_REPO_BASE).toString();
}

// ── Markdown Rendering ─────────────────────────────────────

export function renderMarkdown(markdown) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let paragraph = [];
  let listBuffer = [];
  let listType = null;
  let inCodeBlock = false;
  let codeBuffer = [];
  let sectionTone = null;
  let sectionHeadingClass = "";

  const toneClassName = () => {
    if (sectionTone === "sutra-original") return "sutra-original";
    if (sectionTone === "sutra-translation") return "sutra-translation";
    return "";
  };

  const paragraphClass = () => {
    if (sectionTone === "sutra-original") return ' class="sutra-original"';
    if (sectionTone === "sutra-translation") return ' class="sutra-translation"';
    return "";
  };
  const listClass = () => {
    if (sectionTone === "sutra-original") return ' class="sutra-original sutra-original-list"';
    if (sectionTone === "sutra-translation") return ' class="sutra-translation"';
    return "";
  };
  const codeClass = () => {
    if (sectionTone === "sutra-original") return ' class="sutra-original sutra-original-code"';
    if (sectionTone === "sutra-translation") return ' class="sutra-translation"';
    return "";
  };
  const blockquoteClass = () => {
    const className = toneClassName();
    return className ? ` class="${className}"` : "";
  };

  const flushParagraph = () => {
    if (!paragraph.length) return;
    html.push(`<p${paragraphClass()}>${formatInline(paragraph.join(" "))}</p>`);
    paragraph = [];
  };

  const flushList = () => {
    if (!listBuffer.length) return;
    const tag = listType === "ol" ? "ol" : "ul";
    html.push(`<${tag}${listClass()}>${listBuffer.map((item) => `<li>${formatInline(item)}</li>`).join("")}</${tag}>`);
    listBuffer = [];
    listType = null;
  };

  const flushCode = () => {
    if (!codeBuffer.length) return;
    html.push(`<pre${codeClass()}><code>${escapeHtml(codeBuffer.join("\n"))}</code></pre>`);
    codeBuffer = [];
  };

  lines.forEach((line) => {
    if (line.startsWith("```")) {
      flushParagraph();
      flushList();
      if (inCodeBlock) flushCode();
      inCodeBlock = !inCodeBlock;
      return;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      return;
    }

    if (!line.trim()) {
      flushParagraph();
      flushList();
      return;
    }

    if (/^---+$/.test(line.trim())) {
      flushParagraph();
      flushList();
      html.push("<hr />");
      return;
    }

    const headingMatch = line.match(/^(#{1,4})\s+(.*)$/);
    if (headingMatch) {
      flushParagraph();
      flushList();
      const level = headingMatch[1].length;
      const headingText = headingMatch[2].trim();
      sectionHeadingClass = "";
      if (level >= 3) {
        if (headingText === "原文") {
          sectionTone = "sutra-original";
          sectionHeadingClass = ' class="sutra-original-heading"';
        } else if (headingText === "现代语译" || headingText === "現代語譯") {
          sectionTone = "sutra-translation";
          sectionHeadingClass = ' class="sutra-translation-heading"';
        } else {
          sectionTone = null;
        }
      } else {
        sectionTone = null;
      }
      html.push(`<h${level}${sectionHeadingClass}>${formatInline(headingText)}</h${level}>`);
      return;
    }

    const blockquoteMatch = line.match(/^>\s?(.*)$/);
    if (blockquoteMatch) {
      flushParagraph();
      flushList();
      html.push(`<blockquote${blockquoteClass()}>${formatInline(blockquoteMatch[1])}</blockquote>`);
      return;
    }

    const unorderedMatch = line.match(/^-\s+(.*)$/);
    if (unorderedMatch) {
      flushParagraph();
      if (listType && listType !== "ul") flushList();
      listType = "ul";
      listBuffer.push(unorderedMatch[1]);
      return;
    }

    const orderedMatch = line.match(/^\d+\.\s+(.*)$/);
    if (orderedMatch) {
      if (sectionTone === "sutra-translation") {
        paragraph.push(orderedMatch[1]);
        return;
      }
      flushParagraph();
      if (listType && listType !== "ol") flushList();
      listType = "ol";
      listBuffer.push(orderedMatch[1]);
      return;
    }

    paragraph.push(line.trim());
  });

  flushParagraph();
  flushList();
  flushCode();
  return html.join("");
}

function formatInline(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, "<code>$1</code>")
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
}

export function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ── Chinese Numeral Helper ─────────────────────────────────

function toChineseNumeral(value) {
  const numerals = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"];
  if (value <= 10) return value === 10 ? "十" : numerals[value];
  if (value < 20) return `十${numerals[value % 10]}`;
  const tens = Math.floor(value / 10);
  const ones = value % 10;
  return `${numerals[tens]}十${ones ? numerals[ones] : ""}`;
}
