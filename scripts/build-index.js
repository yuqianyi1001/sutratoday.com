#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const SUTRAS_RAW_DIR = path.join(__dirname, "..", "content", "sutras-raw");
const OUTPUT_PATH = path.join(__dirname, "..", "sutras-raw-index.json");

function parseFrontMatter(raw) {
  const match = raw.match(/^---\n([\s\S]*?)\n---\n?/);
  if (!match) return {};
  const lines = match[1].split("\n");
  return Object.fromEntries(
    lines
      .map((line) => {
        const divider = line.indexOf(":");
        if (divider === -1) return null;
        const key = line.slice(0, divider).trim();
        let value = line.slice(divider + 1).trim();
        if (value === "true") value = true;
        else if (value === "false") value = false;
        else if (/^\d+$/.test(value)) value = Number(value);
        return [key, value];
      })
      .filter(Boolean),
  );
}

function buildIndex() {
  const files = fs.readdirSync(SUTRAS_RAW_DIR).filter((f) => f.endsWith(".md")).sort();
  console.log(`Found ${files.length} markdown files in sutras-raw`);

  const volumesByWork = new Map();

  for (const file of files) {
    const raw = fs.readFileSync(path.join(SUTRAS_RAW_DIR, file), "utf-8");
    const meta = parseFrontMatter(raw);
    const slug = meta.slug || file.replace(/\.md$/, "");
    const cbetaId = meta.cbeta_id || slug.replace(/-\d+$/, "");

    if (!volumesByWork.has(cbetaId)) {
      volumesByWork.set(cbetaId, {
        cbeta_id: cbetaId,
        title: "",
        short_title: "",
        category: meta.category || "",
        translator: meta.translator || "",
        juan_total: 0,
        translation_status: "untranslated",
        review_status: "unreviewed",
        updated_at: "",
        first_slug: slug,
        _volumes: [],
      });
    }

    const work = volumesByWork.get(cbetaId);
    work._volumes.push({
      slug,
      juan_index: meta.juan_index || 1,
      title: meta.title || slug,
      short_title: meta.short_title || "",
      volume_label: meta.volume_label || "",
      translation_status: meta.translation_status || "untranslated",
      review_status: meta.review_status || "unreviewed",
      updated_at: meta.updated_at || "",
    });
  }

  const works = [];
  let totalVolumes = 0;

  for (const [, work] of volumesByWork) {
    work._volumes.sort((a, b) => a.juan_index - b.juan_index);

    const first = work._volumes[0];
    const rawTitle = first.title || "";
    work.title = rawTitle.replace(/\s*卷第?[一二三四五六七八九十百千零〇两兩0-9]+\s*$/, "") || rawTitle;
    work.short_title = first.short_title
      ? first.short_title.replace(/卷[一二三四五六七八九十百千零〇两兩0-9]+$/, "")
      : work.title;
    work.juan_total = work._volumes.length;
    work.first_slug = first.slug;
    work.translation_status = aggregateTranslation(work._volumes);
    work.review_status = aggregateReview(work._volumes);
    work.updated_at = work._volumes.reduce(
      (latest, v) => (v.updated_at > latest ? v.updated_at : latest),
      "",
    );

    // Build compact volume list: just slug and title for volume navigation
    work.volumes = work._volumes.map((v) => [v.slug, v.title]);

    totalVolumes += work._volumes.length;
    delete work._volumes;
    works.push(work);
  }

  works.sort((a, b) => a.cbeta_id.localeCompare(b.cbeta_id));

  const index = {
    works,
    stats: { workCount: works.length, volumeCount: totalVolumes },
  };

  const json = JSON.stringify(index);
  fs.writeFileSync(OUTPUT_PATH, json, "utf-8");
  console.log(`Index written to ${OUTPUT_PATH} (${(json.length / 1024).toFixed(0)} KB)`);
  console.log(`Works: ${works.length}, Volumes: ${totalVolumes}`);
}

function aggregateTranslation(volumes) {
  if (volumes.every((v) => v.translation_status === "translated")) return "translated";
  if (volumes.some((v) => v.translation_status === "translated" || v.translation_status === "translating"))
    return "translating";
  return "untranslated";
}

function aggregateReview(volumes) {
  if (volumes.every((v) => v.review_status === "human_reviewed")) return "human_reviewed";
  if (volumes.every((v) => v.review_status === "human_reviewed" || v.review_status === "ai_reviewed"))
    return "ai_reviewed";
  if (volumes.some((v) => v.review_status === "reviewing")) return "reviewing";
  return "unreviewed";
}

buildIndex();
