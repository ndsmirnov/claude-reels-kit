#!/bin/bash
# Рендер прозрачного слоя графики: render.sh props.json out.mov
# Картинки из props (src — абсолютный путь) копируются в public/, в props подменяются на имя файла.
set -e; P="$(cd "$(dirname "$0")" && pwd)"; IN="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; OUT="$2"
TMP="$P/public/_props.json"
# шрифты Montserrat лежат один раз в ../fonts — копируем в public/fonts, если их там нет
mkdir -p "$P/public/fonts"; for f in "$P"/../fonts/Montserrat-*.ttf; do [ -f "$P/public/fonts/$(basename "$f")" ] || cp "$f" "$P/public/fonts/"; done
[ -d "$P/node_modules" ] || (cd "$P" && npm install --no-audit --no-fund)
# Python с Pillow: $PYTHON, иначе venv из scripts/setup.sh ($REELS_WORKDIR или ~/reels-work), иначе системный python3
VENV_PY="${REELS_WORKDIR:-$HOME/reels-work}/venv/bin/python"; PY_BIN="${PYTHON:-python3}"; [ -z "$PYTHON" ] && [ -x "$VENV_PY" ] && PY_BIN="$VENV_PY"
"$PY_BIN" - "$IN" "$TMP" "$P/public" <<'PY'
import json, os, shutil, sys, hashlib, subprocess
src, dst, pub = sys.argv[1:4]; d = json.load(open(src))
sys.path.insert(0, os.path.join(pub, "..", "..", "scripts")); from textnorm import norm   # стандарт текста: без «ё», деньги «12,000 ₽»
for it in d["items"]:
    for k in ("text", "score"):
        if it.get(k): it[k] = norm(it[k])
from layout import place_thesis   # тезисы мимо лиц (Apple Vision + движение кадра), до подмены путей
for w in place_thesis(d["items"]): print("⚠️", w, file=sys.stderr)
for it in d["items"]:
    if it.get("type") in ("insert", "half") and os.path.splitext(it["src"])[1].lower() in (".mp4", ".mov"):
        # видео-вставка: вырезаем нужный кусок исходника в 1080×1920 h264 (поворот iPhone учитывает ffmpeg)
        n = hashlib.md5(f'{it["src"]}{it.get("from", 0)}{it["end"]-it["start"]}'.encode()).hexdigest()[:10] + ".mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(it.get("from", 0)), "-t", f'{it["end"] - it["start"] + 0.2:.2f}', "-i", it["src"],
                        "-vf", ("scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960" if it["type"] == "half" else "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920") + ",fps=30", "-an", "-c:v", "libx264", "-crf", "18",
                        "-pix_fmt", "yuv420p", os.path.join(pub, n)], check=True)
        it["src"] = n; continue
    if "src" in it and os.path.isabs(it["src"]):
        n = hashlib.md5(it["src"].encode()).hexdigest()[:10] + os.path.splitext(it["src"])[1]
        shutil.copy(it["src"], os.path.join(pub, n)); it["src"] = n
json.dump(d, open(dst, "w"), ensure_ascii=False)
PY
# Если установлен Google Chrome — рендерим им (у некоторых не скачивается chrome-headless-shell); иначе Remotion скачает свой браузер.
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; BROWSER=()
[ -x "$CHROME" ] && BROWSER=(--browser-executable="$CHROME" --chrome-mode=chrome-for-testing)
cd "$P" && nice -n 10 npx remotion render src/index.ts Overlay "$OUT" --props="$TMP" \
  --codec=prores --prores-profile=4444 --image-format=png --pixel-format=yuva444p10le --concurrency=1 --log=error --timeout=120000 \
  "${BROWSER[@]}"
