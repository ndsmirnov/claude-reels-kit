"""Sound effect for black insert cards: 'echo' (word repeats as a fading echo), 'type' (typewriter clicks per character), 'phone' (voice as through an old phone: band 400-3200 Hz + light saturation + hiss, -2 dB) or 'muffle' (for the music track: low-pass 1.5 kHz, -3 dB) inside the windows.
Usage: python vfx.py echo|type|phone|muffle voice.wav chunks_windows.json out.wav --ffmpeg /path/ffmpeg
chunks_windows.json: [{"start": 3.12, "end": 3.42, "text": "привыкла", "step": 0.03}, ...]  (timeline seconds; step = sec per char, same as in subs.py)"""
import sys, json, subprocess, numpy as np
from scipy.signal import butter, lfilter
mode, vin, wj, vout = sys.argv[1:5]; FF = sys.argv[sys.argv.index("--ffmpeg") + 1]; SR = 48000
raw = subprocess.run([FF, "-loglevel", "error", "-i", vin, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64); N = len(x); W = json.load(open(wj)); rng = np.random.default_rng(5)
def lp(a, f): b, c = butter(2, f / (SR / 2), "low"); return lfilter(b, c, a, axis=0)
def hp(a, f): b, c = butter(2, f / (SR / 2), "high"); return lfilter(b, c, a, axis=0)
def add(buf, y, t0, g):
    i = int(t0 * SR)
    if 0 <= i < len(buf): y = y[:len(buf) - i]; buf[i:i + len(y)] += y * g
if mode in ("phone", "muffle"):
    gate = np.zeros(N); r = int(0.015 * SR)
    for w in W:
        a, b = int(w["start"] * SR), int(w["end"] * SR); gate[a:b] = 1; gate[a:a + r] = np.linspace(0, 1, r); gate[b - r:b] = np.linspace(1, 0, r)
    if mode == "phone":
        bp = lp(hp(hp(x, 400), 400), 3200); bp = lp(bp, 3200); d = np.tanh(2.2 * bp) / 2.2 * 1.25
        d = d + 0.004 * rng.standard_normal(d.shape); proc = d * 10 ** (-2 / 20)
    else: proc = lp(lp(x, 1500), 1500) * 10 ** (-3 / 20)
    y = x * (1 - gate[:, None]) + proc * gate[:, None]
elif mode == "echo":
    gate = np.zeros(N); r = int(0.012 * SR)
    for w in W:
        a, b = int(w["start"] * SR), int(w["end"] * SR); gate[a:b] = 1; gate[a:a + r] = np.linspace(0, 1, r); gate[b - r:b] = np.linspace(1, 0, r)
    g = x * gate[:, None]; wet = np.zeros_like(x)
    for d, lv in ((0.24, 0.9), (0.48, 0.62), (0.72, 0.4), (0.96, 0.22), (1.2, 0.1)): add(wet, g, d, lv)
    y = x + lp(hp(wet, 250), 3800)
else:
    clk = np.zeros_like(x)
    for w in W:
        for i, ch in enumerate(w["text"]):
            t = w["start"] + i * w["step"]; n = int(0.012 * SR); tt = np.arange(n) / SR
            c = hp(rng.standard_normal(n), 1500) * np.exp(-tt / 0.0025) + 0.6 * np.sin(2 * np.pi * rng.uniform(150, 210) * tt) * np.exp(-tt / 0.004)
            c = np.stack([c, c], 1) * (0.5 if ch == " " else rng.uniform(0.8, 1.0)); add(clk, c, t, 0.17)
    y = x + clk
y = np.clip(y, -1.5, 1.5)
p = subprocess.Popen([FF, "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "alimiter=limit=0.91:attack=5:release=120:level=disabled", "-c:a", "pcm_s24le", vout], stdin=subprocess.PIPE)
p.stdin.write(y.astype(np.float32).tobytes()); p.stdin.close(); p.wait(); print("ok", mode, vout)
