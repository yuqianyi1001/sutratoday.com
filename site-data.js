const SURANGAMA_VOLUMES = [
  {
    volume_index: 1,
    volume_label: "卷第一",
    summary: "由阿难遭难起疑，层层破除攀缘妄心，开启楞严经卷一显真破妄的论证。",
  },
  {
    volume_index: 2,
    volume_label: "卷第二",
    summary: "由波斯匿王问无常身入手，佛层层显发见性不灭，并进一步破除因缘、自然、和合等执，开示五阴本空。",
  },
  {
    volume_index: 3,
    volume_label: "卷第三",
    summary: "本卷广破六入、十二处、十八界与七大之执，显明一切法皆即如来藏妙真如性，并引发阿难深誓度生。",
  },
  {
    volume_index: 4,
    volume_label: "卷第四",
    summary: "由富楼那发问而广明迷妄起世界、如来藏随缘不变，并转入发心修证、六根优劣与闻性常住的关键开示。",
  },
  {
    volume_index: 5,
    volume_label: "卷第五",
    summary: "本卷广明六根结缚与解结次第，并集诸圣各陈圆通所由，最后以耳根圆通与念佛圆通显出入道关键。",
  },
  {
    volume_index: 6,
    volume_label: "卷第六",
    summary: "本卷先详陈观世音耳根圆通与文殊拣选，后由阿难为末法众生再请修定根本，如来由此开出四种清净明诲，确立修三摩地的戒行基础。",
  },
  {
    volume_index: 7,
    volume_label: "卷第七",
    summary: "本卷详说末法修学的道场仪轨，重宣楞严神咒与护法功德，并转入干慧地总启、众生世界颠倒及十二类生的轮回业因。",
  },
  {
    volume_index: 8,
    volume_label: "卷第八",
    summary: "本卷由三种渐次与五十五位真菩提路展开修证位次，又广明十习因、六交报以及鬼畜人仙诸趣流转，系统说明业因与果报的相续。",
  },
  {
    volume_index: 9,
    volume_label: "卷第九",
    summary: "本卷先收束色界、无色界与阿修罗诸趣，继而系统开示五阴魔境，重点分析色阴、受阴、想阴中的诸种偏差与魔扰。",
  },
  {
    volume_index: 10,
    volume_label: "卷第十",
    summary: "本卷继续辨析行阴、识阴中的外道邪执，收束五阴妄想根元，并以持经功德与法会圆满作为全经结尾。",
  },
];

const SURANGAMA_DOCUMENTS = SURANGAMA_VOLUMES.map((item) => {
  const paddedIndex = String(item.volume_index).padStart(2, "0");
  const volumeUnit = "卷";
  return {
    title: `大佛顶首楞严经 ${item.volume_label}`,
    short_title: `楞严经${getCompactVolumeLabel(item.volume_index, volumeUnit)}`,
    slug: `surangama-sutra-${paddedIndex}`,
    volume_label: item.volume_label,
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-22",
    summary: item.summary,
    tags: ["楞严", "长经", getCompactVolumeLabel(item.volume_index, volumeUnit)],
    translated_by: "gpt5",
    path: `content/sutras/surangama-sutra-${paddedIndex}.md`,
    work_id: "surangama-sutra",
    work_title: "大佛顶首楞严经",
    work_short_title: "楞严经",
    work_summary:
      "《楞严经》十卷次第展开，从破妄显真、圆通修证到戒行、道场、位次与魔境辨析，系统铺陈修行与见地的完整道路。",
    volume_index: item.volume_index,
    volume_unit: volumeUnit,
  };
});

const PLATFORM_SUTRA_VOLUMES = [
  {
    index: 1,
    slug: "01",
    title: "行由品第一",
    summary: "叙述六祖惠能得法因缘，显出顿悟见性、直指本心的禅宗精神。",
  },
  {
    index: 2,
    slug: "02",
    title: "般若品第二",
    summary: "开示摩诃般若波罗蜜，明自性本具智慧，不离见性修行。",
  },
  {
    index: 3,
    slug: "03",
    title: "疑问品第三",
    summary: "通过对净土、功德等问题的解答，揭示唯心净土、见性功德的深刻义理。",
  },
  {
    index: 4,
    slug: "04",
    title: "定慧品第四",
    summary: "阐明定慧一体、不二之义，开示一行三昧与无念法门。",
  },
  {
    index: 5,
    slug: "05",
    title: "坐禅品第五",
    summary: "重新定义禅定与坐禅，强调见性不动、内外无碍。",
  },
  {
    index: 6,
    slug: "06",
    title: "忏悔品第六",
    summary: "传授自性五分法身香及无相忏悔，详述四弘誓愿、三归依与一体三身佛。",
  },
  {
    index: 7,
    slug: "07",
    title: "机缘品第七",
    summary: "记录六祖与法达、智通、智隍等弟子的问答，随机点化，各令悟入。",
  },
  {
    index: 8,
    slug: "08",
    title: "顿渐品第八",
    summary: "辨析顿渐二宗，通过与神秀门人等对话，显明法无顿渐、人有迟疾之旨。",
  },
  {
    index: 9,
    slug: "09",
    title: "宣诏品第九",
    summary: "记录朝廷征诏及六祖与薛简的对话，论说坐禅、见性、道由心悟。",
  },
  {
    index: 10,
    slug: "10",
    title: "付嘱品第十",
    summary: "临终付嘱，教示三十六对法及传法脉络，最后示灭曹溪。",
  },
];

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
    work_summary: "《楞伽经》系统宣说五法、三自性、八识、二无我，是唯识宗与禅宗共同重视的核心经典。",
    volume_index: item.index,
    volume_unit: "卷",
  };
});

