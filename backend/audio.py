import hashlib
from pathlib import Path
import av
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
SR=44100
MAX_BYTES=250*1024*1024
EXTENSIONS={'.wav','.mp3','.m4a','.mp4','.mov'}

def decode(source:Path,dest:Path):
 try:
  with av.open(str(source)) as container:
   if not container.streams.audio:raise ValueError('素材沒有音軌。')
   duration=(container.duration or 0)/av.time_base
   if not duration:
    stream=container.streams.audio[0]
    duration=float(stream.duration*stream.time_base) if stream.duration is not None else 0
  if duration<=0 or duration>180:raise ValueError('素材長度必須大於 0 且不超過三分鐘。')
  # PyAV ships its codec libraries; users need no FFmpeg executable.
  with av.open(str(source)) as container, sf.SoundFile(dest, 'w', samplerate=SR, channels=2, subtype='PCM_24') as output:
   resampler=av.AudioResampler(format='fltp',layout='stereo',rate=SR)
   total=0
   for frame in container.decode(audio=0):
    for converted in resampler.resample(frame):
     samples=converted.to_ndarray().T
     total+=len(samples)
     if total>round(SR*180.005):raise ValueError('素材超過三分鐘。')
     output.write(samples)
   for converted in resampler.resample(None):
    output.write(converted.to_ndarray().T)
  y,s=sf.read(dest,always_2d=True,dtype='float32')
  if len(y)/s>180.005:raise ValueError('素材超過三分鐘。')
  if not len(y) or not np.isfinite(y).all() or np.max(np.abs(y))<1e-5 or np.sqrt(np.mean(y*y))<1e-6:raise ValueError('素材沒有可用聲音，請換一段有說話的素材。')
  n=1000;blocks=np.array_split(y.mean(axis=1),min(n,len(y)))
  peaks=[round(float(np.max(np.abs(b))),5) for b in blocks]
  return {'duration':len(y)/s,'sample_rate':s,'peaks':peaks,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
 except av.FFmpegError as e:
  raise ValueError('無法讀取音訊格式，請重新匯出有效的音檔或影片。') from e

def validate_ranges(s,duration):
 for prefix in ('ref','target') if s['mode']=='replace' else ('ref',):
  a,b=s[f'{prefix}_start'],s[f'{prefix}_end']
  if not (0<=a<b<=duration+.001):raise ValueError('選取範圍超出音檔，或結束時間不大於開始時間。')
 r=s['ref_end']-s['ref_start']
 if r<.999 or r>12.001:raise ValueError('音色參考片段需為 1～12 秒。')

def trim_generated(y,sr):
 y=np.asarray(y,dtype=np.float64).reshape(-1)
 if not len(y) or not np.isfinite(y).all():raise ValueError('生成結果無效，請重試。')
 window=max(1,round(.015*sr));energy=np.sqrt(np.convolve(y*y,np.ones(window)/window,mode='same'))
 active=np.flatnonzero(energy>max(.0004,float(energy.max())*.025))
 if not len(active):raise ValueError('生成結果無聲，請重試或換參考片段。')
 y=y[max(0,active[0]-round(.025*sr)):min(len(y),active[-1]+round(.06*sr))].copy()
 fade=min(round(.008*sr),len(y)//4)
 if fade:y[:fade]*=np.linspace(0,1,fade);y[-fade:]*=np.linspace(1,0,fade)
 return y

def rms(y):
 mono=y.mean(axis=1) if y.ndim>1 else y
 return float(np.sqrt(np.mean(mono*mono)))

def background_for_length(bg,n,sr):
 """Retain the original beginning/tail; extend quiet residual with crossfades."""
 old=len(bg);fade=min(round(.025*sr),old//4,n//4)
 if n<=old:
  out=bg[:n].copy()
  if fade:
   w=np.linspace(0,1,fade)[:,None];out[-fade:]=out[-fade:]*(1-w)+bg[-fade:]*w
  return out,False
 if old<4:return np.zeros((n,bg.shape[1])),True
 width=min(round(.35*sr),old);hop=max(1,width//2)
 starts=list(range(0,max(1,old-width+1),hop))
 st=min(starts,key=lambda k:float(np.mean(bg[k:k+width]**2)))
 loop=bg[st:st+width];out=bg.copy()
 f=min(fade,len(loop)//4)
 while len(out)<n:
  if f:
   w=np.linspace(0,1,f)[:,None];out[-f:]=out[-f:]*(1-w)+loop[:f]*w
  out=np.concatenate([out,loop[f:]])
 out=out[:n]
 if fade:
  w=np.linspace(0,1,fade)[:,None];out[-fade:]=out[-fade:]*(1-w)+bg[-fade:]*w
 return out,True

def replace_audio(source,vocals,generated,gen_sr,start,end,keep_background=True,fixed_slot=False):
 i,j=round(start*SR),round(end*SR)
 voice=resample_poly(generated,SR,gen_sr)
 if fixed_slot:
  from .timing import fit_slot
  # Resampling may round up by one sample; this is padded trailing silence.
  voice=fit_slot(voice,SR,(j-i)/SR)
 reference=vocals[i:j];gain=np.clip(rms(reference)/max(rms(voice),1e-8),.2,5)
 voice=voice*gain
 power=np.sqrt(np.mean(reference*reference,axis=0));pan=power/max(np.sqrt(np.mean(power*power)),1e-9)
 if not np.any(pan):pan=np.ones(2)
 replacement=voice[:,None]*pan
 residual=source[i:j]-vocals[i:j]
 bg,extended=background_for_length(residual,len(voice),SR)
 if keep_background:replacement+=bg
 peak=float(np.max(np.abs(replacement)))
 limited=peak>.98
 if limited:replacement*=.98/peak
 output=np.concatenate([source[:i],replacement,source[j:]],axis=0)
 # Source before/after the replacement is byte-equivalent as decoded samples.
 return output,{'background_extended':bool(extended and keep_background),'gain_limited':limited,'shift_seconds':(len(voice)-(j-i))/SR,'replacement_start':start,'replacement_end':start+len(voice)/SR}
