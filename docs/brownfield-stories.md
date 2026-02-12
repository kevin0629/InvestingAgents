# Brownfield MVP — User Stories

以下 user stories 嚴格根據 `docs/brownfield-epics.md` 撰寫，對應 PRD 的三個階段（Phase 1–3）。每則 story 包含簡短描述與驗收準則。

1) Coordinator: 啟動與任務分派
- As: 開發者（Coordinator 服務）
- I want: 透過 API 或 CLI 提交 `Holdings` 與 `mode` 並啟動月度再平衡任務
- So that: 系統能建立任務、判定 `market_regime` 並產生 `Candidates` 與 ANALYSIS/VERIFICATION 任務
- Acceptance Criteria:
  - API/CLI 接受 JSON 格式的 `Holdings` 與 `mode`，回傳任務 ID 與狀態。
  - Coordinator 能產生 `Candidates` JSON 並將任務分派給 Agent（或 stub）。

2) Agent Stubs: 結構化回應
- As: 開發者
- I want: 為 Financial/Technical/News Agent 提供可運行的 stub/wrapper
- So that: Coordinator 可對 N 檔候選股並行發出分析請求並取得結構化 JSON 回應
- Acceptance Criteria:
  - 每個 Agent stub 接受規定輸入並回傳 README 指定格式的 JSON。
  - Agent 回傳包含 chain-of-thought、tool_calls、source_links（News Agent）。

3) Critic: 產生 Reflection 並儲存（Qdrant）
- As: 開發者
- I want: Critic 能整合 Verification Reports，產生 `Reflection` 並寫入向量庫
- So that: Reflection 可被檢索供 Portfolio Manager 與稽核使用
- Acceptance Criteria:
  - Critic 接收 Agent 的 verification reports，輸出 Reflection JSON。
  - Reflection 成功寫入 Qdrant。

4) Portfolio Manager: 組合決策輸出
- As: Portfolio Manager 開發者
- I want: 檢索 Reflection 並根據 `market_regime` 調整權重與解決衝突
- So that: 最終能輸出符合規格的 `portfolio_decisions` JSON 與執行報告
- Acceptance Criteria:
  - Portfolio Manager 產出 `portfolio_decisions` JSON（含每檔權重與理由）。
  - 輸出包含引用的 Agent outputs 與 Reflection ID，可供稽核追溯。

5) Dataflows 改寫與路由
- As: 資料工程師
- I want: 改寫 `dataflows/*` 並採用 PRD 指定的替代路由（Tavily、backend routers）
- So that: Agent 能存取一致且可測試的價格、基本面與新聞來源
- Acceptance Criteria:
  - `dataflows` 提供統一接口供 Agent 呼叫，且至少以 mock 回傳可測的範例資料。
  - 新路由已文件化並在 README 中說明依賴與用法。

6) 可觀察性與稽核輸出
- As: 審計 / 研究者
- I want: 每次執行保存 Agent 輸出、工具呼叫、來源連結與 Critic Reflection
- So that: 可檢索 chain-of-thought 與來源以供檢驗與回溯
- Acceptance Criteria:
  - 每次執行產生可搜尋的執行包（JSON 或 DB 記錄），包含所有 Agent outputs 與工具使用紀錄。

7) 最小示範腳本與 CLI
- As: 開發者 / 測試者
- I want: 一個示範腳本（`backend/scripts/run_rebalance.py`）或 CLI，可執行端到端流程（stub）
- So that: 團隊可以快速驗證整體流程與文件範例
- Acceptance Criteria:
  - `run_rebalance.py` 能接受本地 sample holdings，執行完整 stub 流程並輸出 `portfolio_decisions.json`。

8) README 與 API 文件
- As: 開發者 / PM
- I want: 更新 README 與 API 文件說明觸發、查詢、輸出格式與示例
- So that: 開發者與使用者能復現並理解各端點與檔案格式
- Acceptance Criteria:
  - README 包含 API 範例、輸入/輸出 JSON 規格、運行示範命令。

9) 自動化驗證流程（verification_status）
- As: 測試/研究者
- I want: 自動化驗證模組能對既有持股產生 `verification_status`
- So that: 系統能以結構化結果揭示資料或決策的一致性
- Acceptance Criteria:
  - 驗證模組輸出 `verification_status` JSON，並被 Critic 與 Portfolio Manager 使用。

10) Phase-based Implementation Stories
- Phase 1 stories: 1,2,7,8（Coordinator API/CLI、Agent stubs、示範腳本、README）。
- Phase 2 stories: 3,5,6（Critic + Qdrant、dataflows 改寫、可觀察性）。
- Phase 3 stories: 4,9（Portfolio Manager 最終實作、驗證流程）。

---
如需我將上述每則 story 轉成 GitHub issue（含 labels、估時），我可以繼續建立。若需要調整 granularity 或語言（中文 / English），請告訴我。