const SANDHINIRMOCANA_VOLUMES = [
  { index: 1, label: "卷第一", summary: "系统宣说胜义谛相之义旨，显明超言绝相之真实境界。" },
  { index: 2, label: "卷第二", summary: "详述心意识相与阿赖耶识之深细道理，揭示万法唯识之根源。" },
  { index: 3, label: "卷第三", summary: "系统宣说遍计所执、依他起、圆成实三自性，及对应的三无性义。" },
  { index: 4, label: "卷第四", summary: "详述菩萨地地转进之止观修持法要，阐明瑜伽行派之实修次第。" },
  { index: 5, label: "卷第五", summary: "详述十地菩萨行愿、法身成就及诸佛功德，明究竟解脱之果位。" },
];

const SANDHINIRMOCANA_DOCUMENTS = SANDHINIRMOCANA_VOLUMES.map((item) => {
  const paddedIndex = String(item.index).padStart(2, "0");
  return {
    title: `解深密经 ${item.label}`,
    short_title: `解深密经卷${item.index}`,
    slug: `sandhinirmocana-sutra-${paddedIndex}`,
    volume_label: item.label,
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-24",
    summary: item.summary,
    tags: ["解深密", "唯识", "瑜伽行派"],
    translated_by: "gemini3",
    path: `content/sutras/sandhinirmocana-sutra-${paddedIndex}.md`,
    work_id: "sandhinirmocana-sutra",
    work_title: "解深密经",
    work_short_title: "解深密经",
    work_summary: "《解深密经》是唯识宗的根本经典，系统宣说了阿赖耶识、三自性、三无性等核心法门。",
    volume_index: item.index,
    volume_unit: "卷",
  };
});

const VIMALAKIRTI_VOLUMES = [
  { index: 1, label: "卷上", summary: "展现佛国净土之因，及维摩诘居士以疾设教，摄化诸声闻弟子与菩萨。" },
  { index: 2, label: "卷中", summary: "涵盖文殊问疾、不可思议解脱、观众生、佛道及入不二法门等核心品第。" },
  { index: 3, label: "卷下", summary: "通过香积佛品、菩萨行品至嘱累品，圆满显发不可思议之大乘境界。" },
];

const VIMALAKIRTI_DOCUMENTS = VIMALAKIRTI_VOLUMES.map((item) => {
  const paddedIndex = String(item.index).padStart(2, "0");
  return {
    title: `维摩诘所说经 ${item.label}`,
    short_title: `维摩诘经${item.label}`,
    slug: `vimalakirti-sutra-${paddedIndex}`,
    volume_label: item.label,
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-24",
    summary: item.summary,
    tags: ["维摩诘", "在家修行", "不二法门"],
    translated_by: "gemini3",
    path: `content/sutras/vimalakirti-sutra-${paddedIndex}.md`,
    work_id: "vimalakirti-sutra",
    work_title: "维摩诘所说经",
    work_short_title: "维摩诘经",
    volume_index: item.index,
    volume_unit: "卷",
  };
});

const LOTUS_SUTRA_VOLUMES = [
  { index: 1, label: "卷第一", summary: "经中之王，宣说“开权显实、会三归一”的圆教真理。卷一包含序品与方便品。" },
  { index: 2, label: "卷第二", summary: "包含譬喻品与信解品，通过著名的“火宅喻”与“穷子喻”开示一乘实相。" },
  { index: 3, label: "卷第三", summary: "包含药草喻品、授记品与化城喻品，以“三草二木”与“化城”为喻，阐明如来随机设教之苦心。" },
  { index: 4, label: "卷第四", summary: "涵盖五百弟子授记至劝持品，其中“见宝塔品”现多宝如来座，极显法华经之宏伟庄严。" },
  { index: 5, label: "卷第五", summary: "包含核心章节“如来寿量品”，揭示如来久远成佛之真相，并阐述菩萨之安乐行。" },
  { index: 6, label: "卷第六", summary: "涵盖随喜功德品至药王菩萨本事品，宣说读诵受持之殊胜功德，并记载常不轻菩萨之大忍。" },
  { index: 7, label: "卷第七", summary: "涵盖普门品等重要品第，最后以普贤菩萨劝发品作为全经之庄严结尾。" },
];

const LOTUS_SUTRA_DOCUMENTS = LOTUS_SUTRA_VOLUMES.map((item) => {
  const paddedIndex = String(item.index).padStart(2, "0");
  return {
    title: `妙法莲华经 ${item.label}`,
    short_title: `法华经卷${item.index}`,
    slug: `lotus-sutra-${paddedIndex}`,
    volume_label: item.label,
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-25",
    summary: item.summary,
    tags: ["法华", "圆教", "一乘"],
    translated_by: "gemini3",
    path: `content/sutras/lotus-sutra-${paddedIndex}.md`,
    work_id: "lotus-sutra",
    work_title: "妙法莲华经",
    work_short_title: "法华经",
    work_summary: "《妙法莲华经》被誉为经中之王，通过精彩的比喻宣说一乘实相，会三归一，是圆教的核心经典。",
    volume_index: item.index,
    volume_unit: "卷",
  };
});

const DHARMAPADA_VOLUMES = [
  { index: 1, label: "卷上", summary: "佛教智慧格言集，通过简短精炼的偈颂宣说出离、慈悲与觉悟的真理。" },
  { index: 2, label: "卷下", summary: "继续阐述爱欲、利养及沙门行等深刻智慧，直至吉祥圆满。" },
];

const DHARMAPADA_DOCUMENTS = DHARMAPADA_VOLUMES.map((item) => {
  const paddedIndex = String(item.index).padStart(2, "0");
  return {
    title: `法句经 ${item.label}`,
    short_title: `法句经${item.label}`,
    slug: `dharmapada-${paddedIndex}`,
    volume_label: item.label,
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-25",
    summary: item.summary,
    tags: ["格言", "智慧", "阿含"],
    translated_by: "gemini3",
    path: `content/sutras/dharmapada-${paddedIndex}.md`,
    work_id: "dharmapada",
    work_title: "法句经",
    work_short_title: "法句经",
    work_summary: "《法句经》是佛教智慧的结晶，以精炼的偈颂呈现，涵盖了修行的各个方面，易于诵读与实践。",
    volume_index: item.index,
    volume_unit: "卷",
  };
});

