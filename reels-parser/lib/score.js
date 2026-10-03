// Скоринг сегмента транскрипта по критериям, подтверждённым на 40 реальных
// примерах (топ-20 vs низ-20 одного русскоязычного аккаунта в нише «отношения», 2026).
// Критерии нишевые: для своей ниши перепроверь их на своих данных.

const DIRECT_ADDRESS = /^\s*(мужчины|пацаны|друзья|девушк|бабы|парни|девчонк|дамы)/i;
const RAW_LANGUAGE_WORDS = ["сука", "тварь", "блять", "нахуй", "ебан", "хуй", "пизд"];
const SUBSTANTIVE_LENGTH_THRESHOLD = 500; // символов — топ~1136 vs низ~290, порог между ними

export function scoreSegment(transcript) {
  const t = (transcript || "").trim();
  const lower = t.toLowerCase();
  const firstSentence = t.split(/[.!?]/)[0] || "";

  return {
    hasQuestion: t.includes("?"),
    directAddress: DIRECT_ADDRESS.test(firstSentence.trim()),
    substantiveLength: t.length >= SUBSTANTIVE_LENGTH_THRESHOLD,
    rawLanguage: RAW_LANGUAGE_WORDS.some((w) => lower.includes(w)),
    length: t.length,
  };
}

// Условный приоритет-скор: hasQuestion и substantiveLength — сильные сигналы (вес 2),
// directAddress — умеренный (вес 1), rawLanguage — НЕ учитывается (стиль автора, не критерий).
export function priorityScore(score) {
  return (score.hasQuestion ? 2 : 0) + (score.substantiveLength ? 2 : 0) + (score.directAddress ? 1 : 0);
}
