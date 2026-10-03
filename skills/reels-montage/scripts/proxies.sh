#!/bin/zsh
# Usage: proxies.sh <ffmpeg> <out_dir> clip1 clip2 ...  -> half-res ProRes Proxy for smooth DaVinci playback.
# Then in Resolve: clip.LinkProxyMedia(out_dir/<name>.mov); project.SetSetting("perfProxyMediaMode","1")
FF=$1; O=$2; shift 2; mkdir -p "$O"
for f in "$@"; do b=$(basename "$f"); b=${b%.*}
  if "$FF" -i "$f" 2>&1 | grep -q arib-std-b67; then C=(-color_primaries bt2020 -color_trc arib-std-b67 -colorspace bt2020nc)
  else C=(-color_primaries bt709 -color_trc bt709 -colorspace bt709); fi
  "$FF" -hide_banner -loglevel error -y -i "$f" -map 0:v:0 -an -vf scale=540:960 -r 30 -c:v prores_ks -profile:v 0 -pix_fmt yuv422p10le $C "$O/$b.mov" &
done; wait
