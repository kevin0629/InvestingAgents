# 1. Coordinator: 啟動與任務分派

- As: 開發者（Coordinator 服務）
- I want: 透過 API 或 CLI 提交 `Holdings` 與 `mode` 並啟動月度再平衡任務
- So that: 系統能建立任務、判定 `market_regime` 並產生 `Candidates` 與 ANALYSIS/VERIFICATION 任務

## Acceptance Criteria
- API/CLI 接受 JSON 格式的 `Holdings` 與 `mode`，回傳任務 ID 與狀態。
- Coordinator 能產生 `Candidates` JSON 並將任務分派給 Agent（或 stub）。
- 任務包含 metadata（timestamp, user, source）且可透過 GET 查詢狀態。

## Tasks
- 建立 Coordinator API endpoint 與 CLI wrapper
- 定義任務 JSON schema
- 實作任務排程與分派到 Agent stub
- 撰寫基本整合測試與範例請求

## Labels
- epic:coordination
- phase:1