const SAMYUKTA_AGAMA_VOLUMES = [
  {
    index: 1,
    label: "卷第一",
    summary: "卷一集中开示五蕴无常、非我、味患、离欲与多闻说法之义，是理解杂阿含早期观法的重要起点。",
  },
  {
    index: 2,
    label: "卷第二",
    summary: "卷二围绕五蕴非我、世间集灭、取著系缚、七处善与速尽诸漏等义展开，是卷一之后对五受阴观的进一步铺陈。",
  },
  {
    index: 3,
    label: "卷第三",
    summary: "卷三集中阐明五受阴的集灭、禅观、有身、重担、圣法印与因缘染净，进一步把五蕴观推进到见道与解脱的层次。",
  },
  {
    index: 4,
    label: "卷第四",
    summary: "卷四集中讨论孝养父母、如法祭会、在家安乐、布施福田、真比丘义与业定贵贱，明显转入面对婆罗门与在家众的教化。",
  },
  {
    index: 5,
    label: "卷第五",
    summary: "卷五围绕差摩、焰摩迦、仙尼、那拘罗长者与萨遮尼犍子的问答，集中辨明五受阴非我、余慢未尽、断常两边与病身病心之别。",
  },
  {
    index: 6,
    label: "卷第六",
    summary: "卷六以罗陀相应为主，从有流、众生、有身、魔与死法等角度层层观照五受阴，并说明出家所为何事及观非我断疑出离。",
  },
  {
    index: 7,
    label: "卷第七",
    summary: "卷七从六见处与五蕴执著入手，系统说明忧苦、我慢与诸外道邪见如何生起，并以断无常、求大师及诸道品灭火收束全卷。",
  },
  {
    index: 8,
    label: "卷第八",
    summary: "卷八围绕六入与六触展开，从无常离贪、一切烧然、罗睺罗受教、二法与大海譬，到涅槃道迹、断一切计及有漏无漏，系统推进六入观。",
  },
  {
    index: 9,
    label: "卷第九",
    summary: "卷九围绕世间与世界边、六触因缘与魔缚、识无我、优波先那不执我所、二十亿耳调弦精进与根门守护等主题，持续展开六入处的修学。",
  },
  {
    index: 10,
    label: "卷第十",
    summary: "卷十重回五受阴观，从无明与明、四果进修、闡陀离二边、泡沫狗柱诸譬，到无常想、低舍与僧团警策，层层推进对五阴无我的体认。",
  },
  {
    index: 11,
    label: "卷第十一",
    summary: "卷十一围绕二法空观、难陀示范根门修学、律仪与不退、供养标准、法次第利益与无上修根等主题，继续从六根六境推进离我执与解脱。",
  },
  {
    index: 12,
    label: "卷第十二",
    summary: "卷十二以缘起相应为主，从爱取有生的集灭、古仙人道与芦束相依，到内触法、因缘法与离二边中道，系统开显缘起正见。",
  },
  {
    index: 13,
    label: "卷第十三",
    summary: "卷十三围绕六六法、六分別六入、见法之义、鹿纽与富楼那问法、一切与内外入处分类，以及第一义空、有因有缘有缚与六常行等主题，系统展开六入观。",
  },
  {
    index: 14,
    label: "卷第十四",
    summary: "卷十四围绕苦乐从缘起生、见具足标准、须深先知法住后知涅槃，以及如实知六入与缘起诸智等主题，系统展开缘起观。",
  },
  {
    index: 15,
    label: "卷第十五",
    summary: "卷十五围绕见法般涅槃、七佛同观缘起、四食集灭、识住增减与四圣谛修证次第，系统展开缘起与四谛观。",
  },
  {
    index: 16,
    label: "卷第十六",
    summary: "卷十六围绕四圣谛是比丘唯一应思惟之法、四谛次第无间等，以及种种界生种种触受爱等主题，系统展开四谛与界观。",
  },
  {
    index: 17,
    label: "卷第十七",
    summary: "卷十七围绕高下诸界、欲害与出要、不我观受、诸受集灭味患离，以及一法至十法的总摄观门，系统展开界观与受观。",
  },
  {
    index: 18,
    label: "卷第十八",
    summary: "卷十八围绕舍利弗与阎浮车问答、三昧与戒根本、如法举罪、净命自活，以及目犍连的圣默然、圣住与勤精进，系统展开出家道与贤圣修学。",
  },
  {
    index: 19,
    label: "卷第十九",
    summary: "卷十九围绕帝释与目犍连问答、布施福报、诸天自记、目犍连所见恶业果报，以及阿那律开示四念处一乘道，系统展开天人福业与业报观。",
  },
  {
    index: 20,
    label: "卷第二十",
    summary: "卷二十围绕阿那律所说四念处、摩诃迦旃延破除争论与种姓执、诃梨聚落长者问爱尽解脱，以及无相心三昧的智果，层层收束到正念、离欲与智慧解脱。",
  },
  {
    index: 21,
    label: "卷第二十一",
    summary: "卷二十一围绕阿难的断爱、善向与三种离炽然之说，以及质多罗长者对三昧、身见、系缚与外道的连串问答，最终收束到不放逸与不再受生的解脱见地。",
  },
  {
    index: 22,
    label: "卷第二十二",
    summary: "卷二十二以天子夜问佛陀的偈颂为主，围绕真实安乐、罗汉假名说我、欲缚出离、商旅与居士受天神警发，以及给孤独长者等因信戒闻法生天的因缘，最终收束到信、不放逸、精进与智慧的解脱路径。",
  },
  {
    index: 23,
    label: "卷第二十三",
    summary: "卷二十三以长篇因缘叙事展开阿育王故事，从童子施沙得佛授记、阿育成长登位、由暴恶转向护法，到礼拜圣迹、供养弟子塔与菩提树，系统呈现法阿育王兴起佛教事业的因缘。",
  },
  {
    index: 24,
    label: "卷第二十四",
    summary: "卷二十四整卷围绕四念处展开，从其作为一乘道、甘露法与善法聚，说到守住自境界、自护护他、初业清净与学地尽漏，以及舍利弗、目揵连涅槃后应以法洲法依安住，层层收束到四念处是众多道品的总持。",
  },
  {
    index: 25,
    label: "卷第二十五",
    summary: "卷二十五以前半卷预记优波掘多出世、难当王中兴佛法与末世斗诤法灭，后半卷叙述阿育王晚年以半个阿摩勒果完成最后布施，并以其后代毁塔灭法收束，集中呈现护法与坏法的两条因缘线。",
  },
  {
    index: 26,
    label: "卷第二十六",
    summary: "卷二十六从三根、五根与五力讲到学力、如来十力，再转入五盖与七觉支的消长，并以无畏王子问答收束，系统说明修行根器、功德增上与众生烦恼清净的因缘。",
  },
  {
    index: 27,
    label: "卷第二十七",
    summary: "卷二十七专讲七觉支的开展与运用，从五盖说十、七觉说十四，到随心调摄、食与不食、善知识、次第生起、修行果报，以及慈心、空处、安那般那念与无常诸想如何摄入觉支，完整铺开这一卷的修道框架。",
  },
  {
    index: 28,
    label: "卷第二十八",
    summary: "卷二十八集中开显八正道，从正见是尽苦前相、无明与明的分路，讲到欲、甘露、学与无学、善知识与正思惟、世俗与出世间正见，以及沙门法、沙门义、沙门果，系统说明邪正二途与解脱正路。",
  },
  {
    index: 29,
    label: "卷第二十九",
    summary: "卷二十九先说沙门、婆罗门与梵行的法、义与果，再广开安那般那念的助缘、十六特胜、诸种功德与多位弟子问答，后半卷转入三学总纲、学地差别与精勤次第，说明从调心入手直到漏尽解脱的完整道路。",
  },
  {
    index: 30,
    label: "卷第三十",
    summary: "卷第三十从乐学戒与三学开篇，继而广说四不坏净、入流分与法镜经，并以诸天天道、那梨迦亡者问答、难提及长者问法等因缘，说明正法信、正思惟与不放逸如何护持学人走向预流乃至究竟解脱。",
  },
  {
    index: 31,
    label: "卷第三十一",
    summary: "卷第三十一先说诸天寿量与凡圣去向，继而广明四禅四无色定、四正断、不放逸与无学三明，并以无为、见谛、求大师、罗睺罗问六入等相应法，系统铺开从禅观到漏尽解脱的修道次第。",
  },
  {
    index: 32,
    label: "卷第三十二",
    summary: "卷第三十二以如来后有不可记与正法沉没因缘开篇，继而借聚落主问答批破伎乐、斗战、自苦、金银受畜等邪见，并广说现法苦集苦灭、布施福不减、慈悲净业以及良马善男子譬喻，显明中道与正法调御的标准。",
  },
  {
    index: 33,
    label: "卷第三十三",
    summary: "卷第三十三以前半卷良马善男子诸譬喻说明根器、调伏与真实禅，后半卷围绕摩诃男所问优婆塞五具足、在家果位、六随念、学无学差别与预流四法展开，并以血、泪、母乳三喻揭出无始轮回之苦，归结到观五阴无常非我而得解脱。",
  },
  {
    index: 34,
    label: "卷第三十四",
    summary: "卷第三十四先以父母难尽、骨山劫久等譬喻极言无始轮回，继以毘富罗山与诸佛出世显示诸行无常，后半卷集中铺开婆蹉种、欝低迦、长爪等外道问难，说明为何不答诸无记见、为何离诸见而依四谛缘起，并以四众得果与止观二法显明佛法真实出路。",
  },
];

