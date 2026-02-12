# 5. Dataflows 改寫與路由

- As: 資料工程師
- I want: 改寫 `dataflows/*` 並採用 PRD 指定的替代路由（Tavily、backend routers）
- So that: Agent 能存取一致且可測試的價格、基本面與新聞來源

## Acceptance Criteria
- `dataflows` 提供統一接口供 Agent 呼叫，且至少以 mock 回傳可測的範例資料。
- 新路由已文件化並在 README 中說明依賴與用法。

## Tasks
- 審視目前 `dataflows` 模組並抽出公共介面
- 實作替代路由與 mock 資料源
- 撰寫使用說明與整合測試

## Labels
- epic:dataflows
- phase:2
