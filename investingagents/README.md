## Qdrant 使用方法
1. 自 github 上 clone 下來 `git clone https://github.com/qdrant/qdrant.git`
2. 使用 CMD 或 powershell 到 clone 下來的目錄位置，執行以下指令: 
   - `docker volume create qdrant_storage`
   - `docker run -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage qdrant/qdrant`


## Langfuse 使用方法
1. 自 github 上 clone 下來
2. 將 `LANGFUSE_S3_BATCH_EXPORT_ENABLED` 改為 `true`，這一步務必要做才能匯出
3. 使用 CMD 或 powershell 到 clone 下來的目錄位置，執行 `docker compose up`
4. 獲取資料方法
   > `python get_langfuse_data.py --username "public_key" --password "private_key" --output langfuse_observations.json` <br>
   但最多只能抓 100 筆...
5. 定期備份 docker clickhouse 內容，traces、observations 都存在其中!
   > `/var/lib/postgresql/data`
     可以從 `http://127.0.0.1:8123/` 去看，帳號密碼都是 clickhouse
     `select * from default.observations;` 為查詢語句


## 使用 Gemini Embedding API
因為免費，且每天用量已足夠做研究使用
> 支持每分鐘 **100** requests， 每分鐘 30K input tokens，每天 **1000** requests

## Investingagents 使用方法
1. 輸入策略以及截止日期，截止日期務必是進場訊號的日期!