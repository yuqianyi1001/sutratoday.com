const getCompactVolumeLabel = (volume, unit = "卷") => {
  const numerals = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"];
  const toChinese = (num) => {
    if (num <= 10) return numerals[num];
    if (num < 20) return "十" + numerals[num % 10];
    const tens = Math.floor(num / 10);
    const ones = num % 10;
    return numerals[tens] + "十" + (ones ? numerals[ones] : "");
  };
  if (unit === "品") return `第${toChinese(volume)}品`;
  return `${unit}${toChinese(volume)}`;
};

const SURANGAMA_VOLUMES = [
  { volume_index: 1, volume_label: "卷第一", summary: "由阿难遭难起疑，层层破除攀缘妄心，开启楞严经卷一显真破妄的论证。" },
  { volume_index: 2, volume_label: "卷第二", summary: "由波斯匿王问无常身入手，佛层层显发见性不灭，并进一步破除因缘、自然、和合等执，开示五阴本空。" },
  { volume_index: 3, volume_label: "卷第三", summary: "本卷广破六入、十二处、十八界与七大之执，显明一切法皆即如来藏妙真如性，并引发阿难深誓度生。" },
  { volume_index: 4, volume_label: "卷第四", summary: "由富楼那发问而广明迷妄起世界、如来藏随缘不变，并转入发心修证、六根优劣与闻性常住的关键开示。" },
  { volume_index: 5, volume_label: "卷第五", summary: "本卷广明六根结缚与解结次第，并集诸圣各陈圆通所由，最后以耳根圆通与念佛圆通显出入道关键。" },
  { volume_index: 6, volume_label: "卷第六", summary: "本卷先详陈观世音耳根圆通与文殊拣选，后由阿难为末法众生再请修定根本，如来由此开出四种清净明诲，确立修三摩地的戒行基础。" },
  { volume_index: 7, volume_label: "卷第七", summary: "本卷详说末法修学的道场仪轨，重宣楞严神咒与护法功德，并转入干慧地总启、众生世界颠倒及十二类生的轮回业因。" },
  { volume_index: 8, volume_label: "卷第八", summary: "本卷由三种渐次与五十五位真菩提路展开修证位次，又广明十习因、六交报以及鬼畜人仙诸趣流转，系统说明业因与果报的相续。" },
  { volume_index: 9, volume_label: "卷第九", summary: "本卷先收束色界、无色界与阿修罗诸趣，继而系统开示五阴魔境，重点分析色阴、受阴、想阴中的诸种偏差与魔扰。" },
  { volume_index: 10, volume_label: "卷第十", summary: "本卷继续辨析行阴、识阴中的外道邪执，收束五阴妄想根元，并以持经功德与法会圆满作为全经结尾。" },
];

const SURANGAMA_DOCUMENTS = SURANGAMA_VOLUMES.map((item) => {
  const paddedIndex = String(item.volume_index).padStart(2, "0");
  return {
    title: `大佛顶首楞严经 ${item.volume_label}`,
    short_title: `楞严经卷${item.volume_index}`,
    slug: `surangama-sutra-${paddedIndex}`,
    volume_label: item.volume_label,
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-22",
    summary: item.summary,
    tags: ["楞严", "长经"],
    translated_by: "gpt5",
    path: `content/sutras/surangama-sutra-${paddedIndex}.md`,
    work_id: "surangama-sutra",
    work_title: "大佛顶首楞严经",
    work_short_title: "楞严经",
    volume_index: item.volume_index,
    volume_unit: "卷",
  };
});

const LANKAVATARA_VOLUMES = [
  { index: 1, label: "卷第一", summary: "禅宗印心之经，系统宣说五法、三自性、八识、二无我及如来藏法门。" },
  { index: 2, label: "卷第二", summary: "深入阐述阿赖耶识与如来藏的关系，区分八识之相，并开示三种意生身之胜境。" },
  { index: 3, label: "卷第三", summary: "详析五法、三自性、八识、二无我等核心义理，并辩证说空、无生、不二之旨。" },
  { index: 4, label: "卷第四", summary: "广说陀罗尼修持、如来涅槃之真实义，并严嘱断除肉食，以此成就慈悲佛种。" },
];

