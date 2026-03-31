from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    """新聞資料項目"""
    model_config = {"from_attributes": True}
    id: str = Field(..., description="新聞 ID")
    title: str = Field(..., description="新聞標題")
    content: str = Field(..., description="新聞內容")
    published_at: datetime = Field(..., description="發布時間")
    link: str = Field(..., description="新聞連結")
    company_symbol: Optional[str] = Field(None, description="公司股票代號")


class NewsListResponse(BaseModel):
    """新聞列表回應"""
    news_data: List[NewsItem] = Field(..., description="新聞列表")