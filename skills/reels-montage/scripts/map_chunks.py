"""Map subtitle chunks from source-recording time to final timeline time.
Usage: python map_chunks.py keep.json chunks_src.json chunks.json
chunks_src.json: [["Первая фраза", 35.31, 1], ["вторая фраза", 35.94, 0], ...]  (text, start in source sec, highlight flag)"""
import sys, json
K = json.load(open(sys.argv[1])); keep, tempo, total = K["keep"], K["tempo"], K["total"]
def m(t):
    acc = 0
    for a, b in keep:
        if t < a: return acc / tempo
        if t <= b: return (acc + t - a) / tempo
        acc += b - a
    return acc / tempo
C = json.load(open(sys.argv[2])); out = []
for i, (txt, s, h) in enumerate(C):
    out.append({"text": txt, "start": round(m(s), 3), "end": round(m(C[i + 1][1]) if i + 1 < len(C) else total, 3), "hl": h})
json.dump(out, open(sys.argv[3], "w"), ensure_ascii=False, indent=0)
for c in out: print(f"{c['start']:6.2f}-{c['end']:6.2f} {c['text']}")
