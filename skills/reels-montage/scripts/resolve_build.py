"""Build a reel timeline in DaVinci Resolve Studio from a JSON config and render it.
Usage: source renv.sh && python resolve_build.py config.json
config = {
  "project": "Мой рилс 1",            # created if missing (1080x1920, 30fps, RCM v2, DaVinci DRT, SDR 100)
  "timeline": "Рилс v1 — описание",        # NEW name every version; an existing timeline with this name is replaced
  "total": 40.687,                          # seconds = voice length
  "clips": {"IMG_5847": "/path/IMG_5847.MOV", "IMG_5886": "/path/sdr/IMG_5886_SDR.mp4", ...},
  "shots": [[0.0, "IMG_5849", 0.0, "punch"], [1.4, "IMG_5849", 37.6, "punch"], ...],  # start, clip, src_in, effect
  "jump_split": 0.95,                        # shots longer than this are split into a jump cut (second half: src+half+0.35, "jump")
  "subs": "/path/субтитры.mov", "voice": "/path/голос.wav", "music": "/path/музыка.wav" | null,
  "cdl": {"IMG_5884": [1.2, 1, 0.83, 0, 1, 0.72]},  # slopeR,G,B, offset, power, sat  (keep G=1, R/B linked)
  "render_dir": "/path/монтаж", "render_name": "рилс_v1_описание"
}
Effects: push 1.0→1.14 | pull 1.18→1.02 | jump 1.26→1.34 | punch 1.45→1.16 in 3 frames + flash gain 1.6→1.0."""
import sys, json, time
import DaVinciResolveScript as dvr
C = json.load(open(sys.argv[1])); FPS = 30
r = dvr.scriptapp("Resolve"); assert r, "DaVinci Resolve Studio must be running (external scripting = Local)"
pm = r.GetProjectManager()
p = pm.LoadProject(C["project"]) or pm.CreateProject(C["project"])
for k, v in [("timelineFrameRate", "30"), ("timelineResolutionWidth", "1080"), ("timelineResolutionHeight", "1920"),
             ("colorScienceMode", "davinciYRGBColorManagedv2"), ("inputDRT", "DaVinci"), ("outputDRT", "DaVinci"),
             ("timelineWorkingLuminanceMode", "SDR 100"), ("perfRenderCacheMode", "smart"), ("perfAutoRenderCacheFuEffect", "1")]:
    p.SetSetting(k, v)
mp = p.GetMediaPool(); root = mp.GetRootFolder()
pool = {c.GetClipProperty("File Path"): c for c in root.GetClipList()}
def item(path):
    if path not in pool:
        res = mp.ImportMedia([path]); assert res, "import failed: " + path   # one file at a time (batch import hung once)
        pool[path] = res[0]
    return pool[path]
# shots with jump-cut splitting
base = C["shots"]; TOTAL = C["total"]; N = int(round(TOTAL * FPS)); shots = []
for i, (ts, clip, src, eff, *_) in enumerate(base):
    en = base[i + 1][0] if i + 1 < len(base) else TOTAL; dur = en - ts
    if dur > C.get("jump_split", 0.95):
        shots.append((ts, clip, src, eff)); shots.append((ts + dur / 2, clip, src + dur / 2 + 0.35, "jump"))
    else: shots.append((ts, clip, src, eff))
old = [p.GetTimelineByIndex(i + 1) for i in range(p.GetTimelineCount())]
old = [t for t in old if t.GetName() == C["timeline"]]
if old: mp.DeleteTimelines(old)
tl = mp.CreateEmptyTimeline(C["timeline"]); p.SetCurrentTimeline(tl); T0 = tl.GetStartFrame()
tl.AddTrack("video"); tl.SetTrackName("video", 1, "Видео"); tl.SetTrackName("video", 2, "Субтитры"); tl.SetTrackName("audio", 1, "Голос")
infos = []
for i, (ts, clip, src, eff) in enumerate(shots):
    a = int(round(ts * FPS)); b = int(round(shots[i + 1][0] * FPS)) if i + 1 < len(shots) else N; s = int(round(src * FPS))
    infos.append({"mediaPoolItem": item(C["clips"][clip]), "startFrame": s, "endFrame": s + (b - a), "recordFrame": T0 + a, "trackIndex": 1, "mediaType": 1})
