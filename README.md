# CrisisLens

災情圖文分類與應變建議系統。上傳災害照片 → CLIP 分類災害類型 → RAG 產生應變建議 → 地理聚合與熱圖。

---

## 快速開始（組員 clone 後照做）

### 1. 取得程式碼

```powershell
git clone <repo-url>
cd CrisisLens
```

### 2. 建立虛擬環境並安裝套件

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1        # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

> 第一次執行 app 時，CLIP 會自動下載 **ViT-L/14** 權重（約 890MB），請耐心等候，之後會快取。

### 3. 設定 API 金鑰（選填）

```powershell
Copy-Item .env.example .env        # macOS/Linux: cp .env.example .env
```

編輯 `.env` 填入 `GEMINI_API_KEY`（[從 Google AI Studio 取得](https://aistudio.google.com/)）。
**不填也能跑**，RAG 會改用內建應變指引、不呼叫 LLM。

### 4. 啟動

```powershell
streamlit run app.py
```

瀏覽器開 http://localhost:8501 即可。資料庫 `crisislens.db` 會在首次啟動自動建立。

---

## CLIP 分類模式

首頁左側「CLIP Prompt Set」可切換分類方式：

| 選項 | 說明 | 需要 |
|------|------|------|
| **E｜Linear Probe（MEDIC訓練）** | 在 MEDIC 資料集上訓練的分類器，**準確率最高（~0.85）**，含溫度校準 | `models/clip_linear_head.pth`（已包含在 repo） |
| **D｜多描述投票版** | Gemini 生成的多 prompt zero-shot | `utils/prompts_generated.json`（已包含） |
| A / B / C | 基礎單 prompt zero-shot（對照用） | 無 |

> `clip_linear_head.pth`（20KB）已隨 repo 提供，clone 下來 **E 選項即可直接用**，不需自行訓練。

---

## （進階）重新訓練 Linear Probe

只有想調整模型時才需要。流程分兩段：

### A. 抽特徵（需 GPU，用 Colab 跑一次）

開 `notebooks/clip_linear_probe_medic.ipynb`（Colab → T4 GPU），它會用 HF streaming 讀取 MEDIC、
抽出 CLIP 特徵存成 `feat_train/dev/test.npz`。

### B. 訓練分類器（本機 CPU，幾秒）

把上一步的 3 個 `.npz`（約 200MB）放到 `features/`，然後：

```powershell
python models/train_linear_probe.py --weighting sqrt --weight-decay 1e-4
```

會自動評估、做溫度校準、覆蓋 `models/clip_linear_head.pth`。重啟 streamlit 即生效。

> **特徵檔（`features/*.npz`）不在 repo 內**（209MB 過大）。需要的話向專案負責人索取 Drive 連結：
> `（在此貼上 Drive 分享連結）`

---

## 不會進 repo 的東西（已由 `.gitignore` 排除）

| 項目 | 原因 |
|------|------|
| `.env` | 含 API 金鑰，**切勿上傳** |
| `features/*.npz` | 209MB 特徵快取，放 Drive |
| `crisislens.db` | 本地測試資料，app 會自動重建 |
| `venv/`、`uploads/`、`outputs/*.png` | 環境 / 本地產物 |
| ResNet 大權重 `models/*.pth` | 檔案過大（`clip_linear_head.pth` 例外保留） |
