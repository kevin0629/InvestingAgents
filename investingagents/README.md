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
   > 如本實驗使用 OpenAI 作為 LLM 模型供應商，使用 Google 作為 Embedding 模型供應商，故要填入`OPENAI_API_KEY`、`GOOGLE_API_KEY`

   > 使用 Google 作為 Embedding 模型的原因：免費，且每天用量已足夠做使用。支持每分鐘 **100** requests， 每分鐘 30K input tokens，每天 **1000** requests
3. 填入 Langfuse 相關變數（`LANGFUSE_BASE_URL`、`LANGFUSE_SECRET_KEY`、`LANGFUSE_PUBLIC_KEY`）
4. 填入 Qdrant 環境變數（`QDRANT_URL`）
5. 填入 backent 環境變數（`BACKEND_API_URL`）


## Run
使用下面的指令來運作：
```
langgraph dev
```