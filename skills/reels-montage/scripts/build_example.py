"""Образец сборки базы рилса в формате «Конторка» (ИИ-кадры + твои кадры) — ffmpeg, без DaVinci.
Новый рилс: скопируй этот файл в папку рилса как build_v1.py и меняй только SEG / items / TOTAL.
Каждая правка — новая версия (build_v2.py, папка сборка/v2), старые не трогать.

Запуск:  python build_v1.py [папка_рилса]   (по умолчанию — текущая папка)
Ожидаемая структура папки рилса (имена — пример, свои подставь в SEG/items):
  видео/          — твои исходники с телефона (.mov/.mp4); HDR-клипы iPhone сначала через hlg_to_sdr.sh → sdr/
  картинки/       — ИИ-кадры (gen_image.sh kontorka …) для вставок
  сборка/chunks.json — субтитры (см. examples/example_chunks.json)
Результат: сборка/v1/база.mp4 (видео без графики и сабов) + сборка/v1/props.json (графика для remotion/render.sh).
Дальше по SKILL.md: render.sh props.json → subs.py → склейка в 2 шага → звук → endcheck.sh.
"""
import json, os, subprocess, statistics, sys
R = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
V = f"{R}/видео"; SDR = f"{R}/sdr"; IMG = f"{R}/картинки"; O = f"{R}/сборка/v1"; T = f"{O}/сегменты"
FF = os.environ.get("FFMPEG", "ffmpeg")
TOTAL = 40.6; os.makedirs(T, exist_ok=True)

FULL = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"            # кадр на весь экран
LOW = "scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,pad=1080:1920:0:960"  # кадр в нижнюю половину
BOT = "scale=1080:608:force_original_aspect_ratio=increase,crop=1080:608,pad=1080:1920:0:1312"  # 16:9 полосой снизу (диптих с half h=1312)
BOTV = "scale=1080:-2,crop=1080:608:0:(ih-608)*0.36,pad=1080:1920:0:1312"                     # вертикальный клип в нижнюю полосу, окно по лицу
LOWFIT = ("split[a][b];[a]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,gblur=sigma=30,eq=brightness=-0.06[bg];"
          "[b]scale=1080:-2[fg];[bg][fg]overlay=0:(960-h)/2,pad=1080:1920:0:960")       # общий план 16:9 целиком в нижней половине

SEG = [  # (start, end, файл|None, с какой секунды исходника, вид). None = чёрное место под ИИ-кадр на весь экран (insert)
    (0.00, 4.68, f"{V}/IMG_0001.MOV", 10.0, BOT),     # 1 К+П: ИИ-кадр сверху (half), ты снизу полосой 16:9
    (4.68, 5.96, None, 0, None),                      # 2 К: ИИ-кадр на весь экран, punch на ударном слове
    (5.96, 8.42, f"{V}/IMG_0002.MOV", 6.5, FULL),     # 3 Я: активный кадр с тобой на весь экран
    (8.42, 12.36, None, 0, None),                     # 4 К: персонаж-гэг
    (12.36, 16.04, f"{SDR}/IMG_0003_SDR.mp4", 1.4, FULL),  # 5 Я: HDR-клип, уже переведённый в SDR
    (16.04, 20.20, f"{V}/IMG_0004.MOV", 11.2, BOTV),  # 6 К+П: вертикальный клип в нижней полосе
    (20.20, TOTAL, f"{V}/IMG_0005.MOV", 8.0, FULL),   # 7 финал: эффектный кадр с тобой
]

def stats(path):  # средние Y/U/V по сегменту (signalstats)
    r = subprocess.run([FF, "-v", "error", "-i", path, "-vf", "signalstats,metadata=print:file=-", "-f", "null", "-"],
                       capture_output=True, text=True).stdout
    vals = {"YAVG": [], "UAVG": [], "VAVG": []}
    for line in r.splitlines():
        for k in vals:
            if f"lavfi.signalstats.{k}=" in line: vals[k].append(float(line.split("=")[1]))
    return {k: statistics.mean(v) for k, v in vals.items()}