const SAMYUKTA_AGAMA_DOCUMENTS = SAMYUKTA_AGAMA_VOLUMES.map((item) => {
  const paddedIndex = String(item.index).padStart(2, "0");
  return {
    title: `杂阿含经 ${item.label}`,
    short_title: `杂阿含经卷${item.index}`,
    slug: `samyukta-agama-${paddedIndex}`,
    volume_label: item.label,
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: item.index === 1 ? "2026-03-27" : "2026-03-28",
    summary: item.summary,
    tags: ["阿含", "五蕴", "无常"],
    translated_by: "gpt5",
    path: `content/sutras/samyukta-agama-${paddedIndex}.md`,
    work_id: "samyukta-agama",
    work_title: "杂阿含经",
    work_short_title: "杂阿含经",
    work_summary: "《杂阿含经》汇集大量围绕五蕴、六处、缘起、无我与解脱展开的早期经教，是理解阿含系佛法的重要根本文献。",
    volume_index: item.index,
    volume_unit: "卷",
  };
});

const RENWANG_VOLUMES = [
  { index: 1, label: "卷上", summary: "般若系护国经典，卷上包含序品、观如来品、菩萨行品及二谛品，阐发般若甚深义理。" },
  { index: 2, label: "卷下", summary: "卷下包含护国品、散华品、受持品及嘱累品，详述持经护国之殊胜功德与感应。" },
];

const RENWANG_DOCUMENTS = RENWANG_VOLUMES.map((item) => {
  const paddedIndex = String(item.index).padStart(2, "0");
  return {
    title: `仁王护国般若波罗蜜多经 ${item.label}`,
    short_title: `仁王经${item.label}`,
    slug: `renwang-sutra-${paddedIndex}`,
    volume_label: item.label,
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-26",
    summary: item.summary,
    tags: ["般若", "护国", "一乘"],
    translated_by: "gemini3",
    path: `content/sutras/renwang-sutra-${paddedIndex}.md`,
    work_id: "renwang-sutra",
    work_title: "仁王护国般若波罗蜜多经",
    work_short_title: "仁王经",
    work_summary: "《仁王经》是般若系的重要护国经典，强调通过般若智慧的修持来护卫国家与众生的安宁。",
    volume_index: item.index,
    volume_unit: "卷",
  };
});

