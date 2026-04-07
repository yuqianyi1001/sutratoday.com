const SCRIPT_MODE_COOKIE = "sutra_reader_script_mode";
const SCRIPT_MODE_DEFAULT = "traditional";
const VALID_SCRIPT_MODES = new Set(["simplified", "traditional"]);
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365;
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

      const converter = scriptMode === "simplified" ? toSimplified : toTraditional;
      if (!converter) {
        return;
      }

      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          convertNodeTree(node, converter);
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

    const converter = nextMode === "simplified" ? toSimplified : toTraditional;
    if (!converter) {
      document.documentElement.lang = nextMode === "simplified" ? "zh-CN" : "zh-TW";
      return;
    }

    isApplyingScriptMode = true;
    try {
      convertNodeTree(document.body, converter);
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

  function convertNodeTree(root, converter) {
    walkTextNodes(root, (textNode) => {
      const converted = converter(textNode.nodeValue);
      if (converted !== textNode.nodeValue) {
        textNode.nodeValue = normalizeVolumeText(converted);
      }
    });
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

function normalizeVolumeText(text) {
  if (!text) {
    return text;
  }
  return text
    .replace(/捲(?=[上下中])/g, "卷")
    .replace(/捲(?=第)/g, "卷")
    .replace(/捲(?=[一二三四五六七八九十百千零〇两兩0-9])/g, "卷")
    .replace(/([全共][一二三四五六七八九十百千零〇两兩0-9]*)捲/g, "$1卷");
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
