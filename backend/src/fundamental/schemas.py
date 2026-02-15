from pydantic import BaseModel, Field
from typing import Dict, Optional


class IndicatorResponse(BaseModel):
    """
    財報資料回應
    結構: 財報資料名稱 -> 時間區段 -> 數值列表
    """
    data: Dict[str, Dict[str, Optional[float]]] = Field(
        ..., 
        description="財報資料",
        example={
            "現金及約當現金": {
                "2023Q1": 15.5,
                "2023Q2": 16.2
            },
            "短期投資": {
                "2023Q1": 5.0,
                "2023Q2": 4.8
            }
        }
    )