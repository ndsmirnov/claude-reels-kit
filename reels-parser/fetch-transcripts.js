// Точечный транскрипт для конкретного списка рилсов (по прямым URL) —
// дешевле, чем гонять транскрипт на весь аккаунт.
//
// Запуск: node --env-file=.env fetch-transcripts.js output/top20-urls.json
// Результат: output/<имя-файла-без-"-urls">-transcripts.json

import fs from "node:fs";
import path from "node:path";
import { runAndFetch, getRunCostUsd } from "./lib/apify.js";

const APIFY_TOKEN = process.env.APIFY_TOKEN;
const urlsFile = process.argv[2];

if (!APIFY_TOKEN || !urlsFile) {
  console.error("Запуск: APIFY_TOKEN=xxx node fetch-transcripts.js output/top20-urls.json");
  process.exit(1);
}

const urls = JSON.parse(fs.readFileSync(urlsFile, "utf-8"));

async function main() {
  console.log(`Запускаю транскрипт для ${urls.length} рилсов...`);
  const { items, run } = await runAndFetch(APIFY_TOKEN, {
    username: urls,
    includeTranscript: true,
  });

  const baseName = path.basename(urlsFile, ".json").replace(/-urls$/, "");
  const outPath = path.join(process.cwd(), "output", `${baseName}-transcripts.json`);
  fs.writeFileSync(outPath, JSON.stringify(items, null, 2), "utf-8");
  console.log(`Сохранено: ${outPath} (${items.length} шт.)`);

  const cost = await getRunCostUsd(APIFY_TOKEN, run.id);
  console.log(`Стоимость: $${cost}`);
}

main().catch((err) => {
  console.error("Ошибка:", err.message);
  process.exit(1);
});
