from typing import Dict, List
from pydantic import BaseModel, Field

class FactorResponse(BaseModel):
    """
    因子資料回應
    結構: 因子名稱 -> 時間區段 -> 數值
    """
    data: Dict[str, Dict[str, float]] = Field(
        ..., 
        description="因子資料",
        example={
            "ROE": {
                "2023Q1": 15.5,
                "2023Q2": 16.2
            },
            "Revenue": {
                "2023/01": 1000.0
            }
        }
    )


class DuPontPeriodData(BaseModel):
    """單一期間的杜邦分析數據"""
    period: str = Field(..., description="期間 (例: 2025Q4)")
    formula: str = Field(..., description="杜邦公式字串")


class DuPontAnalysisResponse(BaseModel):
    """杜邦分析回應"""
    dupont_analysis: List[DuPontPeriodData] = Field(..., description="各期間的杜邦分析數據列表")