import os,tempfile,io,time,json
os.environ['AUDIO_LAB_DATA']=tempfile.mkdtemp(prefix='audio-lab-test-')
os.environ['AUDIO_LAB_SEED_PRESETS']='0'
import numpy as np
import soundfile as sf
import pytest
from fastapi.testclient import TestClient
from backend import main,store

class FakeEngine:
 name='test-engine';version='1';steps=48
 def readiness(self):return {'test':True}
 def transcribe(self,path):return '我知道我不是一個好父親。'
 def separate(self,path):return sf.read(path,dtype='float32',always_2d=True)[0]*.7
 def generate(self,reference,ref_text,target,seed,target_seconds=None):
  if target_seconds is not None:
   from backend.timing import fit_slot
   return fit_slot(np.sin(np.arange(12000)*2*np.pi*200/24000)*.05,24000,target_seconds),24000
  return np.sin(np.arange(36000)*2*np.pi*200/24000)*.05,24000

def wav(silent=False,duration=4):
 b=io.BytesIO();sf.write(b,np.zeros(int(44100*duration)) if silent else np.sin(np.arange(int(44100*duration))*2*np.pi*150/44100)*.1,44100,format='WAV');return b.getvalue()

@pytest.fixture(scope='module')
def client():
 main.ENGINE=FakeEngine()
 with TestClient(main.app) as c:yield c

def test_upload_validation_and_local_origin(client):
 assert client.post('/api/assets',files={'file':('bad.txt',b'no')}).status_code==400
 assert client.post('/api/assets',files={'file':('empty.wav',b'')}).status_code==400
 assert client.post('/api/assets',files={'file':('silent.wav',wav(True))}).status_code==400
 assert client.post('/api/assets',files={'file':('long.wav',wav(duration=181))}).status_code==400
 assert client.post('/api/assets',files={'file':('valid.wav',wav())},headers={'origin':'https://evil.example'}).status_code==403
 assert client.get('/api/health',headers={'host':'evil.example'}).status_code==403

def test_upload_transcribe_generate_retry_rating_export(client):
 r=client.post('/api/assets',files={'file':('聲音.wav',wav())});assert r.status_code==200,r.text
 asset=r.json();s={'asset_id':asset['id'],'mode':'replace','ref_start':0,'ref_end':2,'target_start':1,'target_end':2,'ref_text':'原本台詞','target_text':'我知道我不是一個好父親。','single_speaker':True,'denoise':True,'keep_background':True}
 c=client.post('/api/cases',json={'name':'=test','settings':s}).json()
 def wait(id):
  for _ in range(100):
   j=client.get('/api/jobs/'+id).json()
   if j['status'] in ('completed','failed'):return j
   time.sleep(.03)
  raise AssertionError('job did not finish')
 j=client.post('/api/jobs',json={'case_id':c['id'],'kind':'transcribe','settings':s}).json()
 assert wait(j['id'])['transcript']
 all_ids=[]
 for attempt in range(2):
  r=client.post('/api/jobs',json={'case_id':c['id'],'kind':'generate','settings':s});assert r.status_code==200,r.text
  j=wait(r.json()['id']);assert j['status']=='completed',j
  all_ids+=j['candidate_ids']
 assert len(set(all_ids))==4
 candidates=client.get('/api/candidates?case_id='+c['id']).json();assert len(candidates)==4
 cid=all_ids[0]
 for kind in ('voice','mixed','context','no_background'):
  f=client.get(f'/api/candidates/{cid}/{kind}');assert f.status_code==200
  y,sr=sf.read(io.BytesIO(f.content));assert np.isfinite(y).all()
 original=client.get('/api/assets/'+asset['id']+'/audio');assert original.status_code==200
 rated=client.put('/api/candidates/'+cid+'/rating',json={'scores':{'quality':5},'verdict':'usable','notes':'=danger','failure_reason':''});assert rated.status_code==200
 assert client.put('/api/candidates/'+cid+'/rating',json={'scores':{'quality':6},'verdict':'usable'}).status_code==422
 text=client.get('/api/export.csv').text;assert "'=test" in text and "'=danger" in text
 assert '1.5' in text
 # Settings changes never alter a previous candidate's snapshot.
 s['target_text']='不同內容';client.put('/api/cases/'+c['id'],json={'name':'updated','settings':s})
 assert store.get('candidates',cid)['settings']['target_text']=='我知道我不是一個好父親。'
 s['single_speaker']=False
 assert client.post('/api/jobs',json={'case_id':c['id'],'kind':'generate','settings':s}).status_code==400
 # Interrupted records survive and are marked on restart.
 interrupted=store.put('jobs',{'case_id':c['id'],'kind':'generate','status':'running','stage':'生成中','settings':s})
 store.init();assert store.get('jobs',interrupted['id'])['status']=='interrupted'
 assert store.get('candidates',cid)['rating']['verdict']=='usable'


def test_fixed_slot_download_is_not_full_uploaded_file(client):
 a=client.post('/api/assets',files={'file':('four-seconds.wav',wav())}).json()
 s={'asset_id':a['id'],'mode':'replace','ref_start':0,'ref_end':4,'target_start':1,'target_end':3,'ref_text':'四秒鐘的原始參考。','target_text':'你好。','single_speaker':True,'timing':'fit'}
 case=client.post('/api/cases',json={'name':'兩秒替換','settings':s}).json()
 submitted=client.post('/api/jobs',json={'case_id':case['id'],'settings':s}).json()
 for _ in range(100):
  job=client.get('/api/jobs/'+submitted['id']).json()
  if job['status'] in ('completed','failed'):break
  time.sleep(.03)
 assert job['status']=='completed',job
 source,_=sf.read(io.BytesIO(client.get('/api/assets/'+a['id']+'/audio').content))
 for cid in job['candidate_ids']:
  segment,rate=sf.read(io.BytesIO(client.get('/api/candidates/'+cid+'/replacement').content))
  mixed,_=sf.read(io.BytesIO(client.get('/api/candidates/'+cid+'/mixed').content))
  assert len(segment)==2*rate and len(mixed)==len(source)
  np.testing.assert_array_equal(mixed[:44100],source[:44100])
  np.testing.assert_array_equal(mixed[132300:],source[132300:])
  np.testing.assert_array_equal(segment,mixed[44100:132300])
