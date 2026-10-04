// 打卡分享图：在浏览器里用 canvas 画一张图文卡片（经名 + 卷别 + 今文佛典标识 + 本经二维码）
import { escapeHtml, getReaderUrl } from "./site-data.js";
import qrcode from "./assets/vendor/qrcode-generator.js";

const SITE_ORIGIN = "https://sutratoday.com/";
const SITE_NAME = "今文佛典";
const SITE_SLOGAN = "以白话文读佛教经典";
const LOGO_SRC = "./assets/logo-mark.png";

const WIDTH = 1080;
const HEIGHT = 1440;
const PAD = 96;
const SERIF = `"Noto Serif SC", "Source Han Serif SC", "Songti SC", "STSong", serif`;
const COLORS = {
  bg: "#f4eee2",
  card: "#fffcf6",
  ink: "#241d18",
  muted: "#6f655d",
  accent: "#8f5331",
  line: "rgba(66, 49, 38, 0.16)",
};

// target: { title, slug, volumeLabel, qrSlug, username }
//  - slug 为空表示整部经；qrSlug 是二维码指向的那一卷
export async function openCheckinShare(target) {
  const dialog = mountDialog();
  try {
    const canvas = await drawShareCard(target);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
    if (!blob) throw new Error("生成图片失败");
    showResult(dialog, blob, target);
  } catch (error) {
    dialog.querySelector(".checkin-share-body").innerHTML =
      `<p class="checkin-share-status">${escapeHtml(error.message || "生成图片失败，请稍后再试")}</p>`;
  }
}

// "卷第三" → "第三卷"，"卷上" → "上卷"；其他写法原样保留
export function formatVolumeForShare(volumeLabel) {
  const label = String(volumeLabel || "").trim();
  if (!label || ["全一卷", "单篇", "單篇"].includes(label)) return "";
  const numbered = label.match(/^卷第?([一二三四五六七八九十百千零〇两兩\d]+)$/);
  if (numbered) return `第${numbered[1]}卷`;
  const part = label.match(/^卷([上中下])$/);
  if (part) return `${part[1]}卷`;
  return label;
}

export function shareHeadline(target) {
  const volume = target.slug ? formatVolumeForShare(target.volumeLabel) : "";
  return volume ? `今天阅读完《${target.title}》${volume}` : `今天阅读完《${target.title}》`;
}

async function drawShareCard(target) {
  const title = `《${target.title}》`;
  const volume = target.slug ? formatVolumeForShare(target.volumeLabel) : "";
  await loadFonts(`今天阅读完${title}${volume}${SITE_NAME}${SITE_SLOGAN}扫码阅读本经0123456789年月日`);
  const logo = await loadImage(LOGO_SRC).catch(() => null);

  const canvas = document.createElement("canvas");
  canvas.width = WIDTH;
  canvas.height = HEIGHT;
  const ctx = canvas.getContext("2d");

  ctx.fillStyle = COLORS.bg;
  ctx.fillRect(0, 0, WIDTH, HEIGHT);
  roundRect(ctx, 48, 48, WIDTH - 96, HEIGHT - 96, 40);
  ctx.fillStyle = COLORS.card;
  ctx.fill();
  ctx.strokeStyle = COLORS.line;
  ctx.lineWidth = 2;
  ctx.stroke();

  // 上半部分：日期，以及在剩余空间里垂直居中的"今天阅读完 / 经名 / 卷别 / 署名"
  const qrSize = 260;
  const footerTop = HEIGHT - 48 - PAD - qrSize - 50;
  const maxWidth = WIDTH - PAD * 2 - 40;
  const left = PAD + 20;
  ctx.textBaseline = "alphabetic";
  ctx.textAlign = "left";
  ctx.fillStyle = COLORS.muted;
  ctx.font = `500 36px ${SERIF}`;
  ctx.fillText(formatDate(new Date()), left, 200);

  let titleSize = 84;
  let lines = wrapText(ctx, title, maxWidth, `600 ${titleSize}px ${SERIF}`);
  while (lines.length > 3 && titleSize > 52) {
    titleSize -= 6;
    lines = wrapText(ctx, title, maxWidth, `600 ${titleSize}px ${SERIF}`);
  }
  lines = lines.slice(0, 4);
  // 每行：[字体, 颜色, 文字, 本行占用高度]
  const rows = [[`500 56px ${SERIF}`, COLORS.ink, "今天阅读完", 100]];
  lines.forEach((line, i) => rows.push([`600 ${titleSize}px ${SERIF}`, COLORS.accent, line, titleSize * (i ? 1.3 : 1.6)]));
  if (volume) rows.push([`500 60px ${SERIF}`, COLORS.ink, volume, 110]);
  if (target.username) rows.push([`400 36px ${SERIF}`, COLORS.muted, `—— ${target.username}`, 110]);
  const blockHeight = rows.reduce((sum, row) => sum + row[3], 0);
  const areaTop = 240;
  let y = areaTop + Math.max(0, (footerTop - areaTop - blockHeight) / 2) - 20;
  for (const [font, color, text, height] of rows) {
    y += height;
    ctx.font = font;
    ctx.fillStyle = color;
    ctx.fillText(text, left, y);
  }

  // 下半部分：分隔线、标识与介绍、二维码
  ctx.strokeStyle = COLORS.line;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(PAD, footerTop);
  ctx.lineTo(WIDTH - PAD, footerTop);
  ctx.stroke();

  const qrX = WIDTH - PAD - qrSize;
  const qrY = footerTop + 50;
  drawQr(ctx, getReaderUrl(target.qrSlug, SITE_ORIGIN), qrX, qrY, qrSize);
  ctx.fillStyle = COLORS.muted;
  ctx.font = `400 26px ${SERIF}`;
  ctx.textAlign = "center";
  ctx.fillText("扫码阅读本经", qrX + qrSize / 2, qrY + qrSize + 40);

  ctx.textAlign = "left";
  const logoSize = 112;
  const brandY = qrY + 20;
  let textX = PAD;
  if (logo) {
    // 标识是圆形图案，裁成圆形，去掉方形底色
    ctx.save();
    ctx.beginPath();
    ctx.arc(PAD + logoSize / 2, brandY + logoSize / 2, logoSize / 2 - 2, 0, Math.PI * 2);
    ctx.clip();
    ctx.drawImage(logo, PAD, brandY, logoSize, logoSize);
    ctx.restore();
    textX = PAD + logoSize + 28;
  }
  ctx.fillStyle = COLORS.ink;
  ctx.font = `700 56px ${SERIF}`;
  ctx.fillText(SITE_NAME, textX, brandY + 72);
  ctx.fillStyle = COLORS.muted;
  ctx.font = `400 34px ${SERIF}`;
  ctx.fillText(SITE_SLOGAN, PAD, brandY + logoSize + 76);
  ctx.font = `400 28px ${SERIF}`;
  ctx.fillText("sutratoday.com", PAD, brandY + logoSize + 126);

  return canvas;
}

