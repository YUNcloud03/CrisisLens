# System Card — CrisisLens v2.0

> **Format**: System-level AI Transparency Document  
> **Last Updated**: 2026-06-08  
> **Platform**: CrisisLens Disaster Classification & Response Advisory System  
> **SDG Alignment**: SDG 11 (Sustainable Cities), SDG 13 (Climate Action)

---

## 1. System Purpose

CrisisLens is a disaster classification and response advisory platform designed to help:
- **Citizens** report disaster events by submitting photos + location data
- **Emergency managers / admins** monitor, prioritize, and respond to aggregated disaster events

It does **not** replace official emergency dispatch. All outputs are labeled as advisory.

---

## 2. User Flows

### 2.1 民眾端流程（Citizen Portal）

```
登入 / 註冊
    │
    ▼
app.py（主頁）
    │
    ├── 上傳災情照片
    ├── 選擇 GPS 取得方式（瀏覽器定位 / 手動輸入 / 僅填行政區）
    ├── 填寫災情資訊（人數、受困、受傷、道路、停電）
    │
    ├── [AI 辨識並產生建議] 按鈕
    │       ├── CLIP ViT-L/14 多描述投票推論
    │       ├── （選）DisasterCNN_v1 輔助驗證
    │       └── RAG → Gemini 生成防災建議
    │             ↓
    │        右側顯示：辨識結果 + 防災建議 + Safety 提醒
    │
    └── [送出災情回報] 按鈕
            ├── 圖片儲存（Azure Blob / 本機）
            ├── 計算 report_severity_score
            ├── 事件聚合（disaster group + 地點 + 時間窗口）
            └── 更新 grid_summary（H3 / district / city）
```

**注意**：
- GPS 失敗不阻止送出回報，city/district 作為 fallback
- AI 辨識完成前不顯示防災建議

---

### 2.2 管理端流程（Admin Portal）

| 頁面 | 功能 |
|------|------|
| `2_Event_Dashboard.py` | 事件列表（依 Priority Score 排序）、狀態篩選、狀態更新 |
| `3_Event_Detail.py` | 單一事件詳細（所有 reports、地圖、可信度評等） |
| `4_H3_Heatmap.py` | Multi-scale H3 熱區地圖（可過濾 resolved 事件） |
| `5_Permission_Review.py` | 審核 pending 使用者的 admin 申請 |

---

### 2.3 權限審核流程

```
新 User 註冊
    │
    └── 點擊「申請管理員權限」
            │ permission_status: none → pending
            ▼
        Admin 在 Permission Review 頁面審核
            ├── Approve → permission_status: approved → 可進管理端
            └── Reject  → permission_status: rejected → 可重新申請
```

**Admin 帳號**：由部署環境變數或安全初始化流程建立；不得在前端或公開文件顯示預設密碼。

---

## 3. AI 辨識流程

```
上傳圖片 (PIL.Image)
    │
    ▼
CLIP ViT-L/14（主分類器）
  多描述投票：6 classes × 4–7 prompts → cosine sim → mean → ×100 → softmax
    │
    ├── confidence < 0.50    → need_review = 1
    ├── Top-1/Top-2 gap < 0.15 → need_review = 1
    │
    ▼
DisasterCNN_v1（輔助驗證，若 CNN_AUX_ENABLED=True）
  4-block CNN → softmax → top_class_zh
    │
    └── clip_class_zh ≠ cnn_class_zh → model_agreement = 0, need_review = 1
    │
    ▼
Primary = CLIP 結果（CNN 只觸發 review，不覆蓋 CLIP）
    │
    ▼
RAG 防災建議
  FAISS Top-4 chunks → Gemini 2.0 Flash → 條列建議
  （無 API key 時 fallback 至內建指引）
```

---

## 4. 事件聚合規則

版本：`disaster-group-distance-timewindow-v4`

兩筆 report 被歸為同一事件，需同時滿足：

1. **災害類型相同**（依 `_DISASTER_GROUPS` 分組：水災=淹水+颱風、地質=地震+土石流）
2. **時間條件**（依災害類型有不同時間窗口）：

| 災害類型 | 時間窗口 |
|---------|---------|
| 淹水 / 颱風 | 12 小時 |
| 地震 | 48 小時 |
| 土石流 | 24 小時 |
| 火災 | 6 小時 |
| 其他 | 8 小時 |

3. **位置條件**（任一成立）：
   - H3 cell 相同或相鄰（GPS 模式）
   - Haversine 距離 ≤ 300m（GPS 模式）
   - 同 city + district（無 GPS fallback）

4. **事件狀態不為 resolved / archived**（已關閉事件不再接受合併）

