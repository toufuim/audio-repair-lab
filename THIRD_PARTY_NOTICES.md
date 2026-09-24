# 第三方元件與模型

本專案自己的程式碼採 MIT。第三方套件、模型與使用者素材不因此改變授權。

| 元件 | 上游 | 授權 |
|---|---|---|
| Qwen3-TTS 套件及官方 Base 模型 | https://github.com/QwenLM/Qwen3-TTS 、https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base | Apache-2.0 |
| faster-whisper、Whisper small 轉換權重 | https://github.com/SYSTRAN/faster-whisper 、https://huggingface.co/Systran/faster-whisper-small | MIT |
| Demucs | https://github.com/adefossez/demucs | MIT；模型與上游說明一併查閱 |
| PyAV | https://github.com/PyAV-Org/PyAV | BSD-3-Clause；wheel 內的 FFmpeg 元件另有上游授權 |
| PyTorch | https://github.com/pytorch/pytorch | BSD 類授權及第三方 notices |
| OpenCC Python Reimplemented | https://github.com/yichen0831/opencc-python | Apache-2.0 |
| React | https://github.com/facebook/react | MIT |
| FastAPI | https://github.com/fastapi/fastapi | MIT |

GitHub 儲存庫不包含模型權重。安裝指令從上游下載固定模型版本；模型識別碼、revision 與 SHA-256 記錄於本機 manifest。請保留上游授權與 notices，尤其是在重新分發模型或打包套件時。

此版本不使用 F5-TTS 權重。既有使用者資料若含舊版 F5 生成結果，應依該舊模型授權另行處理。

使用者需有權使用參考人聲與素材。請勿用於冒充他人、詐騙或未經授權的聲音複製；模型授權不會替你取得聲音、肖像或素材的權利。

## 隨附網頁建置檔的授權

### React / React DOM / Scheduler

```text
MIT License

Copyright (c) Meta Platforms, Inc. and affiliates.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Vite（modulepreload runtime）

```text
# Vite core license
Vite is released under the MIT license:

MIT License

Copyright (c) 2019-present, VoidZero Inc. and Vite contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
