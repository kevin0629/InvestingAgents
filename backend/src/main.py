from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import Config
from src.company.router import router as company_router
from src.factor.router import router as factor_router
from src.fundamental.router import router as fundamental_router
from src.stock.router import router as stock_router
from src.backtest.router import router as backtest_router
from src.news.router import router as news_router
from src.utils import get_data_instance



config = Config()
data = get_data_instance()  # 預先載入 Data 實例，確保在啟動時就有資料可用

app = FastAPI(title="BacktestSystem API", version=config.APP_VERSION, description="回測系統 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=config.CORS_CREDENTIALS,
    allow_methods=config.CORS_METHODS,  # 允許所有 HTTP 方法
    allow_headers=config.CORS_HEADERS,  # 允許所有 headers
)

app.include_router(company_router)
app.include_router(factor_router)
app.include_router(fundamental_router)
app.include_router(stock_router)
app.include_router(backtest_router)
app.include_router(news_router)

# 啟動 Web: uvicorn src.main:app --reload
@app.get("/")
async def root():
    """根路徑，返回 API 基本資訊"""
    return {"message": "BacktestSystem API is running"}