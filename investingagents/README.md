## Prerequisite
### Docker Desktop
為了方便後續部屬相關應用，必須安裝 Docker Desktop，按[官方文件](https://docs.docker.com/desktop/setup/install/windows-install/)操作即可完成安裝步驟

### Qdrant
1. Clone Qdrant
   ```
   git clone https://github.com/qdrant/qdrant.git
   ```
2. 使用 CMD 或 powershell 到 clone 下來的目錄位置，執行以下指令: 
   ```
   docker volume create qdrant_storage
   docker run -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage qdrant/qdrant
   ```

### Langfuse
1. Clone Langfuse
2. 使用 CMD 或 powershell 到 clone 下來的目錄位置，執行以下指令: 
   ```
   docker compose up
   ```

## Installation
創建虛擬環境:
```
uv venv --python 3.11
.\.venv\Scripts\activate
```

安裝套件和相依項:
```
uv sync
```

## Setting Env
1. 複製環境變數範例
   ```
   cp .env.example .env
   ```
2. 將會使用到的 LLM 或 Embedding 供應商的 Key 填入環境變數
   > 如本實驗使用 OpenAI 作為 LLM 供應商，使用 Google 作為 Embedding 模型供應商，故要填入`OPENAI_API_KEY`、`GOOGLE_API_KEY`

   > 使用 Google 作為 Embedding 模型的原因：免費，且每天用量已足夠做使用。支持每分鐘 **100** requests， 每分鐘 30K input tokens，每天 **1000** requests
3. 填入 Langfuse 相關變數（`LANGFUSE_BASE_URL`、`LANGFUSE_SECRET_KEY`、`LANGFUSE_PUBLIC_KEY`）
4. 填入 Qdrant 環境變數（`QDRANT_URL`）
5. 填入 backent 環境變數（`BACKEND_API_URL`）


## Run
使用下面的指令來運作：
```
langgraph dev
```

## 程式架構說明

### 根目錄
- `default_config.py`：系統預設設定集中位置
- `langgraph.json`：LangGraph 執行與圖流程相關設定
- `agents/`：多代理核心邏輯與角色實作
- `embedding_clients/`：Embedding 模型供應商的封裝與驗證
- `llm_clients/`：LLM 供應商的封裝與驗證
- `graph/`：投資流程圖（Graph）定義與組裝入口
- `tools/`：代理可呼叫的功能工具（行情、新聞、回測、交易等）
- `results/`：策略執行與組合輸出的結果資料

### agents/
- `analysts/`：分析型代理，負責資料解讀與觀點產出
- `critic/`：檢核型代理，負責審查與反思
- `orchestrator/`：流程協調代理，負責多代理任務分派
- `trader/`：交易型代理，負責下單與決策行為
- `agent_states.py`、`agent_output_formats.py`：代理共用狀態與輸出格式定義
- `utils.py`：代理層共用工具函式

### embedding_clients/
- `base_client.py`：Embedding 客戶端抽象介面
- `google_client.py`、`openai_client.py`：不同供應商實作
- `factory.py`：依設定建立對應客戶端
- `validators.py`：參數與資料格式檢查

### llm_clients/
- `base_client.py`：LLM 客戶端抽象介面
- `anthropic_client.py`、`google_client.py`、`openai_client.py`：供應商實作
- `factory.py`：依設定建立對應客戶端
- `validators.py`：請求參數與設定驗證

### graph/
- `investing_graph.py`：投資主流程圖定義
- `langgraph_dev.py`：開發模式下的圖流程組裝或測試入口
- `setup.py`：圖流程初始化與共用設定

### tools/
- `stock_data_tools.py`、`fundamental_data_tools.py`、`news_data_tools.py`：資料來源工具
- `backtest_tools.py`、`trading_tools.py`：策略回測與交易執行工具
- `reflection_data_tools.py`：反思與檢討流程用資料工具
- `account_utils.py`、`utils.py`、`config.py`：工具層共用設定與輔助函式