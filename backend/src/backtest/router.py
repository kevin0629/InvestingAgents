from fastapi import APIRouter, HTTPException, Query
from src.backtest.schemas import (
    BacktestReportResponse,
    StrategyListResponse,
    StrategyInfo
)
from src.backtest.service import BacktestService
from typing import Optional, Dict, Any
from src.utils import get_data_instance

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.get("/report", response_model=BacktestReportResponse)
async def get_backtest_report(
    strategy_name: str = Query(..., description="策略名稱"),
    end_date: Optional[str] = Query(None, description="回測結束日期 (YYYY-MM-DD)"),
):
    """
    以指定的策略做回測，回傳策略績效報告、這一期持股、換股的清單
    
    - **strategy_name**: 策略名稱 (revenue_growth_roe)
    - **end_date**: 回測結束日期，格式: YYYY-MM-DD，不提供則為今天
    
    回傳內容包括：
    - 策略績效指標（年化報酬率、夏普比率、Alpha、Beta、最大回撤等）
    - 當前持股列表（股票代碼、名稱、股數、權重、市值）
    - 近期交易記錄（進出場日期、報酬率、最大不利偏移等詳細交易資訊）
    """
    try:
        data = get_data_instance()
        service = BacktestService(data)
        
        # 執行回測
        report = service.run_backtest(
            strategy_name=strategy_name,
            end_date=end_date,
        )
        
        return report
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"Error in get_backtest_report: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/strategy", response_model=StrategyListResponse)
async def get_strategy():
    """
    回傳所有已知的策略與其描述
    
    回傳所有可用的量化策略列表，包括：
    - 策略名稱
    - 策略描述
    - 預設參數
    """
    try:
        data = get_data_instance()
        service = BacktestService(data)
        strategies = service.get_strategy_list()
        
        return StrategyListResponse(strategies=strategies)
    
    except Exception as e:
        print(f"Error in get_strategy: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


