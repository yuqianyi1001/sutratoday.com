import { fixTraditional } from "./script-fixes.js?v=3";

const SCRIPT_MODE_COOKIE = "sutra_reader_script_mode";
const SCRIPT_MODE_DEFAULT = "traditional";
const VALID_SCRIPT_MODES = new Set(["simplified", "traditional"]);
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365;
// 文稿里的引号是 CBETA 的「」『』；简体显示时换成“”‘’，切回繁体时从原文重新算，不用反向转换
const TO_SIMPLIFIED_QUOTES = { "「": "“", "」": "”", "『": "‘", "』": "’" };
const NON_TRANSLATABLE_TAGS = new Set(["SCRIPT", "STYLE", "PRE", "CODE", "TEXTAREA"]);

if (typeof window !== "undefined" && typeof document !== "undefined") {
  init();
}

function init() {
  const openCC = window.OpenCC || null;
  const toSimplified = openCC?.Converter?.({ from: "tw", to: "cn" }) || null;
  const toTraditional = openCC?.Converter?.({ from: "cn", to: "tw" }) || null;
  let scriptMode = getSavedScriptMode();
  let isApplyingScriptMode = false;
  // 每个文本节点原本的文字，和我们最后一次显示的文字。切回繁体时从原文重新算，
  // 不拿已经转成简体的文字再转回去（简 → 繁会转错字）。
  const sources = new WeakMap();

  ensureHeaderScriptPicker();
  applyScriptMode(scriptMode);
  observeAddedNodes();

  function ensureHeaderScriptPicker() {
    const header = document.querySelector(".site-header");
    const nav = header?.querySelector(".site-nav");
    if (!header || !nav) {
      return;
    }

    let actions = header.querySelector(".site-header-actions");
    if (!actions) {
      actions = document.createElement("div");
      actions.className = "site-header-actions";
      nav.replaceWith(actions);
      actions.appendChild(nav);
    }

    let tools = actions.querySelector(".site-header-tools");
    if (!tools) {
      tools = document.createElement("div");
      tools.className = "site-header-tools";
      actions.appendChild(tools);
    }

    if (!tools.querySelector(".site-script-picker")) {
      tools.insertAdjacentHTML(
        "beforeend",
        `
          <div class="site-script-picker" role="radiogroup" aria-label="簡繁切換選項">
            <button
              class="site-script-option"
              type="button"
              role="radio"
              aria-checked="true"
              data-site-script-mode-value="traditional"
            >
              繁體
            </button>
            <button
              class="site-script-option"
              type="button"
              role="radio"
              aria-checked="false"
              data-site-script-mode-value="simplified"
            >
              簡體
            </button>
          </div>
        `,
      );
    }

    tools.addEventListener("click", (event) => {
      const button = event.target.closest("[data-site-script-mode-value]");
      if (!button) {
        return;
      }

      const nextMode = button.dataset.siteScriptModeValue;
      if (!VALID_SCRIPT_MODES.has(nextMode)) {
        return;
      }

      applyScriptMode(nextMode, { persist: true });
    });
  }

  function observeAddedNodes() {
    const observer = new MutationObserver((mutations) => {
      if (isApplyingScriptMode) {
        return;
      }

      if (!toSimplified || !toTraditional) {
        return;
      }

      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          convertNodeTree(node, scriptMode);
        });
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  function applyScriptMode(mode, options = {}) {
    const { persist = false } = options;
    const nextMode = VALID_SCRIPT_MODES.has(mode) ? mode : SCRIPT_MODE_DEFAULT;

    scriptMode = nextMode;
    updateScriptButtons(nextMode);

    if (persist) {
      saveCookie(SCRIPT_MODE_COOKIE, nextMode);
    }

    if (!toSimplified || !toTraditional) {
      document.documentElement.lang = nextMode === "simplified" ? "zh-CN" : "zh-TW";
      return;
    }

    isApplyingScriptMode = true;
    try {
      convertNodeTree(document.body, nextMode);
      document.documentElement.lang = nextMode === "simplified" ? "zh-CN" : "zh-TW";
    } finally {
      isApplyingScriptMode = false;
    }
  }

  function updateScriptButtons(mode) {
    document.querySelectorAll("[data-site-script-mode-value]").forEach((button) => {
      const isActive = button.dataset.siteScriptModeValue === mode;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-checked", isActive ? "true" : "false");
    });
  }

  function convertNodeTree(root, mode) {
    walkTextNodes(root, (textNode) => {
      const known = sources.get(textNode);
      // 页面自己改过这个节点的文字时，以新的文字为准
      const source = known && known.shown === textNode.nodeValue ? known.source : textNode.nodeValue;
      const shown = mode === "simplified" ? simplifiedText(source) : toTraditionalText(source);
      sources.set(textNode, { source, shown });
      if (shown !== textNode.nodeValue) {
        textNode.nodeValue = shown;
      }
    });
  }

  function simplifiedText(text) {
    return toSimplified(text).replace(/[「」『』]/g, (ch) => TO_SIMPLIFIED_QUOTES[ch]);
  }

  // 文稿里的原文和译文已经是繁体。已是繁体的文字照原样显示：其中的“云”“尸”“布”
  // 本来就是该用的字，再转一次会变成“雲”“屍”“佈”。只有不含繁体字的文字才转换，
  // 转换后用 script-fixes.js 的字典修正。
  function toTraditionalText(text) {
    if (toSimplified(text) !== text) {
      return text;
    }
    return fixTraditional(toTraditional(text));
  }

  function walkTextNodes(root, visitor) {
    if (!root) {
      return;
    }

    if (root.nodeType === Node.TEXT_NODE) {
      if (shouldTranslateTextNode(root)) {
        visitor(root);
      }
      return;
    }

    if (root.nodeType !== Node.ELEMENT_NODE) {
      return;
    }

    if (NON_TRANSLATABLE_TAGS.has(root.tagName) || root.closest(".ignore-opencc")) {
      return;
    }

    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        return shouldTranslateTextNode(node) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      },
    });

    let textNode = walker.nextNode();
    while (textNode) {
      visitor(textNode);
      textNode = walker.nextNode();
    }
  }
}

function shouldTranslateTextNode(textNode) {
  const parent = textNode.parentElement;
  if (!parent) {
    return false;
  }
  if (NON_TRANSLATABLE_TAGS.has(parent.tagName) || parent.closest(".ignore-opencc")) {
    return false;
  }
  return Boolean(textNode.nodeValue && textNode.nodeValue.trim());
}

function getSavedScriptMode() {
  const cookieValue = readCookie(SCRIPT_MODE_COOKIE);
  return VALID_SCRIPT_MODES.has(cookieValue) ? cookieValue : SCRIPT_MODE_DEFAULT;
}

function saveCookie(name, value) {
  document.cookie = [
    `${name}=${encodeURIComponent(value)}`,
    `Max-Age=${COOKIE_MAX_AGE}`,
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

  if (!matched) {
    return "";
  }

  return decodeURIComponent(matched.slice(cookiePrefix.length));
}
