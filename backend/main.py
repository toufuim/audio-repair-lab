import csv, io, json, logging, os, queue, secrets, shutil, subprocess, threading, time, uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Annotated
import numpy as np
import soundfile as sf
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import store
from .config import readiness, MODEL_ID, MODEL_REVISIONS
from .audio import decode,validate_ranges,replace_audio,MAX_BYTES,EXTENSIONS,SR,rms
log=logging.getLogger('audio-lab')
Q=queue.Queue();ENGINE=None

def engine():
 global ENGINE
 if ENGINE is None:
  from .engine import LocalEngine
  ENGINE=LocalEngine()
 return ENGINE

def asset_path(id):return store.DATA/'assets'/id/'source.wav'
def found(table,id):
 try:return store.get(table,id)
 except KeyError:raise HTTPException(404,'找不到指定資料。')

def import_asset(source,name=None):
 id=uuid.uuid4().hex;folder=store.DATA/'assets'/id;folder.mkdir(parents=True)
 try:meta=decode(source,folder/'source.wav')
 except Exception:shutil.rmtree(folder);raise
 return store.put('assets',{'id':id,'name':name or source.name,**meta})

class Settings(BaseModel):
 asset_id:str
 mode:Literal['generate','replace']='replace'
 ref_start:float=0
 ref_end:float=3
 target_start:float=0
 target_end:float=3
 ref_text:str=Field(default='',max_length=1000)
 target_text:str=Field(default='',max_length=120)
 denoise:bool=True
 keep_background:bool=True
 single_speaker:bool=False
 timing:Literal['natural','fit']='natural'

class CaseInput(BaseModel):
 name:str=Field(min_length=1,max_length=100)
 settings:Settings

class Submit(BaseModel):
 case_id:str
 kind:Literal['generate','transcribe']='generate'
 settings:Settings

class Rating(BaseModel):
 scores:dict[str,Annotated[int,Field(ge=1,le=5)]]=Field(default_factory=dict)
 verdict:Literal['usable','revise','unusable']
 notes:str=Field(default='',max_length=2000)
 failure_reason:str=Field(default='',max_length=500)

def run_job(job):
 id=job['id'];s=job['settings'];start=time.time()
 def stage(t):store.update('jobs',id,status='running',stage=t)
 try:
  stage('準備音訊');folder=store.DATA/'jobs'/id;folder.mkdir(parents=True,exist_ok=True)
  source=asset_path(s['asset_id']);x,_=sf.read(source,dtype='float32',always_2d=True)
  a,b=round(s['ref_start']*SR),round(s['ref_end']*SR)
  if job['kind']=='transcribe':
   ref=folder/'reference.wav';sf.write(ref,x[a:b],SR)
   stage('辨識參考台詞');text=engine().transcribe(ref)
   store.update('jobs',id,status='completed',stage='轉錄完成',transcript=text,elapsed_seconds=time.time()-start);return
  stage('分離人聲' if s['denoise'] or s['mode']=='replace' else '擷取音色參考')
  vocals=engine().separate(source) if s['denoise'] or s['mode']=='replace' else x
  ref=(vocals if s['denoise'] else x)[a:b].mean(axis=1)
  if rms(ref)<1e-5:raise ValueError('選取片段沒有足夠人聲，請改選參考範圍。')
  sf.write(folder/'reference.wav',ref,SR,subtype='PCM_24')
  results=[]
  for index in range(2):
   began=time.time();seed=secrets.randbelow(2**31-1)
   stage(f'生成版本 {index+1}／2（本機運算可能需數分鐘）')
   slot=s['target_end']-s['target_start'] if s['mode']=='replace' and s.get('timing')=='fit' else None
   if slot is None:voice,sr=engine().generate(ref,s['ref_text'],s['target_text'],seed)
   else:voice,sr=engine().generate(ref,s['ref_text'],s['target_text'],seed,target_seconds=slot)
   peak=np.max(np.abs(voice))
   if peak>.98:voice=voice*(.98/peak)
   cid=uuid.uuid4().hex;out=store.DATA/'candidates'/cid;out.mkdir(parents=True)
   sf.write(out/'voice.wav',voice,sr,subtype='PCM_24')
   details={'background_extended':False,'shift_seconds':0.,'gain_limited':bool(peak>.98)}
   if s['mode']=='replace':
    stage(f'混合背景聲 {index+1}／2')
    mixed,details=replace_audio(x,vocals,voice,sr,s['target_start'],s['target_end'],s['keep_background'],fixed_slot=slot is not None)
    muted,_=replace_audio(x,vocals,voice,sr,s['target_start'],s['target_end'],False,fixed_slot=slot is not None)
    sf.write(out/'replacement.wav',mixed[round(s['target_start']*SR):round(s['target_start']*SR)+len(mixed)-(len(x)-round(s['target_end']*SR)+round(s['target_start']*SR))],SR,subtype='PCM_24');sf.write(out/'mixed.wav',mixed,SR,subtype='PCM_24');sf.write(out/'no_background.wav',muted,SR,subtype='PCM_24')
    # A short comparison snippet keeps the surrounding context.
    st=max(0,round((s['target_start']-.7)*SR));en=min(len(mixed),round((details['replacement_end']+.7)*SR))
    sf.write(out/'context.wav',mixed[st:en],SR,subtype='PCM_24')
   stage(f'檢查台詞 {index+1}／2')
   check_error=''
   try:text=engine().transcribe(out/'voice.wav')
   except Exception as exc:log.exception('ASR validation failed');text='';check_error='輔助辨識失敗，請直接試聽確認。'
   result=store.put('candidates',{'id':cid,'case_id':job['case_id'],'job_id':id,'label':chr(65+index),'seed':seed,'model':engine().name,'model_version':engine().version,'steps':engine().steps,'generation_settings':{**getattr(engine(),'generation_settings',{}),'text_normalization':getattr(engine(),'text_normalization','none')},'model_revision':MODEL_REVISIONS.get(engine().name),'settings':s,'asr_text':text,'check_error':check_error,'duration':len(voice)/sr,'replacement_duration':details.get('replacement_end',0)-s['target_start'] if s['mode']=='replace' else None,'elapsed_seconds':time.time()-began,'rating':None,**details})
   results.append(result['id']);store.update('jobs',id,candidate_ids=results)
  store.update('jobs',id,status='completed',stage='完成，請試聽評分',elapsed_seconds=time.time()-start)
 except Exception as exc:
  log.exception('Job failed %s',id)
  message=str(exc) if isinstance(exc,ValueError) else '處理失敗。已保留完成的版本；請重試，詳細原因可查看本機日誌。'
  store.update('jobs',id,status='failed',stage='處理失敗',error=message,elapsed_seconds=time.time()-start)

