# Virgo Agent — 框架修正方案

> 基於材料科學研究方法論文獻調研 + 原版 MVP 分析

## 核心發現：原版是對的，新版走偏了

| 維度 | 原版 virgo_mvp.html | 新版 app_v2.html | 應保留 |
|------|---------------------|------------------|--------|
| 結構 | ✅ 按研究邏輯分段（Purpose→Literature→Goals→Experimental） | ❌ 一般檔案樹 | 原版 |
| 實驗步驟 | ✅ 四格漫畫（固定/變數/檢測/基準） | ❌ 自由編輯 | 原版 |
| 文獻 | ✅ 結構化輸入（作者/期刊/DOI） | ❌ 沒了 | 原版 |
| 編輯體驗 | ❌ 一般 contenteditable | ✅ CodeMirror + KaTeX | 新版 |
| 數學渲染 | ❌ 無 | ✅ KaTeX | 新版 |
| Skill 連接 | ✅ 步驟可綁定 Skill | ❌ 沒了 | 原版 |
| Present | ✅ 簡報模式 | ✅ 全螢幕 | 兩者融合 |

## 修正方案：保留新版技術基底，還原原版領域邏輯

### UI 布局（修正版）

```
┌──────────┬──────────────────────────────────────┬──────────┐
│ Activity │  Main Work Area                      │  AI      │
│  Bar     │                                      │  Panel   │
│          │  [Project: HT-PEMFC 石墨雙極板]      │          │
│  📁      │  ┌────────────────────────────────┐  │          │
│  🧪      │  │ Phase Tabs:                    │  │          │
│  📊      │  │ ISSUE | Literature | GOALS      │  │          │
│  💬      │  │ EXPERIMENTAL | RESULTS | PAPER  │  │          │
│  ⚙      │  └────────────────────────────────┘  │          │
│          │                                      │          │
│          │  Current Phase: EXPERIMENTAL         │          │
│          │  ┌────────────────────────────────┐  │          │
│          │  │ Step 1: APCVD                   │  │          │
│          │  │ ┌─────────────┬──────────────┐  │  │          │
│          │  │ │ ① Fixed     │ ② Variable   │  │  │          │
│          │  │ │ Substrate:  │ T: 850-1050℃ │  │  │          │
│          │  │ │ Ni foam     │ CH4:Ar=1:4   │  │  │          │
│          │  │ │ Precursor:  │              │  │  │          │
│          │  │ │ CH4         │              │  │  │          │
│          │  │ ├─────────────┼──────────────┤  │  │          │
│          │  │ │ ③ Detection │ ④ Benchmark  │  │  │          │
│          │  │ │ SEM, Raman, │ ID/IG ≤ 0.5  │  │  │          │
│          │  │ │ XRD, X-sec  │ Thickness    │  │  │          │
│          │  │ │             │ 1.5-2.0 μm   │  │  │          │
│          │  │ └─────────────┴──────────────┘  │  │          │
│          │  │                                 │  │          │
│          │  │ 📊 EIS Plot  📈 Raman Report   │  │          │
│          │  │ [Run: EIS-NyquistBode]          │  │          │
│          │  └────────────────────────────────┘  │          │
│          │                                      │          │
│          │  Step 2: Corrosion Test              │          │
│          │  Step 3: MEA Assembly                │          │
│          │  [+ Add Step]                        │          │
│          │                                      │          │
└──────────┴──────────────────────────────────────┴──────────┘
│  Status: Auto-saved 2 min ago | Words: 234 | Connected │
└─────────────────────────────────────────────────────────┘
```

## Phase Tabs 邏輯（不可改變的因果鏈）

```
🎯 ISSUE       →  定義研究問題
📚 Literature  →  文獻調研（結構化輸入）
🏁 GOALS       →  量化目標（從文獻收斂）
🔬 EXPERIMENTAL →  實驗設計（參數矩陣 + 四格漫畫）
📊 RESULTS     →  階段成果（自動從 EXPERIMENTAL 彙整）
📝 PAPER       →  論文初稿（從前五階段自動生成）
```

前一個階段完成 → 下一個階段解鎖。強制研究人員按因果鏈推進。

## 四格漫畫（保留原版精髓）

```
┌─────────────────────┬─────────────────────┐
│ ① Fixed Parameters  │ ② Variable Parameters│
│                     │                     │
│ 不變的實驗條件       │ 你改變的參數        │
│ • 基板材料           │ • 溫度 850-1050°C   │
│ • 前驅物             │ • 氣體比            │
│ • 沉積時間 30 min    │                     │
├─────────────────────┼─────────────────────┤
│ ③ Detection         │ ④ Benchmark          │
│                     │                     │
│ 用什麼儀器量測       │ 成功的標準           │
│ • SEM — 表面形貌     │ • ID/IG ≤ 0.5       │
│ • Raman — ID/IG      │ • 厚度 1.5-2.0 μm   │
│ • XRD — 結晶度       │                     │
└─────────────────────┴─────────────────────┘

         貼齊 Skill:
         [🔗 EIS-NyquistBode] [🔗 Raman-Carbon] [🔗 XRD-Analysis]
```

## 每個 Step 下的數據區

```
Step: APCVD ──────────────────────────────────────
│
├── 📊 Results
│   ├── Nyquist 對比圖 (T=850,900,970°C)
│   ├── Raman ID/IG 報告
│   └── [+ 用 Skill 分析新數據]
│
├── 💬 Discussion
│   └── [Markdown 編輯器：討論這個步驟的結果]
│
└── 🔄 Next Action
    ├── ✅ 通過 → 進入 Step 2
    └── ❌ 修正 → 調整參數重做
```

## 技術實現

- **Phase Tabs** — 純 CSS，六個 tab
- **四格漫畫** — 保留原版 comic-grid CSS + 內容
- **編輯器** — CodeMirror 6 用於 Discussion / PAPER 文字區
- **表格** — AG Grid 用於參數矩陣
- **圖表** — Chart.js 用於 Skill 輸出
- **Markdown 渲染** — marked.js + KaTeX（保留新版）

## 與新版 v2 的關係

**不丟棄新版**。取其技術層（CodeMirror, KaTeX, Supabase auth），但用原版的領域結構重組 UI。

執行順序：
1. 重建 `app/index.html` — 以原版結構 + 新版技術
2. 整合 Supabase auth
3. 接上 Skill 系統
4. 自測
