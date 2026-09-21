/**
 * Assign origin / genre / doctrine for catalog browsing.
 * Keeps CBETA category as bibliographic reference; this is a reading taxonomy.
 */

const DOCTRINE_BY_CATEGORY = {
  阿含部類: ["agama"],
  本緣部類: ["avadana"],
  般若部類: ["prajna"],
  法華部類: ["lotus"],
  華嚴部類: ["avatamsaka"],
  淨土宗部類: ["pureland"],
  密教部類: ["esoteric"],
  涅槃部類: ["tathagatagarbha"],
  寶積部類: ["vaipulya"],
  大集部類: ["vaipulya"],
  律部類: ["vinaya_d"],
  毘曇部類: ["abhidharma"],
  中觀部類: ["madhyamaka"],
  瑜伽部類: ["yogacara"],
  禪宗部類: ["chan"],
  論集部類: ["sastra_misc"],
  經集部類: ["misc"],
  史傳部類: [],
  事彙部類: [],
};

const CHINESE_AUTHOR_RE = /[撰述著集記造注疏鈔解說科註注]/;
const TRANSLATION_RE = /[譯译]/;
const INDIAN_COMPOSED_RE = /[造作]/;
const EAST_ASIAN_RE = /新羅|高麗|百濟|日本|鎌倉|平安|室町|朝鮮/;
const COMMENTARY_TITLE_RE =
  /(疏|鈔|玄義|文句|釋籤|要解|註解|注解|義記|義疏|玄贊|指要|略疏|會釋|通義|科文|科註|科注)/;
const YULU_TITLE_RE = /(語錄|语录|燈錄|灯录|廣錄|广录|禪師|禅师)/;

function cleanTitle(title) {
  return String(title || "").replace(/\([^)]*\)/g, "").trim();
}

function classifyOrigin(work) {
  const tr = work.translator || "";
  const title = cleanTitle(work.title);
  const cat = work.category || "";
  const id = work.cbeta_id || "";

  if (EAST_ASIAN_RE.test(tr) || EAST_ASIAN_RE.test(title)) {
    return "other_east_asian";
  }

  if (cat === "禪宗部類") return "chinese";
  if (cat === "史傳部類" || cat === "事彙部類") return "chinese";

  const hasChineseAuthor = CHINESE_AUTHOR_RE.test(tr);
  const hasTranslation = TRANSLATION_RE.test(tr);
  const indianAuthoredThenTranslated =
    INDIAN_COMPOSED_RE.test(tr) && hasTranslation && !/解|註|注|疏|述|撰/.test(tr);

  if (indianAuthoredThenTranslated) return "indian";

  // Chinese commentary / annotation markers in contributor line
  if (hasChineseAuthor && /解|註|注|疏|述|撰|說|記|集|編|校輯/.test(tr)) {
    // e.g. 明 智旭解、隋 智顗說、梁 法雲撰
    if (!hasTranslation || /解|註|注|疏|述|撰/.test(tr)) return "chinese";
  }

  if (COMMENTARY_TITLE_RE.test(title) && (!hasTranslation || hasChineseAuthor)) {
    return "chinese";
  }

  if (hasTranslation) return "indian";

  if (id.startsWith("X")) return "chinese";

  // Empty translator: prefer category defaults
  if (
    ["阿含部類", "本緣部類", "般若部類", "法華部類", "華嚴部類", "淨土宗部類", "涅槃部類", "寶積部類", "大集部類", "律部類", "毘曇部類", "中觀部類", "瑜伽部類", "論集部類", "經集部類"].includes(cat)
  ) {
    if (COMMENTARY_TITLE_RE.test(title)) return "chinese";
    return "indian";
  }

  return "chinese";
}

function classifyGenre(work, origin) {
  const cat = work.category || "";
  const title = cleanTitle(work.title);
  const tr = work.translator || "";

  if (cat === "史傳部類" || cat === "事彙部類") return "history";
  if (cat === "禪宗部類" || YULU_TITLE_RE.test(title)) return "yulu";

  if (origin === "chinese" || origin === "other_east_asian") {
    if (cat === "律部類") return "commentary";
    if (COMMENTARY_TITLE_RE.test(title) || CHINESE_AUTHOR_RE.test(tr)) return "commentary";
    // Chinese systematic works filed under doctrine categories still read as 注疏
    if (["法華部類", "華嚴部類", "般若部類", "淨土宗部類", "涅槃部類", "瑜伽部類", "中觀部類", "毘曇部類", "論集部類", "經集部類", "寶積部類", "大集部類", "本緣部類", "阿含部類"].includes(cat)) {
      return "commentary";
    }
    return "commentary";
  }

  // Indian (and rare other) texts
  if (cat === "律部類") return "vinaya";
  if (["毘曇部類", "中觀部類", "論集部類"].includes(cat)) return "sastra";
  if (cat === "瑜伽部類") {
    if (/經/.test(title) && !/論/.test(title)) return "sutra";
    return "sastra";
  }
  if (/論/.test(title) && !/經/.test(title) && ["般若部類", "經集部類", "寶積部類", "大集部類", "涅槃部類", "淨土宗部類"].includes(cat)) {
    return "sastra";
  }
  return "sutra";
}

function classifyDoctrine(work) {
  const cat = work.category || "";
  const title = cleanTitle(work.title);
  const doctrines = [...(DOCTRINE_BY_CATEGORY[cat] || ["misc"])];

  // Dual-tag well-known cross-system texts
  if (/楞伽/.test(title)) {
    addUnique(doctrines, "yogacara");
    addUnique(doctrines, "tathagatagarbha");
  }
  if (/勝鬘|如來藏|不增不減|無上依/.test(title)) {
    addUnique(doctrines, "tathagatagarbha");
  }
  if (/解深密/.test(title)) {
    addUnique(doctrines, "yogacara");
  }
  if (/维摩|維摩/.test(title) && doctrines.includes("misc")) {
    // keep misc; could also vaipulya
    doctrines.length = 0;
    doctrines.push("vaipulya");
  }

  return doctrines;
}

function addUnique(list, id) {
  if (!list.includes(id)) list.push(id);
}

function classifyWork(work) {
  const origin = classifyOrigin(work);
  const genre = classifyGenre(work, origin);
  const doctrine = classifyDoctrine(work);
  return { origin, genre, doctrine };
}

module.exports = {
  classifyWork,
  DOCTRINE_BY_CATEGORY,
};
