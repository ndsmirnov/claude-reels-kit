"""(chunks may carry "type": true + "step": 0.04 -> typewriter reveal; "color": "#FF4D6D", "fg": "#FFFFFF" -> coloured pill behind that phrase)
Render the subtitle layer (ProRes 4444 with alpha) in the approved style + optional typewriter end card.
Usage: python subs.py chunks.json out.mov --ffmpeg /path/ffmpeg --total 40.687
       [--card "Последняя фраза рилса." --card-start 38.487 --card-times 38.49,38.77,... --card-bold 6]
       Формат Ф1 «демо на экране» (рефы Инсты 02.10.2026): [--title "my confidence booster app" --title-emoji 🔥 --title-style plain|white|black]
       [--plate white|black  (субтитры на плашке)] [--cta "Напиши «МОНТАЖ» в комментах" --cta-emoji 👇 --cta-start 38.0]
Style: Montserrat SemiBold 46px (фирменный шрифт по умолчанию), sentence case, white, soft blurred shadow, 1-3 words, y=1390 on 1080x1920,
3-frame fade/rise-in. End card: black, words typed in sync with voice, keyword bold (Helvetica Neue Bold)."""
import argparse, json, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ap = argparse.ArgumentParser(); ap.add_argument("chunks"); ap.add_argument("out"); ap.add_argument("--ffmpeg", required=True)
ap.add_argument("--total", type=float, required=True); ap.add_argument("--card"); ap.add_argument("--card-start", type=float)
ap.add_argument("--card-times"); ap.add_argument("--card-bold", type=int, default=-1)
ap.add_argument("--font"); ap.add_argument("--font-index", type=int, default=0); ap.add_argument("--size", type=int, default=46); ap.add_argument("--y", type=int, default=1390)  # mono style: --font /System/Library/Fonts/SFNSMono.ttf --size 46 --y 990
ap.add_argument("--title"); ap.add_argument("--title-emoji"); ap.add_argument("--title-style", default="plain"); ap.add_argument("--title-y", type=int, default=230)
ap.add_argument("--title-size", type=int, default=64); ap.add_argument("--plate"); ap.add_argument("--cta"); ap.add_argument("--cta-emoji"); ap.add_argument("--cta-start", type=float)
ap.add_argument("--avoid-video", help="база рилса: сабы обходят лица в её кадрах"); ap.add_argument("--avoid-props", help="props Remotion: сабы обходят лица на вставках «Конторки»")
A = ap.parse_args()
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from textnorm import norm   # стандарт текста: без «ё», деньги «12,000 ₽»
A.title, A.cta, A.card = norm(A.title), norm(A.cta), norm(A.card); FPS = 30; W, H = 1080, 1920; N = int(round(A.total * FPS))
HN = "/System/Library/Fonts/HelveticaNeue.ttc"
# Фирменный шрифт всего монтажа — Montserrat (OFL), файлы в ../fonts
MS = lambda w: os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts", f"Montserrat-{w}.ttf")
font = ImageFont.truetype(A.font, A.size, index=A.font_index) if A.font else ImageFont.truetype(MS("SemiBold"), A.size)  # default — фирменный Montserrat SemiBold
chunks = [dict(c, text=norm(c["text"])) for c in json.load(open(A.chunks))];
if A.avoid_video or A.avoid_props:   # 02.10: субтитры не заходят на лица (кадр базы в середине фразы + вставки поверх)
    from layout import faces, screen_boxes, free_y
    items = json.load(open(A.avoid_props))["items"] if A.avoid_props else []
    for ch in chunks:
        if "y" in ch: continue
        t = (ch["start"] + ch["end"]) / 2; boxes = []
        cover = [it for it in items if it.get("type") in ("insert", "half") and it["start"] <= t < it["end"]]
        if A.avoid_video and not any(it["type"] == "insert" for it in cover):
            boxes += [(x0 * W, y0 * H, x1 * W, y1 * H) for x0, y0, x1, y1 in faces(A.avoid_video, t)]
        for it in cover: boxes += screen_boxes(it)
        y = free_y(boxes, ch["text"], A.size, cands=(A.y, A.y + 160, A.y - 160, 1650, 430))
        if y is not None: ch["y"] = y + int(A.size * 0.6)   # free_y даёт верх полосы, render — центр
