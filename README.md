## Qdrant 使用方法
1. 自 github 上 clone 下來 `git clone https://github.com/qdrant/qdrant.git`
2. 使用 CMD 或 powershell 到 clone 下來的目錄位置，執行以下指令: 
   - `docker volume create qdrant_storage`
   - `docker run -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage qdrant/qdrant`


## Langfuse 使用方法
1. 自 github 上 clone 下來
2. 將 `LANGFUSE_S3_BATCH_EXPORT_ENABLED` 改為 `true`，這一步務必要做才能匯出
3. 使用 CMD 或 powershell 到 clone 下來的目錄位置，執行 `docker compose up`


## 使用 Gemini Embedding API
因為免費，且每天用量已足夠做研究使用
> 支持每分鐘 **100** requests， 每分鐘 30K input tokens，每天 **1000** requests