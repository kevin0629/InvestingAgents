# 9. 自動化驗證流程（verification_status）

- As: 測試/研究者
- I want: 自動化驗證模組能對既有持股產生 `verification_status`
- So that: 系統能以結構化結果揭示資料或決策的一致性

## Acceptance Criteria
- 驗證模組輸出 `verification_status` JSON，並被 Critic 與 Portfolio Manager 使用。
- 驗證結果包含每項檢查的結果、嚴重性與建議處置。

## Tasks
- 定義 `verification_status` schema
- 實作自動化驗證模組並與 Coordinator、Critic 整合
- 撰寫測試與示範資料

## Labels
- epic:verification
- phase:3
