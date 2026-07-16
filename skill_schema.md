# Virgo Agent — Skill 系統技術規格

## 架構總覽

```
Virgo UI (前端)
    │  POST /api/skills/run
    ▼
skill_runner.py (後端執行引擎)
    │  載入 Skill JSON
    │  依序執行節點
    │  遇到判斷 → Hermes (受限)
    ▼
n8n (本機開發工具)
    │  拖拉節點 → 匯出 → 調格式 → 存入 Supabase
```

## Skill JSON Schema

### 頂層結構

```json
{
  "name": "skill-id",
  "version": 1,
  "category": "Electrochemistry",
  "levels": [1, 2, 3],
  "description": "一句話",
  "params": {...},
  "nodes": [...],
  "edges": [...]
}
```

### 節點類型

| 類型 | icon | 說明 |
|------|------|------|
| `input.file` | 📥 | 讀取上傳的 CSV/TXT 檔案 |
| `input.column_select` | 🔍 | 自動 / 手動選擇欄位 |
| `transform.negate` | ± | 取反（Z'' 轉負） |
| `transform.filter` | 🔽 | 過濾數值範圍 |
| `transform.math` | ∑ | 通用數學運算 |
| `analysis.fit_linear` | 📈 | 線性擬合 |
| `analysis.fit_peak` | 〰 | 尋峰 + 擬合 |
| `analysis.drt` | γ | DRT 計算 |
| `output.plot` | 📊 | 產生圖表 |
| `output.table` | 📋 | 產生表格 |
| `output.report` | 📝 | 文字報告 |
| `logic.if` | 🔀 | 條件判斷 |
| `logic.loop` | 🔁 | 多檔案疊代（overlay 核心） |
| `logic.ask_user` | ❓ | 模糊時問使用者 |
| `logic.merge` | ⛙ | 合併多筆結果（疊圖） |

### 節點格式

```json
{
  "id": "node-1",
  "type": "input.file",
  "params": {
    "format": "csv",
    "skip_rows": 0,
    "delimiter": ","
  }
}
```

### 邊格式

```json
{"from": "node-1", "to": "node-2"}
```

### 執行規則

- **拓樸排序**：依 edges 自動決定執行順序
- **節點可覆寫參數**：使用者呼叫 Skill 時可帶 `overrides: { "fit_range": [0.1, 0.5] }`
- **loop 節點**：輸入為檔案陣列時，對每一筆依序跑迴圈，最後 merge 產出一張圖
- **ask_user 節點**：暫停執行，回傳問題給前端，等待使用者回答後繼續

## Overlay 模式流程

```
Param Matrix → user selects rows
    │
    ▼
POST /api/skills/run
{
  "skill": "EIS-NyquistBode",
  "mode": "overlay",
  "overlay_axis": "T/°C",
  "files": [
    {"path": "850.csv", "params": {"T/°C": 850}},
    {"path": "900.csv", "params": {"T/°C": 900}},
    {"path": "970.csv", "params": {"T/°C": 970}}
  ]
}
    │
    ▼
logic.loop → for each file:
    input.file → input.column_select → output.plot
    │
    ▼
logic.merge → 一條 Nyquist 圖上三條線
    圖例：850 / 900 / 970 °C
```

## 第一個 Skill：EIS-NyquistBode

### 節點定義

```json
{
  "name": "EIS-NyquistBode",
  "category": "Electrochemistry",
  "levels": [1, 2, 3],
  "nodes": [
    {"id": "read",    "type": "input.file", "params": {"format": "csv"}},
    {"id": "detect",  "type": "input.column_select", "params": {"auto": true, "patterns": {"freq": ["freq","Hz","frequency"], "zre": ["Z'","Re","real"], "zim": ["Z''","-Im","imag"]}}},
    {"id": "check_z", "type": "logic.if", "params": {"condition": "all(zim > 0)", "true": "negate", "false": "plot"}},
    {"id": "negate",  "type": "transform.negate", "params": {"column": "zim"}},
    {"id": "nyquist", "type": "output.plot", "params": {"type": "nyquist", "x": "zre", "y": "zim_neg", "title": "Nyquist Plot"}},
    {"id": "bode",    "type": "output.plot", "params": {"type": "bode", "freq": "freq", "zre": "zre", "zim": "zim_neg"}},
    {"id": "table",   "type": "output.table", "params": {"columns": ["R_ohm", "R_ct"]}}
  ],
  "edges": [
    {"from": "read", "to": "detect"},
    {"from": "detect", "to": "check_z"},
    {"from": "check_z", "to": "negate"},
    {"from": "negate", "to": "nyquist"},
    {"from": "negate", "to": "bode"},
    {"from": "nyquist", "to": "table"},
    {"from": "bode", "to": "table"}
  ]
}
```

### 使用者可覆寫參數

| 參數 | 預設 | 說明 |
|------|------|------|
| `skip_rows` | 0 | 跳過前 N 行 |
| `freq_col` | auto | 手動指定頻率欄位 |
| `zre_col` | auto | 手動指定 Z' 欄位 |
| `zim_col` | auto | 手動指定 Z'' 欄位 |
| `negate_zim` | auto | 強制取反 |
