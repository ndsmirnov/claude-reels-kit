"""Usage: python transcribe.py <audio> <out.json> [start_sec]
Word-level Russian transcription (faster-whisper medium). Prints words with timestamps.
Tip: re-transcribe disputed snippets separately (cut with ffmpeg -ss/-to) — retakes confuse the model."""
import sys, json
from faster_whisper import WhisperModel
audio, out = sys.argv[1], sys.argv[2]; start = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
import os, subprocess, numpy as np   # новый PyAV ломает decode_audio faster-whisper (metadata_errors) — декодируем сами через ffmpeg
pcm = subprocess.run([os.environ.get("FFMPEG", "ffmpeg"), "-v", "error", "-i", audio, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
audio_arr = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
m = WhisperModel("medium", device="cpu", compute_type="int8")
segs, _ = m.transcribe(audio_arr, language="ru", word_timestamps=True, beam_size=5,
                       condition_on_previous_text=False, clip_timestamps=[start] if start else "0")
words = [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for s in segs for w in s.words]
json.dump(words, open(out, "w"), ensure_ascii=False, indent=0)
print(" ".join(f"{w['w']}({w['s']:.2f})" for w in words))