const LANKAVATARA_DOCUMENTS = LANKAVATARA_VOLUMES.map((item) => {
  const paddedIndex = String(item.index).padStart(2, "0");
  return {
    title: `楞伽阿跋多罗宝经 ${item.label}`,
    short_title: `楞伽经卷${item.index}`,
    slug: `lankavatara-sutra-${paddedIndex}`,
    volume_label: item.label,
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-24",
    summary: item.summary,
    tags: ["楞伽", "唯识", "禅宗"],
    translated_by: "gemini3",
    path: `content/sutras/lankavatara-sutra-${paddedIndex}.md`,
    work_id: "lankavatara-sutra",
    work_title: "楞伽阿跋多罗宝经",
    work_short_title: "楞伽经",
    volume_index: item.index,
    volume_unit: "卷",
  };
});

const SAMYUKTA_AGAMA_VOLUMES = [
  { index: 1, label: "卷第一", summary: "卷一集中开示五蕴无常、非我、味患、离欲与多闻说法之义。" },
  { index: 2, label: "卷第二", summary: "卷二围绕五蕴非我、世间集灭、取著系缚等义展开。" },
  { index: 3, label: "卷第三", summary: "卷三集中阐明五受阴的集灭、禅观、圣法印与因缘染净。" },
  { index: 4, label: "卷第四", summary: "卷四集中讨论孝养父母、布施福田、真比丘义等面对在家众的教化。" },
  { index: 5, label: "卷第五", summary: "卷五集中辨明五受阴非我、断常两边与病身病心之别。" },
  { index: 6, label: "卷第六", summary: "卷六从有流、众生、魔与死法等角度层层观照五受阴。" },
  { index: 7, label: "卷第七", summary: "卷七说明忧苦、我慢与诸外道邪见如何生起。" },
  { index: 8, label: "卷第八", summary: "卷八围绕六入与六触展开，系统推进六入观。" },
  { index: 9, label: "卷第九", summary: "卷九围绕六触因缘与魔缚、二十亿耳调弦精进等主题展开。" },
  { index: 10, label: "卷第十", summary: "卷十重回五受阴观，从无明与明、四果进修到僧团警策。" },
  { index: 11, label: "卷第十一", summary: "卷十一围绕二法空观、难陀示范根门修学等主题展开。" },
  { index: 12, label: "卷第十二", summary: "卷十二以缘起相应为主，系统开显缘起正见。" },
  { index: 13, label: "卷第十三", summary: "卷十三系统展开六入观，包含第一义空等深义。" },
  { index: 14, label: "卷第十四", summary: "卷十四围绕缘起诸智及如实知六入等主题展开。" },
  { index: 15, label: "卷第十五", summary: "卷十五围绕见法涅槃、四食集灭与四圣谛修证次第展开。" },
  { index: 16, label: "卷第十六", summary: "卷十六系统阐述四圣谛的唯一核心地位，包含著名藕孔军譬喻。" },
  { index: 17, label: "卷第十七", summary: "卷十七围绕界观与受观，阐明诸受集灭味患离。" },
  { index: 18, label: "卷第十八", summary: "卷十八围绕出家道与贤圣修学，包含目犍连的圣住。" },
  { index: 19, label: "卷第十九", summary: "卷十九围绕天人福业与业报观，包含阿那律开示四念处。" },
  { index: 20, label: "卷第二十", summary: "卷二十收束到正念、离欲与智慧解脱。" },
  { index: 21, label: "卷第二十一", summary: "卷二十一围绕阿难断爱与质多罗长者问答展开。" },
  { index: 22, label: "卷第二十二", summary: "卷二十二以天子夜问偈颂为主，收束到精进与智慧解脱。" },
  { index: 23, label: "卷第二十三", summary: "卷二十三系统呈现阿育王兴起佛教事业的因缘。" },
  { index: 24, label: "卷第二十四", summary: "卷二十四详述四念处是一乘道、甘露法与善法聚。" },
  { index: 25, label: "卷第二十五", summary: "卷二十五预记法灭之相，记述阿育王晚年施半果因缘。" },
  { index: 26, label: "卷第二十六", summary: "卷二十六系统说明修行根器、五力与七觉支消长。" },
  { index: 27, label: "卷第二十七", summary: "卷二十七完整铺开七觉支的修道框架。" },
  { index: 28, label: "卷第二十八", summary: "卷二十八集中开显八正道与沙门果。" },
  { index: 29, label: "卷第二十九", summary: "卷二十九广开安那般那念十六特胜及三学总纲。" },
  { index: 30, label: "卷第三十", summary: "卷三十说明正法信与不放逸如何护持学人走向解脱。" },
  { index: 31, label: "卷第三十一", summary: "卷三十一系统铺开从禅观到漏尽解脱的修道次第。" },
  { index: 32, label: "卷第三十二", summary: "卷三十二显明中道与正法调御的标准。" },
  { index: 33, label: "卷第三十三", summary: "卷三十三揭出无始轮回之苦，归结到观五阴无常非我。" },
  { index: 34, label: "卷第三十四", summary: "卷三十四说明离诸见而依四谛缘起，显明真实出路。" },
  { index: 35, label: "卷第三十五", summary: "卷三十五说明修行终归八正道、止观与离爱解脱。" },
  { index: 36, label: "卷第三十六", summary: "卷三十六简要开示出离世间与趣向涅槃的要点。" },
  { index: 37, label: "卷第三十七", summary: "卷三十七确立在家与出家同依的正法标准。" },
  { index: 38, label: "卷第三十八", summary: "卷三十八系统显出戒德、智慧与调伏心意的修道标准。" },
  { index: 39, label: "卷第三十九", summary: "卷三十九显出如来与弟子如何以正念智慧超出魔境。" },
  { index: 40, label: "卷第四十", summary: "卷四十赞叹不嗔、忍辱、净戒与调伏嗔恚。" },
  { index: 41, label: "卷第四十一", summary: "卷四十一显出老上座在末世护持正法的风骨与标准。" },
  { index: 42, label: "卷第四十二", summary: "卷四十二反复劝人及早修善、修心、修道。" },
  { index: 43, label: "卷第四十三", summary: "卷四十三系统指向从六入、五欲中出离，终归涅槃。" },
  { index: 44, label: "卷第四十四", summary: "卷四十四收束为“依法而住，终归寂灭”的主线。" },
  { index: 45, label: "卷第四十五", summary: "卷四十五收束为“以正见破魔，以正法自净”的主线。" },
  { index: 46, label: "卷第四十六", summary: "卷四十六归结到“善护身口意，修福而不放逸”。" },
  { index: 47, label: "卷第四十七", summary: "卷四十七系统铺开修学次第，归结到断有、无住。" },
  { index: 48, label: "卷第四十八", summary: "卷四十八收束为“以正行积福，以智慧度流”。" },
  { index: 49, label: "卷第四十九", summary: "卷四十九归结到“世间边在此身中，离爱方出魔网”。" },
  { index: 50, label: "卷第五十", summary: "卷五十收束为“鬼神诸天皆劝人精进出离”。" },
];

