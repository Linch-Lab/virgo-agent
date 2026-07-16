# Virgo Agent — Skill Runner 設計

## 執行引擎架構

```
skill_runner.py
├── load_skill(name)        → 從 Supabase 或本機 cache 載入 JSON
├── topological_sort(nodes, edges)  → 決定執行順序
├── execute_node(node, context)     → 分派節點類型
├── run(skill_name, files, overrides) → 主入口
└── SkillContext                   → 執行時狀態
```

## SkillContext

```python
class SkillContext:
    files: list[dict]        # 輸入檔案列表
    overrides: dict          # 使用者覆寫參數
    node_outputs: dict       # 節點 ID → 輸出結果
    variables: dict          # 共享變數
    mode: str                # "single" | "overlay"
    overlay_axis: str        # 疊圖時的圖例軸
```

## 節點執行器

| 節點類型 | 實作方式 |
|----------|---------|
| `input.file` | pandas.read_csv(file_path, **params) |
| `input.column_select` | 正則匹配 header → 找不到 → ask_user |
| `transform.negate` | df[column] = -df[column] |
| `transform.filter` | df = df[(df[col] >= lo) & (df[col] <= hi)] |
| `transform.math` | eval(expression) over dataframe |
| `analysis.fit_linear` | scipy.stats.linregress(x, y) |
| `analysis.fit_peak` | scipy.signal.find_peaks + curve_fit |
| `analysis.drt` | pyDRTtools (if installed) |
| `output.plot` | matplotlib → base64 PNG |
| `output.table` | pandas.DataFrame → JSON |
| `output.report` | template string |
| `logic.if` | eval(condition) → 決定跳轉 |
| `logic.loop` | for each file → execute subgraph → collect outputs |
| `logic.ask_user` | raise AskUserException(question) |
| `logic.merge` | 收集 loop 輸出 → 合併到一張圖 |

## Overlay 模式流程

```
logic.loop:
  for file in files:
    ┌─ input.file(file.path)
    ├─ input.column_select
    ├─ output.plot(overlay_label=file.params[overlay_axis])
    └─ store in loop_results

logic.merge:
  ┌─ 收集所有 loop_results 中的 plot data
  ├─ 同一張圖上疊加所有曲線
  ├─ 圖例顯示 overlay_axis 值
  └─ return merged plot
```

## API 端點

```
POST /api/skills/run
{
  "skill": "EIS-NyquistBode",
  "mode": "overlay",
  "overlay_axis": "T/°C",
  "files": [
    {"path": "/data/850.csv", "params": {"T/°C": 850}},
    {"path": "/data/900.csv", "params": {"T/°C": 900}}
  ],
  "overrides": {"skip_rows": 3}
}

Response:
{
  "status": "ok",
  "plots": [{"type": "nyquist", "image": "base64..."}],
  "tables": [{"name": "R_ohm_R_ct", "data": [...]}],
  "reports": ["R_ohm = 1.23 Ω, R_ct = 45.6 Ω"]
}
```

## ask_user 流程

```
節點執行 → raise AskUserException(question)
    │
    ▼
POST /api/skills/continue?exec_id=xxx
{
  "answers": {"zim_col": 2}
}
    │
    ▼
從中斷點繼續執行
```

## 與 Hermes 的整合點

受限 Hermes 處理兩件事：
1. **column_select 節點**：AI 判斷 header 中哪欄是什麼
2. **ask_user 節點**：AI 生成對使用者的問題文字

Hermes 權限：僅讀取 `/data/` 目錄，不可寫入網站程式碼。
