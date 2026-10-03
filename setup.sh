#!/bin/bash
# Установка claude-reels-kit на Mac:  bash setup.sh
#   1) копирует скиллы в ~/.claude/skills/ (reels-montage, reel-remix)
#   2) копирует reels-parser в ~/reels-parser и создаёт .env из .env.example (токен Apify вставляешь сам)
#   3) собирает scripts/faces из faces.swift, кладёт шрифты для Remotion, ставит npm-пакеты Remotion
#   4) создаёт Python-окружение в $REELS_WORKDIR (по умолчанию ~/reels-work)
# Переменные: SKIP_PY=1 — не ставить Python-пакеты; SKIP_NPM=1 — не ставить Remotion; PARSER_DIR — куда положить reels-parser.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SK="$HOME/.claude/skills"
PARSER_DIR="${PARSER_DIR:-$HOME/reels-parser}"
export REELS_WORKDIR="${REELS_WORKDIR:-$HOME/reels-work}"
ok() { echo "  ✓ $*"; }; warn() { echo "  ! $*"; }

echo "1. Проверяю программы"
command -v python3 >/dev/null && ok "python3 $(python3 --version 2>&1 | cut -d' ' -f2)" || warn "нет python3 — установи: xcode-select --install или brew install python"
if command -v node >/dev/null; then
  NV=$(node -p 'process.versions.node.split(".")[0]'); [ "$NV" -ge 20 ] && ok "node $(node --version)" || warn "node $(node --version) — нужен 20+ (brew install node)"
else warn "нет node — установи: brew install node"; fi
command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null && ok "ffmpeg + ffprobe" || warn "нет ffmpeg/ffprobe — установи: brew install ffmpeg"
command -v swiftc >/dev/null && ok "swiftc" || warn "нет swiftc — установи: xcode-select --install (нужно для раскладки текста мимо лиц)"

echo "2. Копирую скиллы в $SK"
mkdir -p "$SK"
for s in reels-montage reel-remix; do
  rsync -a --exclude node_modules --exclude '.DS_Store' "$HERE/skills/$s/" "$SK/$s/"; ok "$s"
done
M="$SK/reels-montage"

echo "3. reels-parser → $PARSER_DIR"
mkdir -p "$PARSER_DIR/output"
rsync -a --exclude '.env' --exclude 'hooks-bank.md' --exclude 'output' "$HERE/reels-parser/" "$PARSER_DIR/"
[ -f "$PARSER_DIR/hooks-bank.md" ] || cp "$HERE/reels-parser/hooks-bank.md" "$PARSER_DIR/"   # свой банк хуков не перезаписываем
[ -f "$PARSER_DIR/.env" ] || { cp "$HERE/reels-parser/.env.example" "$PARSER_DIR/.env"; warn "впиши токен Apify в $PARSER_DIR/.env (open -e \"$PARSER_DIR/.env\")"; }
ok "reels-parser"

echo "4. Распознавание лиц и шрифты"
if command -v swiftc >/dev/null; then
  swiftc -O "$M/scripts/faces.swift" -o "$M/scripts/faces" && ok "scripts/faces собран"
else warn "scripts/faces не собран — текст будет ставиться без учёта лиц"; fi
mkdir -p "$M/remotion/public/fonts"; cp "$M"/fonts/Montserrat-*.ttf "$M/remotion/public/fonts/"; ok "шрифты Montserrat → remotion/public/fonts"

if [ -z "$SKIP_NPM" ] && command -v npm >/dev/null; then
  echo "5. Ставлю Remotion (npm, 1–3 мин)"; (cd "$M/remotion" && npm ci --no-audit --no-fund --loglevel=error) && ok "Remotion"
fi
if [ -z "$SKIP_PY" ] && command -v python3 >/dev/null; then
  echo "6. Python-окружение в $REELS_WORKDIR (whisper и др., несколько минут)"; bash "$M/scripts/setup.sh" "$REELS_WORKDIR"
fi

echo
echo "Готово. Перезапусти Claude Code и напиши, например: «смонтируй рилс из папки ~/reels/первый»."
echo "DaVinci Resolve Studio нужен только для классического пути (resolve_build.py); «Конторка» собирается без него."
