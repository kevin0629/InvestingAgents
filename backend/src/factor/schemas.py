from typing import Dict, List
from pydantic import BaseModel, Field

class FactorResponse(BaseModel):
    """
    因子資料回應
    結構: 群組(quarter/month) -> 因子名稱 -> 時間區段 -> 數值列表
    """
    data: Dict[str, Dict[str, Dict[str, List[float]]]] = Field(
        ..., 
        description="分組後的因子資料",
        example={
            "quarter": {
                "ROE": {
                    "2023Q1": [15.5],
                    "2023Q2": [16.2]
                }
            },
            "month": {
                "Revenue": {
                    "2023/01": [1000.0]
                }
            }
        }
    )
