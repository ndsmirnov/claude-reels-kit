#!/bin/zsh
# Usage: hlg_to_sdr.sh <ffmpeg> <out_dir> clip1.MOV clip2.MOV ...
# iPhone HLG -> natural SDR WITHOUT tonemapping: treat HLG as BT.709 transfer, convert BT.2020 -> BT.709 primaries/matrix.
# Frame count stays identical (-r 30). Only for clips whose color_trc is arib-std-b67 (check with ffmpeg -i).
FF=$1; O=$2; shift 2; mkdir -p "$O"
for f in "$@"; do b=$(basename "$f"); b=${b%.*}
  "$FF" -hide_banner -loglevel error -y -i "$f" -map 0:v:0 -an \
   -vf "zscale=primariesin=2020:primaries=709:transferin=709:transfer=709:matrixin=2020_ncl:matrix=709:rangein=tv:range=tv,format=yuv420p" \
   -r 30 -c:v libx264 -crf 14 -preset fast -color_primaries bt709 -color_trc bt709 -colorspace bt709 "$O/${b}_SDR.mp4" &
  while [ $(jobs -r | wc -l) -ge 3 ]; do sleep 1; done
done; wait
for f in "$O"/*_SDR.mp4; do echo "$(basename $f) $("$FF" -i "$f" -map 0:v -c copy -f null - 2>&1 | grep -o 'frame= *[0-9]*' | tail -1)"; done
