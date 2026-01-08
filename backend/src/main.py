from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import Config


config = Config()

app = FastAPI(title="BacktestSystem API", version=config.APP_VERSION, description="回測系統 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=config.CORS_CREDENTIALS,
    allow_methods=config.CORS_METHODS,  # 允許所有 HTTP 方法
    allow_headers=config.CORS_HEADERS,  # 允許所有 headers
)


@app.get("/")
async def root():
    """根路徑，返回 API 基本資訊"""
    return {"message": "BacktestSystem API is running"}