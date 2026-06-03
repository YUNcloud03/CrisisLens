# 設計文件：自訓 CNN 升級 6 類（MEDIC）並合併 Huang 分支

- 日期：2026-06-03
- 目標分支：`feature/custom-cnn`（目前）＋ `Huang`
- 作者：ahd31（與 Claude 協作）
- 狀態：待使用者審閱

---

## 1. 背景與目標

CrisisLens 目前有兩條分支，從共同祖先 `0c41418` 分岔，代表兩條不同的模型路線：

- **`feature/custom-cnn`（目前分支）**：自訓 Custom CNN（4 類），含大量 docs/notebooks 與訓練報告。
- **`Huang`**：CLIP 重訓路線（ViT-L/14 + Linear Probe + 多描述投票），對齊 6 類 MEDIC 體系，含 prompt 生成工具與 `clip_linear_head.pth`。

兩分支的根本分歧在**災害類別體系**：目前分支 4 類、Huang 6 類。經決策，**統一採用 Huang 的 6 類體系（保留最多辨識能力）**，並進一步**將自訓 CNN 從 4 類重訓成 6 類，訓練資料改用 MEDIC（HuggingFace `QCRI/MEDIC`）**。

**目標：**
1. 重構自訓 CNN 的 Kaggle 訓練 notebook，改以 MEDIC 6 類資料集訓練。
2. 合併兩分支，使最終 app 同時具備「自訓 CNN（6 類）」與「CLIP A/B/C/D/E」兩條分類路線並存。
3. 統一類別體系為 6 類，消除 config 的語意矛盾。

## 2. 類別體系與 MEDIC 映射（正準順序）

6 類正準順序的**單一事實來源**為 `utils/config.py::CLASSES_EN`（與 Huang 的 notebook `MEDIC_MAP`、`train_linear_probe.py` 三處已驗證一致）：

| index | CLASSES_EN | CLASSES_ZH | ← MEDIC `disaster_types` 原始標籤 |
|---|---|---|---|
| 0 | Earthquake Damage | 地震或建築損壞 | `earthquake` |
| 1 | Flood | 淹水 | `flood` |
| 2 | Fire | 火災 | `fire` |
| 3 | Typhoon or Storm Damage | 颱風或強風災損 | `hurricane` |
| 4 | Landslide | 土石流或坍方 | `landslide` |
| 5 | Other or No Disaster | 其他或無明顯災害 | `not_disaster` + `other_disaster`（兩類合併） |

**鐵則：** notebook 與 classifier 一律以此 index 顯式指派標籤，**禁止依賴 `ImageFolder` 字母排序**（會與 config 對不上）。

## 3. 範圍

**納入（In scope）**
- 原地改寫 `train_custom_cnn_kaggle.ipynb` 成 MEDIC 6 類版（HF 直拉、v1～v4 ablation）。
- 合併 `Huang` 進 `feature/custom-cnn`，解 README 衝突，採 6 類 config。
- 以 6 類 Custom CNN 取代 ResNet 作為 `pages/1_Submit_Report.py` 的輔助交叉驗證模型；移除 ResNet 推論/訓練程式與 `train_resnet_kaggle.ipynb`；DB `resnet_*` 欄位沿用儲存 CNN 輔助結果（不改 schema）。

**不納入（Out of scope）**
- 實際在 Kaggle 執行訓練（由使用者執行，產出權重檔後回放）。
- CLIP linear probe（`clip_linear_head.pth`）的重訓——沿用 Huang 既有產物。
- 任何與 6 類整合無關的重構。

## 4. 交付物總覽

| 交付物 | 內容 |
|---|---|
| 合併分支 | `merge/huang-6class`（從 `feature/custom-cnn` 開，merge `Huang`） |
| 重構 notebook | `train_custom_cnn_kaggle.ipynb`（MEDIC 6 類、HF 直拉、v1～v4 ablation） |
| 合併程式 | `utils/config.py`（採 Huang 6 類，移除 `RESNET_WEIGHTS`）、`app.py`（CNN + CLIP A/B/C/D/E 並存）、`README.md`（融合版） |
| 零改碼 | `models/custom_cnn_classifier.py`（讀 json 動態決定類別數，不需改） |
| ResNet→CNN | Submit_Report 輔助模型由 ResNet 改為 Custom CNN；移除 `resnet_baseline.py`/`train_resnet.py`/`train_resnet_kaggle.ipynb`/`RESNET_WEIGHTS`；`resnet_*` DB 欄位沿用存 CNN 值 |
| 訓練產物（使用者於 Kaggle 產出後回放） | `models/custom_cnn.pth`（6 類 v1 權重）、`models/custom_cnn_classes.json`（6 類正準順序） |

## 5. Notebook 重構設計（核心）

