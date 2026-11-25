from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date, datetime

class StockChartQueryParams(BaseModel):
    timeframe: Literal["D", "W", "M"] = Field("D", description="時間週期 (D=日線, W=週線, M=月線)")
    end_date: Optional[date] = Field(None, description="結束日期 (YYYY-MM-DD)")


class StockResponse(BaseModel):
    date: datetime = Field(..., description="日期")
    open: float = Field(..., description="開盤價")
    high: float = Field(None, description="最高價")
    low: float = Field(None, description="最低價")
    close: float = Field(..., description="收盤價")
    volume: int = Field(..., description="成交量")

class StockListResponse(BaseModel):
    data: list[StockResponse] = Field(..., description="股價列表")
