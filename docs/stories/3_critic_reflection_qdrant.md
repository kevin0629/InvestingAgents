# 3. Critic: 產生 Reflection 並儲存（Qdrant）

- As: 開發者
- I want: Critic 能整合 Verification Reports，產生 `Reflection` 並寫入向量庫
- So that: Reflection 可被檢索供 Portfolio Manager 與稽核使用

## Acceptance Criteria
- Critic 接收 Agent 的 verification reports，輸出 Reflection JSON。
- Reflection 成功寫入 Qdrant 並可依向量檢索回傳相關 Reflection IDs。
- Reflection JSON 包含來源引用（Agent outputs, verification_status）與摘要。

## Tasks
- 定義 Reflection 結構與向量化流程
- 實作寫入與檢索 Qdrant 的封裝
- 提供示範檢索與單元測試

## Labels
- epic:critic
- phase:2