const SAMYUKTA_AGAMA_DOCUMENTS = SAMYUKTA_AGAMA_VOLUMES.map((item) => {
  const paddedIndex = String(item.index).padStart(2, "0");
  return {
    title: `杂阿含经 卷第${item.index}`,
    short_title: `杂阿含经卷${item.index}`,
    slug: `samyukta-agama-${paddedIndex}`,
    volume_label: item.label,
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-29",
    summary: item.summary,
    tags: ["阿含", "早期佛教"],
    translated_by: "gemini3",
    path: `content/sutras/samyukta-agama-${paddedIndex}.md`,
    work_id: "samyukta-agama",
    work_title: "杂阿含经",
    work_short_title: "杂阿含经",
    volume_index: item.index,
    volume_unit: "卷",
  };
});

export const manifest = [
  "content/sutras/heart-sutra.md",
  "content/sutras/diamond-sutra.md",
  "content/sutras/amitabha-sutra.md",
  "content/sutras/medicine-buddha-sutra.md",
  "content/sutras/lotus-sutra-universal-gate.md",
  "content/sutras/samantabhadra-vows.md",
  "content/sutras/buddha-bequeathed-teaching.md",
  "content/sutras/sutra-in-forty-two-sections.md",
  "content/sutras/sutra-of-eight-realizations.md",
  ...SURANGAMA_DOCUMENTS.map((doc) => doc.path),
  ...LANKAVATARA_DOCUMENTS.map((doc) => doc.path),
  ...SAMYUKTA_AGAMA_DOCUMENTS.map((doc) => doc.path),
  "content/sutras/ullambana-sutra.md",
  "content/sutras/tathagatagarbha-sutra.md",
  "content/sutras/satipatthana-sutra.md",
  "content/sutras/anapanasati-sutra.md",
  "content/sutras/ksitigarbha-divination-sutra.md",
  "content/sutras/milinda-panha.md",
  "content/sutras/mulamadhyamakakarika.md",
  "content/sutras/awakening-of-faith.md",
];

