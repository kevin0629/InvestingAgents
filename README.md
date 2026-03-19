## Qdrant 使用方法
1. 自 github 上 clone 下來 `git clone https://github.com/qdrant/qdrant.git`
2. 使用 CMD 或 powershell 到 clone 下來的目錄位置，執行以下指令: 
   - `docker volume create qdrant_storage`
   - `docker run -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage qdrant/qdrant`