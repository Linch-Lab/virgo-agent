# Virgo Agent — Skill 設計文件 v2

## 核心概念：層級化架構

材料科學研究是多層次的。同一種分析技術，在不同層級有不同的設置、參數、與判讀方式。

```
專案：HT-PEMFC 石墨塗層雙極板
│
├── Level 1: 材料層 (Material)
│   範疇：粉末、薄膜、墨水
│   量測環境：三電極半電池、粉末 XRD、粉末 Raman
│   參數表例：前驅物、沉積溫度、氣體比、退火條件
│
├── Level 2: 元件層 (Component)
│   範疇：電極、MEA、雙極板、GDL
│   量測環境：夾具式腐蝕測試、接觸阻抗、截面 SEM
│   參數表例：塗層厚度、熱壓條件、離子omer 含量
│
└── Level 3: 裝置層 (Device)
    範疇：單電池、短堆疊
    量測環境：燃料電池測試站（溫控、氣體供應、背壓）
    參數表例：電池溫度、氣體流量、背壓、濕度
```

## Skill 分層表

| Skill | L1 材料 | L2 元件 | L3 裝置 | 核心差異 |
|-------|:---:|:---:|:---:|------|
| **EIS-NyquistBode** | ✅ 三電極 | ✅ 夾具 | ✅ 單電池 | 電極配置不同，等效電路不同 |
| **EIS-DRT** | ✅ | ✅ | ✅ | DRT 峰數隨層級增加 |
| **CV-ECSA** | ✅ RDE | ✅ 氣體擴散電極 | — | L1 用液態電解質，L2 用固態 |
| **LSV-Tafel** | ✅ 三電極 | ✅ 夾具 | ✅ 單電池 | iR 補償需求不同 |
| **XPS-Fitting** | ✅ 粉末/薄膜 | — | — | 僅材料層 |
| **XRD-Analysis** | ✅ 粉末 | ✅ 薄膜 | — | 薄膜有織構效應 |
| **Raman-Carbon** | ✅ 粉末 | ✅ 薄膜表面 | — | 聚焦深度不同 |
| **SEM-ParticleSize** | ✅ 粉末 | ✅ 截面 | — | 粉末：粒徑；截面：厚度 |
| **Chrono-iV** | ✅ | — | ✅ 耐久性 | L1 測催化劑穩定性，L3 測電池壽命 |
| **IV-Curve** | — | — | ✅ 單電池 | 極化曲線 + 功率密度 |
| **GC-Analysis** | — | — | ✅ | 產物分析（H₂, O₂, CO₂） |
| **通用繪圖** | ✅ | ✅ | ✅ | 跨層級參數對比 |

---

## Skill 格式定義

```json
{
  "name": "skill-id",
  "level": [1, 2, 3],
  "category": "Electrochemistry | Spectroscopy | Microscopy | Chromatography | General",
  "description": "一句話說明",
  "parameter_context": "這個層級特有的實驗條件說明",
  "auto_detect": {"columns": [...], "patterns": {...}},
  "pipeline": [...],
  "params": {...},
  "output": {"plot": "...", "table": "..."},
  "ambiguity_rules": [...]
}
```

---

## Skill 詳細設計

### [L1/L2/L3] EIS-NyquistBode

**層級差異**:
| | L1 三電極 | L2 夾具 | L3 單電池 |
|---|---|---|---|
| 電極配置 | RE + CE + WE | 兩端點 | 陽極/陰極 |
| 等效電路 | R_s + R_ct//CPE | R_s + R_ct//CPE + W | R_s + (R_a//CPE_a) + (R_c//CPE_c) |
| 頻率範圍 | 100kHz–0.1Hz | 100kHz–0.1Hz | 10kHz–0.01Hz |
| R_ohm 意義 | 溶液阻抗 | 接觸阻抗 | 膜阻抗 |

**Expected columns**:
```
freq/Hz, Z'/Ω, Z''/Ω       → Bio-Logic, Gamry
Frequency (Hz), Z'(Ω), -Z''(Ω) → Solartron
f/Hz, Re(Z)/Ω, -Im(Z)/Ω    → Zahner
```

**Auto-detect logic**:
1. 找 header 含 `freq` / `Hz` / `frequency` 的欄 → 頻率
2. 找 `Z'` / `Re` / `real` → Z'
3. 找 `Z''` / `-Im` / `imag` → Z''（需確認正負）

**Ambiguity rules**:
- Z'' 全為正 → 問「是否需取反？」
- 找不到頻率欄 → 問「頻率欄是？」
- 資料含多個頻段 → 可能是多段 EIS，問「是否分段量測？」
- 兩組以上 Z', Z'' → 可能同時測了陽極+陰極 EIS（L3），問「哪組是陽極/陰極？」

**Params**:
- `level`: auto-detect from project context
- `skip_rows`: 0

**Output**:
- Nyquist plot + Bode plot
- Table: R_ohm, R_ct (estimated)
- L3 額外：陽極/陰極 R_ct 分離（如數據支援）

**Prompt**:
```
Analyze EIS data at the {level} level. Auto-detect columns for frequency, Z', Z''.
If Z'' values are all positive, negate them per instrument convention.
For Level 3 (single-cell), check if both anode and cathode EIS are present.
Generate Nyquist and Bode plots. Mark R_ohm and estimate R_ct from semicircle diameter.
At Level 3, separate anode and cathode contributions if reference electrode data available.
```

