from pydantic import BaseModel, Field

class FinancialData(BaseModel):
    """財務指標模型"""
    report_period: str = Field(..., description="資料日期")
    factor: float = Field(..., description="財務指標值")


class FinancialDataResponse(BaseModel):
    """財務指標回應"""
    financial_data: list[FinancialData] = Field(..., description="財務指標資料列表")


class DuPontAnalysisResponse(BaseModel):
    """杜邦分析回應"""
    report_period: str = Field(..., description="資料日期")
    return_on_equity: float = Field(..., description="股東權益報酬率 (ROE)")
    net_profit_margin: float = Field(..., description="淨利率")
    asset_turnover: float = Field(..., description="總資產週轉率")
    financial_leverage: float = Field(..., description="財務槓桿")