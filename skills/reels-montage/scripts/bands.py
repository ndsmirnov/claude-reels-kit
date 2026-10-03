import sys,os,subprocess,numpy as np,json
import shutil; FF=os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"  # $FFMPEG (symlink from setup.sh) or ffmpeg from PATH
def load(p):
    r=subprocess.run([FF,"-loglevel","error","-i",p,"-ac","1","-ar","48000","-f","f32le","-"],capture_output=True).stdout
    return np.frombuffer(r,dtype=np.float32).astype(np.float64)
def bands(x,sr=48000):
    hop=sr//10; idx=range(0,len(x)-hop,hop); e=[np.sqrt((x[i:i+hop]**2).mean()) for i in idx]
    thr=max(e)*10**(-30/20); seg=np.concatenate([x[i:i+hop] for i,v in zip(idx,e) if v>thr])
    F=np.abs(np.fft.rfft(seg))**2; f=np.fft.rfftfreq(len(seg),1/sr)
    edges=[0,80,200,500,2000,5000,10000,24000]; names=["<80","80-200","200-500","500-2k","2-5k","5-10k",">10k"]
    tot=F.sum(); return {n:float(round(100*F[(f>=a)&(f<b)].sum()/tot,1)) for n,a,b in zip(names,edges[:-1],edges[1:])}
def lu(p):
    o=subprocess.run([FF,"-hide_banner","-nostats","-i",p,"-af","ebur128=peak=true","-f","null","-"],capture_output=True,text=True).stderr
    import re; i=re.findall(r"I:\s+(-?[\d.]+) LUFS",o)[-1]; lra=re.findall(r"LRA:\s+([\d.]+)",o)[-1]; pk=re.findall(r"Peak:\s+(-?[\d.]+) dBFS",o)[-1]
    return float(i),float(lra),float(pk)
if __name__=="__main__":
    for p in sys.argv[1:]:
        x=load(p); print(p.split("/")[-1],json.dumps(bands(x)),"LUFS/LRA/TP",lu(p))
