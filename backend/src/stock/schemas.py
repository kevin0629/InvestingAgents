from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

class StockChartQueryParams(BaseModel):
    end_date: Optional[date] = Field(None, description="結束日期 (YYYY-MM-DD)")
    timeframe: Optional[str] = Field("D", description="時間週期 (D=日線, W=週線, M=月線)")