const FANWANG_VOLUMES = [
  { index: 1, label: "卷上", summary: "卷上宣说卢舍那佛为大众开示菩萨心地法门，阐明大乘修行的心要与位次。" },
  { index: 2, label: "卷下", summary: "卷下为菩萨戒本，详列十重四十八轻戒，是大乘修行者受持戒律的根本指南。" },
];

const FANWANG_DOCUMENTS = FANWANG_VOLUMES.map((item) => {
  const paddedIndex = String(item.index).padStart(2, "0");
  return {
    title: `梵网经 ${item.label}`,
    short_title: `梵网经${item.label}`,
    slug: `fanwang-sutra-${paddedIndex}`,
    volume_label: item.label,
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-26",
    summary: item.summary,
    tags: ["戒律", "菩萨道", "心地"],
    translated_by: "gemini3",
    path: `content/sutras/fanwang-sutra-${paddedIndex}.md`,
    work_id: "fanwang-sutra",
    work_title: "梵网经",
    work_short_title: "梵网经",
    work_summary: "《梵网经》是大乘菩萨戒的核心经典，卷上明心地法门，卷下详列菩萨戒条。",
    volume_index: item.index,
    volume_unit: "卷",
  };
});

const GOLDEN_LIGHT_VOLUMES = [
  { index: 1, label: "卷第一", summary: "包含序品及如来寿量品，开示如来寿量无量之真相，为全经之宏伟开端。" },
  { index: 2, label: "卷第二", summary: "核心为忏悔品，详述灭罪除障之法，是全经修行之精要所在。" },
  { index: 3, label: "卷第三", summary: "详述灭业障品，开示远离诸垢、净除恶业之深广义理。" },
  { index: 4, label: "卷第四", summary: "包含最胜品、莲华胜品、金胜陀罗尼品等，宣说持经功德与陀罗尼妙法。" },
  { index: 5, label: "卷第五", summary: "涵盖莲华胜等品，开示菩萨修行之胜境与金光明大义。" },
  { index: 6, label: "卷第六", summary: "包含四天王观察人天品等，宣说护世四天王护持国土之宏愿。" },
  { index: 7, label: "卷第七", summary: "涵盖正安品、大辩才天女品，赞叹辩才天女之智慧与护法。" },
  { index: 8, label: "卷第八", summary: "包含大吉祥天女品、坚牢地神品，阐发吉祥繁荣与大地护持之深义。" },
  { index: 9, label: "卷第九", summary: "涵盖僧慎尔耶大将品、王法正论品及善集品，开示护法大将之威德与护国王法。" },
  { index: 10, label: "卷第十", summary: "为全经大圆满，包含舍身品、十方菩萨赞叹品等，并以嘱累品庄严结尾。" },
];

const GOLDEN_LIGHT_DOCUMENTS = GOLDEN_LIGHT_VOLUMES.map((item) => {
  const paddedIndex = String(item.index).padStart(2, "0");
  return {
    title: `金光明最胜王经 ${item.label}`,
    short_title: `金光明经${item.label}`,
    slug: `golden-light-sutra-${paddedIndex}`,
    volume_label: item.label,
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-26",
    summary: item.summary,
    tags: ["护国", "祈福", "金光明"],
    translated_by: "gemini3",
    path: `content/sutras/golden-light-sutra-${paddedIndex}.md`,
    work_id: "golden-light-sutra",
    work_title: "金光明最胜王经",
    work_short_title: "金光明经",
    work_summary: "《金光明最胜王经》是著名的护国三经之一，宣说忏悔灭罪、护世利国及不思议之功德。",
    volume_index: item.index,
    volume_unit: "卷",
  };
});

const PLATFORM_SUTRA_DOCUMENTS = PLATFORM_SUTRA_VOLUMES.map((item) => {
  const volumeUnit = "品";
  return {
    title: `六祖坛经 ${item.title}`,
    short_title: `坛经${item.title.split("品")[0]}品`,
    slug: `platform-sutra-${item.slug}`,
    volume_label: `全一卷 · ${item.title}`,
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-23",
    summary: item.summary,
    tags: ["禅宗", "坛经", item.title.split("品")[0]],
    translated_by: "gemini3",
    path: `content/sutras/platform-sutra-${item.slug}.md`,
    work_id: "platform-sutra",
    work_title: "六祖坛经",
    work_short_title: "坛经",
    work_summary: "《六祖坛经》记载六祖慧能言教，强调顿悟见性、不二法门，是禅宗的核心经典。",
    volume_index: item.index,
    volume_unit: volumeUnit,
  };
});

export const manifest = [
  "content/sutras/heart-sutra.md",
  "content/sutras/diamond-sutra.md",
  "content/sutras/amitabha-sutra.md",
  "content/sutras/medicine-buddha-sutra.md",
  "content/sutras/ksitigarbha-vow-sutra-01.md",
  "content/sutras/ksitigarbha-vow-sutra-02.md",
  "content/sutras/lotus-sutra-universal-gate.md",
  "content/sutras/samantabhadra-vows.md",
  ...PLATFORM_SUTRA_DOCUMENTS.map((doc) => doc.path),
  "content/sutras/buddha-bequeathed-teaching.md",
  "content/sutras/sutra-in-forty-two-sections.md",
  "content/sutras/sutra-of-eight-realizations.md",
  ...SURANGAMA_DOCUMENTS.map((doc) => doc.path),
  ...LANKAVATARA_DOCUMENTS.map((doc) => doc.path),
  ...SANDHINIRMOCANA_DOCUMENTS.map((doc) => doc.path),
  ...VIMALAKIRTI_DOCUMENTS.map((doc) => doc.path),
  ...LOTUS_SUTRA_DOCUMENTS.map((doc) => doc.path),
  ...DHARMAPADA_DOCUMENTS.map((doc) => doc.path),
  ...SAMYUKTA_AGAMA_DOCUMENTS.map((doc) => doc.path),
  "content/sutras/amitayurdhyana-sutra.md",
  "content/sutras/perfect-enlightenment-sutra.md",
  "content/sutras/srimala-sutra.md",
  "content/sutras/rice-seedling-sutra.md",
  "content/sutras/ten-good-karmic-actions-sutra.md",
  ...RENWANG_DOCUMENTS.map((doc) => doc.path),
  ...FANWANG_DOCUMENTS.map((doc) => doc.path),
  ...GOLDEN_LIGHT_DOCUMENTS.map((doc) => doc.path),
  "content/sutras/larger-sukhavati-vyuha-01.md",
  "content/sutras/larger-sukhavati-vyuha-02.md",
];

