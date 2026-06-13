# CLIP Linear Probe 復活設計

- 日期：2026-06-13
- 分支：feature/5class-disaster
- 狀態：已通過 brainstorming，待寫實作計畫

## 目標

把已被移除的 CLIP linear probe 加回 CrisisLens，**取代雙主投票中的 zero-shot CLIP 訊號**，目標是提高分類精準度。同時保留 zero-shot 在選單中當退路，方便非正式 A/B 比對。

## 背景

- 目前 CLIP 是純 zero-shot（`models/clip_classifier.py:classify_multi_prompt`，ViT-L/14 多 prompt 平均），無任何訓練權重。
- EfficientNet-B0 是雙主投票第二主（`models/efficientnet_classifier.py`，5 類微調，test macro-F1 0.8375）。
- linear probe 曾在 commit `f39c2b4`（2026-06-01）引入，v2.1（`699479c`）被移除。

### 為什麼可以「沿用舊權重 + 程式邏輯切片」，不必重訓

linear probe 是一層 `W (N×768)` 線性層，每個輸出類別 = 一行獨立分類器，共用同一個凍結的 CLIP 768 維特徵空間。經 git 確認：

1. 舊 `clip_linear_head.pth` 仍存在於 `f39c2b4`（20517 bytes），可 `git checkout` 取回。
2. 舊 head 的 6 類（`git show f39c2b4:utils/config.py`）為：
   `Earthquake Damage` / `Flood` / `Fire` / `Typhoon or Storm Damage` / `Landslide` / `Other or No Disaster`。
   **前 5 類與現在的 `CLASSES_EN` 完全相同、順序一致**；第 6 類 `Other or No Disaster` 為多餘。
3. 舊特徵用 `ViT-L/14`（768 維）抽取，與現在 `CLIP_MODEL_NAME = "ViT-L/14"` 一致 → 特徵空間相容。
4. `.pth` 存檔格式含 `state_dict` / `classes_en` / `clip_model` / `in_dim` / `temperature`。

因此只要載入舊權重、依「類別名稱」挑出對應現在 5 類的 5 行、丟掉 `Other or No Disaster`、對 5 個 logit 重新 softmax 即可，無需資料集、無需重訓。

### 已知取捨（明確接受）

- 取代 zero-shot 後，CLIP 與 EfficientNet 都變成「吃同一份資料、不懂語意」的監督式模型，錯誤相關性升高，雙主投票的 `need_review`（抓兩模型不一致）互補性會下降。
- 沿用舊 head 無法取得「現在 5 類設定下」的新驗證數據；採非正式驗證（靠選單切換 zero-shot / probe 人工比對），不做標籤測試集硬性驗證。
- 舊 `temperature` 是為 6 類 softmax 校準的，切到 5 類後信心度校準為近似值（不影響排序，可能略影響 `need_review` 信心閾值 0.50 的觸發）。

## 架構與元件

### 1. 取回權重
- `git checkout f39c2b4 -- models/clip_linear_head.pth`
- `.gitignore` 加例外讓它被追蹤（比照 `!models/efficientnet_b0_5class_v2.pth`）。

### 2. `models/clip_classifier.py` 新增

- **`_slice_head_to_current_classes(state_dict, saved_classes_en, target_classes_en)`** — 純函式，**不載入 CLIP**：
  - 依「類別名稱」把舊 `weight (6×768)` / `bias (6,)` 挑出對應 `target_classes_en` 的列，輸出 `weight (5×768)` / `bias (5,)`。
  - 用名稱對應而非位置硬切（即使順序不同也安全）。
  - 若 `target_classes_en` 中任一類在 `saved_classes_en` 找不到 → 回 `None`。
- **`_load_linear_head()`**（`functools.lru_cache`）：
  - 讀 `clip_linear_head.pth`，組 `nn.Linear`，載入 state，呼叫切片函式。
  - 檔案不存在 / `in_dim` 不符當前 CLIP 維度 / 類別對不上 → 回 `None`。
  - 回傳 `(sliced_linear_head, temperature)` 或 `None`。
- **`classify_linear_probe(image)`**：
  - CLIP `encode_image` → L2 normalize → `head(feat) / temperature` → 5 類 softmax。
  - 回傳 dict **與 `classify_multi_prompt` 同結構**：`top_class` / `top_class_zh` / `confidence` / `top_3` / `all_scores`，外加 `method: "linear_probe"`。
- **`classify_clip(image, prefer_probe=True)`**（對外統一入口）：
  - `prefer_probe` 時先試 `classify_linear_probe`；`_load_linear_head` 回 `None` 或推論失敗 → fallback 到 `classify_multi_prompt`。
  - 結果標 `method`（`"linear_probe"` 或 `"zero_shot"`）供 UI 顯示。

### 3. `utils/versions.py`
- 新增 `CLIP_PROBE_VERSION = "linear-probe-medic-6to5-v1"`，結果頁可標示。

### 4. `app.py` 整合
選單由 3 項改為 4 項：
- `雙主投票 (CLIP linear-probe + EfficientNet-B0)` — **預設**，CLIP 走 probe
- `CLIP linear-probe`（單獨）
- `CLIP ViT-L/14 (zero-shot)`（單獨，退路）
- `EfficientNet-B0`（單獨）

雙主投票的 CLIP 呼叫由 `classify_multi_prompt` 改為 `classify_clip(img, prefer_probe=True)`；投票與 `need_review` 邏輯（`app.py:557-573`）**不動**（回傳結構一致）。UI 顯示目前 CLIP 用哪條（`method`）。

### 5. 錯誤處理 / fallback
- `.pth` 不存在或載入失敗 → 自動退回 zero-shot，UI 顯示一行提示（例：「linear probe 權重未就緒，已退回 zero-shot」），系統不崩。

## 資料流

```
影像 → CLIP encode_image (凍結, 768d) → linear head (5×768, 切片自舊 6 類)
     → /temperature → softmax(5) → {top_class, confidence, top_3, all_scores, method}
                                          ↓ (載入失敗時)
                                     classify_multi_prompt (zero-shot 退路)
```

## 測試

- `_slice_head_to_current_classes`：
  - 餵假 6 類 `state_dict`，斷言輸出 5 行、對齊 `CLASSES_EN` 順序、被丟的是 `Other or No Disaster`。
  - 某 target 類缺失於 saved → 回 `None`。
  - （純邏輯，不載入 CLIP，快速）
- `classify_linear_probe`：回傳含必要 key；5 類機率總和 ≈ 1。
- fallback：`.pth` 缺席時 `classify_clip` 使用 zero-shot 且 `method == "zero_shot"`。

## 不做（YAGNI）

- 不重訓 5 類 head（已選擇捷徑）。
- 不建立標籤測試集自動驗證流程（採非正式人工比對）。
- 不改動 EfficientNet 與投票/`need_review` 既有邏輯。
- 不移除 zero-shot 程式碼（保留為退路）。
