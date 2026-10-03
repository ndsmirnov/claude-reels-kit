// Применяет scoreSegment (lib/score.js) к файлу с транскриптами и выводит
// ранжированный отчёт — локально, без обращения к Apify.
//
// Запуск: node score-reels.js output/top20-transcripts.json

import fs from "node:fs";
import { scoreSegment, priorityScore } from "./lib/score.js";

const file = process.argv[2];
if (!file) {
  console.error("Запуск: node score-reels.js output/<файл>-transcripts.json");
  process.exit(1);
}

const items = JSON.parse(fs.readFileSync(file, "utf-8"));

const scored = items.map((it) => {
  const score = scoreSegment(it.transcript);
  return {
    url: it.url,
    plays: it.videoPlayCount || it.videoViewCount || 0,
    score,
    priority: priorityScore(score),
    firstSentence: (it.transcript || "").split(/[.!?]/)[0].trim().slice(0, 90),
  };
});

scored.sort((a, b) => b.priority - a.priority);

console.log(`Ранжировано ${scored.length} рилсов по priorityScore (hasQuestion+substantiveLength — вес 2, directAddress — вес 1):\n`);
for (const s of scored) {
  console.log(
    `priority=${s.priority} | plays=${s.plays.toLocaleString()} | Q:${s.score.hasQuestion ? "✓" : "·"} L:${s.score.substantiveLength ? "✓" : "·"} A:${s.score.directAddress ? "✓" : "·"} | "${s.firstSentence}"`
  );
}
