# 4. Portfolio Manager: 組合決策輸出

- As: Portfolio Manager 開發者
- I want: 檢索 Reflection 並根據 `market_regime` 調整權重與解決衝突
- So that: 最終能輸出符合規格的 `portfolio_decisions` JSON 與執行報告

## Acceptance Criteria
- Portfolio Manager 產出 `portfolio_decisions` JSON（含每檔權重與理由）。
- 輸出包含引用的 Agent outputs 與 Reflection ID，可供稽核追溯。
- 支援基本衝突解決策略與回滾/審計紀錄。

## Tasks
- 定義 `portfolio_decisions` JSON schema
- 實作決策合成邏輯與權重演算法（可先用 rules/stubs）
- 加入可追溯的引用欄位（Reflection IDs / Agent outputs）

## Labels
- epic:portfolio
- phase:3
