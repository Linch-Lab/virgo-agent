# Virgo Agent — 產品架構文件

## 核心流程

每個研究專案循著因果鏈推進：

```
ISSUE ──→ Literature ──→ GOALS ──→ EXPERIMENTAL ──→ RESULTS ──→ PAPER
```

| 階段 | 輸入 | 輸出 | AI 輔助 |
|------|------|------|---------|
| **ISSUE** | 研究問題描述 | 明確的研究命題 | 協助精煉問題 |
| **Literature** | 關鍵字 / 上傳論文 | 文獻整理筆記 | 自動搜尋、摘要、分類 |
| **GOALS** | 文獻整理內容 | 量化目標（KPI） | 從文獻中擷取基準值 |
| **EXPERIMENTAL** | 目標 + 材料層級 | 參數矩陣 + 四格漫畫 | 自動建議實驗條件 |
| **RESULTS** | 實驗數據 | 標準圖表 + 分析報表 | Skill 自動分析 |
| **PAPER** | 所有前階段累積 | 論文初稿 | 自動生成各章節 |

## 層級化實驗設計

```
專案
├── L1 材料層（粉末、薄膜）
│   ├── 參數矩陣：前驅物、溫度、時間…
│   └── 檢測項目：XRD, Raman, XPS, SEM, CV, EIS
├── L2 元件層（電極、MEA、雙極板）
│   ├── 參數矩陣：塗層厚度、熱壓條件…
│   └── 檢測項目：腐蝕測試、接觸阻抗、截面 SEM
└── L3 裝置層（單電池、短堆疊）
    ├── 參數矩陣：溫度、氣體流量、背壓…
    └── 檢測項目：IV曲線, EIS, 耐久性, GC
```

每個層級有獨立的參數矩陣和四格漫畫，數據按層級 + 步驟組織。

## 參數矩陣（SmartUQ 風格）

```csv
Sample, T/°C, t/min, CH4:Ar, EIS_file, Raman_file, SEM_file
Ni-850, 850, 30, 1:4, 850_eis.csv, 850_raman.txt, -
Ni-900, 900, 30, 1:4, 900_eis.csv, 900_raman.txt, 900_sem.png
```

- 參數是可變因子
- 數據檔掛在對應的 cell
- Skill 從矩陣中拉數據交叉分析

## Skill 系統（分層）

| Skill | L1 | L2 | L3 |
|-------|:--:|:--:|:--:|
| EIS-NyquistBode | ✅ 三電極 | ✅ 夾具 | ✅ 單電池 |
| EIS-DRT | ✅ | ✅ | ✅ |
| CV-ECSA | ✅ RDE | — | — |
| LSV-Tafel | ✅ | ✅ | ✅ |
| IV-Curve | — | — | ✅ |
| Chrono-iV | ✅ | — | ✅ |
| XPS-Fitting | ✅ | — | — |
| XRD-Analysis | ✅ 粉末 | ✅ 薄膜 | — |
| Raman-Carbon | ✅ | ✅ | — |
| SEM-ParticleSize | ✅ | ✅ | — |
| GC-Analysis | — | — | ✅ |
| 通用繪圖 | ✅ | ✅ | ✅ |
