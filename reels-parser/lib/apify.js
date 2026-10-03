// Общие функции для работы с Apify API — запуск актора, опрос статуса, чтение датасета.
// Используется fetch-account.js и fetch-transcripts.js.

const API_BASE = "https://api.apify.com/v2";
const ACTOR_ID = "apify~instagram-reel-scraper";

export const FIELDS = [
  "id", "shortCode", "url", "caption", "timestamp",
  "likesCount", "commentsCount", "videoViewCount", "videoPlayCount",
  "videoDuration", "hashtags", "transcript",
].join(",");

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function startRun(token, input) {
  const url = `${API_BASE}/acts/${ACTOR_ID}/runs?token=${token}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`Не удалось запустить run: ${res.status} ${await res.text()}`);
  const { data } = await res.json();
  return data;
}

export async function pollRun(token, runId, { intervalMs = 5000 } = {}) {
  const url = `${API_BASE}/actor-runs/${runId}?token=${token}`;
  while (true) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Не удалось проверить статус: ${res.status}`);
    const { data } = await res.json();
    process.stdout.write(`\rСтатус: ${data.status}   `);
    if (["SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"].includes(data.status)) {
      console.log("");
      return data;
    }
    await sleep(intervalMs);
  }
}

// Поля ограничены явно — полный ответ (с комментариями/картинками) может быть
// достаточно большим, чтобы fetch падал с "terminated" на 50+ рилсах.
export async function getDatasetItems(token, datasetId, fields = FIELDS) {
  const url = `${API_BASE}/datasets/${datasetId}/items?token=${token}&format=json&clean=true&fields=${fields}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Не удалось получить датасет: ${res.status}`);
  const data = await res.json();
  if (data && data.error) {
    throw new Error(`Apify: ${data.error.type} — ${data.error.message}`);
  }
  return data;
}

export async function getRunCostUsd(token, runId) {
  const url = `${API_BASE}/actor-runs/${runId}?token=${token}`;
  const res = await fetch(url);
  const { data } = await res.json();
  return data.usageTotalUsd;
}

export async function runAndFetch(token, input, { fields = FIELDS } = {}) {
  const run = await startRun(token, input);
  console.log(`Run id: ${run.id}`);
  const finished = await pollRun(token, run.id);
  if (finished.status !== "SUCCEEDED") {
    throw new Error(`Run завершился со статусом ${finished.status} (id ${finished.id}, датасет ${finished.defaultDatasetId} — можно дочитать вручную позже)`);
  }
  const items = await getDatasetItems(token, finished.defaultDatasetId, fields);
  return { items, run: finished };
}