def worker():
 while True:
  id=Q.get()
  try:run_job(store.get('jobs',id))
  except Exception:log.exception('Worker failed')
  finally:Q.task_done()

@asynccontextmanager
async def lifespan(app):
 store.init();
 threading.Thread(target=worker,daemon=True).start();yield

app=FastAPI(title='語音修補測試室',lifespan=lifespan)

@app.middleware('http')
async def local_only(request,call_next):
 host=request.headers.get('host','').split(':')[0]
 origin=request.headers.get('origin')
 if host not in ('127.0.0.1','localhost','testserver'):
  return Response('只接受本機存取',status_code=403)
 if request.method not in ('GET','HEAD','OPTIONS') and origin and origin not in ('http://127.0.0.1:8765','http://localhost:8765','http://127.0.0.1:5173','http://localhost:5173'):
  return Response('不允許此來源',status_code=403)
 return await call_next(request)

@app.get('/api/health')
def health():
 return {'status':'ok','device':os.environ.get('AUDIO_LAB_DEVICE','auto'),'models':readiness(),'model':MODEL_ID,'license':'程式 MIT / Qwen 模型 Apache-2.0','queue_size':Q.qsize()}

@app.get('/api/assets')
def assets():return store.all_rows('assets')

@app.post('/api/assets')
def upload(file:UploadFile=File(...)):
 ext=Path(file.filename or '').suffix.lower()
 if ext not in EXTENSIONS:raise HTTPException(400,'支援 WAV、MP3、M4A、MP4、MOV。')
 temp=store.DATA/'uploads';temp.mkdir(exist_ok=True);path=temp/(uuid.uuid4().hex+ext)
 try:
  total=0
  with path.open('wb') as f:
   while block:=file.file.read(1024*1024):
    total+=len(block)
    if total>MAX_BYTES:raise HTTPException(413,'檔案不可超過 250 MB。')
    f.write(block)
  if total==0:raise HTTPException(400,'檔案是空的。')
  return import_asset(path,Path(file.filename or '素材').name)
 except ValueError as e:raise HTTPException(400,str(e))
 finally:path.unlink(missing_ok=True);file.file.close()

@app.get('/api/assets/{id}/audio')
def asset_audio(id:str):found('assets',id);return FileResponse(asset_path(id),media_type='audio/wav')

@app.get('/api/cases')
def cases():return store.all_rows('cases')

@app.post('/api/cases')
def create_case(body:CaseInput):
 a=found('assets',body.settings.asset_id)
 try:validate_ranges(body.settings.model_dump(),a['duration'])
 except ValueError as e:raise HTTPException(400,str(e))
 return store.put('cases',body.model_dump())

@app.put('/api/cases/{id}')
def save_case(id:str,body:CaseInput):
 found('cases',id);a=found('assets',body.settings.asset_id)
 try:validate_ranges(body.settings.model_dump(),a['duration'])
 except ValueError as e:raise HTTPException(400,str(e))
 return store.update('cases',id,**body.model_dump())