---

### [L1/L2/L3] EIS-DRT

**Description**: DRT 分析 — 將 EIS 頻譜拆解為弛豫時間分佈

**層級差異**:
- L1: 通常 1-2 個 DRT 峰（電荷轉移 + 擴散）
- L2: 2-3 個峰（+ 接觸效應）
- L3: 3-5 個峰（陽極 + 陰極 + 膜 + 擴散）

**Pipeline**:
1. 繼承 EIS-NyquistBode 輸出
2. DRT 計算（Tikhonov 正則化）
3. 峰值檢測 + Gaussian 拆解
4. 自動建議 ECM 結構
5. 可導出至 DRTxECM（若安裝）

**Params**:
- `regularization`: auto (GCV)
- `rbf_shape`: Gaussian
- `lambda`: auto

**Output**:
- DRT γ(τ) 圖
- Peak table: τ, R, C, f_c per peak
- 建議 ECM 拓撲

---

### [L1] CV-ECSA (三電極)

**Description**: 從 RDE 或靜態電極的 CV 多掃描速率計算 C_dl

**為什麼不適用 L2/L3**: 固態電解質中非法拉第區定義不同，需改用 EIS-ECSA 或 CO-stripping

**Expected columns**:
```
E/V, I/A              → Autolab
Potential (V), Current (A) → CHI
```

**Pipeline**:
1. 擷取非法拉第區（OCP ± 0.1V）
2. 找各掃描速率的充電電流中點
3. i vs v 線性擬合 → C_dl = slope

**Ambiguity rules**:
- 只有一個掃描速率 → 問「請上傳多個速率」
- R² < 0.95 → 提示品質警告
- 資料不是 CV（是 LSV）→ 建議改用 LSV-Tafel

**Output**:
- CV 疊加圖
- i vs v + 線性擬合圖
- Table: C_dl, R², per-rate currents

---

### [L3] IV-Curve (單電池)

**Description**: 燃料電池/電解槽極化曲線 + 功率密度

**Expected columns**:
```
E/V, I/A              → 標準
Current (A), Voltage (V) → 通用
還有：溫度、流量（metadata，不在 CSV 內）
```

**Pipeline**:
1. 繪製 E vs i（極化曲線）
2. 計算功率密度 P = E × i / Area
3. 標記三個區域：活化、歐姆、質量傳輸
4. 擷取關鍵指標：OCV, i @ 0.6V, P_max

**Output**:
- 極化曲線 + 功率密度雙 Y 軸圖
- Table: OCV, i@0.6V, i@0.4V, P_max, P@0.6V

---

### [L1] XPS-Fitting

**Expected columns**: `BE (eV)`, `Intensity (cps)`

**Pipeline**:
1. Shirley / Tougaard 背景扣除
2. 尋峰 → 使用者指定峰數或自動
3. Gauss-Lorentz 混合擬合
4. 面積積分 → At.% 賦歸

**Ambiguity rules**:
- 沒指定元素 → 從 BE 推測（C 1s ~284.8, O 1s ~532, N 1s ~400）
- 峰不對稱 → 建議增加峰或改用 asymmetric lineshape
- 雙重態 → 自動檢測 spin-orbit splitting

**Output**:
- 擬合疊加圖 + 背景扣除圖
- Table: Peak | BE | Area | FWHM | At.%

---

### [L1/L2] XRD-Analysis

**層級差異**: L1 粉末用標準 PDF 比對；L2 薄膜需考慮織構

**Pipeline**: 尋峰 → Kα2 stripping → Scherrer 粒徑 → (L2: 殘餘應力)

**Output**:
- 標準 XRD 圖 + 峰標記
- Table: 2θ, d, FWHM, Size, (hkl)

---

### [L1/L2] Raman-Carbon

**層級差異**: L1 粉末 → 整體結晶度；L2 薄膜 → 可能需 mapping

**Pipeline**: 基線校正 → D/G 峰擬合 → ID/IG

**Output**:
- Raman 圖 + 擬合拆解
- Table: Peak, Position, FWHM, Area, ID/IG

---

### [L1] SEM-ParticleSize / [L2] SEM-CrossSection

**L1**: 粒徑分布  
**L2**: 膜厚量測 + 界面分析

---

### [L3] Chrono-iV (耐久性)

**Description**: 定電流/定電壓長時間穩定性

**Pipeline**:
1. 自動分段（活化期、穩定期、衰退期）
2. 衰退率計算（mV/h 或 %/kh）
3. 多組對比疊圖

**Output**:
- i-t / E-t 曲線 + 分段標記
- Table: 初始值, 最終值, 衰退率

---

### [L1/L2/L3] 通用繪圖

**核心功能**: 從參數矩陣中勾選數據 → 跨層級對比

**智能欄位對比**:
1. 使用者選 X 軸參數（如「溫度」）→ 系統從矩陣中找出所有含該參數的數據
2. 使用者勾選要畫的數據行 → 自動配色 + 圖例
3. 支援雙 Y 軸（如左：電流，右：功率）

**Prompt**:
```
From the project parameter matrix, let user pick an independent variable (e.g., temperature).
Filter all data rows containing that parameter.
User selects which rows to plot on the same graph.
Auto-generate axis labels and legend from parameter values.
Output publication-quality plot.
```
