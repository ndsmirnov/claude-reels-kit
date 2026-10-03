"""Раскладка текста мимо лиц (субтитры и тезисы не должны заходить на лица героев).
Механика, не правило на словах: лица ищет Apple Vision (scripts/faces, собрать: swiftc -O faces.swift -o faces), учитывается движение кадра
(наезд/проход/резкий наезд → лицо растёт и смещается), текст ставится в первую свободную позицию.
  place_thesis(items, W=1080, H=1920)  — для props Remotion: проставляет it["y"] у thesis
  free_y(boxes, text, size, cands)     — для subs.py: выбор y под конкретный кадр видео
"""
import json, os, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FACES = os.path.join(HERE, "faces")
_cache = {}


def faces(path, t=None):
    """Лица в долях кадра. Для видео — кадр в момент t."""
    key = (path, t)
    if key in _cache:
        return _cache[key]
    src = path
    if os.path.splitext(path)[1].lower() in (".mp4", ".mov"):
        src = tempfile.mktemp(suffix=".jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t or 0:.2f}", "-i", path, "-frames:v", "1", src])
    try:
        out = json.loads(subprocess.run([FACES, src], capture_output=True, text=True).stdout or "[]")
    except Exception:
        out = []
    _cache[key] = out
    return out


def _img_size(path):
    from PIL import Image
    with Image.open(path) as im:
        return im.size


def screen_boxes(it, W=1080, H=1920):
    """Лица картинки insert/half в пикселях экрана, объединение по началу/концу движения (+ punch)."""
    if os.path.splitext(it["src"])[1].lower() in (".mp4", ".mov"):
        fr = faces(it["src"], it.get("from", 0) + (it["end"] - it["start"]) / 2)
        iw, ih = (W, it.get("h", 960)) if it["type"] == "half" else (W, H)
    else:
        fr = faces(it["src"]); iw, ih = _img_size(it["src"])
    bw, bh = (W, it.get("h", 960)) if it["type"] == "half" else (W, H)
    k = (min if it.get("fit") == "contain" else max)(bw / iw, bh / ih); dw, dh = iw * k, ih * k
    ox0, oy0 = (bw - dw) / 2, (bh - dh) * it.get("py", 0.5)   # 03.10: как в Overlay — fit/py/h
    mv = it.get("move", "in"); half = it["type"] == "half"
    if mv == "out": zooms = [1.14, 1.02]
    elif mv == "to": zooms = [1.0, 1.35]
    elif mv.startswith("pan"): zooms = [1.12]
    else: zooms = [1.0, 1.06 if half else 1.1]
    if it.get("punch"): zooms += [z * it.get("pz", 1.35) for z in zooms]
    own = "fx" in it or "fy" in it
    ox = (it.get("fx", 0.5) if own else 0.5) * bw; oy = (it.get("fy", 0.35) if own else 0.35) * bh
    tx = [-40, 40] if mv.startswith("pan") else [0]
    out = []
    for x0, y0, x1, y1 in fr:
        X0, Y0, X1, Y1 = ox0 + x0 * dw, oy0 + y0 * dh, ox0 + x1 * dw, oy0 + y1 * dh
        for z in zooms:
            for t in tx:
                out.append((ox + (X0 - ox) * z + t - 8, oy + (Y0 - oy) * z - 8, ox + (X1 - ox) * z + t + 8, oy + (Y1 - oy) * z + 8))
    return out


def text_h(text, size=56, width=920):
    per_line = max(8, int(width / (size * 0.55)))
    return (len(text) // per_line + 1) * size * 1.2 + 24


def free_y(boxes, text, size=56, cands=(150, 330, 1450, 1600, 560), x=(80, 1000)):
    h = text_h(text, size)
    for y in cands:
        if not any(b[0] < x[1] and b[2] > x[0] and b[1] < y + h and b[3] > y for b in boxes):
            return y
    return None


def place_thesis(items, W=1080, H=1920):
    """Для каждого thesis — y, свободный от лиц всех картинок, идущих одновременно с ним. Возвращает список предупреждений."""
    warn = []
    vis = [it for it in items if it.get("type") in ("insert", "half")]
    for it in items:
        if it.get("type") != "thesis":
            continue
        boxes = [b for v in vis if v["start"] < it["end"] and v["end"] > it["start"] for b in screen_boxes(v, W, H)]
        y = free_y(boxes, it["text"])
        if y is None:
            warn.append(f"нет свободного места под тезис «{it['text']}» — лица везде; оставил y={it.get('y', 150)}")
        elif "y" not in it or it.get("y_auto", True):
            it["y"] = y
    return warn


if __name__ == "__main__":
    import sys
    d = json.load(open(sys.argv[1])); w = place_thesis(d["items"])
    for it in d["items"]:
        if it["type"] == "thesis":
            print(it["y"], it["text"])
    print("\n".join(w))