function drawQr(ctx, text, x, y, size) {
  const qr = qrcode(0, "M");
  qr.addData(text);
  qr.make();
  const count = qr.getModuleCount();
  const quiet = 2;
  const cell = Math.floor(size / (count + quiet * 2));
  const drawn = cell * (count + quiet * 2);
  const offsetX = x + Math.floor((size - drawn) / 2);
  const offsetY = y + Math.floor((size - drawn) / 2);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(x, y, size, size);
  ctx.fillStyle = COLORS.ink;
  for (let row = 0; row < count; row += 1) {
    for (let col = 0; col < count; col += 1) {
      if (qr.isDark(row, col)) {
        ctx.fillRect(offsetX + (col + quiet) * cell, offsetY + (row + quiet) * cell, cell, cell);
      }
    }
  }
}

// 按字折行（中文没有空格可断）
function wrapText(ctx, text, maxWidth, font) {
  ctx.font = font;
  const lines = [];
  let line = "";
  for (const char of text) {
    if (line && ctx.measureText(line + char).width > maxWidth) {
      lines.push(line);
      line = char;
    } else {
      line += char;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function formatDate(d) {
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`;
}

// 网页字体按需加载；加载失败（如网络受限）时用系统字体
async function loadFonts(text) {
  if (!document.fonts?.load) return;
  const weights = ["400", "500", "600", "700"];
  await Promise.race([
    Promise.all(weights.map((w) => document.fonts.load(`${w} 40px "Noto Serif SC"`, text).catch(() => null))),
    new Promise((resolve) => setTimeout(resolve, 3000)),
  ]);
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

// ── 弹窗 ───────────────────────────────────────────────────

function mountDialog() {
  document.querySelector(".checkin-share")?.remove();
  const dialog = document.createElement("div");
  dialog.className = "checkin-share";
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-modal", "true");
  dialog.setAttribute("aria-label", "分享打卡");
  dialog.innerHTML = `
    <div class="checkin-share-panel">
      <div class="checkin-share-head">
        <p class="checkin-share-title">分享打卡</p>
        <button class="checkin-share-close" type="button" aria-label="关闭">×</button>
      </div>
      <div class="checkin-share-body">
        <p class="checkin-share-status">正在生成图片…</p>
      </div>
    </div>
  `;
  const close = () => {
    const url = dialog.dataset.objectUrl;
    if (url) URL.revokeObjectURL(url);
    dialog.remove();
    document.removeEventListener("keydown", onKey);
  };
  const onKey = (event) => {
    if (event.key === "Escape") close();
  };
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog || event.target.closest(".checkin-share-close")) close();
  });
  document.addEventListener("keydown", onKey);
  document.body.appendChild(dialog);
  dialog.querySelector(".checkin-share-close")?.focus();
  return dialog;
}

function showResult(dialog, blob, target) {
  const url = URL.createObjectURL(blob);
  dialog.dataset.objectUrl = url;
  const fileName = `今文佛典-打卡-${target.qrSlug || "sutra"}.png`;
  const file = typeof File === "function" ? new File([blob], fileName, { type: "image/png" }) : null;
  const canShareFile = Boolean(file && navigator.canShare?.({ files: [file] }));
  dialog.querySelector(".checkin-share-body").innerHTML = `
    <img class="checkin-share-image" src="${url}" alt="${escapeHtml(shareHeadline(target))}" />
    <p class="checkin-share-hint">手机上可长按图片保存或发送给朋友</p>
    <div class="checkin-share-actions">
      ${canShareFile ? `<button class="primary-link" type="button" data-share-action="share">分享</button>` : ""}
      <a class="${canShareFile ? "checkin-share-secondary" : "primary-link"}" href="${url}" download="${escapeHtml(fileName)}">保存图片</a>
    </div>
  `;
  dialog.querySelector('[data-share-action="share"]')?.addEventListener("click", () => {
    navigator
      .share({ files: [file], title: SITE_NAME, text: shareHeadline(target) })
      .catch(() => {
        // 读者取消分享时忽略
      });
  });
}