raw = []
for i, (s, e, src, ss, vf) in enumerate(SEG):
    out = f"{T}/{i:02d}_raw.mp4"; nf = round(e * 30) - round(s * 30); d = nf / 30   # сетка кадров = как в Remotion (round(t*fps)), без накопления ошибки
    if src is None:
        cmd = [FF, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=black:s=1080x1920:r=30:d={d}", "-frames:v", str(nf)]
    else:
        cmd = [FF, "-v", "error", "-y", "-ss", str(ss), "-i", src, "-frames:v", str(nf), "-an", "-vf", f"{vf},fps=30,setsar=1"]
    subprocess.run(cmd + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", out], check=True)
    raw.append(out)

# выравнивание цвета твоих кадров («кадры скачут по цветокоррекции»): яркость к медиане, оттенок U/V к нейтрали наполовину, предел ±7
real = [i for i, sg in enumerate(SEG) if sg[2] is not None]
crop = lambda i: "crop=1080:608:0:1312," if SEG[i][4] in (BOT, BOTV) else ""
st = {}
for i in real:
    probe = f"{T}/{i:02d}_probe.mp4"
    subprocess.run([FF, "-v", "error", "-y", "-i", raw[i], "-vf", f"{crop(i)}scale=270:-2", "-an", probe], check=True)
    st[i] = stats(probe)
Yt = statistics.median(v["YAVG"] for v in st.values()); Ut = statistics.median(v["UAVG"] for v in st.values()); Vt = statistics.median(v["VAVG"] for v in st.values())
Ut, Vt = (Ut + 128) / 2, (Vt + 128) / 2
parts = []
for i, p in enumerate(raw):
    out = f"{T}/{i:02d}.mp4"
    if i in st:
        g = max(0.82, min(1.22, Yt / st[i]["YAVG"]))
        du = max(-7, min(7, Ut - st[i]["UAVG"])); dv = max(-7, min(7, Vt - st[i]["VAVG"]))
        lut = f"lutyuv=y='clip(val*{g:.3f},16,235)':u='clip(val+{du:.1f},16,240)':v='clip(val+{dv:.1f},16,240)'"
        print(f"{i:02d} Y {st[i]['YAVG']:.0f}→×{g:.2f}  U {du:+.1f}  V {dv:+.1f}")
        subprocess.run([FF, "-v", "error", "-y", "-i", p, "-vf", lut, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", out], check=True)
    else:
        os.replace(p, out)
    parts.append(out)
open(f"{T}/list.txt", "w").write("".join(f"file '{p}'\n" for p in parts))
subprocess.run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{T}/list.txt", "-c", "copy", f"{O}/база.mp4"], check=True)

items = [  # графика Remotion. fit/py/pz/fx/fy — чтобы лица персонажей не резались; пути — абсолютные
    {"type": "half", "h": 1312, "src": f"{IMG}/кадр1.png", "start": 0.0, "end": 4.68, "move": "in", "py": 0.5, "fx": 0.4, "fy": 0.4, "punch": True, "pz": 1.2},
    {"type": "insert", "src": f"{IMG}/кадр2.png", "start": 4.68, "end": 5.96, "move": "in", "fx": 0.45, "fy": 0.2, "wobble": True, "punch": True, "pz": 1.25},
    {"type": "insert", "src": f"{IMG}/кадр3.png", "start": 8.42, "end": 12.36, "move": "out", "fx": 0.55, "fy": 0.35, "wobble": True, "punch": True, "pz": 1.12},
    {"type": "half", "h": 1312, "src": f"{IMG}/кадр4.png", "start": 16.04, "end": 20.20, "move": "pan-l", "py": 0.3, "wobble": True},
]
json.dump({"duration": TOTAL, "items": items}, open(f"{O}/props.json", "w"), ensure_ascii=False, indent=1)
if os.path.exists(f"{R}/сборка/chunks.json"):
    subprocess.run(["cp", f"{R}/сборка/chunks.json", f"{O}/chunks.json"], check=True)
print("ok:", f"{O}/база.mp4", f"{O}/props.json")