export const documentIndex = [
  {
    title: "佛说阿弥陀经",
    short_title: "阿弥陀经",
    slug: "amitabha-sutra",
    volume_label: "全一卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-22",
    summary: "净土宗常诵短经，摄极乐依正庄严与执持名号求生净土之旨。",
    tags: ["净土", "短经", "往生"],
    translated_by: "gpt5",
    path: "content/sutras/amitabha-sutra.md",
  },
  {
    title: "佛遗教经",
    short_title: "佛遗教经",
    slug: "buddha-bequeathed-teaching",
    volume_label: "全一卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-22",
    summary: "佛陀临涅槃前的遗教，撮要开示持戒、少欲、精进与修心之道。",
    tags: ["遗教", "戒律", "修行"],
    translated_by: "gpt5",
    path: "content/sutras/buddha-bequeathed-teaching.md",
  },
  {
    title: "金刚般若波罗蜜经",
    short_title: "金刚经",
    slug: "diamond-sutra",
    volume_label: "全一卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-22",
    summary: "般若系重要经典，以反复破相破执开显无住、无我、无所得的菩萨行。",
    tags: ["般若", "破执", "问答"],
    translated_by: "gpt5",
    path: "content/sutras/diamond-sutra.md",
  },
  {
    title: "般若波罗蜜多心经",
    short_title: "心经",
    slug: "heart-sutra",
    volume_label: "全一卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-22",
    summary: "般若系代表短经，直指五蕴皆空、无所得与离执解脱的核心义旨。",
    tags: ["般若", "入门", "短经"],
    translated_by: "gpt5",
    path: "content/sutras/heart-sutra.md",
  },
  {
    title: "地藏菩萨本愿经 卷上",
    short_title: "地藏经卷上",
    slug: "ksitigarbha-vow-sutra-01",
    volume_label: "卷上",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-22",
    summary: "以地藏菩萨大愿、因果业感与孝亲救苦为主线，展开卷上六品义理。",
    tags: ["地藏", "愿力", "孝道"],
    translated_by: "gpt5",
    path: "content/sutras/ksitigarbha-vow-sutra-01.md",
    work_id: "ksitigarbha-vow-sutra",
    work_title: "地藏菩萨本愿经",
    work_short_title: "地藏经",
    work_summary: "《地藏菩萨本愿经》两卷围绕地藏菩萨大愿、因果业报、临终救拔与见闻利益展开，兼明孝亲、修福、称名与救苦之道。",
    volume_index: 1,
  },
  {
    title: "地藏菩萨本愿经 卷下",
    short_title: "地藏经卷下",
    slug: "ksitigarbha-vow-sutra-02",
    volume_label: "卷下",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-23",
    summary: "围绕临终助念、存亡修福、称佛名号与见闻利益等展开卷下七品的实践开示。",
    tags: ["地藏", "愿力", "存亡"],
    translated_by: "gpt5",
    path: "content/sutras/ksitigarbha-vow-sutra-02.md",
    work_id: "ksitigarbha-vow-sutra",
    work_title: "地藏菩萨本愿经",
    work_short_title: "地藏经",
    work_summary: "《地藏菩萨本愿经》两卷围绕地藏菩萨大愿、因果业报、临终救拔与见闻利益展开，兼明孝亲、修福、称名与救苦之道。",
    volume_index: 2,
  },
  {
    title: "佛说无量寿经 卷上",
    short_title: "无量寿经卷上",
    slug: "larger-sukhavati-vyuha-01",
    volume_label: "卷上",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-22",
    summary: "净土系根本长经卷上，铺陈法藏比丘发愿、修行与极乐国土庄严的成就因缘。",
    tags: ["净土", "无量寿", "愿海"],
    translated_by: "gpt5",
    path: "content/sutras/larger-sukhavati-vyuha-01.md",
    work_id: "larger-sukhavati-vyuha",
    work_title: "佛说无量寿经",
    work_short_title: "无量寿经",
    work_summary: "《佛说无量寿经》两卷围绕法藏比丘成就净土、三辈往生、五恶五善对治、胎化差别与闻名得益展开，是净土系根本长经。",
    volume_index: 1,
  },
  {
    title: "佛说无量寿经 卷下",
    short_title: "无量寿经卷下",
    slug: "larger-sukhavati-vyuha-02",
    volume_label: "卷下",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-23",
    summary: "净土系根本长经卷下，广说三辈往生、五恶五善、胎化差别与闻经得益。",
    tags: ["净土", "无量寿", "愿海"],
    translated_by: "gpt5",
    path: "content/sutras/larger-sukhavati-vyuha-02.md",
    work_id: "larger-sukhavati-vyuha",
    work_title: "佛说无量寿经",
    work_short_title: "无量寿经",
    work_summary: "《佛说无量寿经》两卷围绕法藏比丘成就净土、三辈往生、五恶五善对治、胎化差别与闻名得益展开，是净土系根本长经。",
    volume_index: 2,
  },
  {
    title: "妙法莲华经 观世音菩萨普门品",
    short_title: "普门品",
    slug: "lotus-sutra-universal-gate",
    volume_label: "第二十五品",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-22",
    summary: "宣说观世音菩萨随类救苦、普门示现与称名感应的法华要义。",
    tags: ["法华", "观音", "救苦"],
    translated_by: "gpt5",
    path: "content/sutras/lotus-sutra-universal-gate.md",
  },
  {
    title: "药师琉璃光如来本愿功德经",
    short_title: "药师经",
    slug: "medicine-buddha-sutra",
    volume_label: "全一卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-22",
    summary: "以药师如来十二大愿为主，开示现世救苦、消灾除难与愿行并修之道。",
    tags: ["药师", "愿力", "消灾"],
    translated_by: "gpt5",
    path: "content/sutras/medicine-buddha-sutra.md",
  },
  ...PLATFORM_SUTRA_DOCUMENTS,
  ...SURANGAMA_DOCUMENTS,
  ...LANKAVATARA_DOCUMENTS,
  ...SANDHINIRMOCANA_DOCUMENTS,
  ...VIMALAKIRTI_DOCUMENTS,
  ...LOTUS_SUTRA_DOCUMENTS,
  ...DHARMAPADA_DOCUMENTS,
  ...SAMYUKTA_AGAMA_DOCUMENTS,
  {
    title: "大方广佛华严经 普贤行愿品",
    short_title: "普贤行愿品",
    slug: "samantabhadra-vows",
    volume_label: "全一卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-25",
    summary: "华严经的压轴之作，系统宣说普贤菩萨十大愿王，是净土与华严修持的核心。",
    tags: ["华严", "愿力", "普贤"],
    translated_by: "gemini3",
    path: "content/sutras/samantabhadra-vows.md",
  },
  {
    title: "佛说观无量寿佛经",
    short_title: "观无量寿经",
    slug: "amitayurdhyana-sutra",
    volume_label: "全一卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-24",
    summary: "净土三经之一，详述十六观修持方法与九品往生阶位，是净土宗修行的重要依据。",
    tags: ["净土", "观想", "十六观"],
    translated_by: "gemini3",
    path: "content/sutras/amitayurdhyana-sutra.md",
  },
  {
    title: "大乘圆觉修多罗了义经",
    short_title: "圆觉经",
    slug: "perfect-enlightenment-sutra",
    volume_label: "全一卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-24",
    summary: "阐述如来圆觉境界及修行奢摩他、三摩钵提、禅那三种法门的圆顿经典。",
    tags: ["圆觉", "圆顿", "实修"],
    translated_by: "gemini3",
    path: "content/sutras/perfect-enlightenment-sutra.md",
  },
  {
    title: "胜鬘师子吼一乘大便利方广经",
    short_title: "胜鬘经",
    slug: "srimala-sutra",
    volume_label: "全一卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-24",
    summary: "以胜鬘夫人为主角，阐发“如来藏”与“一乘”大义的重要经典。",
    tags: ["胜鬘", "如来藏", "一乘"],
    translated_by: "gemini3",
    path: "content/sutras/srimala-sutra.md",
  },
  {
    title: "佛说稻秆经",
    short_title: "稻秆经",
    slug: "rice-seedling-sutra",
    volume_label: "全一卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-25",
    summary: "通过稻秆生长的比喻，系统阐述十二因缘的深刻义理，揭示万法缘起性空的本质。",
    tags: ["缘起", "因缘", "比喻"],
    translated_by: "gemini3",
    path: "content/sutras/rice-seedling-sutra.md",
  },
  {
    title: "佛说十善业道经",
    short_title: "十善业道经",
    slug: "ten-good-karmic-actions-sutra",
    volume_label: "全一卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-26",
    summary: "佛教道德观的基石，详细讲解十善业及其殊胜果报，是人天乘修行的根本。",
    tags: ["业力", "道德", "十善业"],
    translated_by: "gemini3",
    path: "content/sutras/ten-good-karmic-actions-sutra.md",
  },
  ...RENWANG_DOCUMENTS,
  ...FANWANG_DOCUMENTS,
  ...GOLDEN_LIGHT_DOCUMENTS,
  {
    title: "佛说四十二章经",
    short_title: "四十二章经",
    slug: "sutra-in-forty-two-sections",
    volume_label: "全一卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-22",
    summary: "以短章格言体开示出家、修心、离欲与解脱的佛法要点。",
    tags: ["入门", "格言", "短章"],
    translated_by: "gpt5",
    path: "content/sutras/sutra-in-forty-two-sections.md",
  },
  {
    title: "佛说八大人觉经",
    short_title: "八大人觉经",
    slug: "sutra-of-eight-realizations",
    volume_label: "全一卷",
    translation_status: "translated",
    review_status: "ai_reviewed",
    updated_at: "2026-03-22",
    summary: "以八条觉悟纲领总摄出离、少欲、精进、利他的修行次第。",
    tags: ["修行", "提纲", "短经"],
    translated_by: "gpt5",
    path: "content/sutras/sutra-of-eight-realizations.md",
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

let documentsCache = null;

export async function loadDocuments() {
  if (documentsCache) {
    return documentsCache;
  }

  const loaded = await Promise.all(
    manifest.map(async (path) => mergeDocumentMeta(await loadDocument(path))),
  );

  documentsCache = loaded.sort((a, b) => a.title.localeCompare(b.title, "zh-Hans-CN"));
  return documentsCache;
}

export async function loadDocument(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`无法读取 ${path}`);
  }
  const raw = await response.text();
  return parseDocument(raw, path);
}

