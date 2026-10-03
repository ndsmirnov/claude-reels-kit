// Discovery-шаг: ищет топовые рилсы по хештегам через Apify Instagram Hashtag Scraper.
// Отдельный актор от instagram-reel-scraper — свой клиент, своя схема полей.
//
// Запуск: node --env-file=.env fetch-hashtags.js ai,claudecode,chatgpt [лимит на хештег]

import fs from "node:fs";
import path from "node:path";

const APIFY_TOKEN = process.env.APIFY_TOKEN;
const API_BASE = "https://api.apify.com/v2";
const ACTOR_ID = "apify~instagram-hashtag-scraper";

const hashtagsArg = process.argv[2];
const resultsLimit = Number(process.argv[3] ?? 30);

if (!APIFY_TOKEN || !hashtagsArg) {
  console.error("Запуск: APIFY_TOKEN=xxx node fetch-hashtags.js ai,claudecode,chatgpt 30");
  process.exit(1);
}

const hashtags = hashtagsArg.split(",").map((h) => h.trim());

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function startRun() {
  const url = `${API_BASE}/acts/${ACTOR_ID}/runs?token=${APIFY_TOKEN}`;
  const input = { hashtags, resultsLimit, resultsType: "reels" };
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`Не удалось запустить run: ${res.status} ${await res.text()}`);
  const { data } = await res.json();
  return data;
}

async function pollRun(runId) {
  const url = `${API_BASE}/actor-runs/${runId}?token=${APIFY_TOKEN}`;
  while (true) {
    const res = await fetch(url);
    const { data } = await res.json();
    process.stdout.write(`\rСтатус: ${data.status}   `);
    if (["SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"].includes(data.status)) {
      console.log("");
      return data;
    }
    await sleep(5000);
  }
}

async function main() {
  console.log(`Запускаю Instagram Hashtag Scraper для [${hashtags.join(", ")}], лимит ${resultsLimit}/хештег...`);
  const run = await startRun();
  console.log(`Run id: ${run.id}`);
  const finished = await pollRun(run.id);
  if (finished.status !== "SUCCEEDED") throw new Error(`Run завершился со статусом ${finished.status}`);

  const res = await fetch(`${API_BASE}/datasets/${finished.defaultDatasetId}/items?token=${APIFY_TOKEN}&format=json&clean=true`);
  const items = await res.json();
  console.log(`Получено ${items.length} объектов.`);

  const outDir = path.join(process.cwd(), "output");
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, "hashtags-ai.json");
  fs.writeFileSync(outPath, JSON.stringify(items, null, 2), "utf-8");
  console.log(`Сохранено: ${outPath}`);

  const costRes = await fetch(`${API_BASE}/actor-runs/${finished.id}?token=${APIFY_TOKEN}`);
  const { data: costData } = await costRes.json();
  console.log(`Стоимость: $${costData.usageTotalUsd}`);
}

main().catch((err) => {
  console.error("Ошибка:", err.message);
  process.exit(1);
});
