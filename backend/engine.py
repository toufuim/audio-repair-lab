import os
import random
from importlib.metadata import version
from opencc import OpenCC
import numpy as np
import soundfile as sf
from .store import DATA
from .config import MODELS, QWEN, WHISPER, MODEL_ID, MODEL_REVISIONS, readiness
from .audio import SR, trim_generated
from .timing import fit_slot

CACHE=DATA/'cache';CACHE.mkdir(parents=True,exist_ok=True)
os.environ['NUMBA_CACHE_DIR']=str(CACHE/'numba')
os.environ['MPLCONFIGDIR']=str(CACHE/'matplotlib')
os.environ['HF_HUB_OFFLINE']='1'
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
os.environ['GRADIO_ANALYTICS_ENABLED']='False'
os.environ['DO_NOT_TRACK']='1'
import torch

class LocalEngine:
 name=MODEL_ID
 steps=None
 text_normalization="opencc-t2s"
 generation_settings={'language':'Chinese','non_streaming_mode':True,'do_sample':True,'temperature':.9,'top_k':50,'top_p':1.,'repetition_penalty':1.05,'max_new_tokens':1024}
 def __init__(self):
  self.asr=None;self.separator=None;self.tts=None
  self.converter=OpenCC("t2s")
  self.version=version('qwen-tts')
  self.device=os.environ.get('AUDIO_LAB_DEVICE','auto')
  if self.device=='auto':self.device='cuda:0' if torch.cuda.is_available() else 'cpu'
  if self.device not in ('cpu','cuda','cuda:0'):raise ValueError('AUDIO_LAB_DEVICE 支援 auto、cpu 或 cuda。')
  if self.device.startswith('cuda') and not torch.cuda.is_available():raise ValueError('目前 PyTorch 無法使用 CUDA，請改用 cpu 或安裝對應的 CUDA 版 PyTorch。')
  torch.set_num_threads(max(1,int(os.environ.get('AUDIO_LAB_THREADS','4'))))
 def readiness(self):return readiness()
 def transcribe(self,path):
  if self.asr is None:
   from faster_whisper import WhisperModel
   self.asr=WhisperModel(str(WHISPER),device='cpu',compute_type='int8',cpu_threads=4,local_files_only=True)
  segments,_=self.asr.transcribe(str(path),language='zh',word_timestamps=True,beam_size=5,condition_on_previous_text=False)
  return ''.join(s.text for s in segments).strip()
 def separate(self,path):
  cached=path.parent/'vocals.wav'
  if cached.exists():return sf.read(cached,dtype='float32',always_2d=True)[0]
  from demucs.pretrained import get_model
  from demucs.apply import apply_model
  if self.separator is None:self.separator=get_model('955717e8',repo=MODELS/'demucs').eval().to('cpu')
  x,sr=sf.read(path,dtype='float32',always_2d=True);w=torch.from_numpy(x.T.copy())
  ref=w.mean(0);mean=ref.mean();std=ref.std()
  if std<1e-7:raise ValueError('素材音量太低，無法分離人聲。')
  with torch.inference_mode():
   stems=apply_model(self.separator,((w-mean)/std)[None],device='cpu',shifts=0,split=True,overlap=.25,num_workers=0)[0].cpu()*std+mean
  v=stems[self.separator.sources.index('vocals')].T.numpy()
  sf.write(cached,v,sr,subtype='FLOAT');return v
 def generate(self,reference,ref_text,target,seed,target_seconds=None):
  if not ref_text.strip():raise ValueError('請先填寫原聲實際台詞。')
  if self.tts is None:
   if not readiness()['Qwen 語音生成']:raise ValueError('缺少 Qwen 模型，請先執行 python -m scripts.download_models。')
   import onnxruntime
   onnxruntime.disable_telemetry_events()
   from qwen_tts import Qwen3TTSModel
   dtype=torch.float32 if self.device=='cpu' else (torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16)
   self.tts=Qwen3TTSModel.from_pretrained(str(QWEN),device_map=self.device,dtype=dtype,attn_implementation='eager',local_files_only=True)
  random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
  if torch.cuda.is_available():torch.cuda.manual_seed_all(seed)
  with torch.inference_mode():
   waves,sr=self.tts.generate_voice_clone(text=self.converter.convert(target),ref_audio=(np.asarray(reference,dtype=np.float32),SR),ref_text=self.converter.convert(ref_text),x_vector_only_mode=False,**self.generation_settings)
  if not waves:raise ValueError('Qwen 未產生音訊，請重試。')
  if len(waves[0])/sr>=self.generation_settings['max_new_tokens']/12-.5:
   raise ValueError('生成達到安全長度上限，可能尚未說完；請縮短台詞重試。')
  wave=trim_generated(waves[0],sr)
  if target_seconds is not None:wave=fit_slot(wave,sr,target_seconds)
  return wave,sr
