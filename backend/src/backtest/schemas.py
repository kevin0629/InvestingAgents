from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date


class StrategyInfo(BaseModel):
    """策略資訊"""
    name: str = Field(..., description="策略名稱")
    description: str = Field(..., description="策略描述")
    parameters: Optional[Dict[str, Any]] = Field(None, description="策略參數")


class StrategyListResponse(BaseModel):
    """策略列表回應"""
    strategies: List[StrategyInfo] = Field(..., description="策略列表")


class HoldingInfo(BaseModel):
    """持股資訊"""
    stock_id: str = Field(..., description="股票代碼")
    position: Optional[float] = Field(None, description="權重")
    entry_sig_date: Optional[str] = Field(None, description="進場訊號日期")


class PerformanceMetrics(BaseModel):
    """績效指標"""
    annualized_rate_of_return: float = Field(..., description="年化報酬率(%)")
    sharpe: Optional[float] = Field(None, description="夏普比率")
    alpha: Optional[float] = Field(None, description="Alpha值")
    beta: Optional[float] = Field(None, description="Beta值")
    max_drawdown: Optional[float] = Field(None, description="最大回撤(%)")
    avg_holdings: Optional[float] = Field(None, description="平均持股數量")
    max_holdings: Optional[int] = Field(None, description="最大持股數量")
    win_ratio: Optional[float] = Field(None, description="勝率(%)")


class BacktestReportResponse(BaseModel):
    """回測報告回應"""
    strategy_name: str = Field(..., description="策略名稱")
    strategy_description: str = Field(..., description="策略描述")
    performance: PerformanceMetrics = Field(..., description="績效指標")
    previous_period_return: str = Field(..., description="上一期加權報酬率")
    current_holdings: List[HoldingInfo] = Field(..., description="當前持股列表")
    message: Optional[str] = Field(None, description="附加訊息")


class BacktestSimResponse(BaseModel):
    """自定義持股回測回應"""
    performance: PerformanceMetrics = Field(..., description="此次模擬持股績效")
    holdings_performance: List[Dict[str, Any]] = Field(
        ..., description="模擬持股績效明細"
    )
    message: Optional[str] = Field(None, description="附加訊息")


class MarketReturnResponse(BaseModel):
    """大盤績效回應"""
    entry_sig_date: str = Field(..., description="進場訊號日期")
    exit_sig_date: str = Field(..., description="出場訊號日期")
    entry_trade_date: str = Field(..., description="進場實際交易日(訊號日後第一個交易日)")
    exit_trade_date: Optional[str] = Field(None, description="出場實際交易日(訊號日後第一個交易日)")
    entry_price: float = Field(..., description="進場價格")
    exit_price: Optional[float] = Field(None, description="出場價格")
    market_return: str = Field(..., description="大盤報酬率")
    message: Optional[str] = Field(None, description="附加訊息")