d = tempfile.mkdtemp(); Y = A.y
def hexrgb(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def render(text, alpha, dy, color=None, fg=None, shown=None, yc=None):
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(txt)
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if dr.textlength(t, font=font) > 760 and cur: lines.append(cur); cur = w
        else: cur = t
    lines.append(cur); lh = 56; y0 = (yc or Y) - lh * len(lines) // 2 + dy
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
    cnt = shown if shown is not None else 10 ** 9   # typewriter: only the first `shown` characters are drawn, layout uses the full text
    for i, l in enumerate(lines):
        tw = dr.textlength(l, font=font); x = (W - tw) / 2; y = y0 + i * lh
        full, l = l, l[:max(cnt, 0)]; cnt -= len(full) + 1
        if not l: continue
        if A.plate and not color:   # Ф1: плашка под каждой строкой субтитров
            bg, tx = ((255, 255, 255), (0, 0, 0)) if A.plate == "white" else ((0, 0, 0), (255, 255, 255))
            dr.rounded_rectangle([x - 18, y - 4, x + tw + 18, y + lh - 2], radius=12, fill=bg + (235,))
            dr.text((x, y), l, font=font, fill=tx + (255,)); continue
        if color:   # coloured pill behind the line (accent word)
            dr.rounded_rectangle([x - 24, y - 6, x + tw + 24, y + 58], radius=30, fill=hexrgb(color) + (255,))
            dr.text((x, y), l, font=font, fill=hexrgb(fg or "#FFFFFF") + (255,)); continue
        ds.text((x, y + 4), l, font=font, fill=(0, 0, 0, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))  # плотная тень (видна на светлом фоне)
        dr.text((x, y), l, font=font, fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0, 90))
    out = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5)), txt)
    if alpha < 1: out.putalpha(out.getchannel("A").point(lambda v: int(v * alpha)))
    return out
EMO = "/System/Library/Fonts/Apple Color Emoji.ttc"
def emoji(ch, h):   # цветной эмодзи: шрифт Apple отдаёт только 160 px → масштаб под высоту строки
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0)); ImageDraw.Draw(im).text((0, 0), ch, font=ImageFont.truetype(EMO, 160), embedded_color=True)
    im = im.crop(im.getbbox()); return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
def badge(text, emo, y, size, style, scale=1.0):   # строка-заголовок / призыв: plain = белый текст с тенью, white/black = плашка
    f = ImageFont.truetype(MS("Bold"), int(size * scale)); img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(img)
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if dr.textlength(t, font=f) > 900 and cur: lines.append(cur); cur = w
        else: cur = t
    lines.append(cur); lh = int(f.size * 1.25); em = emoji(emo, int(f.size * 0.95)) if emo else None
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
    for i, l in enumerate(lines):
        last = em is not None and i == len(lines) - 1; tw = dr.textlength(l, font=f) + ((em.width + 14) if last else 0)
        x = (W - tw) / 2; yy = y + i * lh
        if style in ("white", "black"):
            bg, tx = ((255, 255, 255), (0, 0, 0)) if style == "white" else ((0, 0, 0), (255, 255, 255))
            dr.rounded_rectangle([x - 26, yy - 10, x + tw + 26, yy + lh + 2], radius=18, fill=bg + (245,)); dr.text((x, yy), l, font=f, fill=tx + (255,))
        else:
            ds.text((x, yy + 5), l, font=f, fill=(0, 0, 0, 255), stroke_width=3, stroke_fill=(0, 0, 0, 255)); dr.text((x, yy), l, font=f, fill=(255, 255, 255, 255))  # плотная тень (видна на светлом фоне)
        if last: img.alpha_composite(em, (int(x + tw - em.width), int(yy + (lh - em.height) / 2)))
    return Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)), img)
