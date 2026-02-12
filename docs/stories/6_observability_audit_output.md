# 6. 可觀察性與稽核輸出

- As: 審計 / 研究者
- I want: 每次執行保存 Agent 輸出、工具呼叫、來源連結與 Critic Reflection
- So that: 可檢索 chain-of-thought 與來源以供檢驗與回溯

## Acceptance Criteria
- 每次執行產生可搜尋的執行包（JSON 或 DB 記錄），包含所有 Agent outputs 與工具使用紀錄。
- 執行包可依 task_id、timestamp 與 agent_id 查詢並導出。

## Tasks
- 定義執行包 schema 與儲存位置（文件或 DB）
- 實作記錄 hook 並在流程中匯出 JSON 包
- 撰寫檢索範例與測試

## Labels
- epic:observability
- phase:2
