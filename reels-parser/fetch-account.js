// Тянет рилсы одного Instagram-аккаунта через Apify (apify/instagram-reel-scraper)
// и сохраняет caption + метрики (без транскрипта — дорого на весь аккаунт) в
// output/<username>.json
//
// Запуск: node --env-file=.env fetch-account.js <username> [лимит]

import fs from "node:fs";
import path from "node:path";
import { runAndFetch } from "./lib/apify.js";

const APIFY_TOKEN = process.env.APIFY_TOKEN;
const username = process.argv[2];
const resultsLimit = Number(process.argv[3] ?? 100);

if (!APIFY_TOKEN || !username) {
  console.error("Запуск: APIFY_TOKEN=xxx node fetch-account.js <username> 100");
  process.exit(1);
}

async function main() {
  console.log(`Запускаю Apify actor для @${username}, лимит ${resultsLimit}...`);
  const { items } = await runAndFetch(APIFY_TOKEN, {
    username: [username],
    resultsLimit,
    includeTranscript: false, // дорого на весь аккаунт — транскрипт точечно через fetch-transcripts.js
  });
  console.log(`Получено ${items.length} объектов.`);

  const outDir = path.join(process.cwd(), "output");
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, `${username}.json`);
  fs.writeFileSync(outPath, JSON.stringify(items, null, 2), "utf-8");
  console.log(`Сохранено: ${outPath}`);
}

main().catch((err) => {
  console.error("Ошибка:", err.message);
  process.exit(1);
});
