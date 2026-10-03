import sys,subprocess,numpy as np,os
import shutil; FF=os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"  # $FFMPEG (symlink from setup.sh) or ffmpeg from PATH
def stats(p,fps=2):
    r=subprocess.run([FF,"-loglevel","error","-i",p,"-vf",f"fps={fps},scale=108:192","-f","rawvideo","-pix_fmt","rgb24","-"],capture_output=True).stdout
    a=np.frombuffer(r,np.uint8).reshape(-1,192,108,3).astype(float)/255
    lum=(0.2126*a[...,0]+0.7152*a[...,1]+0.0722*a[...,2]); live=lum.reshape(len(a),-1).mean(1)>0.06   # skip black cards
    a=a[live]; lum=lum[live]; mx=a.max(-1); mn=a.min(-1); sat=np.where(mx>0.02,(mx-mn)/np.maximum(mx,1e-3),0)
    return dict(RB=round(float((a[...,0]-a[...,2]).mean()),3),sat=round(float(sat.mean()),3),Y=round(float(lum.mean()),3),p2=round(float(np.percentile(lum,2)),3),p98=round(float(np.percentile(lum,98)),3))
for p in sys.argv[1:]: print(os.path.basename(p)[:40],stats(p))
