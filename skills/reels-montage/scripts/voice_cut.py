"""Cut the voiceover: keep speech of the clean take, drop pauses/breaths/false starts, speed up without pitch change.
Usage: python voice_cut.py config.json
config: {"input": "voice.m4a", "ffmpeg": ".../ffmpeg", "take_start": 35.25, "take_end": 92.95,
         "exclude": [[81.0, 82.2]],   # false starts inside the take (seconds in source)
         "tempo": 1.15, "gain_db": 9.3, "out_wav": ".../голос_нарезка.wav", "keep_json": ".../keep.json"}
Proven values: threshold -48 dB, pad -35/+50 ms, merge gaps <70 ms, 6 ms fades, Rubber Band R3 tempo,
highpass 60 Hz + gain + alimiter 0.89 (≈ -17.5 LUFS). NO fast compressor, NO ffmpeg atempo (rattly)."""
import sys, json, subprocess, wave, os, tempfile
import numpy as np
C = json.load(open(sys.argv[1])); FF = C["ffmpeg"]
tmp = tempfile.mkdtemp()
raw = os.path.join(tmp, "raw.wav")
subprocess.run([FF, "-loglevel", "error", "-y", "-i", C["input"], "-ac", "1", "-ar", "48000", raw], check=True)
w = wave.open(raw); sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
hop = sr // 100
db = np.array([20 * np.log10(np.sqrt((x[i:i + 2 * hop] ** 2).mean()) + 1e-9) for i in range(0, len(x) - 2 * hop, hop)])
T0, T1 = C["take_start"], C["take_end"]; thr = C.get("threshold_db", -48)
regs, cur = [], None
for k in range(int(T0 * 100), int(T1 * 100)):
    t = k / 100; v = db[k] > thr
    if v and cur is None: cur = [t, t]
    if v: cur[1] = t + 0.02
    if not v and cur is not None and t - cur[1] > 0.10: regs.append(cur); cur = None
if cur: regs.append(cur)
keep = []
for a, b in regs:
    a = max(T0, a - 0.035); b = min(T1, b + 0.05)
    if keep and a - keep[-1][1] < 0.07: keep[-1][1] = b
    else: keep.append([a, b])
keep = [k for k in keep if not any(ex[0] <= k[0] <= ex[1] for ex in C.get("exclude", []))]
f = int(sr * 0.006); ramp = np.linspace(0, 1, f, dtype=np.float32); parts = []
for s, e in keep:
    p = x[int(s * sr):int(e * sr)].copy(); p[:f] *= ramp; p[-f:] *= ramp[::-1]; parts.append(p)
y = np.concatenate(parts)
tempo = C.get("tempo", 1.0)
if tempo != 1.0:
    from pylibrb import RubberBandStretcher, Option
    st = RubberBandStretcher(sr, 1, Option.PROCESS_OFFLINE | Option.ENGINE_FINER | Option.FORMANT_PRESERVED | Option.CHANNELS_TOGETHER, 1 / tempo, 1.0)
    B = 8192; st.set_max_process_size(B); a = y.reshape(1, -1); L = a.shape[1]; st.set_expected_input_duration(L)
    for i in range(0, L, B): st.study(np.ascontiguousarray(a[:, i:i + B]), final=(i + B >= L))
    out = []
    def drain():
        while True:
            n = st.available()
            if n <= 0: return n
            out.append(st.retrieve(n))
    for i in range(0, L, B): st.process(np.ascontiguousarray(a[:, i:i + B]), final=(i + B >= L)); drain()
    while not st.is_done():
        if drain() == -1: break
    drain(); y = np.concatenate(out, axis=1)[0]
mid = os.path.join(tmp, "mid.wav")
ww = wave.open(mid, "wb"); ww.setnchannels(1); ww.setsampwidth(2); ww.setframerate(sr)
ww.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()); ww.close()
subprocess.run([FF, "-loglevel", "error", "-y", "-i", mid, "-af",
                f"highpass=f=60,volume={C.get('gain_db', 9.3)}dB,alimiter=limit=0.89:attack=5:release=150:level=disabled",
                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", C["out_wav"]], check=True)
json.dump({"keep": keep, "tempo": tempo, "total": len(y) / sr}, open(C["keep_json"], "w"))
print(f"pieces={len(keep)} cut={sum(b - a for a, b in keep):.2f}s final={len(y) / sr:.2f}s")