採**資料管線方案 A**：`load_dataset("QCRI/MEDIC")` 非串流完整下載+快取，包成 map-style `torch Dataset`，取用時套 `MEDIC_MAP`(7→6) + CNN transforms。理由：CNN 需多 epoch 隨機抽樣、`WeightedRandomSampler`、ablation 重跑，且能直接用 MEDIC 原生 `train/dev/test` 切分（比舊版單資料夾 `random_split` 嚴謹）。

**Cell 流程**（沿用舊框架，改資料管線）：

1. 環境檢查 + GPU + `pip install datasets` + **提醒開 Kaggle internet**。
2. **Config**：硬編 6 類正準順序（`CLASSES_EN/ZH` + `MEDIC_MAP`，對齊 `utils/config.py`）；超參 `BATCH=32 / LR=1e-3 / Adam / SEED=42 / AMP=on`；`MAX_SAMPLES_PER_CLASS`（可選每類抽樣上限，控時間）；`ImageFile.LOAD_TRUNCATED_IMAGES=True`。
3. imports。
4. **載入 MEDIC**：`load_dataset("QCRI/MEDIC")` 取 `train/dev/test`，用 `disaster_types` 欄位，套 `MEDIC_MAP` 過濾無對應者（回 `None` 者 skip）。
5. 類別分布統計（凸顯不平衡，尤其 index 5「其他/無災害」會很大）。
6. **transforms（沿用舊版 224 + ImageNet normalize，不照抄 CLIP preprocess）**：
   - train：`RandomResizedCrop(224)` + HFlip + `ColorJitter(0.3)` + `RandomRotation(15)` + ToTensor + ImageNet normalize。
   - val/test：`Resize(256)` + `CenterCrop(224)` + ToTensor + ImageNet normalize。
7. **map-style `Dataset`**：PIL → 強制 RGB → transform；label 由 `MEDIC_MAP` 指派（顯式 index）。
8. DataLoader：train 用 `WeightedRandomSampler`（**sqrt-inverse 類別權重**，沿用 Huang 思路處理不平衡）；dev/test 不抽樣。`num_workers=CPU 核數`、`pin_memory=True`（加速資料載入，這是真正瓶頸）。
9. **v1 模型定義**：與 `models/custom_cnn_model.py::DisasterCNN_v1` **逐位元組一致**，`num_classes=6`（GAP 設計，換類別只動最後一層 `Linear(256,6)`）。
10. `train_one_model` + 訓練 v1：**用 MEDIC `dev` 當驗證**、best-by-dev-acc、AMP。
11. v2 No-BN / v3 Big-FC / v4 Shallow ablation 訓練（與舊版定義一致）。
12. 4 模型對比表（dev/test acc、params、訓練時間）。
13. 訓練曲線。
14. **v1 在 `test` 的混淆矩陣 + classification report**，特別檢視「地震 ↔ 土石流」混淆與「其他/無災害」主導效應。
15. **存檔**：
    - `custom_cnn.pth`：只存 v1 `best state_dict`（非 dict 包裝，與 classifier 載入方式一致）。
    - `custom_cnn_classes.json`：`classes`（6 類英文，正準順序）、`zh_labels`、`class_to_idx`、`num_classes=6`、`architecture="DisasterCNN_v1"`、`val_acc`，並記錄 `medic_map` 規則。
16. 下載連結。

**GPU 設定**：預設**單顆 T4 + AMP**（T4 有 Tensor Cores，AMP 下與 P100 相當；不必換 P100）。`nn.DataParallel` 吃滿 T4×2 列為**可選加速**（一個 config flag 控制）。

## 6. 合併整合設計

