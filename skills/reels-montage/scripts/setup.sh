#!/bin/bash
# Usage: bash setup.sh [workdir]   -> creates <workdir>/venv and <workdir>/ffmpeg symlink
# workdir по умолчанию — $REELS_WORKDIR или ~/reels-work (одна папка с venv на все рилсы).
W=${1:-${REELS_WORKDIR:-$HOME/reels-work}}; mkdir -p "$W"; cd "$W" || exit 1; W="$(pwd)"
[ -d venv ] || python3 -m venv venv
./venv/bin/pip install -q imageio-ffmpeg faster-whisper pillow numpy scipy pylibrb yt-dlp 2>&1 | grep -v -i warn
ln -sf "$(./venv/bin/python -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')" "$W/ffmpeg"
"$W/ffmpeg" -hide_banner -version | head -1
echo "Готово: source \"$W/venv/bin/activate\"; export FFMPEG=\"$W/ffmpeg\""
