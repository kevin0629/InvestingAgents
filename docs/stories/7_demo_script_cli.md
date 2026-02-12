# 7. 最小示範腳本與 CLI

- As: 開發者 / 測試者
- I want: 一個示範腳本（backend/scripts/run_rebalance.py）或 CLI，可執行端到端流程（stub）
- So that: 團隊可以快速驗證整體流程與文件範例

## Acceptance Criteria
- `run_rebalance.py` 能接受本地 sample holdings，執行完整 stub 流程並輸出 `portfolio_decisions.json`。
- CLI 提供 `--sample`、`--task-id` 與 `--dry-run` 等參數。

## Tasks
- 新增 `backend/scripts/run_rebalance.py` 範例（或 CLI 命令）
- 整合 Agent stubs 與 Coordinator 呼叫
- 撰寫 README 範例命令

## Labels
- epic:demos
- phase:1