- **`utils/config.py`** → `git checkout Huang -- utils/config.py`，一次採 6 類全套（`ViT-L/14`、6 類 `CLASSES_EN/ZH`、`PROMPT_SETS`、`MULTI_PROMPT_SETS`）。順帶移除已無用的 `RESNET_WEIGHTS`。目前分支對 config 的唯一改動就是「改成 4 類」，採 6 類等於放棄該改動，無其他 CNN 設定需保留（CNN 設定在自己的 json）。
- **`app.py`** → 採 `git merge` 自動結果（line-level 乾淨）：CNN 走非 CLIP 分支（`cnn_classify`）、CLIP 走 A/B/C/D/E。複查並移除 ResNet 殘留字樣（選單/sidebar）。
- **`pages/1_Submit_Report.py`（ResNet→CNN）** → 輔助交叉驗證模型由 ResNet 換成 Custom CNN（`custom_cnn_classifier.classify`，回傳介面完全相同）。CLIP 仍是主判斷、決定 `disaster_type`；CNN 與 CLIP 中文標籤不一致時照常觸發 `model_agreement=0`／`need_review=1`。`full_report` 與 `model_run` 沿用 `resnet_model_version/resnet_disaster_type/resnet_confidence` 這三個 **dict key 寫入既有 DB 欄位（存 CNN 值，零 schema 變動）**。`utils/versions.py` 的 `RESNET_ENABLED`/`RESNET_MODEL_VERSION` 改名為 `CNN_AUX_ENABLED`/`CNN_MODEL_VERSION`，並修正 `CLIP_MODEL_VERSION` 為 ViT-L/14。顯示文字「ResNet50」改「自訓 CNN」。移除 `models/resnet_baseline.py`、`models/train_resnet.py` 與 config 的 `RESNET_WEIGHTS`。DB schema 的 `resnet_*` 欄位與 `seed.py` 的對應 key **保留不動**。
- **`models/custom_cnn_classifier.py`** → **零改碼**。它讀 `custom_cnn_classes.json` 動態決定 `num_classes`，放入 6 類 json 即自動支援；下游 app 用 `top_class_zh` 串接，6 類中文已涵蓋舊 4 類中文，不會錯位。
- **`README.md`** → add/add 衝突，以目前分支 591 行版為骨架，更正成 ViT-L/14 + 6 類 + 補 D/E 選項說明，併入 Huang 版獨有段落（`clip_linear_head.pth` 取得、`features/*.npz`、`.gitignore` 清單、組員快速上手）。
- **其餘 Huang 新增檔**（`train_linear_probe.py`、`notebooks/clip_linear_probe_medic.ipynb`、`tools/generate_prompts.py`、`utils/prompts_generated.json`、`clip_linear_head.pth`、`db/`、`rag/generator.py`、`pages/`、`.gitignore`、`.streamlit`）→ 加法式自動帶入，不衝突。

## 7. 執行順序（三階段）

- **Phase 1（程式合併，可立即做、不需 GPU）**：開分支 `merge/huang-6class` → `git merge Huang` → `git checkout Huang -- utils/config.py`（並移除 `RESNET_WEIGHTS`）→ 解 `README.md` 衝突 → 移除 `train_resnet_kaggle.ipynb` 與 ResNet 殘留 → app 複查 → 重構 `train_custom_cnn_kaggle.ipynb`。此時 app 可啟動，CNN 因 6 類權重未生成會顯示「未訓練（隨機）」。
- **Phase 2（使用者在 Kaggle 訓練）**：跑重構後 notebook → 產出 6 類 `custom_cnn.pth` + `custom_cnn_classes.json` → 放進 `models/`。
- **Phase 3（驗證 + 合回）**：本地測 5 條推論路徑 → 合回 `feature/custom-cnn`（或發 PR）。

## 8. 風險與緩解

| 風險 | 緩解 |
|---|---|
| **Kaggle 單 session ~12h 連續執行上限**（7 萬張 × 4 模型偏滿；估 6～10h） | `MAX_SAMPLES_PER_CLASS` 抽樣 + 控 epoch；先小樣本跑通再全量；單模型存點。 |
| Kaggle **每週 30h GPU 配額**（ablation 反覆重跑會吃額度） | 一次跑完 v1～v4；確認資料管線無誤再正式全量跑。 |
| 類別順序錯位 | 一律用 `MEDIC_MAP` 顯式指派 index，禁止靠字母序。 |
| normalize 不一致 | CNN 用 ImageNet normalize（非 CLIP preprocess）。 |
| 截斷/灰階影像報錯 | `ImageFile.LOAD_TRUNCATED_IMAGES=True` + 強制 `.convert("RGB")`。 |
| 嚴重類別不平衡（index 5 主導） | `WeightedRandomSampler`（sqrt-inverse）；評估看 per-class recall 而非僅 overall acc。 |
| 資料載入 CPU-bound（真正瓶頸） | `num_workers` 開滿、`pin_memory=True`、維持 AMP；換 GPU 無助於此。 |
| E 選項（Linear Probe）依賴 ViT-L/14 | config 已對齊 ViT-L/14；首次會下載大模型，確認資源。 |

## 9. 驗證計畫（Phase 3）

本地啟動 streamlit，逐一跑以下 5 條推論路徑，確認**不丟例外、中文標籤與信心顯示正常、H3 聚合與 RAG 正常**：

1. 自訓 CNN（6 類，確認回傳 6 類之一、`top_class_zh` 正確）
2. CLIP A/B/C（6 類 prompt）
3. CLIP D 多描述投票（6 類）
4. CLIP E Linear Probe（6 維 head，需 ViT-L/14 已下載）
5. 「比較」模式（CLIP + CNN 並排）

另檢查：移除 ResNet 後無 import / 設定殘留導致的啟動錯誤。

## 10. 未涵蓋 / 後續

- 自訓 CNN 6 類的實際準確率未知，需 Phase 2 訓練後以 test 混淆矩陣評估；若 index 5 主導或地震↔土石流嚴重混淆，可能需調整抽樣策略或增 epoch（屬後續迭代，非本設計範圍）。
- `DataParallel` 吃 T4×2 為可選加速，預設不啟用。
