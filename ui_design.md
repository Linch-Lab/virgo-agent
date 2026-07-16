# Virgo Agent — UI 設計文件

## 布局骨架（JupyterLab 風格）

```
┌──────────┬────────────────────────────┬─────────────┐
│ Activity │  Main Work Area            │  Aux Panel  │
│  Bar     │                            │             │
│  (48px)  │  ┌──────────────────────┐  │  AI Chat    │
│          │  │  Markdown Editor     │  │  +          │
│  📁      │  │  (Live Preview)      │  │  Progress   │
│  🔍      │  │                      │  │             │
│  📊      │  │  切換：Edit / Preview │  │             │
│  💬      │  │  / Split             │  │             │
│  ⚙      │  └──────────────────────┘  │             │
│          │                            │             │
│          │  ┌──────────────────────┐  │             │
│          │  │  Data Table / Plot   │  │             │
│          │  │  (collapsible)       │  │             │
│          │  └──────────────────────┘  │             │
│          │                            │             │
├──────────┴────────────────────────────┴─────────────┤
│  Status Bar (Present 按鈕, Word Count, Sync Status) │
└─────────────────────────────────────────────────────┘
```

## 三種模式

| 模式 | 觸發 | 畫面 |
|------|------|------|
| **Edit** | 預設 | Markdown 原始碼在左，即時預覽在右（或上下） |
| **Preview** | 點擊 Preview tab | 全版渲染的漂亮頁面（像 Markdown Preview Enhanced） |
| **Present** | 點 Present 按鈕 | 全螢幕投影模式，黑底/白底可選 |

## 左側導航欄

專案樹狀結構（Origin 風格）：

```
📁 HT-PEMFC 石墨雙極板
├── 🎯 ISSUE
│   └── 問題定義.md
├── 📚 Literature
│   ├── 文獻1：IJHE 2024.md
│   └── 文獻2：JPS 2023.md  
├── 🏁 GOALS
│   └── 量化目標.md
├── 🔬 EXPERIMENTAL
│   ├── 📋 參數矩陣 (L1)
│   ├── 📋 參數矩陣 (L2)
│   ├── Step 1：APCVD
│   │   └── 四格漫畫.md
│   ├── Step 2：Corrosion
│   └── Step 3：MEA Assembly
├── 📊 RESULTS
│   ├── Nyquist 對比圖
│   ├── Raman ID/IG
│   └── 腐蝕測試結果
├── 📝 PAPER
│   └── 論文初稿.md
└── ⚡ AI Chat
```

## Markdown 編輯器

採用 **CodeMirror 6** + **marked.js** 渲染。

支援：
- 標準 Markdown（標題、粗斜體、表格、程式碼、LaTeX 數學式 $...$）
- WikiLink：`[[文獻1]]` 自動連結到其他頁面
- 內嵌圖表：`![[Nyquist 對比圖]]` 插入已生成的圖
- `/` 指令：`/table` 插入表格、`/plot` 插入圖表、`/skill` 呼叫分析
- 拖放上傳：拖 CSV 檔案直接插入資料表

## AI 對話面板

右側 340px 可收合面板：
- 聊天對話框（底部輸入）
- 任務進度追蹤（Cursor 風格）：
  ```
  ⏳ Analyzing EIS data... (Step 2/4)
  ✅ Column detection complete
  ⏳ Generating Nyquist plot...
  ⬜ Computing R_ct
  ```
- 上下文感知：知道目前在編輯哪個頁面

## 參數矩陣表格

SmartUQ 風格的 DOE 矩陣：
- 可編輯行列
- 每個 cell 可掛檔案
- 選中多行 → 右鍵 → 呼叫 Skill 分析
- 跨視圖雙向選取（JMP Brushing）

## 技術選型

| 元件 | 方案 |
|------|------|
| 面板布局 | CSS Grid + flexbox（純手寫，不依賴框架） |
| Markdown 編輯 | CodeMirror 6（CDN） |
| Markdown 渲染 | marked.js（CDN） |
| 數學式 | KaTeX（CDN，自動渲染 $...$） |
| 圖表 | Chart.js（CDN，已使用） |
| 程式碼高亮 | highlight.js（CDN） |
| 資料儲存 | IndexedDB（離線）+ Supabase（雲端） |
