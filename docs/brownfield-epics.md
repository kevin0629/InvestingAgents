# Epic: Brownfield MVP — Coordinator 驅動的月度再平衡

## 概要
- 專案目標：將現有研究原型整合為可運作的褐地（brownfield）MVP，支援排程式月度再平衡（BATCH）與即時單股分析（SINGLE）。
- 關鍵組件：Coordinator、Financial/Technical/News Agent、Critic、Portfolio Manager、向量資料庫（Qdrant）、PostgreSQL、`dataflows/*` 整合模組。

## 目標與成功衡量
- 功能性：系統能對 N 檔候選股執行月度再平衡，並為每檔生成 `portfolio_decisions` JSON。
- 可觀察性：每次執行保存 Agent 輸出、工具呼叫、來源連結與 Critic Reflection（至 Qdrant 或 JSONL 備援）。
- 正確性：提供自動化驗證流程，回傳結構化 `verification_status`。
- 開發者便利性：完善 README 與 API 文件，提供最小示範腳本可執行完整流程。

## 範圍（In-scope）
- Coordinator 服務：接受 `Holdings` 與 `mode`，判定 `market_regime`，產出 `Candidates` 並依 README JSON 規格分派 ANALYSIS / VERIFICATION 任務。
- Agent：Financial、Technical、News 三類 Agent（可先以 wrapper 或 stub 實作），回傳 README 指定格式的結構化 JSON。
- Critic：整合 Verification 報告並產生 `Reflection`，將 Reflection 寫入 Qdrant，且提供 JSONL 備援以防向量庫不可用。
- Portfolio Manager：整合 Agent 輸出與 Reflection，依 `market_regime` 調整權重並輸出 `portfolio_decisions`。
- 資料整合：改用/改寫現有 `dataflows/*`（finnhub、yfin、googlenews、reddit、stockstats），並採用指定替代路由（Tavily、backend/src/stock/router.py、backend/src/factor/router.py、backend/src/indicator/router.py）。
- 儲存：向量資料庫使用 Qdrant；關聯資料使用 PostgreSQL（參考 backend/src/database.py 實作）。

## 範圍（Out-of-scope for MVP）
- 企業級認證、水平擴充與完整監控。
- 進階前端 UI（MVP 以 API 與 Agent Chat UI / 示範為主）。

## 工作流程（高階序列）
1. Coordinator 執行量化篩選產出 `Candidates`，判定 `market_regime` 並發出 ANALYSIS/VERIFICATION 任務。
2. Financial / Technical / News Agent 並行執行，回傳結構化 JSON。
3. Critic 整合 Verification Reports，產生 `Reflection` 並存入 Qdrant（或 JSONL 備援）。
4. Portfolio Manager 檢索 Reflection，解決衝突並依 `market_regime` 調整權重，輸出 `portfolio_decisions`。
5. 保存所有產物（Agent 輸出、工具呼叫、來源連結、Reflection）以利稽核與檢索。

## 驗收準則（Acceptance Criteria）
- Coordinator 能以 API 或 CLI 接受 `Holdings` 與 `mode` 並回傳任務啟動回應。
- 對 N 檔候選股執行完整流程（Agent → Critic → Portfolio Manager），最後生成 `portfolio_decisions` 的 JSON 檔案。
- Critic 的 Reflection 成功寫入 Qdrant，且在 Qdrant 不可用時寫入 JSONL 備援檔案。
- 每次執行產出包含 Agent chain-of-thought、工具使用紀錄與來源連結的可稽核輸出。
- 提供最小示範腳本（例如 `backend/scripts/run_rebalance.py`）能執行一次端到端流程並產生示例報告。
- README 與 API 文件更新以說明觸發、查詢與輸出格式。

## 里程碑與階段（對應 PRD）
- Phase 1（1–2 週）：建立 Coordinator 與 Agent stub、示範 CLI，將輸出儲存為 JSON，並新增觸發與查詢的 API。
- Phase 2（2–3 週）：接入真實 Agent 實作（改寫 `dataflows/*`），整合 Qdrant，完成 Critic 的 Reflection 儲存與檢索。
- Phase 3（2 週）：實作 Portfolio Manager 邏輯、部位大小計算、執行報告與基本測試；完成 README/API 文件與示範 notebook。

## 風險與緩解措施
- Agent 幻覺風險：要求 News Agent 提供 `source_links`；Critic 標註或拒絕無依據主張。
- 向量庫不可用：實作 JSONL 備援以確保 Reflection 不遺失。

## 交付項目（Deliverables）
- Coordinator API 與示範腳本（`backend/scripts/run_rebalance.py`）。
- Agent stub 與逐步替換成真實 `dataflows/*` 實作的模組。
- Critic 寫入 Qdrant（及 JSONL 備援）。
- Portfolio Manager 輸出 `portfolio_decisions` JSON 與執行報告。
- 更新的 README、API 文件與示範 notebook/CLI。

## 所有人與關係人（Stakeholders）
- 開發者 / 倉庫維護者（實作 Coordinator、Agent 與整合）。
- 產品 / PM（驗收與驗證成功衡量）。
- 研究人員（提供量化篩選與回測驗證）。

---
註：本 epic 嚴格根據 `docs/brownfield-prd.md` 的內容撰寫，未新增 PRD 未列出的功能或非必要需求。
