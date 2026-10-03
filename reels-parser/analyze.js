// Локальный анализ уже собранных данных — НЕ обращается к Apify, работает
// только с уже скачанными файлами в output/.
//
// Запуск: node analyze.js output/<аккаунт>.json [output/<файл>-transcripts.json]

import fs from "node:fs";

function load(path) {
  if (!fs.existsSync(path)) return [];
  return JSON.parse(fs.readFileSync(path, "utf-8"));
}

const full = load(process.argv[2] ?? "output/account.json");
const withTranscript = load(process.argv[3] ?? "output/top20-transcripts.json");

function plays(it) {
  return it.videoPlayCount || it.videoViewCount || 0;
}

// --- 1. Общая статистика по всем 100 ---
const sorted = [...full].sort((a, b) => plays(b) - plays(a));
const viewsArr = sorted.map(plays).filter((v) => v > 0);
const median = viewsArr[Math.floor(viewsArr.length / 2)];
const avg = Math.round(viewsArr.reduce((s, v) => s + v, 0) / viewsArr.length);

console.log("=== Общая статистика (100 рилсов) ===");
console.log(`Медиана просмотров: ${median.toLocaleString()}`);
console.log(`Среднее: ${avg.toLocaleString()}`);
console.log(`Топ: ${plays(sorted[0]).toLocaleString()}, Низ: ${plays(sorted[sorted.length - 1]).toLocaleString()}`);
console.log(`Разброс топ/медиана: x${(plays(sorted[0]) / median).toFixed(1)}`);

// --- 2. caption длина vs просмотры (проверяем, работает ли длина caption как сигнал) ---
function corr(xs, ys) {
  const n = xs.length;
  const mx = xs.reduce((s, x) => s + x, 0) / n;
  const my = ys.reduce((s, y) => s + y, 0) / n;
  let num = 0, dx2 = 0, dy2 = 0;
  for (let i = 0; i < n; i++) {
    const dx = xs[i] - mx, dy = ys[i] - my;
    num += dx * dy; dx2 += dx * dx; dy2 += dy * dy;
  }
  return num / Math.sqrt(dx2 * dy2);
}

const capLenVsViews = corr(full.map((it) => (it.caption || "").length), full.map(plays));
console.log(`\nКорреляция (длина caption) vs (просмотры): ${capLenVsViews.toFixed(2)} (слабая связь, если близко к 0)`);

// --- 3. Транскрипты топ-20: первая фраза + длина ---
console.log("\n=== Топ-20 с транскриптами: первая фраза ===");
const withPlays = withTranscript
  .map((it) => ({ ...it, plays: plays(it) }))
  .sort((a, b) => b.plays - a.plays);

for (const it of withPlays) {
  const firstSentence = (it.transcript || "").split(/[.!?]/)[0].trim();
  console.log(`${it.plays.toLocaleString()} | "${firstSentence.slice(0, 90)}"`);
}

// --- 4. Длина транскрипта vs просмотры (в топ-20) ---
const tLenVsViews = corr(withPlays.map((it) => (it.transcript || "").length), withPlays.map((it) => it.plays));
console.log(`\nКорреляция (длина транскрипта) vs (просмотры, топ-20): ${tLenVsViews.toFixed(2)}`);

// --- 5. Простые лексические сигналы: вопрос в первой фразе? мат? конфликт-слова? ---
const CONFLICT_WORDS = ["сука", "тварь", "блять", "нахуй", "ебан", "хуй", "пизд"];
const QUESTION_MARK = "?";

console.log("\n=== Лексические сигналы (топ-20) ===");
for (const it of withPlays) {
  const t = (it.transcript || "").toLowerCase();
  const hasConflict = CONFLICT_WORDS.some((w) => t.includes(w));
  const hasQuestion = t.includes(QUESTION_MARK);
  console.log(`${it.plays.toLocaleString()} | мат:${hasConflict ? "да" : "нет"} | вопрос:${hasQuestion ? "да" : "нет"}`);
}

fs.writeFileSync(
  "output/analysis-summary.json",
  JSON.stringify(
    {
      totalReels: full.length,
      medianViews: median,
      avgViews: avg,
      captionLengthCorrelation: capLenVsViews,
      top20TranscriptLengthCorrelation: tLenVsViews,
    },
    null,
    2
  )
);
console.log("\nСводка сохранена в output/analysis-summary.json");
