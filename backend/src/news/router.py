from fastapi import APIRouter, HTTPException
from typing import Optional
from src.news.schemas import NewsListResponse
from src.news.service import NewsService

router = APIRouter(prefix="/news", tags=["news"])

@router.get("/macro", response_model=NewsListResponse)
async def get_macro_news(
    end_date: Optional[str] = None, 
    look_back_days: int = 7,
    limit: int = 100,
):
    service = NewsService()
    try:
        data = await service.get_macro_news(end_date, look_back_days, limit)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return NewsListResponse(
        news_data=data,
        message="查不到新聞" if not data else None
    )

@router.get("/{company_symbol}", response_model=NewsListResponse)
async def get_company_news(
    company_symbol: str, 
    end_date: Optional[str] = None, 
    look_back_days: Optional[int] = None,
    limit: int = 10,
):
    service = NewsService()
    try:
        data = await service.get_company_news(company_symbol, end_date, look_back_days, limit)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid end_date format")

    return NewsListResponse(
        news_data=data,
        message="查不到新聞" if not data else None
    )