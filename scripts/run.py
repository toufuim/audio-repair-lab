"""Start the loopback-only web service and open the local UI."""
import argparse
import threading
import socket
import time
import urllib.request
import webbrowser
from pathlib import Path
import uvicorn


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    from backend.store import ROOT
    if not (ROOT/'frontend/dist/index.html').exists():
        raise SystemExit('缺少網頁檔案，請執行 npm --prefix frontend ci && npm --prefix frontend run build')
    with socket.socket() as probe:
        probe.settimeout(1)
        if probe.connect_ex(('127.0.0.1',8765))==0:
            raise SystemExit('8765 埠已被使用，請先關閉已開啟的語音修補室。')
    def open_when_ready():
        for _ in range(120):
            try:
                with urllib.request.urlopen('http://127.0.0.1:8765/api/health',timeout=2):pass
                webbrowser.open('http://127.0.0.1:8765/');return
            except OSError:time.sleep(1)
    if not args.no_browser:threading.Thread(target=open_when_ready,daemon=True).start()
    uvicorn.run('backend.main:app',host='127.0.0.1',port=8765,workers=1)

if __name__=='__main__':main()
