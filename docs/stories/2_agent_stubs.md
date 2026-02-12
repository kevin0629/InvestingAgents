# 2. Agent Stubs: 結構化回應

- As: 開發者
- I want: 為 Financial / Technical / News Agent 提供可運行的 stub/wrapper
- So that: Coordinator 可對 N 檔候選股並行發出分析請求並取得結構化 JSON 回應

## Acceptance Criteria
- 每個 Agent stub 接受規定輸入並回傳 README 指定格式的 JSON。
- Agent 回傳包含 `chain_of_thought`、`tool_calls`、`source_links`（News Agent）。
- Stub 必有開發者可讀的 README 與範例輸出。

## Tasks
- 定義 Agent stub 接口與 JSON schema
- 建立 Financial / Technical / News stub 實作
- 撰寫單元測試與示範呼叫腳本

## Labels
- epic:agents
- phase:1
