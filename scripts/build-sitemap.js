#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const INDEX_PATH = path.join(__dirname, "..", "sutras-raw-index.json");
const OUTPUT_PATH = path.join(__dirname, "..", "sitemap.xml");
const SITE_URL = "https://sutratoday.com";

// Well-known sutras that should always be included (by CBETA ID)
const PRIORITY_WORKS = new Set([
  // 般若部
  "T0235", // 金刚经
  "T0251", // 心经
  "T0220", // 大般若经
  "T0221", // 光赞般若经
  "T0223", // 摩诃般若波罗蜜经
  "T0227", // 小品般若波罗蜜经
  // 法华部
  "T0262", // 妙法莲华经
  "T0263", // 正法华经
  // 华严部
  "T0278", // 大方广佛华严经(60卷)
  "T0279", // 大方广佛华严经(80卷)
  "T0293", // 十地经
  // 宝积部
  "T0310", // 大宝积经
  "T0360", // 佛说无量寿经
  "T0365", // 佛说观无量寿佛经
  "T0366", // 佛说阿弥陀经
  // 涅槃部
  "T0374", // 大般涅槃经
  "T0375", // 大般涅槃经(南本)
  // 大集部
  "T0397", // 大方等大集经
  // 经集部
  "T0412", // 地藏菩萨本愿经
  "T0416", // 大方广十轮经
  "T0417", // 地藏十轮经
  "T0450", // 药师经
  "T0475", // 维摩诘所说经
  "T0480", // 文殊师利所说摩诃般若波罗蜜经
  "T0586", // 佛说无量寿经
  "T0642", // 佛说首楞严三昧经
  "T0665", // 金光明经
  "T0663", // 金光明最胜王经
  "T0784", // 四十二章经
  "T0842", // 圆觉经
  "T0848", // 大毘卢遮那成佛经
  // 阿含部
  "T0001", // 长阿含经
  "T0026", // 中阿含经
  "T0099", // 杂阿含经
  "T0125", // 增一阿含经
  // 本缘部
  "T0152", // 六度集经
  "T0190", // 佛本行集经
  // 律部
  "T1428", // 四分律
  "T1421", // 弥沙塞部五分律
  // 净土
  "T1969A", // 往生论注
  // 禅宗
  "T2007", // 大慧普觉禅师语录
  "T2008", // 圆悟佛果禅师语录
  "T2076", // 景德传灯录
  // 论部
  "T1509", // 大智度论
  "T1564", // 中论
  "T1585", // 成唯识论
  "T1579", // 瑜伽师地论
  "T1558", // 阿毘达磨俱舍论
  "T1666", // 大乘起信论
]);

function buildSitemap() {
  const index = JSON.parse(fs.readFileSync(INDEX_PATH, "utf-8"));

  // Score works: priority list gets high score, then by translation/review status
  const scored = index.works.map((work) => {
    let score = 0;
    if (PRIORITY_WORKS.has(work.cbeta_id)) score += 1000;
    if (work.review_status === "human_reviewed") score += 100;
    if (work.review_status === "ai_reviewed") score += 50;
    if (work.translation_status === "translated") score += 30;
    if (work.translation_status === "translating") score += 10;
    return { work, score };
  });

  // Sort by score descending, take top 100
  scored.sort((a, b) => b.score - a.score || a.work.cbeta_id.localeCompare(b.work.cbeta_id));
  const top100 = scored.slice(0, 100);

  const today = new Date().toISOString().split("T")[0];

  let xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>${SITE_URL}/</loc>
    <lastmod>${today}</lastmod>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>${SITE_URL}/catalog.html</loc>
    <lastmod>${today}</lastmod>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>${SITE_URL}/participate.html</loc>
    <lastmod>${today}</lastmod>
    <priority>0.5</priority>
  </url>
`;

  for (const { work } of top100) {
    const slug = work.first_slug;
    const lastmod = work.updated_at || today;
    const priority = PRIORITY_WORKS.has(work.cbeta_id) ? "0.8" : "0.6";
    xml += `  <url>
    <loc>${SITE_URL}/reader.html?doc=${encodeURIComponent(slug)}</loc>
    <lastmod>${lastmod}</lastmod>
    <priority>${priority}</priority>
  </url>
`;
  }

  xml += `</urlset>
`;

  fs.writeFileSync(OUTPUT_PATH, xml, "utf-8");
  console.log(`Sitemap written to ${OUTPUT_PATH} with ${top100.length + 3} URLs`);
}

buildSitemap();
