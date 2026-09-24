"""Run a real local Qwen generation on an explicitly provided reference.

Example: python -m scripts.smoke_qwen reference.wav --ref-text '原聲台詞' --text '你好。'
Outputs stay under ignored data/smoke; nothing is uploaded.
"""
import argparse
import json
import time
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from backend.engine import LocalEngine
from backend.audio import SR
from backend.store import DATA

def main():
    p=argparse.ArgumentParser();p.add_argument('reference',type=Path);p.add_argument('--ref-text',required=True);p.add_argument('--text',default='你好。');p.add_argument('--seed',type=int,default=20260924)
    args=p.parse_args();x,sr=sf.read(args.reference,always_2d=True,dtype='float32');x=x.mean(axis=1)
    if sr!=SR:x=resample_poly(x,SR,sr)
    engine=LocalEngine();began=time.monotonic()
    y,rate=engine.generate(x,args.ref_text,args.text,args.seed)
    if not np.isfinite(y).all() or not len(y):raise RuntimeError('Generated audio invalid')
    out=DATA/'smoke';out.mkdir(parents=True,exist_ok=True)
    sf.write(out/'qwen-smoke.wav',y/max(1,float(np.max(abs(y)))/.98),rate,subtype='PCM_24')
    report={'model':engine.name,'device':engine.device,'seed':args.seed,'duration':len(y)/rate,'elapsed_seconds':time.monotonic()-began,'sample_rate':rate,'peak':float(np.max(abs(y))),'audio':str(out/'qwen-smoke.wav')}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