export const documentIndex = [
  {
    title: "般若波罗蜜多心经",
    short_title: "心经",
    slug: "heart-sutra",
    volume_label: "全一卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-22",
    summary: "直指五蕴皆空、无所得与离执解脱的核心义旨。",
    tags: ["般若", "入门"],
    translated_by: "gpt5",
    path: "content/sutras/heart-sutra.md",
  },
  ...SURANGAMA_DOCUMENTS,
  ...SAMYUKTA_AGAMA_DOCUMENTS,
  {
    title: "佛说大安般守意经",
    short_title: "大安般守意经",
    slug: "anapanasati-sutra",
    volume_label: "全二卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-27",
    summary: "汉传佛教最早译出的禅经，系统教授“六妙门”法要。",
    tags: ["禅定", "数息观"],
    translated_by: "gemini3",
    path: "content/sutras/anapanasati-sutra.md",
  },
  {
    title: "那先比丘经",
    short_title: "那先经",
    slug: "milinda-panha",
    volume_label: "全三卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-27",
    summary: "记录国王弥兰陀与那先比丘的哲学辩论。",
    tags: ["经", "辩论"],
    translated_by: "gemini3",
    path: "content/sutras/milinda-panha.md",
  },
  {
    title: "中论",
    short_title: "中论",
    slug: "mulamadhyamakakarika",
    volume_label: "全四卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-27",
    summary: "龙树菩萨造，中观学派的根本论著。",
    tags: ["论书", "中观"],
    translated_by: "gemini3",
    path: "content/sutras/mulamadhyamakakarika.md",
  },
  {
    title: "大乘起信论",
    short_title: "起信论",
    slug: "awakening-of-faith",
    volume_label: "全一卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-27",
    summary: "系统归纳大乘佛教理论骨架，明“一心二门”。",
    tags: ["论书", "一心二门"],
    translated_by: "gemini3",
    path: "content/sutras/awakening-of-faith.md",
  },
];

export const HOME_FEATURED_LIMIT = 6;
export const SITE_BASE_URL = "https://sutratoday.com/";
export const GITHUB_REPO_BASE = "https://github.com/yuqianyi1001/sutratoday.com/blob/main/";

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

export async function loadDocuments() {
  const loaded = await Promise.all(manifest.map(loadDocument));
  return loaded.sort((a, b) => a.title.localeCompare(b.title, "zh-Hans-CN"));
}

export async function loadDocument(path) {
  const response = await fetch(path);
  const raw = await response.text();
  const matched = documentIndex.find(item => item.path === path);
  const { meta, body } = parseDocument(raw, path);
  return { ...matched, ...meta, body, path };
}

function parseDocument(raw, path) {
  const match = raw.match(/^---\n([\s\S]*?)\n---\n?/);
  let meta = {};
  let body = raw;
  if (match) {
    const lines = match[1].split("\n");
    meta = Object.fromEntries(lines.map(line => {
      const d = line.indexOf(":");
      return d === -1 ? null : [line.slice(0, d).trim(), line.slice(d + 1).trim()];
    }).filter(Boolean));
    body = raw.slice(match[0].length);
  }
  return { meta, body, slug: meta.slug || path.split("/").pop().replace(/\.md$/, "") };
}

export function renderMarkdown(markdown) {
  return markdown.split("\n").map(l => `<p>${l}</p>`).join("");
}