export function getDocumentBySlug(slug) {
  if (!documentsCache) {
    throw new Error("文稿尚未加载");
  }
  return documentsCache.find((doc) => doc.slug === slug) || documentsCache[0];
}

export function getPrimarySample(docs) {
  return docs.find((doc) => doc.slug === "heart-sutra") || docs[0];
}

export function getFeaturedDocuments(docs, limit = HOME_FEATURED_LIMIT) {
  return getCatalogDocuments(docs)
    .sort((a, b) => scoreDocument(b) - scoreDocument(a) || a.title.localeCompare(b.title, "zh-Hans-CN"))
    .slice(0, limit);
}

export function getCatalogDocuments(docs) {
  const groups = new Map();

  docs.forEach((doc) => {
    const key = getWorkKey(doc);
    const siblings = groups.get(key) || [];
    siblings.push(doc);
    groups.set(key, siblings);
  });

  return Array.from(groups.values()).map((group) => buildCatalogDocument(group));
}

export function getVolumeNavigation(doc, docs = documentIndex) {
  const current = typeof doc === "string" ? getDocumentIndexBySlug(doc) : doc;
  const siblings = docs
    .filter((candidate) => getWorkKey(candidate) === getWorkKey(current) && Number.isFinite(candidate.volume_index))
    .sort(compareVolumeDocs);

  if (siblings.length <= 1) {
    return [];
  }

  return siblings.map((item) => ({
    slug: item.slug,
    label: getVolumeNavigationLabel(item),
    title: item.title,
    isCurrent: item.slug === current.slug,
  }));
}

