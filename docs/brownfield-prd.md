
# InvestingAgents — Brownfield PRD

## 1. 摘要
- **專案：** InvestingAgents — 多代理人量化投資系統
- **目的：** 將現有研究原型轉為可運作的褐地（brownfield）MVP，支援以 Coordinator 搭配專家 Agent（Financial、Technical、News、Critic、Portfolio Manager）執行月度投組再平衡與單株分析。

## 2. 背景與問題
此倉庫包含研究等級的多代理人框架，可產生投資分析與回測結果。現有資產（README、agents、backend、dataflows）功能豐富，但欠缺一份清楚的產品規格，說明如何將量化篩選、Agent 分析、反思（存入向量資料庫）與投組決策整合成可重複執行的月度再平衡流程。

## 3. 目標
- 交付一個 MVP：能執行排程式月度再平衡（BATCH）與即時單股票分析（SINGLE）。
- 保留稽核性：記錄 Agent 輸出、chain-of-thought、工具使用與來源連結，供 Critic 產生反思並存入向量資料庫（Qdrant）。
- 提供清晰的 REST API 端點以觸發作業並取得報告（回測、分析、投組決策）。

## 4. 成功衡量指標
- 功能性：系統能對 N 檔候選股執行月度再平衡，並為每檔生成 `portfolio_decisions` 的 JSON。
- 可觀察性：每次執行均將 Agent 輸出與 Critic 反思存入向量資料庫或備援檔案，以利檢索。
- 正確性：自動化的驗證流程可對既有持股回傳結構化的 `verification_status`。
- 開發者便利性：更新 README 與 API 文件；提供最小示範腳本可執行一次完整流程。

## 5. MVP 範圍
包含項目：
- Coordinator 服務：接受 `Holdings` 與 `mode` 並依 JSON 規格發出任務分派，按需求執行 backtest，產生 `Candidates`。
- Financial / Technical / News Agent：提供 README 指定格式的 JSON 回應（可先以 wrapper 或 stub 實作）。
- Critic：整合驗證報告並將 `Reflection` 寫入向量資料庫。
- Portfolio Manager：整合 Agent 報告與 Reflection，輸出符合 README 的 `portfolio_decisions`。

不包含（MVP 外）：
- 企業級認證、水平擴充與完整監控。
- 進階前端 UI（MVP 以 API 與 Agent Chat UI/示範為主）。


## 6. 資料與整合
- 資料來源：依現有API，改寫 `dataflows/*` 模組（finnhub、yfin、googlenews、reddit、stockstats）取得價格、基本面與新聞。
    - 使用 Tavily 取代 googlenews、reddit
    - 使用 `backend/src/stock/router.py` 取代 yfin、stockstats
    - 使用 `backend/src/factor/router.py`、`backend/src/indicator/router.py` 取代 finnhub
    - 新增 company、backtest 模組，功能如 `backend/src/company/router.py`、`backend/src/backtest/router.py` 所示
- 向量資料庫：Qdrant 儲存 Reflection；
- 資料庫：使用 PostgreSQL 儲存 backend API 所需資料（可參考 `backend/src/database.py` 的實作範例）。


## 7. 架構與工作流程
1. Coordinator 依需求執行量化篩選以產出 `Candidates`。接收輸入並判定 `market_regime`，依 README JSON 規格發出 ANALYSIS / VERIFICATION 任務給子 Agent。
2. 子 Agent（Financial、Technical、News）並行執行並回傳結構化 JSON。
3. Critic 整合針對持股的 Verification Reports，產生 `Reflection` 並存入向量資料庫或備援檔案。
4. Portfolio Manager 檢索 Reflection、依 `market_regime` 調整權重、解決意見衝突，最後輸出 `portfolio_decisions`。
5. 所有產物（Agent 輸出、工具呼叫、來源連結）皆保存以供稽核與後續檢索。

## 8. 最小可行實作計畫（階段）
- Phase 1（1–2 週）：Coordinator 與 Agent stub、示範 CLI。將輸出儲為 JSON 檔，並新增觸發與查詢的 API。
- Phase 2（2–3 週）：接入真實 Agent 實作（使用 `dataflows/*`），整合 Qdrant，完成 Critic 的 Reflection 儲存與檢索。
- Phase 3（2 週）：實作 Portfolio Manager 邏輯、部位大小計算、執行報告與基本測試。

## 9. 風險與緩解措施
- Agent 幻覺風險：限制 News Agent 回傳 `source_links` 並要求證據；Critic 將標註無依據的主張。
- 向量庫不可用：實作 JSONL 備援以確保反思不遺失。

## 10. 下一步 / 交付項目
- 撰寫 `docs/architecture.md`（包含序列圖，後續執行）。
- 實作 Coordinator API 與示範腳本 `backend/scripts/run_rebalance.py`。
- 新增示範執行的 notebook 或 CLI，展示使用快取資料的端到端流程。

---
依據專案 README 與 Agent 設計說明產生。