@app.post('/api/jobs')
def submit(body:Submit):
 found('cases',body.case_id);a=found('assets',body.settings.asset_id);s=body.settings.model_dump()
 try:validate_ranges(s,a['duration'])
 except ValueError as e:raise HTTPException(400,str(e))
 if body.kind=='generate':
  if not s['single_speaker']:raise HTTPException(400,'請先確認參考片段只有同一位說話者。')
  if not s['ref_text'].strip() or not s['target_text'].strip():raise HTTPException(400,'請填寫原聲實際台詞與新台詞。')
  if not all(engine().readiness().values()):raise HTTPException(503,'模型檔案不齊全，請查看安裝說明。')
  duplicate=next((j for j in store.all_rows('jobs') if j['case_id']==body.case_id and j['kind']=='generate' and j['status'] in ('queued','running')),None)
  if duplicate:raise HTTPException(409,'這個案例已有處理中的工作，完成後再重新生成。')
 ref,_=sf.read(asset_path(a['id']),start=round(s['ref_start']*SR),stop=round(s['ref_end']*SR),always_2d=True)
 if rms(ref)<1e-6:raise HTTPException(400,'音色參考範圍沒有可用聲音。')
 job=store.put('jobs',{'case_id':body.case_id,'kind':body.kind,'settings':s,'status':'queued','stage':'等待處理','candidate_ids':[],'error':''})
 Q.put(job['id']);return job

@app.get('/api/jobs')
def jobs(case_id:str|None=None):return [j for j in store.all_rows('jobs') if not case_id or j['case_id']==case_id]
@app.get('/api/jobs/{id}')
def job(id:str):return found('jobs',id)
@app.get('/api/candidates')
def candidates(case_id:str|None=None):return [r for r in store.all_rows('candidates') if not case_id or r['case_id']==case_id]
@app.get('/api/candidates/{id}/{kind}')
def media(id:str,kind:Literal['voice','mixed','no_background','context','replacement'],download:bool=False):
 result=found('candidates',id);path=store.DATA/'candidates'/id/(kind+'.wav')
 if not path.is_file():raise HTTPException(404,'此版本沒有這種音檔。')
 labels={'replacement':'替換片段','voice':'純人聲','mixed':'完整修正版','no_background':'替換處無背景','context':'前後文試聽'}
 return FileResponse(path,media_type='audio/wav',filename=f"{result['label']}_{labels[kind]}.wav" if download else None)
@app.put('/api/candidates/{id}/rating')
def rating(id:str,body:Rating):
 found('candidates',id)
 if set(body.scores)-{'pronunciation','similarity','prosody','quality','background'}:raise HTTPException(400,'未知評分欄位。')
 return store.update('candidates',id,rating=body.model_dump())

@app.get('/api/export.csv')
def export():
 out=io.StringIO();w=csv.writer(out);columns=['案例','版本','生成時間','模式','原台詞','目標台詞','模型','模型版本','步數','種子','參考起點','參考終點','替換起點','替換終點','背景','去背景參考','輸出秒數','處理秒數','整件秒數','重試次數','辨識','發音','音色','語氣','音質','背景銜接','判定','備註','失敗原因','背景補接','長度模式','生成參數']
 w.writerow(columns)
 def safe(v):
  text=str(v if v is not None else '')
  return "'"+text if text.startswith(('=','+','-','@','\t','\r')) else text
 for r in store.all_rows('candidates'):
  c=found('cases',r['case_id']);j=found('jobs',r['job_id']);s=r['settings'];rating=r.get('rating') or {};scores=rating.get('scores',{})
  attempts=[x for x in store.all_rows('jobs') if x['case_id']==c['id'] and x['kind']=='generate' and x['created']<j['created']]
  row=[c['name'],r['label'],time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(r['created'])),s['mode'],s['ref_text'],s['target_text'],r['model'],r['model_version'],r['steps'],r['seed'],s['ref_start'],s['ref_end'],s['target_start'],s['target_end'],s['keep_background'],s['denoise'],round(r['duration'],3),round(r['elapsed_seconds'],2),round(j.get('elapsed_seconds',0),2),len(attempts),r['asr_text'],*[scores.get(k,'') for k in ('pronunciation','similarity','prosody','quality','background')],rating.get('verdict',''),rating.get('notes',''),rating.get('failure_reason',''),r['background_extended'],s.get('timing','natural'),json.dumps(r.get('generation_settings',{}),ensure_ascii=False)]
  w.writerow([safe(x) for x in row])
 return Response('\ufeff'+out.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="audio-tests.csv"'})

DIST=store.ROOT/'frontend/dist'
if DIST.is_dir():app.mount('/',StaticFiles(directory=DIST,html=True),name='frontend')
