# 聲音修補室 · Audio Repair Lab

用 **Qwen3-TTS** 參考音色生成新台詞，或選取一句話、替換後接回原音。繁體中文介面，安裝在自己的電腦，透過本機瀏覽器操作。

> 目前為早期測試版。GitHub 提供原始碼與安裝方式，不提供線上 GPU 推論；Windows/Linux 安裝流程尚需更多實機驗證。不要把本機服務直接公開到網際網路。

## 功能

- WAV、MP3、M4A、MP4、MOV；影片只抽取聲音，輸出 WAV。
- 波形拖曳／秒數選取，音色參考與替換區間分開設定。
- 參考台詞自動辨識與人工修正，新台詞另行輸入。
- 每次生成兩版，保留既有版本、試聽、下載與五項評分。
- 保留背景音，下載單獨替換片段或完整修正版。
- 案例與評分儲存在本機 SQLite；CSV 匯出包含模型、種子及生成參數。
- 單一工作佇列；不做嘴型同步、影片匯出、會員或付款。

## 安裝

建議 16 GB 以上記憶體並預留至少 20 GB 磁碟空間（CUDA 套件可能需要更多）。CPU 可用但生成可能很慢；NVIDIA CUDA 可加速，需安裝適用的 PyTorch。Apple Silicon 此版先使用 CPU，不宣稱已驗證 MPS。macOS 的預編譯 PyAV 套件要求 14 以上；Windows 以 10/11 x64 為測試目標。

先依 [uv 官方說明](https://docs.astral.sh/uv/getting-started/installation/) 安裝 uv，再下載或 clone 本儲存庫。安裝器會建立 Python 3.12 環境，安裝套件並下載 Qwen、Whisper、Demucs 模型。首次需連網；模型準備好後，推論使用本機檔案，不將音訊上傳到服務商。

### macOS / Linux

```sh
git clone https://github.com/toufuim/audio-repair-lab.git
cd audio-repair-lab
bash install.sh
bash start.sh
```

Mac 也可雙擊 `啟動語音修補室.command`。終端機保持開啟；Control-C 停止。安裝失敗可重跑 `install.sh`。

### Windows PowerShell

```powershell
git clone https://github.com/toufuim/audio-repair-lab.git
cd audio-repair-lab
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
.\start.cmd
```

PowerShell 的 Bypass 只用在這次安裝程序，不更動系統永久執行政策。企業裝置若限制執行腳本，請依管理政策處理。

啟動後開啟 **http://127.0.0.1:8765/**。若連接埠被其他版本占用，先關閉舊服務。前端建置結果隨原始碼提供，一般使用者不需要 Node.js。

### 手動安裝

使用 Python 3.12 建立虛擬環境後：

```sh
python -m pip install -r requirements.txt
python -m scripts.download_models
python -m scripts.run
```

模型下載是明確的安裝步驟；網頁不會在按下生成時偷偷下載。檔案較大，中斷後重新執行 `python -m scripts.download_models`。

## 模型與時間控制

預設是支援音色複製的 `Qwen/Qwen3-TTS-12Hz-0.6B-Base`。可在下載和啟動兩個步驟都設定 `AUDIO_LAB_QWEN_MODEL=Qwen/Qwen3-TTS-12Hz-1.7B-Base` 改用較大版本。CustomVoice／VoiceDesign 不是本工具採用的複製介面。模型使用官方 qwen-tts 套件，中文語言設定。介面與案例保留繁體原文；推論前以 OpenCC 將參考台詞和新台詞轉為簡體，降低部分中文字形造成的錯音。這不保證台灣口音或每個聲調都正確，仍須試聽。

Qwen Base 目前這個整合沒有精確秒數控制：

- **保留選取長度**：自然生成後，短句補尾端靜音。新語音超過範圍就提示修改，不截斷、變調或時間伸縮。
- **自然長度**：使用新句實際長度，後面的原音整段平移；下載完整修正版可保留後續內容。

音色參考長度不會附加到輸出新句。背景使用 Demucs 分離後的殘餘層，必要時補接；動態音效、殘留人聲或背景接縫仍可能不自然。

限制：單檔 250 MB／三分鐘，新台詞 120 字，參考 1～12 秒；建議至少三秒且只有同一位說話者。辨識結果只作輔助，不能證明音質或發音正確。

## 本機資料與設定

- `data/`：使用者音訊、案例、版本、SQLite、快取與模型，已排除 Git。
- `AUDIO_LAB_DATA`：覆寫資料目錄。
- `AUDIO_LAB_MODELS`：模型根目錄。
- `AUDIO_LAB_QWEN_PATH`、`AUDIO_LAB_WHISPER`：重用已下載的模型資料夾。
- `AUDIO_LAB_DEVICE`：`auto`（有 CUDA 就使用，否則 CPU）、`cpu`、`cuda`。
- `AUDIO_LAB_THREADS`：CPU 執行緒，預設 4。
- `AUDIO_LAB_ENV`：安裝腳本使用的虛擬環境目錄。

`.env.example` 是設定示例，不會自動載入；請在終端機 export／設定環境變數。不要把私有音檔、權重、存取金鑰或 `data/` commit 到 Git。範例測試使用合成波形，不包含真實人物音檔。

## 開發與測試

```sh
npm --prefix frontend ci
npm --prefix frontend run build
npm --prefix frontend test
python -m pip install -r requirements-test.txt
python -m pytest -q
```

[CI 設定範例](docs/ci.example.yml)使用輕量後端依賴和替代模型（此範例尚未啟用為 GitHub Actions），驗證上傳、時間軸、API、下載、評分與資料保留；它不代表模型自然度已驗收。完整 Qwen 環境另有 adapter contract tests。真實模型試聽結果與平台限制見 [VALIDATION.md](VALIDATION.md)。

架構：React/TypeScript/Vite → FastAPI → 單一工作佇列 → Qwen3-TTS／faster-whisper／Demucs → WAV + SQLite。PyAV 解碼，不要求另外安裝 FFmpeg 命令列工具。API 文件在本機 `/docs`。

## 授權與貢獻

本專案程式碼採 [MIT](LICENSE)。Qwen Base 模型採 Apache-2.0；其他元件依各自授權，詳見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。請只使用具備權利的聲音與素材。

歡迎 issue／PR；回報問題請提供作業系統、CPU/GPU、套件版本、操作步驟與已去識別化的錯誤訊息。未取得同意時，請勿在公開 issue 上傳別人的聲音。