added = mp.AppendToTimeline(infos); print("video items", len(added), "of", len(infos))
mp.AppendToTimeline([{"mediaPoolItem": item(C["subs"]), "startFrame": 0, "endFrame": N, "recordFrame": T0, "trackIndex": 2, "mediaType": 1}])
mp.AppendToTimeline([{"mediaPoolItem": item(C["voice"]), "startFrame": 0, "endFrame": N, "recordFrame": T0, "trackIndex": 1, "mediaType": 2}])
if C.get("overlay"):   # motion-graphics layer (motion.py) on its own track above the subtitles
    tl.AddTrack("video"); tl.SetTrackName("video", 3, "Моушн")
    mp.AppendToTimeline([{"mediaPoolItem": item(C["overlay"]), "startFrame": 0, "endFrame": N, "recordFrame": T0, "trackIndex": 3, "mediaType": 1}])
if C.get("music"):
    tl.AddTrack("audio", "stereo"); tl.SetTrackName("audio", 2, "Музыка")
    mp.AppendToTimeline([{"mediaPoolItem": item(C["music"]), "startFrame": 0, "endFrame": N, "recordFrame": T0, "trackIndex": 2, "mediaType": 2}])
def anim(it, eff):
    comp = it.AddFusionComp(); mi = comp.FindToolByID("MediaIn"); mo = comp.FindToolByID("MediaOut")
    at = comp.GetAttrs(); st, en = at["COMPN_RenderStart"], at["COMPN_RenderEnd"]
    comp.Lock()
    tr = comp.AddTool("Transform", -32768, -32768); tr.SetAttrs({"TOOLS_Name": "Zoom"}); tr.Input = mi.Output; last = tr
    tr.Size = comp.BezierSpline()
    if eff == "push": tr.Size[st] = 1.0; tr.Size[en] = 1.14
    elif eff == "pull": tr.Size[st] = 1.18; tr.Size[en] = 1.02
    elif eff == "jump": tr.Size[st] = 1.26; tr.Size[en] = 1.34
    elif eff == "punch":
        tr.Size[st] = 1.45; tr.Size[st + 3] = 1.16; tr.Size[en] = 1.2
        bc = comp.AddTool("BrightnessContrast", -32768, -32768); bc.SetAttrs({"TOOLS_Name": "Flash"}); bc.Input = tr.Output; last = bc
        bc.Gain = comp.BezierSpline(); bc.Gain[st] = 1.6; bc.Gain[st + 3] = 1.0
    mo.Input = last.Output; comp.Unlock()
items = sorted(tl.GetItemListInTrack("video", 1), key=lambda x: x.GetStart())
cdl = C.get("cdl", {}); n = 0
for it, sh in zip(items, shots):
    anim(it, sh[3])
    if sh[1] in cdl:
        r_, g_, b_, of, pw, sa = cdl[sh[1]]
        n += bool(it.SetCDL({"NodeIndex": "1", "Slope": f"{r_} {g_} {b_}", "Offset": f"{of} {of} {of}", "Power": f"{pw} {pw} {pw}", "Saturation": f"{sa}"}))
print("shots", len(shots), "avg", round(TOTAL / len(shots), 2), "s; CDL on", n)
pm.SaveProject()
r.OpenPage("deliver"); p.DeleteAllRenderJobs(); p.SetCurrentRenderFormatAndCodec("mp4", "H264")
p.SetRenderSettings({"SelectAllFrames": True, "TargetDir": C["render_dir"], "CustomName": C["render_name"],
                     "FormatWidth": 1080, "FormatHeight": 1920, "FrameRate": 30, "ExportVideo": True, "ExportAudio": True})
j = p.AddRenderJob(); p.StartRendering(j)
while p.IsRenderingInProgress(): time.sleep(3)
print(p.GetRenderJobStatus(j)); r.OpenPage("edit"); pm.SaveProject()
