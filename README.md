# Google AI Studio (Gemini) TTS 語音合成工作台

使用 Google 官方 `google-genai` SDK 與 Google AI Studio API Key，調用 Gemini TTS 原生語音合成模型將輸入文字轉換為 **MP3** 音訊檔（Web 介面）或 WAV 音訊檔。

---

## Web 網頁介面特色

純前端的現代化靜態網頁 [index.html](file:///c:/AntiProject/TTS/index.html)：
- **安全密碼存取保護**：內建 AES-256-GCM 高強度加密，金鑰與密碼均不在前端原始碼中以明文顯示，防止金鑰外洩與濫用。
- **自動轉為 MP3 下載**：瀏覽器端整合高效 MP3 編碼模組，直接下載標準 `.mp3` 檔案。
- **語速選項**：支援 9 段語速調節（0.5x 最慢、0.65x 極慢、0.75x 較慢、0.9x 略慢、1.0x 標準預設、1.15x 略快、1.25x 較快、1.5x 極快、2.0x 最快）。
- **男女性別清楚分類**：語音下拉選單已依 👩 女性聲音 與 👨 男性聲音 完整分類與標註特點。

### 開啟方式一：一鍵啟動（推薦）
```bash
python run_web.py
```
> 會自動啟動本地伺服器並開啟瀏覽器。

### 開啟方式二：直接雙擊打開
在檔案總管中直接雙擊打開 [index.html](file:///c:/AntiProject/TTS/index.html) 亦可直接使用！

---

## 終端機 CLI 快速使用方法

### 1. 互動模式（直接執行，在終端機輸入文字）
```bash
python tts_app.py
```

### 2. 單行指令模式（直接傳入文字）
```bash
python tts_app.py "你好，這是使用 Google Gemini 語音模型產生的測試音訊。" -o output.wav
```

### 3. 從純文字檔案轉換
```bash
python tts_app.py -f input.txt -o story.wav
```

---

## 語音角色清單

執行以下指令可查看推薦聲音列表：
```bash
python tts_app.py --list-voices
```

- **👩 女性角色 (Female)**：
  - `Kore`：沉穩、堅定（預設推薦）
  - `Zephyr`：明亮、清晰
  - `Aoede`：輕鬆、微風感
  - `Leda`：年輕、活力
  - `Despina`：柔和、流暢
- **👨 男性角色 (Male)**：
  - `Puck`：輕快、活潑
  - `Charon`：知性、解說型
  - `Fenrir`：熱情、興奮
  - `Orus`：沉穩、剛毅
  - `Sulafat`：溫暖、親和
