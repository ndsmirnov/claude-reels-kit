import subprocess,sys,os
sys.path.insert(0,os.path.dirname(__file__)); from bands import lu,load,bands,FF
"""Voice -> storyteller-like loudness/tone. Usage: python vproc.py src.wav out.wav LOW MID PRES   (e.g. 6 -3 2.5)
EQ: +LOW dB @150 Hz, -|MID| dB @900 Hz, +PRES dB @3.5 kHz, compressor 3:1 (attack 30 ms), limiter; iterates gain to -14.2 LUFS. Set FFMPEG or link ffmpeg next to the scripts."""
src,out=sys.argv[1],sys.argv[2]
LOW,MID,PRES=float(sys.argv[3]),float(sys.argv[4]),float(sys.argv[5])
eq=f"highpass=f=55,equalizer=f=150:t=q:w=0.7:g={LOW},equalizer=f=250:t=q:w=1:g={LOW/3},equalizer=f=900:t=q:w=0.8:g={MID},equalizer=f=3500:t=q:w=0.8:g={PRES}"
comp="acompressor=threshold=0.06:ratio=3:attack=30:release=250:makeup=1"
def run(gain,o):
    subprocess.run([FF,"-loglevel","error","-y","-i",src,"-af",f"{eq},{comp},volume={gain}dB,alimiter=limit=0.917:attack=5:release=120:level=disabled","-ar","48000","-ac","2","-c:a","pcm_s24le",o],check=True)
g=8.0
for _ in range(4):
    run(g,out); I,lra,tp=lu(out)
    if abs(I+14.2)<0.15: break
    g+=(-14.2-I)*1.0
print("gain",round(g,1),"LUFS/LRA/TP",lu(out)); print(bands(load(out)))
