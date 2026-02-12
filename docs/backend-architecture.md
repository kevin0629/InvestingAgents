# 後端系統架構（Langchain / Langgraph + Qdrant）

版本與範圍
- 目標技術棧：Python + Qdrant（向量資料庫）、Langchain、Langgraph v1.0
- 互動介面：Agent Chat UI（前端/桌面/嵌入式皆可使用）
- 觀察與分析：Langfuse（agent 追蹤與細緻效果分析）

設計目標
- 提供可擴充的 agent 平台，支援多 agent 類型（分析、交易、風控、研究）
- 保持低延遲的聊天互動（WebSocket 支援）
- 支援向量檢索、上下文記憶與可觀察的 agent 執行紀錄
- 運維可觀察性（追蹤、日誌、指標）與安全性（認證、權限、資料保護）

- Agent Orchestrator（Langchain v1.0 + Langgraph v1.0）
  - 使用 Langchain v1.0 做通用 agent 工作流程與工具介接
  - 使用 Langgraph v1.0 做複雜的 agent graph、條件邏輯、工作流程編排
  - Agent 執行由 orchestrator 管理：輸入前處理、檢索、模型推理、後處理、Action 呼叫

- 向量與檢索層（Qdrant）
  - 儲存 embedding 與 metadata（doc id、chunk、source、timestamp、embedding model）
  - 支援近鄰搜尋與 filtered search（利用 metadata 篩選）
  - 背景資料同步/ingestion worker：負責 chunk、embed（選擇 embedding provider）並寫入 Qdrant

- Embedding / Model Provider 層
  - 支援 pluggable providers（OpenAI, Anthropic, local LLMs）
  - Embedding 與 LLM 請求經由統一 client 層處理，並記錄到 Langfuse/Tracing

- 觀察與分析（Langfuse）
  - 每次 agent run、chains、tool-call、prompt step 等皆向 Langfuse 發送 event
  - 儲存 run-level 與 step-level trace，供後續可視化、比較和回溯

系統資料流程（簡述）
1. 使用者經由 Agent Chat UI 發出訊息（WebSocket 或 HTTP）。
2. API 層驗證並送至 Orchestrator（Langgraph 節點啟動 run）。
3. 若需要檢索，Orchestrator 呼叫向量檢索（Qdrant）取得相關上下文。
4. Orchestrator 呼叫 LLM（透過 Embedding/LLM provider client），中間步驟與結果向 Langfuse 傳送 trace。
5. 最終回應回到 API，並回送給前端； trace 存入 Langfuse。I



開發與交付清單（最小可交付）
- 1. Qdrant client + ingestion worker 範例
- 2. Langchain + Langgraph v1.0 範例 flow
- 3. Langfuse integration sample（emit run & step events）
- 4. 簡易 Agent Chat UI 範例（可使用現成 Agent Chat UI）


參考連結
- Langchain v1.0: https://langchain.com
- Langgraph v1.0: （請使用官方 repo / docs 的 v1.0 版本）
- Qdrant: https://qdrant.tech
- Langfuse: https://www.langfuse.io

---
作者：架構建議（自動生成），日期：2026-02-12