base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
if A.title: base = Image.alpha_composite(base, badge(A.title, A.title_emoji, A.title_y, A.title_size, A.title_style))
cta_start = A.cta_start if A.cta else 1e9; cta_imgs = {}
def cta(k):   # появление призыва: 3 кадра с увеличением 0.8 → 1.0
    if k not in cta_imgs: cta_imgs[k] = badge(A.cta, A.cta_emoji, 1500, 52, "white", (0.8, 0.9, 1.0)[min(k, 2)])
    return cta_imgs[k]
blank = os.path.join(d, "blank.png"); base.save(blank)
anim = [(0.35, 8), (0.7, 4), (1.0, 1)]; cache = {}
card_start = A.card_start if A.card else 1e9
for fr in range(N):
    t = fr / FPS; dst = os.path.join(d, f"f{fr:05d}.png")
    if fr >= int(round(card_start * FPS)): continue  # same rounding as the card loop below (else a frame is written twice)
    cur = next((c for c in chunks if c["start"] <= t + 1e-6 < c["end"]), None)
    if fr >= int(round(cta_start * FPS)):   # Ф1: с призыва субтитры уступают место карточке
        k = min(fr - int(round(cta_start * FPS)), 2); key = ("cta", k)
        if key not in cache: p = os.path.join(d, f"c{len(cache):04d}.png"); Image.alpha_composite(base, cta(k)).save(p); cache[key] = p
        os.link(cache[key], dst); continue
    if not cur: os.link(blank, dst); continue
    k = fr - int(round(cur["start"] * FPS)); al, dy = anim[k] if 0 <= k < len(anim) else (1.0, 0)
    nsh = min(len(cur["text"]), int((t - cur["start"]) / cur["step"]) + 1) if cur.get("type") else None   # "type": true, "step": sec per char
    key = (cur["text"], al, dy, cur["start"], cur.get("color"), nsh, cur.get("y"))
    if key not in cache: p = os.path.join(d, f"c{len(cache):04d}.png"); Image.alpha_composite(base, render(cur["text"], al, dy, cur.get("color"), cur.get("fg"), nsh, cur.get("y"))).save(p); cache[key] = p
    os.link(cache[key], dst)
if A.card:
    words = A.card.split(); times = [float(x) for x in A.card_times.split(",")]; assert len(times) == len(words)
    reg = ImageFont.truetype(MS("Medium"), 44); bold = ImageFont.truetype(MS("ExtraBold"), 44)
    half = (len(words) + 1) // 2; lines = [list(range(half)), list(range(half, len(words)))]
    def card(n):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 255)); dr = ImageDraw.Draw(img); sp = dr.textlength(" ", font=reg)
        for li, idx in enumerate(lines):
            fs = [bold if i == A.card_bold else reg for i in idx]; ws = [dr.textlength(words[i], font=f) for i, f in zip(idx, fs)]
            x = (W - sum(ws) - sp * (len(idx) - 1)) / 2; y = H // 2 - 60 + li * 62
            for i, f, wd in zip(idx, fs, ws):
                if i < n: dr.text((x, y), words[i], font=f, fill=(255, 255, 255, 255))
                x += wd + sp
        return img
    cc = {}
    for fr in range(int(round(card_start * FPS)), N):
        n = sum(1 for ts in times if ts <= fr / FPS + 1e-6)
        if n not in cc: p = os.path.join(d, f"card{n}.png"); card(n).save(p); cc[n] = p
        os.link(cc[n], os.path.join(d, f"f{fr:05d}.png"))
subprocess.run([A.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-framerate", "30", "-i", os.path.join(d, "f%05d.png"),
                "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", A.out], check=True)
print("frames", N, "unique", len(cache))
