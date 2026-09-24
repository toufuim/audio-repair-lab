"""Explicit, resumable model setup. The web server never downloads models."""
import hashlib
import json
import shutil
import ssl
import certifi
import urllib.request
from pathlib import Path
from huggingface_hub import snapshot_download
from backend.config import QWEN, WHISPER, DEMUCS, MODEL_ID, MODEL_REVISIONS, QWEN_FILES, WHISPER_FILES, readiness

DEMUCS_SHA='8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4'

def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    print('下載 Qwen 模型（Apache-2.0），模型留在本機。首次下載需數 GB 空間。',flush=True)
    snapshot_download(MODEL_ID,revision=MODEL_REVISIONS[MODEL_ID],local_dir=QWEN,allow_patterns=[*QWEN_FILES,'README.md','LICENSE*'])
    print('下載辨識模型…',flush=True)
    snapshot_download('Systran/faster-whisper-small',revision='536b0662742c02347bc0e980a01041f333bce120',local_dir=WHISPER,allow_patterns=[*WHISPER_FILES,'README.md','LICENSE*'])
    if not DEMUCS.is_file() or sha256(DEMUCS)!=DEMUCS_SHA:
        print('下載人聲分離模型…',flush=True);DEMUCS.parent.mkdir(parents=True,exist_ok=True)
        temp=DEMUCS.with_suffix('.download')
        with urllib.request.urlopen('https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/955717e8-8726e21a.th',timeout=90,context=ssl.create_default_context(cafile=certifi.where())) as src,temp.open('wb') as dst:shutil.copyfileobj(src,dst)
        if sha256(temp)!=DEMUCS_SHA:raise RuntimeError('Demucs 校驗失敗，請重試。')
        temp.replace(DEMUCS)
    if not all(readiness().values()):raise RuntimeError('模型檔案不完整，請重新下載。')
    manifest={'repo':MODEL_ID,'revision':MODEL_REVISIONS[MODEL_ID],'files':{p:sha256(QWEN/p) for p in QWEN_FILES}}
    (QWEN/'audio-lab-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('模型準備完成。',flush=True)

if __name__=='__main__':main()