export function getTranslationState(status) {
  return translationStates[status] || translationStates.untranslated;
}

export function getReviewState(status) {
  return reviewStates[status] || reviewStates.unreviewed;
}

export function getCatalogVolumeBadgeLabel(doc) {
  return normalizeCatalogVolumeLabel(doc?.volume_label);
}

export function formatUpdatedAtBadgeLabel(value) {
  return value ? `更新 ${value}` : "未标注日期";
}

export function getMarkdownSourceUrl(path) {
  return new URL(path, GITHUB_REPO_BASE).toString();
}

export function getReaderUrl(slug, base = "") {
  const encodedSlug = encodeURIComponent(slug);
  const queryOnly = `reader.html?doc=${encodedSlug}`;
  if (base) {
    return new URL(queryOnly, base).toString();
  }
  return `./${queryOnly}`;
}

export function getDocumentIndexBySlug(slug) {
  return documentIndex.find((doc) => doc.slug === slug) || documentIndex[0];
}

function mergeDocumentMeta(doc) {
  const matched = documentIndex.find((item) => item.path === doc.path || item.slug === doc.slug);
  if (!matched) {
    return doc;
  }

  return {
    ...matched,
    ...doc,
    slug: matched.slug,
    path: matched.path,
  };
}

function getWorkKey(doc) {
  return doc.work_id || doc.slug;
}

function buildCatalogDocument(group) {
  const sortedGroup = [...group].sort(compareVolumeDocs);
  const representative = sortedGroup[0];

  if (sortedGroup.length === 1) {
    return representative;
  }

  const isPlatformSutra = representative.work_id === "platform-sutra";

  return {
    ...representative,
    title: representative.work_title || representative.title,
    short_title: representative.work_short_title || representative.short_title || representative.title,
    volume_label: isPlatformSutra ? `全一卷（${sortedGroup.length}品）` : `全${sortedGroup.length}卷`,
    summary: representative.work_summary || representative.summary,
    translation_status: getAggregateTranslationStatus(sortedGroup),
    review_status: getAggregateReviewStatus(sortedGroup),
    updated_at: sortedGroup.reduce((latest, item) => (item.updated_at > latest ? item.updated_at : latest), ""),
  };
}

function getAggregateTranslationStatus(group) {
  if (group.every((item) => item.translation_status === "translated")) {
    return "translated";
  }
  if (group.some((item) => item.translation_status === "translated" || item.translation_status === "translating")) {
    return "translating";
  }
  return "untranslated";
}

function getAggregateReviewStatus(group) {
  if (group.every((item) => item.review_status === "human_reviewed")) {
    return "human_reviewed";
  }
  if (group.every((item) => item.review_status === "human_reviewed" || item.review_status === "ai_reviewed")) {
    return "ai_reviewed";
  }
  if (group.some((item) => item.review_status === "reviewing")) {
    return "reviewing";
  }
  return "unreviewed";
}

function compareVolumeDocs(a, b) {
  const aVolume = Number.isFinite(a.volume_index) ? a.volume_index : Number.MAX_SAFE_INTEGER;
  const bVolume = Number.isFinite(b.volume_index) ? b.volume_index : Number.MAX_SAFE_INTEGER;
  if (aVolume !== bVolume) {
    return aVolume - bVolume;
  }
  return a.title.localeCompare(b.title, "zh-Hans-CN");
}

function getVolumeNavigationLabel(doc) {
  if (Number.isFinite(doc.volume_index)) {
    const unit = doc.volume_unit || "卷";
    if (unit === "品") {
      return `第${toChineseNumeral(doc.volume_index)}品`;
    }
    return `${unit}${toChineseNumeral(doc.volume_index)}`;
  }
  return doc.volume_label || doc.short_title || doc.title;
}

function getCompactVolumeLabel(volume, unit = "卷") {
  if (unit === "品") {
    return `第${toChineseNumeral(volume)}品`;
  }
  return `${unit}${toChineseNumeral(volume)}`;
}

function toChineseNumeral(value) {
  const numerals = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"];
  if (value <= 10) {
    return value === 10 ? "十" : numerals[value];
  }
  if (value < 20) {
    return `十${numerals[value % 10]}`;
  }
  const tens = Math.floor(value / 10);
  const ones = value % 10;
  return `${numerals[tens]}十${ones ? numerals[ones] : ""}`;
}

function scoreDocument(doc) {
  const translationScore =
    doc.translation_status === "translated" ? 40 : doc.translation_status === "translating" ? 20 : 0;
  const reviewScore =
    doc.review_status === "human_reviewed"
      ? 90
      : doc.review_status === "ai_reviewed"
        ? 60
        : doc.review_status === "reviewing"
          ? 30
          : 0;
  return translationScore + reviewScore;
}

function normalizeCatalogVolumeLabel(value) {
  if (!value) {
    return "单篇";
  }
  if (/^共\d+卷$/.test(value)) {
    return value.replace(/^共/, "全");
  }
  return value;
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
          if (divider === -1) {
            return null;
          }
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
      if (inCodeBlock) {
        flushCode();
      }
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
        } else if (headingText === "现代语译") {
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
      if (listType && listType !== "ul") {
        flushList();
      }
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
      if (listType && listType !== "ol") {
        flushList();
      }
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