---

## 5. Priority Score 計算

```
Priority Score = Severity × 0.50 + Vulnerability × 0.30 + Credibility × 0.20
```

| 維度 | 計算方式 |
|------|---------|
| Severity | report_severity_score（受傷/受困/阻斷/人數/高風險類型/AI信心度） |
| Vulnerability | 估計需協助人數 + 受困旗標 |
| Credibility | 回報數量 + model_agreement 比例 + event status |

**Priority Level**：
- `High` ≥ 70
- `Medium` 40–69  
- `Low` < 40

---

## 6. H3 熱區地圖

- **H3 Resolution**: Res 5（縣市）→ Res 7（鄉鎮）→ Res 9（街區 ~174m）
- **Zoom-based switching**: 地圖縮放等級決定顯示哪個 resolution
- **grid_summary 三層 fallback**：

| grid_type | grid_id | 適用場景 |
|-----------|---------|---------|
| `h3` | H3 cell（res 9） | 有 GPS |
| `district` | `"{city}_{district}"` | 有行政區 |
| `city` | `"{city}"` | 僅有縣市 |

- **已關閉事件過濾**：側邊欄 toggle 可決定是否顯示 resolved 事件的格網

---

## 7. 事件狀態說明

| 狀態 | 說明 | 誰可以設定 |
|------|------|-----------|
| `pending_review` | 新建事件，等待 admin 確認 | 系統自動 |
| `active` | 已確認進行中的事件 | Admin |
| `resolved` | 已處理完成 | Admin |
| `archived` | 封存（不再顯示於熱圖） | Admin |

> 每次狀態變更都寫入 `admin_action_logs`（含 admin_user、reason、old_value、new_value）

---

## 8. RAG 應變建議來源

| 知識庫文件 | 涵蓋災害 |
|-----------|---------|
| `earthquake_sop.md` | 地震 |
| `flood_sop.md` | 淹水 |
| `fire_sop.md` | 火災 |
| `typhoon_sop.md` | 颱風 |
| `landslide_sop.md` | 土石流 |
| `emergency_guideline.md` | 通用緊急應變 |

**Fallback 機制**：
1. Gemini API 可用 + FAISS 有檢索結果 → LLM 生成（`used_llm=True`）
2. FAISS 有結果但 Gemini 失敗 → 靜態 fallback（`used_rag=True, used_llm=False`）
3. 無任何結果 → 內建應急指引（`used_llm=False, used_rag=False`）

---

## 9. AI Safety 聲明

> ⚠️ **本系統分類與建議僅供初步參考，不代表官方災害判定。**

- 若有人員受困、受傷或有立即危險，請**優先撥打 119 / 110**
- CLIP 信心度 < 0.50 或 Top-2 gap < 0.15 的回報一律標記 `need_review = 1`
- `need_review` 回報在 credibility 計算中權重較低，降低對 Priority Score 的影響
- 所有 AI 建議均加上 disclaimer：「本系統分類與建議僅供初步參考，不代表官方災害判定」

---

## 10. 安全與隱私

| 風險 | 緩解措施 |
|------|---------|
| GPS + 照片洩露使用者位置 | 僅 admin 可存取完整位置資訊；前台不顯示精確座標 |
| 圖片中出現可識別人臉 | 系統不執行人臉辨識；僅用於災害類型分類 |
| 密碼儲存 | PBKDF2-SHA256（120,000 iterations）+ 隨機 salt |
| Admin 操作可審計 | `admin_action_logs` 記錄所有狀態變更 |
| 錯誤日誌 | `error_logs` 持久化至 DB，`context` 欄位標示模組 |
| API Key 不暴露前端 | 所有 API 呼叫在 server side 執行 |
| 對抗攻擊 | CLIP 和 CNN 均有信心度閾值；低信心一律送人工審查 |

---

## 11. MLOps 追蹤

每次推論寫入 `model_runs` 表：

```python
{
  "clip_model_version":      "clip-vitl14-v1",
  "clip_prompt_version":     "multi-prompt-avg-v1",
  "resnet_model_version":    "custom-cnn-medic-6class-v1",
  "rag_index_version":       "faiss-multilingual-minilm-v1",
  "rag_prompt_version":      "gemini-flash-rag-v1",
  "aggregation_rule_version":"disaster-group-distance-timewindow-v4",
  "priority_rule_version":   "svcp-weighted-v2",
}
```

`admin_corrections` 表記錄人工修正，`used_for_retraining = 1` 的資料可用於未來 retraining。

**Retraining 觸發建議**：
- `need_review` 率 > 30% 超過 100 筆連續回報
- Model agreement 率 < 60% 持續 7 天
