#!/bin/bash
# Озвучка рилса через fish.audio (без записи голоса): tts.sh <голос> text.txt out.mp3 [model]
#   <голос>  — kontorka (публичная модель тренда «Конторка») или id любой модели голоса с fish.audio
#              (в т.ч. твой собственный клон голоса — id из личного кабинета fish.audio)
#   model    — s2.1-pro-free (по умолчанию, бесплатно) | s2-pro (платно, см. тарифы fish.audio)
# Ключ API — переменная окружения FISH_API_KEY (fish.audio → API Keys). Ключ никому не отправляй и не клади в git.
# В тексте для голоса писать названия фонетически («Клод Код», «Давинчи»), числа словами; правильное написание — только в субтитрах.
set -e
[ -z "$3" ] && { echo "usage: tts.sh kontorka|<voice_id> text.txt out.mp3 [model]"; exit 1; }
case "$1" in
  kontorka) REF=bf36604cb53d41e19a8bec710d0af12e ;;
  *) REF="$1" ;;
esac
[ -z "$FISH_API_KEY" ] && { echo "Нет FISH_API_KEY: export FISH_API_KEY=<ключ с fish.audio>"; exit 1; }
MODEL=${4:-s2.1-pro-free}
BODY=$(python3 -c "import json,sys;print(json.dumps({'text':open(sys.argv[1]).read().strip(),'reference_id':sys.argv[2],'format':'mp3'}))" "$2" "$REF")
CODE=$(curl -s -m 300 -o "$3" -w "%{http_code}" https://api.fish.audio/v1/tts -H "Authorization: Bearer $FISH_API_KEY" \
  -H "Content-Type: application/json" -H "model: $MODEL" -d "$BODY")
[ "$CODE" = 200 ] && echo "$3 $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$3") с" || { echo "ОШИБКА $CODE: $(head -c 300 "$3")"; exit 1; }
