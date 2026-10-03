#!/bin/bash
# Проверка конца ролика ПЕРЕД показом пользователю (частая беда — «звук в конце обрывается»; проверка тем же
# конвейером, которым собирали, ничего не ловит). Независимый канал — спектрограмма + распознавание:
#   endcheck.sh черновик.mp4 [голос.mp3]  → <черновик>-конец-спектр.png (смотреть глазами!) + RMS по 0,1 с + последние слова
# На спектрограмме не должно быть: вертикальных полос по всем частотам (щелчки), «стены» — резкого обрыва шума/музыки,
# тёмного провала между голосом и музыкой. Нет картинки, просмотренной глазами, — нет слова «исправлено».
F="$1"; D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$F"); S=$(python3 -c "print(max(0,$D-3))")
ffmpeg -v error -y -ss $S -i "$F" -vn -lavfi "showspectrumpic=s=1200x400:legend=1:scale=log" "${F%.*}-конец-спектр.png"
echo "RMS по 0,1 с от $S:"; ffmpeg -hide_banner -ss $S -i "$F" -vn -af "aresample=48000,asetnsamples=4800,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-" -f null - 2>/dev/null | grep RMS | awk -F= '{printf "%.0f ", $2}'; echo
echo "спектр: ${F%.*}-конец-спектр.png"
# Чёрные провалы в кадре (бывает: при склейке 3 слоёв за один проход терялась графика и мелькал чёрный).
echo "чёрные провалы (верх кадра / весь кадр), должно быть пусто:"
ffmpeg -hide_banner -i "$F" -vf "crop=iw:ih*0.6:0:0,blackdetect=d=0.03:pix_th=0.10" -an -f null - 2>&1 | grep -o "black_start:[0-9.]* black_end:[0-9.]*" | sed 's/^/  верх: /'
ffmpeg -hide_banner -i "$F" -vf "blackdetect=d=0.03:pix_th=0.10" -an -f null - 2>&1 | grep -o "black_start:[0-9.]* black_end:[0-9.]*" | sed 's/^/  кадр: /'
